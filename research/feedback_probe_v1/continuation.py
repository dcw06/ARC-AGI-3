"""Injectable CPU continuation path; calls require a separately bounded owner.

No launcher, model constructor, GPU code or authority bypass exists here.
Restoration replays every prefix action; screenshots never substitute for state.
"""
from copy import deepcopy
import time

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation, parse_answer, request_for
from .checkpoints import checked_checkpoint
from .interface import VARIANTS, policy_request


def continuation(checkpoint, variant, engine, complete, sink, *, model, deadline, now=time.monotonic):
    initial = current = None
    history = []
    restored = calls = dispatches = 0
    reason, error, failure = None, None, None

    def check():
        if now() >= deadline: raise TimeoutError('checkpoint continuation admission closed')
    def emit(kind, **values): sink(deepcopy(dict(kind=kind, **values)))
    try:
        checked_checkpoint(checkpoint, model=model)
        if variant not in VARIANTS: raise ValueError('unknown policy condition')
        initial = checkpoint['initial']
        history = deepcopy(checkpoint['prefix'])
        check()
        emit('bootstrap_intent', checkpoint_id=checkpoint['checkpoint_id'], variant=variant, seed=0)
        check()
        current = check_observation(engine.bootstrap())
        if current != initial: raise ValueError('restored initial observation differs')
        emit('initial', observation=current)
        for old in history:
            if current != old['before']: raise ValueError('restore prefix before differs')
            emit('prefix_dispatch_intent', step=old['step'], action=old['action'])
            check()
            observed = check_observation(engine.dispatch(deepcopy(old['action'])))
            emit('prefix_transition', step=old['step'], observation=observed)
            restored += 1
            if observed != old['after']: raise ValueError('restored prefix outcome differs')
            current = observed
        if current != checkpoint['current']: raise ValueError('restored checkpoint differs')
        emit('checkpoint_ready', observation=current, prefix_dispatches=restored)
        while dispatches < 4:
            if current['levels_completed'] > 0 or current['state'] == 'WIN':
                reason = 'first_level_complete'; break
            if current['state'] == 'GAME_OVER': reason = 'game_over'; break
            check()
            step = len(history)
            body = policy_request(request_for(initial, checkpoint['initial_case']['geometry']['reviewed'], current,
                                              history, step, model), variant)
            emit('request', step=step, body=body, request_sha256=digest(body))
            check()
            text = complete(deepcopy(body))
            emit('response', step=step, text=text)
            calls += 1
            check()
            try: answer = parse_answer(text, current['legal_actions'])
            except ValueError as exc:
                reason, error = 'invalid_answer', str(exc); break
            action = {k: answer[k] for k in ('action_id', 'action_data')}
            emit('dispatch_intent', step=step, action=action, before_sha256=digest(current))
            check()
            after = check_observation(engine.dispatch(deepcopy(action)))
            record = {'step': step, 'before': deepcopy(current), 'after': deepcopy(after), 'action': action,
                      'predicted_visible_change': answer['predicted_visible_change']}
            emit('transition', **record)
            history.append(record)
            dispatches += 1
            current = after
        if reason is None:
            reason = ('first_level_complete' if current['levels_completed'] > 0 or current['state'] == 'WIN' else
                      'game_over' if current['state'] == 'GAME_OVER' else 'action_cap')
    except BaseException as exc:
        failure, error = exc, type(exc).__name__+': '+str(exc)
        reason = 'deadline' if isinstance(exc, TimeoutError) else 'exception'
    try: emit('closed', receipt=engine.close())
    except BaseException as exc:
        if failure is None: failure, error, reason = exc, str(exc), 'exception'
    result = {'checkpoint_id': checkpoint['checkpoint_id'], 'variant': variant, 'reason': reason, 'error': error,
              'prefix_dispatches': restored, 'policy_calls': calls, 'continuation_dispatches': dispatches,
              'final_observation': current, 'lifecycle_certified': False}
    emit('summary', **result)
    if failure is not None: raise failure
    check()
    return result
