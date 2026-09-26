"""Independent answer keys, recomputed from raw frames and dispatch outcomes (revision 2).

Deliberately imports nothing: shown entries are rebuilt from the raw events (the stored continuous
trajectories for synthetic contexts, archived engine steps for real ones), frames are decoded and
cell changes recounted here, trajectory continuity is re-checked here, and each question is
answered by separate logic. Agreement with the primary keys shows the answers do not depend on how
the history field was constructed.
"""
LIMIT = 4  # the live history arm's entry limit
STATUS = {'dispatch_failed': 'dispatch_failed', 'outcome_unknown': 'outcome_unknown'}


def decode(text):
    size, cells = text.split(':')
    height, width = (int(v) for v in size.split('x'))
    if len(cells) != height * width:
        raise ValueError('frame size')
    return [[int(cells[y * width + x], 16) for x in range(width)] for y in range(height)]


def cells_differ(before, after):
    if len(before) != len(after) or any(len(a) != len(b) for a, b in zip(before, after)):
        return None
    return sum(1 for y in range(len(before)) for x in range(len(before[0])) if before[y][x] != after[y][x])


def raw_entry(step, action, status, before=None, returned=None):
    if status != 'acknowledged':
        return {'step': step, 'action': action, 'kind': status}
    counts = [cells_differ(before, frame) for frame in returned]
    moved = [c is None or c != 0 for c in counts]
    kind = ('final_frame_changed' if moved[-1] else 'changed_then_returned' if True in moved
            else 'acknowledged_no_change')
    return {'step': step, 'action': action, 'kind': kind, 'dimension_change': None in counts}


def check_continuity(context):
    """Each event must start from the frame the previous event left current (independent re-check)."""
    events = context['events']
    for i, event in enumerate(events):
        following = events[i + 1]['pre'] if i + 1 < len(events) else context['final']
        if event['kind'] == 'dispatch_failed':
            if event['pre'] != following:
                raise ValueError(f'{context["context_id"]}: failed dispatch changed the frame')
        elif event['kind'] != 'outcome_unknown':
            if decode(event['returned'][-1]) != decode(following):
                raise ValueError(f'{context["context_id"]}: discontinuous trajectory at event {i}')


def synthetic_entries(context):
    check_continuity(context)
    rows = [raw_entry(step, event['action'], STATUS.get(event['kind'], 'acknowledged'), decode(event['pre']),
                      [decode(f) for f in event.get('returned', [])])
            for step, event in enumerate(context['events'])]
    return rows[-LIMIT:], len(rows) - len(rows[-LIMIT:])


def archived_entries(episode, decision):
    """Entries the history arm was shown before decision `decision`, rebuilt from archived engine steps."""
    rows = []
    steps = episode['steps'][:decision]
    for i, step in enumerate(steps):
        if step['after']['levels_completed'] != step['before']['levels_completed'] or step['after'].get('full_reset'):
            raise ValueError('real contexts must stay within one segment')
        if i + 1 < len(steps) and steps[i + 1]['before']['frames'][-1] != step['after']['frames'][-1]:
            raise ValueError('archived trajectory is discontinuous')
        rows.append(raw_entry(step['index'], step['action'], step['status'],
                              step['before']['frames'][-1], step['after']['frames']))
    return rows[-LIMIT:], len(rows) - len(rows[-LIMIT:])


def same(a, b):
    return a['action_id'] == b['action_id'] and a['action_data'] == b['action_data']


def answer(entries, legal, family, arg):
    by_step = {row['step']: row for row in entries}
    if family == 'available_actions':
        return sorted(set(legal))
    if family == 'coordinate_actions':
        return [i for i in sorted(set(legal)) if i == 6]
    if family in ('recall_action', 'outcome_class'):
        row = (entries[-1] if entries else None) if arg == 'latest' else by_step.get(arg)
        if row is None:
            return 'not_shown'
        if family == 'outcome_class':
            return row['kind']
        return {'action_id': row['action']['action_id'], 'action_data': dict(row['action']['action_data'])}
    if family == 'observed_effect':
        for row in reversed(entries):
            if same(row['action'], arg):
                return row['kind']
        return 'not_observed'
    if family == 'tried_unchanged':
        # Scan forward: a frame change or unknown outcome resets the set of actions tried on the current frame.
        current = []
        for row in entries:
            if row['kind'] in ('final_frame_changed', 'outcome_unknown'):
                current = []
            elif row['kind'] in ('acknowledged_no_change', 'changed_then_returned'):
                action = {'action_id': row['action']['action_id'], 'action_data': dict(row['action']['action_data'])}
                current = [a for a in current if not same(a, action)] + [action]
        return current
    raise ValueError(family)
