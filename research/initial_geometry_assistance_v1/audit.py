"""Reconstruct retained requests, actions, stop reasons and counts.

This is an episode-content audit, NOT a GPU/lifecycle certification. An optional
fresh offline engine also replays every retained action and observation.
"""
import math
from .geometry import decode_mask, digest
from .policy import check_observation, parse_answer, request_for


def audit_episode(case, arm, events, *, model, cap, replay_engine=None):
    if arm not in ('automatic', 'reviewed') or type(cap) is not int or not 1 <= cap <= 24:
        raise ValueError('invalid audit scope')
    index, history = 0, []

    def take(kind):
        nonlocal index
        if index >= len(events) or events[index].get('kind') != kind:
            raise ValueError('missing/out-of-order event: ' + kind)
        value = events[index]
        index += 1
        return value

    if take('bootstrap_intent') != {'kind': 'bootstrap_intent', 'case_id': case['case_id'], 'arm': arm, 'seed': 0}:
        raise ValueError('bootstrap binding differs')
    initial = check_observation(take('initial')['observation'])
    if digest(initial['grid']) != case['grid_sha256'] or initial['levels_completed'] != 0 or initial['state'] != 'NOT_FINISHED':
        raise ValueError('starting observation differs')
    current, calls, reason = initial, 0, None
    invalid = False
    try:
        if replay_engine is not None and replay_engine.bootstrap() != initial:
            raise ValueError('engine initial replay differs')
        while index < len(events) and events[index].get('kind') == 'request':
            if len(history) >= cap or current['levels_completed'] > 0 or current['state'] in ('WIN', 'GAME_OVER'):
                raise ValueError('request after terminal/cap')
            step = len(history)
            retained = take('request')
            expected = request_for(initial, case['geometry'][arm], current, history, step, model)
            if retained != {'kind': 'request', 'step': step, 'body': expected, 'request_sha256': digest(expected)}:
                raise ValueError('complete frozen request differs')
            response = take('response')
            if set(response) != {'kind', 'step', 'text'} or response['step'] != step:
                raise ValueError('response binding differs')
            calls += 1
            try:
                answer = parse_answer(response['text'], current['legal_actions'])
            except ValueError:
                invalid, reason = True, 'invalid_answer'
                break
            action = {k: answer[k] for k in ('action_id', 'action_data')}
            if take('dispatch_intent') != {'kind': 'dispatch_intent', 'step': step, 'action': action,
                                           'pre_observation_sha256': digest(current)}:
                raise ValueError('dispatch intent differs')
            event = take('transition')
            if set(event) != {'kind', 'step', 'before', 'after', 'action', 'predicted_visible_change'}:
                raise ValueError('transition fields differ')
            after = check_observation(event['after'])
            if (event['step'] != step or event['before'] != current or event['action'] != action
                    or event['predicted_visible_change'] != answer['predicted_visible_change']):
                raise ValueError('transition chain/action differs')
            if replay_engine is not None and replay_engine.dispatch(action) != after:
                raise ValueError('engine transition replay differs')
            history.append({k: v for k, v in event.items() if k != 'kind'})
            current = after
        if not invalid:
            if current['levels_completed'] > 0 or current['state'] == 'WIN':
                reason = 'first_level_complete'
            elif current['state'] == 'GAME_OVER':
                reason = 'game_over'
            elif len(history) == cap:
                reason = 'action_cap'
            else:
                raise ValueError('unexplained early stop')
        closed = take('closed')
        if closed != {'kind': 'closed', 'receipt': {'closed': True, 'local_scorecard_opened': True,
                      'local_scorecard_closed': True, 'online_calls': 0}}:
            raise ValueError('engine close not established')
        summary = take('summary')
        if index != len(events):
            raise ValueError('trailing events')
        if (any(type(summary.get(k)) is not int for k in ('action_cap', 'policy_calls', 'dispatches'))
                or type(summary.get('elapsed_seconds')) not in (int, float)
                or not math.isfinite(summary['elapsed_seconds']) or summary['elapsed_seconds'] < 0
                or summary.get('lifecycle_certified') is not False):
            raise ValueError('invalid summary types')
        expected = {'case_id': case['case_id'], 'arm': arm, 'action_cap': cap,
                    'policy_calls': calls, 'dispatches': len(history), 'stop_reason': reason,
                    'final_observation': current, 'lifecycle_certified': False}
        if any(summary.get(k) != v for k, v in expected.items()):
            raise ValueError('summary differs from retained events')
        if not invalid and summary.get('error') is not None:
            raise ValueError('unexpected error')
    finally:
        if replay_engine is not None:
            replay_engine.close()
    known = [h for h in history if h['predicted_visible_change'] != 'unknown']
    correct = sum((h['predicted_visible_change'] == 'yes') == (h['before']['grid'] != h['after']['grid']) for h in known)
    first_contact = None
    if history and history[0]['action']['action_id'] == 6:
        point = [history[0]['action']['action_data'][k] for k in ('x', 'y')]
        first_contact = any(point in decode_mask({k: v for k, v in obj.items() if k != 'id'})
                            for obj in case['geometry']['reviewed'])
    return {'case_id': case['case_id'], 'arm': arm, 'first_level_complete': reason == 'first_level_complete',
            'stop_reason': reason, 'policy_calls': calls, 'dispatches': len(history),
            'first_action_click_on_reviewed_object': first_contact,
            'known_visible_change_predictions': len(known), 'correct_visible_change_predictions': correct,
            'unknown_visible_change_predictions': len(history)-len(known),
            'content_replay_passed': True, 'engine_replayed': replay_engine is not None,
            'lifecycle_certified': False, 'outcome_claim_permitted': False}
