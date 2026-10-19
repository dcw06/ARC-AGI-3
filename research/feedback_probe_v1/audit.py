"""Independent reconstruction of checkpoint restoration and short continuations.

This checks retained content, optionally against a fresh offline engine. It
never certifies a runtime lifecycle or interprets action diversity as learning.
"""
from copy import deepcopy

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation, parse_answer, request_for
from .checkpoints import checked_checkpoint
from .interface import PROBE_INSTRUCTION, VARIANTS


CUT_OFF = ('deadline', 'exception')
SUMMARY_FIELDS = {'kind', 'checkpoint_id', 'variant', 'reason', 'error', 'prefix_dispatches',
                  'policy_calls', 'continuation_dispatches', 'final_observation', 'lifecycle_certified'}


def _same(left, right):
    # Python dictionary equality equates True, 1 and 1.0. Canonical JSON hashes
    # retain those distinctions in request settings, observations and counters.
    return digest(left) == digest(right)


def _stop(current, dispatched):
    if current['levels_completed'] > 0 or current['state'] == 'WIN':
        return 'first_level_complete'
    if current['state'] == 'GAME_OVER':
        return 'game_over'
    if dispatched == 4:
        return 'action_cap'
    return None


def _request(checkpoint, variant, current, history, model):
    # Rebuild from observations and the original frozen request constructor;
    # do not use policy_request(), a retained body, or a producer request hash.
    body = request_for(checkpoint['initial'], checkpoint['initial_case']['geometry']['reviewed'],
                       current, history, len(history), model)
    if variant == 'probe_instruction':
        body['messages'][1]['content'].append({'type': 'text', 'text': PROBE_INSTRUCTION})
    return body


