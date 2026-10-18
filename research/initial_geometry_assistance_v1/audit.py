"""Reconstruct retained requests, actions, stop reasons and counts.

This is an episode-content audit, NOT a GPU/lifecycle certification. An optional
fresh offline engine also replays every retained action and observation.
Records cut off by a deadline or exception are classified, never completed: the
retained prefix is checked, at most one unfinished step may follow it, and no
outcome is credited beyond the last retained observation.
"""
import math
from .episodes import terminal
from .geometry import decode_mask, digest
from .policy import check_observation, parse_answer, request_for

CUT_OFF = ('deadline', 'exception')
SUMMARY_KEYS = {'kind', 'case_id', 'arm', 'action_cap', 'policy_calls', 'dispatches', 'stop_reason', 'error',
                'final_observation', 'elapsed_seconds', 'lifecycle_certified'}


def cells(obj):
    return decode_mask({k: v for k, v in obj.items() if k != 'id'})


def audit_episode(case, arm, events, *, model, cap, replay_engine=None):
    if arm not in ('automatic', 'reviewed') or type(cap) is not int or not 1 <= cap <= 24:
        raise ValueError('invalid audit scope')
    index, history = 0, []

    def upcoming():
        return events[index].get('kind') if index < len(events) else None

    def take(kind):
        nonlocal index
        if index >= len(events) or events[index].get('kind') != kind:
            raise ValueError('missing/out-of-order event: ' + kind)
        value = events[index]
        index += 1
        return value

    initial = current = unfinished = None
    calls, invalid = 0, False
    try:
        # A record cut off before bootstrap or before the first observation stops here.
        if upcoming() != 'closed':
            if take('bootstrap_intent') != {'kind': 'bootstrap_intent', 'case_id': case['case_id'], 'arm': arm, 'seed': 0}:
                raise ValueError('bootstrap binding differs')
        if upcoming() != 'closed':
            initial = current = check_observation(take('initial')['observation'])
            if digest(initial['grid']) != case['grid_sha256'] or initial['levels_completed'] != 0 or initial['state'] != 'NOT_FINISHED':
                raise ValueError('starting observation differs')
            if replay_engine is not None and replay_engine.bootstrap() != initial:
                raise ValueError('engine initial replay differs')
        while initial is not None and upcoming() == 'request':
            if terminal(initial, current, len(history), cap) is not None:
                raise ValueError('request after terminal/cap')
            step = len(history)
            retained = take('request')
            expected = request_for(initial, case['geometry'][arm], current, history, step, model)
            if retained != {'kind': 'request', 'step': step, 'body': expected, 'request_sha256': digest(expected)}:
                raise ValueError('complete frozen request differs')
            if upcoming() == 'closed':
                unfinished = 'request'
                break
            response = take('response')
            if set(response) != {'kind', 'step', 'text'} or response['step'] != step:
                raise ValueError('response binding differs')
            calls += 1
            try:
                answer = parse_answer(response['text'], current['legal_actions'])
            except ValueError:
                invalid = True
                break
            if upcoming() == 'closed':
                unfinished = 'response'
                break
            action = {k: answer[k] for k in ('action_id', 'action_data')}
            if take('dispatch_intent') != {'kind': 'dispatch_intent', 'step': step, 'action': action,
                                           'pre_observation_sha256': digest(current)}:
                raise ValueError('dispatch intent differs')
            if upcoming() == 'closed':
                unfinished = 'dispatch_intent'
                break
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
        closed = take('closed')
        # Without a recorded first observation, bootstrap may have stopped before or after opening the scorecard.
        if not any(closed == {'kind': 'closed', 'receipt': {'closed': True, 'local_scorecard_opened': opened,
                                                           'local_scorecard_closed': opened, 'online_calls': 0}}
                   for opened in ((True,) if initial is not None else (True, False))):
            raise ValueError('engine close not established')
        summary = take('summary')
        if index != len(events):
            raise ValueError('trailing events')
        if (set(summary) != SUMMARY_KEYS
                or any(type(summary[k]) is not int for k in ('action_cap', 'policy_calls', 'dispatches'))
                or type(summary['elapsed_seconds']) not in (int, float)
                or not math.isfinite(summary['elapsed_seconds']) or summary['elapsed_seconds'] < 0
                or summary['lifecycle_certified'] is not False):
            raise ValueError('invalid summary types')
        # A record that reached a terminal state must carry that reason. Only an
        # interrupted record may carry a deadline or exception stop.
        if invalid:
            allowed = ('invalid_answer',) + CUT_OFF
        elif initial is None or unfinished is not None:
            allowed = CUT_OFF
        else:
            reached = terminal(initial, current, len(history), cap)
            allowed = (reached,) if reached else CUT_OFF
        reason = summary['stop_reason']
        if reason not in allowed:
            raise ValueError('stop reason differs from retained events')
        expected = {'case_id': case['case_id'], 'arm': arm, 'action_cap': cap, 'policy_calls': calls,
                    'dispatches': len(history), 'final_observation': current, 'lifecycle_certified': False}
        if any(summary[k] != v for k, v in expected.items()):
            raise ValueError('summary differs from retained events')
        if reason in CUT_OFF or reason == 'invalid_answer':
            if type(summary['error']) is not str or not summary['error']:
                raise ValueError('stop error missing')
        elif summary['error'] is not None:
            raise ValueError('unexpected error')
    finally:
        if replay_engine is not None:
            replay_engine.close()
    known = [h for h in history if h['predicted_visible_change'] != 'unknown']
    correct = sum((h['predicted_visible_change'] == 'yes') == (h['before']['grid'] != h['after']['grid']) for h in known)
    # The reviewed arm receives the reviewed masks and an anchor for each, so its
    # reviewed-object rate cannot separate localization from use of that geometry.
    contact = dict.fromkeys(('first_action_click_on_reviewed_object', 'first_action_click_in_supplied_mask',
                             'first_action_click_on_supplied_anchor'))
    if history and history[0]['action']['action_id'] == 6:
        point = [history[0]['action']['action_data'][k] for k in ('x', 'y')]
        supplied = case['geometry'][arm]
        contact = {'first_action_click_on_reviewed_object': any(point in cells(o) for o in case['geometry']['reviewed']),
                   'first_action_click_in_supplied_mask': any(point in cells(o) for o in supplied),
                   'first_action_click_on_supplied_anchor': any(point == o['occupied_anchor_xy'] for o in supplied)}
    return {'case_id': case['case_id'], 'arm': arm, 'first_level_complete': reason == 'first_level_complete',
            'stop_reason': reason, 'policy_calls': calls, 'dispatches': len(history),
            'unconfirmed_model_call': unfinished == 'request', 'unconfirmed_dispatch': unfinished == 'dispatch_intent',
            **contact,
            'known_visible_change_predictions': len(known), 'correct_visible_change_predictions': correct,
            'unknown_visible_change_predictions': len(history)-len(known),
            'content_replay_passed': True, 'engine_replayed': replay_engine is not None,
            'lifecycle_certified': False, 'outcome_claim_permitted': False}
