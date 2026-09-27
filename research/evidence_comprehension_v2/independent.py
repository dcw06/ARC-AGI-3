"""Independent answer keys for evidence comprehension v2, from raw frames and dispatch outcomes.

Deliberately imports nothing. Shown entries are rebuilt from raw events (stored synthetic trajectories, or
archived engine steps): frames are decoded and compared here, the reset/level-change segment boundary and
the four-entry window are applied here, continuity is re-checked here, and every question is answered by
separate logic. Agreement with the primary keys shows the keys do not depend on the record code or the
history field that produced the prompt.
"""
LIMIT = 4  # the live history field's entry limit


def decode(text):
    size, cells = text.split(':')
    height, width = (int(v) for v in size.split('x'))
    if len(cells) != height * width:
        raise ValueError('frame size')
    return [[int(cells[y * width + x], 16) for x in range(width)] for y in range(height)]


def differs(before, after):
    if len(before) != len(after) or any(len(a) != len(b) for a, b in zip(before, after)):
        return True
    return any(before[y][x] != after[y][x] for y in range(len(before)) for x in range(len(before[0])))


def resolve(packed, frames):
    """A stored trajectory with its frame references replaced by the frames themselves."""
    events = [{**e, 'pre': frames[e['pre']], **({'returned': [frames[f] for f in e['returned']]} if 'returned' in e else {})}
              for e in packed['events']]
    return {**packed, 'events': events, 'final': frames[packed['final']]}


def row(step, action, status, before=None, returned=None, boundary=False):
    """One raw entry: `moved` lists, per returned frame, whether it differs from the frame before the action."""
    if status != 'acknowledged':
        return {'step': step, 'action': action, 'status': status, 'moved': None, 'boundary': False}
    return {'step': step, 'action': action, 'status': status, 'boundary': boundary,
            'moved': [differs(before, frame) for frame in returned]}


def check_continuity(context):
    events = context['events']
    for i, event in enumerate(events):
        following = events[i + 1]['pre'] if i + 1 < len(events) else context['final']
        if event['kind'] == 'dispatch_failed':
            if event['pre'] != following:
                raise ValueError(f'{context["context_id"]}: failed dispatch changed the frame')
        elif event['kind'] != 'outcome_unknown':
            if decode(event['returned'][-1]) != decode(following):
                raise ValueError(f'{context["context_id"]}: discontinuous trajectory at event {i}')


def window(rows):
    """Rows after the last reset or level change, most recent LIMIT; (shown, omitted count, all steps)."""
    start = 0
    for i, r in enumerate(rows):
        if r['boundary']:
            start = i + 1
    current = rows[start:]
    shown = current[-LIMIT:] if current else []
    return shown, len(current) - len(shown), [r['step'] for r in rows]


def synthetic_rows(context):
    check_continuity(context)
    rows = []
    for step, event in enumerate(context['events']):
        status = event['kind'] if event['kind'] in ('dispatch_failed', 'outcome_unknown') else 'acknowledged'
        boundary = status == 'acknowledged' and (event['levels_after'] != event['levels_before'] or event['full_reset'])
        rows.append(row(step, event['action'], status, decode(event['pre']),
                        [decode(f) for f in event.get('returned', [])], boundary))
    return rows


def archived_rows(episode, decision):
    rows = []
    steps = episode['steps'][:decision]
    for i, step in enumerate(steps):
        if i + 1 < len(steps) and steps[i + 1]['before']['frames'][-1] != step['after']['frames'][-1]:
            raise ValueError('archived trajectory is discontinuous')
        boundary = (step['status'] == 'acknowledged' and (step['after']['levels_completed']
                    != step['before']['levels_completed'] or step['after'].get('full_reset') is True))
        rows.append(row(step['index'], step['action'], step['status'], step['before']['frames'][-1],
                        step['after']['frames'], boundary))
    return rows


def same(a, b):
    return a['action_id'] == b['action_id'] and a['action_data'] == b['action_data']


def kind(r):
    if r['status'] != 'acknowledged':
        return r['status']
    if r['moved'][-1]:
        return 'final_frame_changed'
    return 'changed_then_returned' if any(r['moved']) else 'acknowledged_no_change'


def still_current(shown):
    """Rows whose action left the still-current frame unchanged: scanning forward, a final change or an unknown
    outcome clears the set; a failed dispatch neither joins nor clears it."""
    current = []
    for r in shown:
        k = kind(r)
        if k in ('final_frame_changed', 'outcome_unknown'):
            current = []
        elif k in ('acknowledged_no_change', 'changed_then_returned'):
            current.append(r)
    return current


def answer(shown, legal, family, arg):
    by_step = {r['step']: r for r in shown}
    if family == 'legal_actions':
        return sorted(set(legal))
    if family == 'action6_legal':
        return 'yes' if 6 in set(legal) else 'no'
    if family == 'coordinate_rule':
        return [6]
    if family == 'legal_coordinate_actions':
        return [i for i in sorted(set(legal)) if i == 6]
    if family == 'step_action_match':
        r = by_step.get(arg['step'])
        return 'not_shown' if r is None else ('yes' if same(r['action'], arg['action']) else 'no')
    if family == 'observed_effect':
        for r in reversed(shown):
            if same(r['action'], arg):
                return kind(r)
        return 'not_observed'
    if family == 'qualifying_steps':
        return [r['step'] for r in still_current(shown)]
    if family == 'tried_unchanged':
        actions = []
        for r in still_current(shown):
            action = {'action_id': r['action']['action_id'], 'action_data': dict(r['action']['action_data'])}
            if not any(same(a, action) for a in actions):
                actions.append(action)
        return actions
    r = by_step.get(arg)
    if r is None:
        return 'not_shown'
    if family == 'dispatch_status':
        return r['status']
    if family == 'outcome_class':
        return kind(r)
    if family == 'frame_since_step':
        later = [x for x in shown if x['step'] >= arg]
        if any(x['status'] == 'acknowledged' and x['moved'][-1] for x in later):
            return 'changed_at_least_once'
        return 'cannot_tell' if any(x['status'] == 'outcome_unknown' for x in later) else 'stayed_same'
    if r['status'] != 'acknowledged':
        return 'not_observed'
    if family == 'any_change':
        return 'yes' if any(r['moved']) else 'no'
    if family == 'final_equals_pre':
        return 'no' if r['moved'][-1] else 'yes'
    raise ValueError(family)
