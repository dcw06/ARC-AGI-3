"""Descriptive metrics from independently validated events, using frozen definitions.

This module does not certify a run or change its outcome. Callers must verify the
independent evaluation's complete evidence digest before aggregating anything.
"""
from research.initial_geometry_assistance_v1.geometry import digest


def episode_metrics(events):
    requests = [e for e in events if e['kind'] == 'request']
    moves = [e for e in events if e['kind'] == 'transition']
    by_step = {e['step']: e for e in moves}
    if len(by_step) != len(moves) or len({e['step'] for e in requests}) != len(requests):
        raise ValueError('duplicate decisions or transitions')
    initial = next(e['observation'] for e in events if e['kind'] == 'initial')
    repeat = {key: {'eligible': 0, 'repeated': 0, 'unexecuted': 0}
              for key in ('all', 'same_grid', 'different_grid')}
    consecutive = {'eligible': 0, 'repeated': 0, 'unexecuted': 0}
    for request in requests:
        step = request['step']
        history = [by_step[i] for i in range(max(0, step-2), step)]
        current = by_step[step-1]['after'] if step else initial
        chosen = by_step[step]['action'] if step in by_step else None
        unchanged = [m for m in history if m['before']['grid'] == m['after']['grid']]
        groups = {'all': unchanged,
                  'same_grid': [m for m in unchanged if m['before']['grid'] == current['grid']],
                  'different_grid': [m for m in unchanged if m['before']['grid'] != current['grid']]}
        for key, candidates in groups.items():
            if candidates:
                repeat[key]['eligible'] += 1
                repeat[key]['repeated'] += any(chosen == m['action'] for m in candidates)
                repeat[key]['unexecuted'] += chosen is None
        if history:
            consecutive['eligible'] += 1
            consecutive['repeated'] += chosen == history[-1]['action']
            consecutive['unexecuted'] += chosen is None
    known = [m for m in moves if m['predicted_visible_change'] != 'unknown']
    return {'decisions': len(requests), 'dispatched_actions': len(moves),
        'repeat_after_unchanged': repeat, 'consecutive_repeat': consecutive,
        'distinct_full_actions': len({digest(m['action']) for m in moves}),
        'distinct_action_ids': len({m['action']['action_id'] for m in moves}),
        'visibly_changed_steps': sum(m['before']['grid'] != m['after']['grid'] for m in moves),
        'prediction': {'asserted': len(known), 'dispatched': len(moves),
            'correct_assertions': sum((m['predicted_visible_change'] == 'yes') ==
                (m['before']['grid'] != m['after']['grid']) for m in known)}}
