"""Independent reference for progress_subgoal_v1 keys (imports nothing).

A second implementation, written without transition.py, vocabulary.py or subgoal.py. Frames are turned into a
dictionary {(x, y): colour} with their dimensions, and every rule is re-derived by separate logic: visual effect,
progress, the rectangle rule, the gap rule, the effect-hypothesis rule and the subgoal checker. Agreement with the
contract-derived facts (subgoal.py) and with the construction shows that the keys do not depend on one implementation.
"""


def cells(grid):
    """(height, width, {(x, y): colour}) for a valid frame, else None."""
    if not isinstance(grid, list) or not grid:
        return None
    width = len(grid[0]) if isinstance(grid[0], list) else 0
    out = {}
    for y, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != width or width == 0:
            return None
        for x, v in enumerate(row):
            if type(v) is not int or not 0 <= v <= 15:
                return None
            out[(x, y)] = v
    return len(grid), width, out


def returned(raw):
    """The returned frames as parsed cells (None for an invalid one), or None when nothing was observed."""
    if raw['outcome']['status'] != 'acknowledged':
        return None
    return [cells(g) for g in raw['outcome']['after'].get('frames') or []]


def differs_in(a, b, rect):
    """True/False when comparable, None when dimensions differ."""
    if a[0] != b[0] or a[1] != b[1]:
        return None
    x0, y0, w, h = rect
    return any(a[2].get((x, y)) != b[2].get((x, y)) for x in range(x0, x0 + w) for y in range(y0, y0 + h)
               if (x, y) in a[2])


def visual(raw):
    frames = returned(raw)
    if not frames or frames[-1] is None:  # nothing observed, nothing returned, or no valid final frame
        return 'indeterminate'
    pre = cells(raw['before']['frames'][-1])
    change = [f is not None and (f[:2] != pre[:2] or f[2] != pre[2]) for f in frames]
    if change[-1]:
        return 'final_frame_differs'
    if any(change):
        return 'changed_then_returned'
    return 'indeterminate' if any(f is None for f in frames) else 'no_observed_change'


def progress(raw):
    if raw['outcome']['status'] != 'acknowledged':
        return 'unknown'
    a, b = raw['outcome']['after'], raw['before']
    return 'confirmed' if a['levels_completed'] > b['levels_completed'] or a.get('state') == 'WIN' else 'unknown'


def region(raw, rect):
    frames = returned(raw)
    if not frames:
        return 'cannot_tell'
    pre = cells(raw['before']['frames'][-1])
    results = [None if f is None else differs_in(pre, f, rect) for f in frames]
    if True in results:
        return 'yes'
    return 'no' if all(r is False for r in results) else 'cannot_tell'


def last_seen(raw):
    status = raw['outcome']['status']
    if status == 'failed':
        return cells(raw['before']['frames'][-1])
    if status == 'outcome_unknown':
        return None
    frames = returned(raw)
    return frames[-1] if frames else None


def gap(previous, raw, rect):
    last = last_seen(previous)
    if last is None:
        return 'cannot_tell'
    d = differs_in(last, cells(raw['before']['frames'][-1]), rect)
    return 'cannot_tell' if d is None else ('yes' if d else 'no')


def hypothesis(raws, action, rect):
    trials, controls, gaps = [], [], []
    for n, raw in enumerate(raws):
        if n:
            gaps.append(gap(raws[n - 1], raw, rect))
        (trials if raw['dispatched'] == action else controls).append(region(raw, rect))
    if 'no' in trials or 'yes' in controls or 'yes' in gaps:  # an unchanged gap is never a control
        return 'weakened'
    if trials.count('yes') >= 2 and 'no' in controls:
        return 'strengthened'
    return 'insufficient_evidence'


def meets(parsed, test):
    if parsed is None:
        return False
    x0, y0, w, h = test['region_xywh']
    if y0 + h > parsed[0] or x0 + w > parsed[1]:
        return False
    return all(parsed[2][(x, y)] == test['colour'] for x in range(x0, x0 + w) for y in range(y0, y0 + h))


def subgoal(sg, raws):
    """(status, decision) of a subgoal record over a sequence, by separate logic."""
    test = sg['success_test']
    seen = [cells(raw['before']['frames'][-1]) for raw in raws]
    blind = False
    for raw in raws:
        frames = returned(raw)
        if raw['outcome']['status'] == 'failed':
            continue
        if frames is None or not frames or frames[-1] is None:
            blind = True
        else:
            seen.append(frames[-1])
    status = 'achieved' if any(meets(s, test) for s in seen) else ('cannot_tell' if blind else 'not_achieved')
    invalid = False
    for item in sg['invalidation_evidence']:
        if item['kind'] == 'no_region_change_after_attempts':
            hits = sum(1 for raw in raws if raw['dispatched'] == item['action'] and region(raw, item['region_xywh']) == 'no')
            invalid |= hits >= item['attempts']
        if item['kind'] == 'state_reported':
            invalid |= any(raw['outcome']['status'] == 'acknowledged' and raw['outcome']['after'].get('state') ==
                           item['state'] for raw in raws)
    if status == 'achieved':
        decision = 'stop_achieved'
    elif invalid:
        decision = 'abandon_invalidated'
    elif len(raws) >= sg['action_budget']:
        decision = 'abandon_budget_exhausted'
    else:
        decision = 'continue'
    return status, decision
