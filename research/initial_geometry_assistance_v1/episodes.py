"""CPU-rehearsable episode state machine; no deployment or model launcher.

The injected engine/completion/sink must be supervised by a separately reviewed
live runtime. This module deliberately provides no way to enable a live run.
"""
from copy import deepcopy
import time

from .geometry import digest
from .policy import check_observation, parse_answer, request_for


def terminal(initial, current, dispatched, cap):
    if current['levels_completed'] > initial['levels_completed'] or current['state'] == 'WIN':
        return 'first_level_complete'
    if current['state'] == 'GAME_OVER':
        return 'game_over'
    if dispatched >= cap:
        return 'action_cap'
    return None


def describe(exc):
    return type(exc).__name__ + ': ' + str(exc)


def episode(case, arm, engine, complete, sink, *, model, deadline, cap=24, now=time.monotonic):
    """A single episode, with write-before-effect records and no retry path.

    Deadline checks guard admission, inference return, dispatch and evidence.
    They do not bound a stalled injected call; the live supervisor must do so.
    Every episode ends with 'closed' and 'summary' records, including deadline
    and exception stops, which are re-raised after them. The stop test runs
    before each deadline check, so an observed completion is kept.
    No success/lifecycle certificate is emitted by this component.
    """
    if arm not in ('automatic', 'reviewed') or type(cap) is not int or not 1 <= cap <= 24:
        raise ValueError('invalid episode scope')
    history, current, initial, reason, error, failure, calls = [], None, None, None, None, None, 0
    started = now()

    def check():
        if now() >= deadline:
            raise TimeoutError('episode admission closed')

    def emit(kind, **values):
        sink(deepcopy({'kind': kind, **values}))

    try:
        check()
        emit('bootstrap_intent', case_id=case['case_id'], arm=arm, seed=0)
        check()
        observed = check_observation(engine.bootstrap())
        if (digest(observed['grid']) != case['grid_sha256'] or observed['levels_completed'] != 0
                or observed['state'] != 'NOT_FINISHED'):
            raise ValueError('engine does not reproduce reviewed level-1 start')
        emit('initial', observation=observed)
        initial, current = deepcopy(observed), deepcopy(observed)
        while (reason := terminal(initial, current, len(history), cap)) is None:
            check()
            step = len(history)
            request = request_for(initial, case['geometry'][arm], current, history, step, model)
            emit('request', step=step, body=request, request_sha256=digest(request))
            check()
            response = complete(deepcopy(request))
            emit('response', step=step, text=response)
            calls += 1
            check()
            try:
                answer = parse_answer(response, current['legal_actions'])
            except ValueError as exc:
                reason, error = 'invalid_answer', describe(exc)
                break
            action = {k: answer[k] for k in ('action_id', 'action_data')}
            emit('dispatch_intent', step=step, action=action, pre_observation_sha256=digest(current))
            # A potentially slow evidence write cannot reopen action admission.
            check()
            after = check_observation(engine.dispatch(deepcopy(action)))
            entry = {'step': step, 'before': deepcopy(current), 'after': deepcopy(after), 'action': action,
                     'predicted_visible_change': answer['predicted_visible_change']}
            emit('transition', **entry)
            history.append(entry)
            current = after
    except BaseException as exc:
        failure, error = exc, describe(exc)
        reason = 'deadline' if isinstance(exc, TimeoutError) else 'exception'
    # Close is reached even if bootstrap, request writing or inference fails.
    # The owner of the engine must make close safe after partial bootstrap.
    # A close failure is recorded and never replaces the error that stopped the episode.
    try:
        closing = {'receipt': engine.close()}
    except BaseException as exc:
        closing = {'receipt': None, 'error': describe(exc)}
        if failure is None:
            failure = exc
    summary = {'case_id': case['case_id'], 'arm': arm, 'action_cap': cap, 'policy_calls': calls,
               'dispatches': len(history), 'stop_reason': reason, 'error': error, 'final_observation': current,
               'elapsed_seconds': now()-started, 'lifecycle_certified': False}
    try:
        emit('closed', **closing)
        emit('summary', **summary)
    except BaseException as exc:
        if failure is None:
            failure = exc
    if failure is not None:
        raise failure
    # A late final write cannot return success.
    check()
    return summary
