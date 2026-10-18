"""Retrospective feedback availability; no policy, inference or game execution.

All per-decision findings use completed transitions strictly before that
decision. Pixel equality is observational, never a hidden-state certificate.
"""
from .initial_geometry_assistance_v1.geometry import digest
from .initial_geometry_assistance_v1.policy import request_for


def changed_cells(before, after):
    return [[x, y] for y, (left, right) in enumerate(zip(before['grid'], after['grid']))
            for x, (a, b) in enumerate(zip(left, right)) if a != b]


def decision_feedback(history, action, current):
    """Report previous matching actions, including whether their images were shown."""
    visible = history[-2:]
    identical = [h for h in history if h['action'] == action]
    unchanged = [h for h in identical if h['before']['grid'] == h['after']['grid']]
    visible_unchanged = [h for h in visible if h in unchanged]
    exact = [h for h in unchanged if h['before'] == current]
    visible_exact = [h for h in visible if h in exact]
    # Changes in state, counters or legal controls are retained independently.
    full_unchanged = [h for h in identical if h['before'] == h['after']]
    omitted = [h for h in unchanged if h not in visible]
    return {'visible_transition_steps': [h['step'] for h in visible],
            'prior_same_action_steps': [h['step'] for h in identical],
            'visible_same_action_steps': [h['step'] for h in visible if h['action'] == action],
            'prior_same_action_unchanged_grid_steps': [h['step'] for h in unchanged],
            'visible_same_action_unchanged_grid_steps': [h['step'] for h in visible_unchanged],
            'omitted_same_action_unchanged_grid_steps': [h['step'] for h in omitted],
            'prior_same_action_same_observation_unchanged_grid_steps': [h['step'] for h in exact],
            'visible_same_action_same_observation_unchanged_grid_steps': [h['step'] for h in visible_exact],
            'prior_same_action_unchanged_full_observation_steps': [h['step'] for h in full_unchanged],
            'consecutive_action_repeat': bool(history and history[-1]['action'] == action),
            'qualification': 'Available as images/action records; not proof the model recognized the outcome or that repetition is useless.'}


def episode_feedback(case, arm, events, *, model):
    """Rebuild every request and restrict availability to its displayed history.

    Intended for independently certified complete episodes. Earlier certified
    inputs and the evidence digest must be checked by the invoking collector.
    """
    initial = next(e['observation'] for e in events if e['kind'] == 'initial')
    history, rows, pending = [], [], None
    current = initial
    for event in events:
        kind = event['kind']
        if kind == 'request':
            step = event['step']
            expected = request_for(initial, case['geometry'][arm], current, history, step, model)
            if pending is not None or event['body'] != expected or event['request_sha256'] != digest(expected):
                raise ValueError('request differs from displayed history')
            pending = step
        elif kind == 'transition':
            step = event['step']
            if pending != step or step != len(history) or event['before'] != current:
                raise ValueError('transition ordering differs')
            feedback = decision_feedback(history, event['action'], current)
            pixels = changed_cells(current, event['after'])
            rows.append({'step': step, 'action': event['action'],
                         'current_observation_sha256': digest(current), **feedback,
                         'subsequent_outcome': {'changed_cells_xy': pixels, 'changed_cell_count': len(pixels),
                             'grid_unchanged': not pixels, 'full_observation_unchanged': current == event['after'],
                             'state_before': current['state'], 'state_after': event['after']['state'],
                             'levels_before': current['levels_completed'], 'levels_after': event['after']['levels_completed']}})
            history.append(event)
            current, pending = event['after'], None
    if pending is not None:
        raise ValueError('unfinished decision')
    actions = [h['action'] for h in history]
    cycle_period = next((p for p in range(2, 5) if len(actions) >= 2*p and
                         len({digest(a) for a in actions[:p]}) > 1 and
                         all(a == actions[i % p] for i, a in enumerate(actions))), None)
    return {'case_id': case['case_id'], 'game_id': case['game_id'], 'arm': arm, 'decisions': rows,
            'summary': {'decisions': len(rows), 'consecutive_repeats': sum(r['consecutive_action_repeat'] for r in rows),
                'visible_same_action_decisions': sum(bool(r['visible_same_action_steps']) for r in rows),
                'visible_prior_unchanged_grid_decisions': sum(bool(r['visible_same_action_unchanged_grid_steps']) for r in rows),
                'visible_same_observation_prior_unchanged_grid_decisions': sum(bool(r['visible_same_action_same_observation_unchanged_grid_steps']) for r in rows),
                'omitted_only_prior_unchanged_grid_decisions': sum(bool(r['omitted_same_action_unchanged_grid_steps']) and
                    not r['visible_same_action_unchanged_grid_steps'] for r in rows),
                'no_prior_unchanged_grid_example_decisions': sum(not r['prior_same_action_unchanged_grid_steps'] for r in rows),
                'unchanged_grid_outcomes': sum(r['subsequent_outcome']['grid_unchanged'] for r in rows),
                'unchanged_full_observation_outcomes': sum(r['subsequent_outcome']['full_observation_unchanged'] for r in rows),
                'whole_episode_action_cycle_period_2_to_4': cycle_period}}
