"""Injectable CPU-only two-decision path; no model or provider constructor."""
from copy import deepcopy
import time

from research.action_effect_choice_v2.flow import restored, terminal
from research.action_effect_choice_v2.interface import checked_pair, parse_choice
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation, request_for
from .feedback import freeze_forecast
from .interface import CONDITIONS, make_request


class AdmissionClosed(TimeoutError):
    """A witnessed refusal of new work; transport and cleanup failures differ."""


def run_case(checkpoint, pair, condition, engine, complete, sink, *, deadline, now=time.monotonic):
    failure = None; reason = error = current = None
    calls = 0; transitions = []; previous = frozen = forecast_pin = None
    trajectory = checkpoint['checkpoint_id']+'-'+condition
    def emit(kind, **fields): sink(deepcopy(dict(kind=kind, **fields)))
    checks = 0
    def check():
        nonlocal checks
        checks += 1
        observed = now()
        if observed >= deadline:
            emit('admission_stop', check_index=checks, overrun_seconds=observed-deadline)
            raise AdmissionClosed('verified-feedback admission closed')
    try:
        if condition not in CONDITIONS: raise ValueError('unknown feedback condition')
        checked_pair(pair, checkpoint['current']['legal_actions']); check()
        current, history = restored(checkpoint, engine, emit, check)
        for decision in range(2):
            reason = terminal(current)
            if reason: break
            if any(action['action_id'] not in current['legal_actions'] for action in pair.values()):
                reason = 'candidate_set_invalid'; break
            check()
            base = request_for(checkpoint['initial'], checkpoint['initial_case']['geometry']['reviewed'],
                               current, history, len(history), checkpoint['base_request']['model'])
            context = {} if decision == 0 else dict(frozen=frozen, forecast_pin=forecast_pin,
                transition=transitions[0], transition_pin=digest(transitions[0]), current=current)
            body = make_request(base, pair, condition, previous, study_decision_index=decision,
                restored_prefix_length=len(checkpoint['prefix']), trajectory_id=trajectory, **context)
            emit('request', decision=decision, body=body, request_sha256=digest(body)); check()
            text = complete(deepcopy(body)); calls += 1
            emit('response', decision=decision, text=text); check()
            try: answer = parse_choice(text, first=decision == 0)
            except (ValueError, TypeError, RecursionError) as exc:
                reason, error = 'invalid_answer', str(exc); break
            action = deepcopy(pair[answer['selected_candidate']])
            if decision == 0:
                frozen = freeze_forecast(answer, pair, trajectory_id=trajectory,
                    study_decision_index=0, game_action_index=len(history), before=current)
                forecast_pin = digest(frozen)
                # A durable sink must finish this write before any dispatch is admitted.
                emit('forecast_commit', forecast=frozen, forecast_sha256=forecast_pin); check()
            emit('dispatch_intent', decision=decision, action=action, before_sha256=digest(current)); check()
            after = check_observation(engine.dispatch(deepcopy(action)))
            forecast = answer['candidate_predictions'][answer['selected_candidate']]
            record = {'step': len(history), 'before': deepcopy(current), 'after': deepcopy(after), 'action': action,
                      'predicted_visible_change': 'unknown' if forecast == 'unknown' else 'no' if forecast == 'none' else 'yes'}
            emit('transition', decision=decision, record=record, transition_sha256=digest(record), answer=answer)
            transitions.append(deepcopy(record)); history.append(deepcopy(record)); current = after; previous = answer
        reason = reason or terminal(current) or 'action_cap'
    except AdmissionClosed:
        # Preserve the exact observed prefix. The enclosing lifecycle still
        # enforces the separate hard deadline through cleanup/finalization.
        reason = 'deadline'
    except BaseException as exc:
        failure, error = exc, type(exc).__name__+': '+str(exc)
        reason = 'deadline' if isinstance(exc, TimeoutError) else 'exception'
    try: emit('closed', receipt=engine.close())
    except BaseException as exc:
        if failure is None: failure, error, reason = exc, str(exc), 'exception'
    result = {'checkpoint_id': checkpoint['checkpoint_id'], 'condition': condition, 'reason': reason, 'error': error,
              'model_calls': calls, 'new_dispatches': len(transitions), 'final_observation': current,
              'lifecycle_certified': False}
    emit('summary', **result)
    if failure is not None: raise failure
    return result
