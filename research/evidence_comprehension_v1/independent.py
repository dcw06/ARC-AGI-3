"""Independent answer keys, recomputed from raw frames and dispatch outcomes.

Deliberately imports neither the record code nor probes.py: shown entries are rebuilt from the raw
events (fixture frames for synthetic contexts, archived engine steps for real ones), cell changes
are recounted, and each question is answered by separate logic. Agreement with the primary keys
shows the answers do not depend on how the history field was constructed.
"""
LIMIT = 4  # the live history arm's entry limit


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


def synthetic_entries(context, fixtures):
    cases = {c['case_id']: c for c in fixtures['cases']}
    rows = []
    for step, event in enumerate(context['events']):
        case = cases[event['template']]
        outcome = case['outcome']
        post = outcome.get('post') or {}
        if outcome['status'] == 'acknowledged' and (post['levels_completed'] != case['pre']['levels_completed']
                                                     or post.get('full_reset')):
            raise ValueError('synthetic contexts must stay within one segment')
        rows.append(raw_entry(step, event['action'], outcome['status'], case['pre']['frames'][-1], post.get('frames')))
    return rows[-LIMIT:], len(rows) - len(rows[-LIMIT:])


def archived_entries(episode, decision):
    """Entries the history arm was shown before decision `decision`, rebuilt from archived engine steps."""
    rows = []
    for step in episode['steps'][:decision]:
        if step['after']['levels_completed'] != step['before']['levels_completed'] or step['after'].get('full_reset'):
            raise ValueError('real contexts must stay within one segment')
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
