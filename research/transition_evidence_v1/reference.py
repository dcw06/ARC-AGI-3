"""Independent reference for transition evidence (imports nothing).

A second implementation of the headline facts, written without transition.py or vocabulary.py. It flattens frames
into (height, width, tuple-of-cells) and compares those; it re-derives availability, visual effect, per-frame counts,
environment events, progress, segments and continuity by separate logic. Agreement with transition.py shows the
facts do not depend on one implementation.
"""


def flat(grid):
    """(height, width, cells) for a valid frame; None for anything else."""
    if not isinstance(grid, list) or not grid or not all(isinstance(r, list) and r for r in grid):
        return None
    width = len(grid[0])
    if any(len(r) != width for r in grid):
        return None
    cells = tuple(v for r in grid for v in r)
    if any(type(v) is not int or v < 0 or v > 15 for v in cells):
        return None
    return len(grid), width, cells


def diff_count(a, b):
    if a[0] != b[0] or a[1] != b[1]:
        return None
    return sum(1 for p, q in zip(a[2], b[2]) if p != q)


def facts(raw):
    status = raw['outcome']['status']
    pre = flat(raw['before']['frames'][-1])
    if status != 'acknowledged':
        return {'dispatch': status, 'availability': 'not_applicable' if status == 'failed' else 'missing',
                'visual': 'indeterminate', 'vs_pre': [], 'vs_previous': [], 'any_differs': None, 'final_equals': None,
                'events': ['not_observed'], 'progress': 'unknown'}
    after = raw['outcome']['after']
    frames = [flat(g) for g in (after.get('frames') or [])]
    good = [f for f in frames if f is not None]
    vs_pre, vs_previous, last = [], [], pre
    for f in frames:
        if f is None:
            vs_pre.append('invalid')
            vs_previous.append('invalid')
            last = None
            continue
        vs_pre.append(diff_count(pre, f))
        vs_previous.append(diff_count(last, f) if last is not None else 'no_valid_previous')
        last = f
    if not good:
        availability = 'missing'
    elif len(good) < len(frames):
        availability = 'partial'
    else:
        availability = 'complete'
    changed = [c is None or c > 0 for c in vs_pre if c != 'invalid']
    if availability == 'missing':
        any_differs = final_equals = None
    else:
        any_differs = True if any(changed) else (None if availability == 'partial' else False)
        final_equals = None if frames[-1] is None else (vs_pre[-1] == 0)
    if final_equals is None:
        visual = 'indeterminate'
    elif final_equals is False:
        visual = 'final_frame_differs'
    elif any_differs:
        visual = 'changed_then_returned'
    elif any_differs is False:
        visual = 'no_observed_change'
    else:
        visual = 'indeterminate'
    before = raw['before']
    events, progress = [], 'unknown'
    if after['levels_completed'] > before['levels_completed']:
        events.append('level_completed')
        progress = 'confirmed'
    if after['levels_completed'] < before['levels_completed']:
        events.append('level_count_decreased')
    if after.get('state') not in (None, 'NOT_FINISHED'):
        events.append('terminal_state')
        if after.get('state') == 'WIN':
            progress = 'confirmed'
    if after.get('full_reset') is True:
        events.append('reset_acknowledged')
    return {'dispatch': status, 'availability': availability, 'visual': visual, 'vs_pre': vs_pre,
            'vs_previous': vs_previous, 'any_differs': any_differs, 'final_equals': final_equals,
            'events': events or ['none_reported'], 'progress': progress}


def sequence(raws):
    """[(segment, continuity)] per transition, by separate logic."""
    out, segment, prior = [], 0, None
    for raw in raws:
        if prior is not None:
            f = facts(prior)
            if {'reset_acknowledged', 'level_completed', 'level_count_decreased', 'terminal_state'} & set(f['events']):
                segment += 1
                prior = None
        if prior is None:
            continuity = 'first_in_segment'
        else:
            status = prior['outcome']['status']
            if status == 'outcome_unknown':
                continuity = 'gap_after_unknown_outcome'
            else:
                if status == 'failed':
                    last = flat(prior['before']['frames'][-1])
                else:
                    frames = prior['outcome']['after'].get('frames') or []
                    last = flat(frames[-1]) if frames else None
                if last is None:
                    continuity = 'gap_after_missing_observation'
                else:
                    here = flat(raw['before']['frames'][-1])
                    continuity = 'matches_previous_final' if here == last else 'differs_from_previous_final'
        out.append((segment, continuity))
        prior = raw
    return out
