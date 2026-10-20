"""Injectable two-decision CPU path; no model, GPU or provider constructor."""
from copy import deepcopy
import time

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation, request_for
from research.feedback_probe_v1.checkpoints import checked_checkpoint
from .interface import VARIANTS, checked_pair, make_request, parse_choice

def restored(checkpoint, engine, emit, check, path=()):
    checked_checkpoint(checkpoint, model=checkpoint['base_request']['model'])
    emit('bootstrap_intent', seed=0); check()
    current = check_observation(engine.bootstrap())
    if digest(current) != digest(checkpoint['initial']): raise ValueError('initial restoration differs')
    emit('initial', observation=current)
    history = deepcopy(checkpoint['prefix'])
    for record in list(history) + list(path):
        if digest(current) != digest(record['before']): raise ValueError('restore before differs')
        emit('restore_dispatch_intent', step=record['step'], action=record['action']); check()
        current = check_observation(engine.dispatch(deepcopy(record['action'])))
        emit('restored_transition', step=record['step'], observation=current)
        if digest(current) != digest(record['after']): raise ValueError('restored full observation differs')
    if not path and digest(current) != digest(checkpoint['current']): raise ValueError('checkpoint restoration differs')
    history.extend(deepcopy(path))
    return current, history

def terminal(current):
    return ('first_level_complete' if current['levels_completed'] > 0 or current['state'] == 'WIN' else
            'game_over' if current['state'] == 'GAME_OVER' else None)

def run_case(checkpoint, pair, variant, engine, complete, sink, *, deadline, now=time.monotonic):
    failure = None; reason = None; error = None; current = None; calls = 0; transitions = []
    def check():
        if now() >= deadline: raise TimeoutError('candidate-choice admission closed')
    def emit(kind, **fields): sink(deepcopy(dict(kind=kind, **fields)))
    try:
        if variant not in VARIANTS: raise ValueError('unknown condition')
        checked_pair(pair, checkpoint['current']['legal_actions']); check()
        current, history = restored(checkpoint, engine, emit, check)
        previous = None
        for decision in range(2):
            reason = terminal(current)
            if reason: break
            if any(action['action_id'] not in current['legal_actions'] for action in pair.values()):
                reason = 'candidate_set_invalid'; break
            check()
            base = request_for(checkpoint['initial'], checkpoint['initial_case']['geometry']['reviewed'],
                               current, history, len(history), checkpoint['base_request']['model'])
            body = make_request(base, pair, variant, previous)
            emit('request', decision=decision, body=body, request_sha256=digest(body)); check()
            text = complete(deepcopy(body)); calls += 1
            emit('response', decision=decision, text=text); check()
            try: answer = parse_choice(text, first=decision == 0)
            except (ValueError, TypeError, RecursionError) as exc:
                reason, error = 'invalid_answer', str(exc); break
            action = deepcopy(pair[answer['selected_candidate']])
            emit('dispatch_intent', decision=decision, action=action, before_sha256=digest(current)); check()
            after = check_observation(engine.dispatch(deepcopy(action)))
            record = {'step': len(history), 'before': deepcopy(current), 'after': deepcopy(after), 'action': action,
                      'predicted_visible_change': ('unknown' if answer['candidate_predictions'][answer['selected_candidate']] == 'unknown'
                          else 'no' if answer['candidate_predictions'][answer['selected_candidate']] == 'none' else 'yes')}
            emit('transition', decision=decision, record=record, answer=answer)
            transitions.append(record); history.append(record); current = after; previous = answer
        check()
        reason = reason or terminal(current) or 'action_cap'
    except BaseException as exc:
        failure, error = exc, type(exc).__name__+': '+str(exc)
        reason = 'deadline' if isinstance(exc, TimeoutError) else 'exception'
    try: emit('closed', receipt=engine.close())
    except BaseException as exc:
        if failure is None: failure, error, reason = exc, str(exc), 'exception'
    try: check()
    except BaseException as exc:
        if failure is None: failure, error, reason = exc, str(exc), 'deadline'
    result = {'checkpoint_id': checkpoint['checkpoint_id'], 'variant': variant, 'reason': reason, 'error': error,
              'model_calls': calls, 'new_dispatches': len(transitions), 'final_observation': current,
              'lifecycle_certified': False}
    emit('summary', **result)
    if failure is not None: raise failure
    check()
    return result

def reference_branch(checkpoint, pair, label, engine, sink, *, path=(), deadline, now=time.monotonic):
    """Evaluation-only restore of a real candidate, never used to select a pair."""
    def check():
        if now() >= deadline: raise TimeoutError('reference-branch admission closed')
    def emit(kind, **fields): sink(deepcopy(dict(kind=kind, **fields)))
    try:
        if label not in ('A', 'B'): raise ValueError('unknown reference candidate')
        check()
        current, _ = restored(checkpoint, engine, emit, check, path)
        checked_pair(pair, current['legal_actions'])
        if terminal(current): raise ValueError('no candidate forecast at terminal state')
        action = deepcopy(pair[label])
        emit('reference_dispatch_intent', action=action, before_sha256=digest(current)); check()
        after = check_observation(engine.dispatch(deepcopy(action)))
        record = {'before': deepcopy(current), 'action': action, 'after': after}
        emit('reference_outcome', record=record)
        return record
    finally:
        emit('closed', receipt=engine.close())