def audit_continuation(checkpoint, variant, events, *, model, replay_engine=None):
    """Reject drifted requests, observations, dispatches and aggregate labels.

    A well-formed interrupted prefix can be checked, but is never credited as a
    completed continuation. Counts concern retained evidence only; an unfinished
    dispatch or request is explicitly reported rather than assumed not to occur.
    """
    index = restored = calls = dispatched = 0
    current = None
    history, executed = [], []
    ready = invalid = False
    unfinished = invalid_error = None

    def upcoming():
        if index >= len(events):
            return None
        if type(events[index]) is not dict:
            raise ValueError('non-object continuation event')
        return events[index].get('kind')

    def take(kind):
        nonlocal index
        if upcoming() != kind:
            raise ValueError('missing/out-of-order event: '+kind)
        event = events[index]
        index += 1
        return event

    def exact(kind, **values):
        event = take(kind)
        if not _same(event, dict(kind=kind, **values)):
            raise ValueError(kind+' differs from reconstructed evidence')
        return event

    try:
        checked_checkpoint(checkpoint, model=model)
        if variant not in VARIANTS or type(events) is not list:
            raise ValueError('invalid continuation audit scope')
        history = deepcopy(checkpoint['prefix'])
        if upcoming() != 'closed':
            exact('bootstrap_intent', checkpoint_id=checkpoint['checkpoint_id'], variant=variant, seed=0)
            unfinished = 'bootstrap_intent'
        if upcoming() != 'closed':
            initial = take('initial')
            if set(initial) != {'kind', 'observation'}:
                raise ValueError('initial event fields differ')
            current = deepcopy(check_observation(initial['observation']))
            if not _same(current, checkpoint['initial']):
                raise ValueError('checkpoint initial observation differs')
            if replay_engine is not None and not _same(replay_engine.bootstrap(), current):
                raise ValueError('engine initial replay differs')
            unfinished = None
            for old in history:
                if upcoming() == 'closed':
                    break
                exact('prefix_dispatch_intent', step=old['step'], action=old['action'])
                unfinished = 'prefix_dispatch_intent'
                if upcoming() == 'closed':
                    break
                if not _same(current, old['before']):
                    raise ValueError('prefix before observation differs')
                event = take('prefix_transition')
                if set(event) != {'kind', 'step', 'observation'}:
                    raise ValueError('prefix transition fields differ')
                observed = check_observation(event['observation'])
                if not _same(event, {'kind': 'prefix_transition', 'step': old['step'],
                                     'observation': old['after']}):
                    raise ValueError('prefix transition differs from frozen checkpoint')
                if replay_engine is not None and not _same(replay_engine.dispatch(old['action']), observed):
                    raise ValueError('engine prefix replay differs')
                current = deepcopy(observed)
                restored += 1
                unfinished = None
            if restored == len(history) and upcoming() != 'closed':
                exact('checkpoint_ready', observation=current, prefix_dispatches=restored)
                if not _same(current, checkpoint['current']):
                    raise ValueError('restored checkpoint observation differs')
                ready = True
            while ready and upcoming() == 'request':
                if _stop(current, dispatched) is not None:
                    raise ValueError('request after terminal state or continuation cap')
                step = len(history)
                body = _request(checkpoint, variant, current, history, model)
                exact('request', step=step, body=body, request_sha256=digest(body))
                unfinished = 'request'
                if upcoming() == 'closed':
                    break
                response = take('response')
                if set(response) != {'kind', 'step', 'text'} or type(response['step']) is not int or response['step'] != step:
                    raise ValueError('response binding differs')
                calls += 1
                try:
                    answer = parse_answer(response['text'], current['legal_actions'])
                except (ValueError, TypeError, RecursionError) as exc:
                    invalid, invalid_error, unfinished = True, str(exc), None
                    break
                unfinished = 'response'
                if upcoming() == 'closed':
                    break
                action = {key: answer[key] for key in ('action_id', 'action_data')}
                exact('dispatch_intent', step=step, action=action, before_sha256=digest(current))
                unfinished = 'dispatch_intent'
                if upcoming() == 'closed':
                    break
                event = take('transition')
                if set(event) != {'kind', 'step', 'before', 'after', 'action', 'predicted_visible_change'}:
                    raise ValueError('continuation transition fields differ')
                observed = check_observation(event['after'])
                record = {'step': step, 'before': deepcopy(current), 'after': deepcopy(observed),
                          'action': action, 'predicted_visible_change': answer['predicted_visible_change']}
                if not _same(event, dict(kind='transition', **record)):
                    raise ValueError('continuation transition differs from response/observation chain')
                if replay_engine is not None and not _same(replay_engine.dispatch(action), observed):
                    raise ValueError('engine continuation replay differs')
                executed.append(record)
                history.append(record)
                current = deepcopy(observed)
                dispatched += 1
                unfinished = None

        closed = take('closed')
        # Opening may occur during interrupted bootstrap before its first
        # observation. Once an initial observation exists, opening is certain.
        opened_options = (True,) if current is not None else (False, True)
        if not any(_same(closed, {'kind': 'closed', 'receipt': {
                'closed': True, 'local_scorecard_opened': opened,
                'local_scorecard_closed': opened, 'online_calls': 0}}) for opened in opened_options):
            raise ValueError('engine close not established')
        summary = take('summary')
        if index != len(events) or set(summary) != SUMMARY_FIELDS:
            raise ValueError('trailing events or summary fields differ')
        for key in ('prefix_dispatches', 'policy_calls', 'continuation_dispatches'):
            if type(summary[key]) is not int or summary[key] < 0:
                raise ValueError('summary counter type differs')
        if summary['lifecycle_certified'] is not False:
            raise ValueError('content audit cannot certify lifecycle')
        expected = {'checkpoint_id': checkpoint['checkpoint_id'], 'variant': variant,
                    'prefix_dispatches': restored, 'policy_calls': calls,
                    'continuation_dispatches': dispatched, 'final_observation': current}
        if any(not _same(summary[key], value) for key, value in expected.items()):
            raise ValueError('summary differs from independently reconstructed counts/state')
        reason = summary['reason']
        reached = _stop(current, dispatched) if ready else None
        if reason in CUT_OFF:
            if type(summary['error']) is not str or not summary['error']:
                raise ValueError('interruption error missing')
        elif invalid:
            if reason != 'invalid_answer' or summary['error'] != invalid_error:
                raise ValueError('invalid answer stop/error differs')
        elif not ready or unfinished is not None or reached is None or reason != reached or summary['error'] is not None:
            raise ValueError('completion reason not established by retained events')
    finally:
        if replay_engine is not None:
            replay_engine.close()

    known = [entry for entry in executed if entry['predicted_visible_change'] != 'unknown']
    previous = checkpoint['prefix'][-1]
    eligible = repeated = 0
    for entry in executed:
        if _same(previous['before'], previous['after']) and _same(previous['after'], entry['before']):
            eligible += 1
            repeated += _same(previous['action'], entry['action'])
        previous = entry
    return {'checkpoint_id': checkpoint['checkpoint_id'], 'variant': variant,
            'prefix_dispatches': restored, 'policy_calls': calls,
            'continuation_dispatches': dispatched, 'reason': reason,
            'first_level_complete': reason == 'first_level_complete',
            'content_replay_passed': True, 'engine_replayed': replay_engine is not None,
            'restoration_complete': ready, 'unconfirmed_model_call': unfinished == 'request',
            'unconfirmed_dispatch': unfinished in ('dispatch_intent', 'prefix_dispatch_intent'),
            'lifecycle_certified': False, 'outcome_claim_permitted': False,
            'diagnostics': {
                'executed_decisions_after_full_unchanged': eligible,
                'repeated_previous_action_after_full_unchanged': repeated,
                'distinct_executed_full_actions': len({digest(entry['action']) for entry in executed}),
                'visibly_changed_transitions': sum(entry['before']['grid'] != entry['after']['grid'] for entry in executed),
                'known_visible_change_predictions': len(known),
                'correct_known_visible_change_predictions': sum(
                    (entry['predicted_visible_change'] == 'yes') == (entry['before']['grid'] != entry['after']['grid'])
                    for entry in known),
                'unknown_visible_change_predictions': len(executed)-len(known)},
            'qualification': 'Content replay only. Diagnostic counters describe executed continuation actions; '
                             'restoration is counted separately. Repetition, diversity and changed pixels '
                             'do not establish usefulness, learning or progress.'}
