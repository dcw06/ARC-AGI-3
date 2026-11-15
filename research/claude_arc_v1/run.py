"""Fresh-memory, sequential controller. No launch or inference at import time."""
import hashlib
import json
import os
from pathlib import Path
import time
from contextlib import contextmanager

from agent.action import ActionDecision
from agent.framework_adapter import PreDispatchFailure
from .backends import BudgetExceeded
from .transport import TransportFailure
from .policy import Policy, observation_value
from . import recovery, resume


@contextmanager
def _commit_acknowledgement():
    """Keep a returned observation's event and counters coherent across real POSIX interrupts."""
    import signal
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM}) if hasattr(signal, 'pthread_sigmask') else None
    try:
        yield
    finally:
        if previous is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous)


class Evidence:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(self.folder, 0o700)
        self.path = self.folder / 'events.jsonl'
        self.stream = self.path.open('x', encoding='utf-8')
        os.chmod(self.path, 0o600)
        self.previous = '0' * 64
        self.sequence = 0

    def write(self, kind, **value):
        if {'sequence', 'previous_sha256', 'sha256'} & value.keys():
            raise ValueError('event payload uses a reserved chain field')
        self.sequence += 1
        body = {'sequence': self.sequence, 'previous_sha256': self.previous, 'kind': kind, **value}
        raw = json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False)
        self.previous = hashlib.sha256(raw.encode()).hexdigest()
        self.stream.write(json.dumps({**body, 'sha256': self.previous}, separators=(',', ':'), allow_nan=False) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


def evaluate(config, backend, adapter, evidence, *, now=time.monotonic, started_at=None, sleep=time.sleep,
             on_scorecard=None):
    start, rows, problems = now() if started_at is None else started_at, [], []
    card, close_result, selected = None, None, []
    def remaining():
        return config.run_seconds - config.cleanup_seconds - (now() - start)
    evidence.write('configuration', config=config.public())
    try:
        inventory = adapter.list_game_ids()
        if len(set(inventory)) != len(inventory) or not inventory:
            raise ValueError('invalid live game inventory')
        selected = list(inventory) if config.mode == 'competition' else []
        if config.mode == 'online':
            for requested in config.games:
                matches = [g for g in inventory if g == requested or g.split('-', 1)[0] == requested]
                if len(matches) != 1:
                    raise ValueError('requested game missing or ambiguous: ' + requested)
                if matches[0] in selected:
                    raise ValueError('duplicate resolved game')
                selected.append(matches[0])
        if remaining() <= 0:
            raise TimeoutError('study deadline before scorecard creation')
        evidence.write('inventory', games=list(inventory), selected=selected,
                       scoring_scope='all_available_environments' if config.mode == 'competition' else 'development')
        resumed = {}
        if config.resume_actions:
            # Read before any scorecard exists: a saved run that cannot be repeated must not open one.
            resumed = resume.load(config.resume_events, selected, config.resume_actions, config)
            evidence.write('resume_source', events_sha256=resume.file_sha256(config.resume_events),
                           actions_per_game=config.resume_actions)
        evidence.write('scorecard_open_entered')
        card = adapter.open_scorecard(tags=['claude-arc-v1', config.stage, config.mode])
        evidence.write('scorecard_open_acknowledged', card_id=card)
        if on_scorecard is not None:
            try:
                on_scorecard('https://arcprize.org/scorecards/' + card)
            except Exception:
                pass  # a display problem must never affect the run
        games_without_actions = 0
        for game in selected:
            if remaining() <= 0:
                problems.append('study_deadline')
                break
            backend.budget.check()  # do not consume a new environment when no model call can be admitted
            policy = Policy(config)  # deliberately fresh for each independent game
            row = {'game_id': game, 'actions_acknowledged': 0, 'actions_uncertain': 0,
                   'levels_completed': None, 'stop_reason': 'action_cap', 'same_action_unchanged_final_repeats': 0,
                   'prediction_scored': 0, 'prediction_correct': 0, 'prediction_abstained_or_unobservable': 0,
                   'final_state': None, 'last_dispatch_status': 'not_attempted'}
            # Register the attempted game before any operation that can be interrupted.
            # The same row is updated in place, never appended only on the success path.
            rows.append(row)
            client = None
            previous_action = None
            dispatch_pending = False
            model_stage = False
            replied = False
            try:
                evidence.write('make_entered', game_id=game)
                client = adapter.bootstrap(game)
                initial = client.observation.levels_completed
                row['levels_completed'] = 0
                row['final_state'] = client.observation.state.name
                evidence.write('initial_observation', game_id=game, observation=observation_value(client.observation))
                resets_used = 0
                if config.resets_per_game:
                    row['level_resets'] = 0
                # Recovery study state; all of it stays empty in the control.
                tracker = recovery.Tracker(client.observation.latest_frame) if config.recovery_on else None
                saved, replay = [], []
                if game in resumed:
                    if client.observation.canonical_hash != resumed[game]['initial_sha256']:
                        raise resume.Diverged('the first board differs from the saved run')
                    saved = list(resumed[game]['actions'])
                if tracker is not None or saved:
                    row.update(model_resets=0, recovery_checks=0, replayed_actions=0, resumed_actions=0)
                for index in range(config.max_actions_per_game):
                    state = client.observation.state.name
                    if state == 'WIN' or (state == 'GAME_OVER' and resets_used >= config.resets_per_game):
                        row['stop_reason'] = state.lower()
                        break
                    if remaining() <= 0:
                        row['stop_reason'] = 'study_deadline'
                        break
                    if config.stop_after_levels and row['levels_completed'] >= config.stop_after_levels:
                        row['stop_reason'] = 'level_target'
                        break
                    before = client.observation
                    expected = context = None   # saved observation hash to check; recovery facts for this turn
                    chosen_by_model = True
                    if saved:
                        # Repeat a saved action: no model call; the saved reply rebuilds the notes.
                        item = saved.pop(0)
                        decision = ActionDecision(item['action']['action_id'], dict(item['action']['action_data']),
                                                  source='controller_resume')
                        chosen_by_model = item['answer'] is not None
                        answer = item['answer'] or {'action': item['action'], 'hypotheses': list(policy.hypotheses)}
                        expected = item['after_sha256']
                        if decision.action_id == 0 and state == 'GAME_OVER':
                            resets_used += 1
                            row['level_resets'] = resets_used
                        row['resumed_actions'] += 1
                    elif state == 'GAME_OVER':
                        # Controller-issued level reset: no model call; the model's notes are carried forward.
                        resets_used += 1
                        row['level_resets'] = resets_used
                        decision = ActionDecision(0, {}, source='controller_level_reset')
                        answer = {'action': {'action_id': 0, 'action_data': {}}, 'hypotheses': list(policy.hypotheses)}
                        chosen_by_model = False
                    elif replay:
                        # Repeat the next action of the ended attempt: no model call.
                        action, expected = replay.pop(0)
                        decision = ActionDecision(action['action_id'], dict(action['action_data']),
                                                  source='controller_replay')
                        answer = {'action': action, 'hypotheses': list(policy.hypotheses)}
                        chosen_by_model = False
                        row['replayed_actions'] += 1
                    else:
                        decision, answer = None, None
                        if tracker is not None:
                            left = config.max_actions_per_game - index   # actions that can still be sent, this one included
                            baseline = recovery.baseline_for(config, game, tracker.level)
                            reasons = tracker.due(config, baseline)
                            context = {'check': recovery.check_block(tracker, reasons, config) if reasons else None,
                                       'offer': tracker.offer(left - 1 if config.recovery_pricing else None)
                                       if config.replay_after_reset else None,
                                       'may_reset': bool(tracker.attempt), 'baseline': baseline,
                                       'reset_pays_back': recovery.can_pay_back(left, baseline)}
                    request = policy.request(before, recovery=context) if decision is None else None
                    model_stage = decision is None
                    for attempt in range(1 + config.model_retries_per_action if model_stage else 0):
                        if attempt and remaining() <= 0:
                            raise TimeoutError('study deadline during model retry')
                        backend.budget.check()
                        evidence.write('model_entered', game_id=game, action_index=index, request=request,
                                       **({'attempt': attempt} if config.model_retries_per_action else {}))
                        replied = False
                        try:
                            result = backend.complete(request)
                            evidence.write('model_returned', game_id=game, content=result.content,
                                           metadata=backend.last_record, elapsed_seconds=result.elapsed_seconds)
                            replied = True
                            decision, answer = policy.parse(result.content, before, recovery=context)
                            break
                        except Exception as exc:
                            # No game action has been sent for this request, so another request is safe.
                            if attempt == config.model_retries_per_action or isinstance(exc, (BudgetExceeded, PermissionError)):
                                raise
                            evidence.write('model_failed_retrying', game_id=game, action_index=index, attempt=attempt,
                                           error_type=type(exc).__name__, error=str(exc)[:500],
                                           backend_record=backend.last_record)
                            if isinstance(exc, TransportFailure):
                                # No reply (CLI error, timeout, network): wait, then resend the same request.
                                sleep(max(0, min(config.model_retry_backoff_seconds, remaining())))
                            elif replied:
                                # A received but rejected reply: tell the model why, so the retry can correct it.
                                request = policy.request(before, rejection='%s: %s' % (type(exc).__name__, exc),
                                                         recovery=context)
                    model_stage = False
                    if context is not None:
                        if context['check']:
                            tracker.checked(context['check']['why'], answer['recovery'], context['baseline'])
                            row['recovery_checks'] += 1
                            evidence.write('recovery_check', game_id=game, action_index=index,
                                           facts=context['check'], answer=answer['recovery'])
                        if answer.get('replay'):
                            # The controller repeats the ended attempt's opening; the model's own action is not sent.
                            queue = [(item['action'], item['after_sha256'])
                                     for item in tracker.ended_attempt[:answer['replay']]]
                            evidence.write('replay_entered', game_id=game, action_index=index, actions=len(queue),
                                           model_action_not_sent=answer['action'])
                            (action, expected), replay = queue[0], queue[1:]
                            decision = ActionDecision(action['action_id'], dict(action['action_data']),
                                                      source='controller_replay')
                            chosen_by_model = False
                            # The model's prediction was about its own action, which is not sent.
                            answer = {k: v for k, v in answer.items() if k != 'prediction'}
                            row['replayed_actions'] += 1
                        if decision.action_id == 0 and not tracker.attempt:
                            # Never reachable through the policy; a second lock on the whole-game restart.
                            raise ValueError('reset before the first action of an attempt')
                    if remaining() <= 0:
                        raise TimeoutError('no action after study cutoff')
                    dispatch_pending = True
                    evidence.write('dispatch_entered', game_id=game, action_index=index,
                                   action={'action_id': decision.action_id, 'action_data': dict(decision.action_data)})
                    try:
                        after = adapter.dispatch(client, decision)
                    except PreDispatchFailure:
                        # Proven pre-transport rejection is not an uncertain executed input.
                        dispatch_pending = False
                        row['last_dispatch_status'] = 'not_sent'
                        evidence.write('dispatch_not_sent', game_id=game, action_index=index)
                        raise
                    transition = policy.observe(before, decision, after, answer)
                    with _commit_acknowledgement():
                        evidence.write('transition', game_id=game, **transition)
                        row['actions_acknowledged'] += 1
                        row['last_dispatch_status'] = 'acknowledged'
                        row['levels_completed'] = after.levels_completed - initial
                        row['final_state'] = after.state.name
                        if previous_action == transition['action'] and transition['observed']['final_frame_changed'] is False:
                            row['same_action_unchanged_final_repeats'] += 1
                        previous_action = transition['action']
                        for check in transition['prediction_checks'].values():
                            if check['correct'] is None:
                                row['prediction_abstained_or_unobservable'] += 1
                            else:
                                row['prediction_scored'] += 1
                                row['prediction_correct'] += check['correct']
                        dispatch_pending = False
                    if tracker is not None:
                        facts = tracker.record(transition['transition_id'], decision, before, after,
                                               by_model=chosen_by_model,
                                               notes=policy.hypotheses if policy.rank >= 2 else None)
                        evidence.write('recovery_state', game_id=game, action_index=index, source=decision.source, **facts)
                        if decision.action_id == 0 and decision.source == 'api_evaluation':
                            row['model_resets'] += 1
                        if decision.action_id == 0 and after.levels_completed != before.levels_completed:
                            # A reset must restart the level only. Do not play on in a restarted game.
                            raise recovery.WholeGameReset('a reset changed the number of completed levels')
                    if expected is not None and after.canonical_hash != expected:
                        if decision.source == 'controller_resume':
                            # The matched start is the point of a resume: do not play on from a different position.
                            raise resume.Diverged('resume differed from the saved run at action %d' % (index + 1))
                        evidence.write('replay_diverged', game_id=game, action_index=index, actions_dropped=len(replay))
                        replay = []
                    if row['levels_completed'] < 0:
                        raise ValueError('level counter decreased')
                    # A terminal result on the final permitted action still takes precedence over action_cap.
                    # GAME_OVER continues only when a level reset remains and an action remains to send it.
                    if row['final_state'] == 'WIN' or (row['final_state'] == 'GAME_OVER' and (
                            resets_used >= config.resets_per_game or index == config.max_actions_per_game - 1)):
                        row['stop_reason'] = row['final_state'].lower()
                        break
            except BaseException as exc:
                if dispatch_pending:
                    row['actions_uncertain'] += 1
                    row['last_dispatch_status'] = 'outcome_unknown'
                    # final_state and levels_completed remain the last acknowledged observation;
                    # an adapter mutating its client before interruption is not a returned observation.
                row['stop_reason'] = type(exc).__name__
                problems.append(game + ': ' + type(exc).__name__)
                evidence.write('game_failed', game_id=game, error_type=type(exc).__name__, error=str(exc)[:500],
                               dispatch_unresolved=dispatch_pending, backend_record=backend.last_record)
                # With next_game, only an unusable reply ends just this game. An infrastructure failure
                # (TransportFailure: usage limit, login, network, CLI) would fail every later game too, so it stops
                # the attempt instead of initializing and discarding the remaining environments.
                if isinstance(exc, (resume.Diverged, recovery.WholeGameReset)) and not dispatch_pending:
                    continue   # this game cannot be used; the others are unaffected
                if (config.on_model_failure == 'next_game' and model_stage and not dispatch_pending
                        and isinstance(exc, Exception)
                        and not isinstance(exc, (BudgetExceeded, PermissionError, TimeoutError, TransportFailure))):
                    games_without_actions = games_without_actions + 1 if row['actions_acknowledged'] == 0 else 0
                    if games_without_actions < 3:
                        continue
                    problems.append('stopped: three consecutive games ended before any action')
                # Otherwise unknown model billing, invalid output or uncertain game execution stops the entire attempt.
                break
            finally:
                if client is not None:
                    adapter.finalize_client(client)
            games_without_actions = 0  # reached only by a game that ended without failing
    except BaseException as exc:
        problems.append('controller: ' + type(exc).__name__)
    finally:
        # Closing is attempted once, even after failure/interruption. Never open a replacement scorecard.
        adapter._evaluation_cleanup = True
        if card is not None:
            try:
                evidence.write('scorecard_close_entered', card_id=card)
            except BaseException as exc:
                problems.append('close_intent_log: ' + type(exc).__name__)
            try:
                close_result = adapter.close_scorecard()
            except BaseException as exc:
                problems.append('scorecard_close: ' + type(exc).__name__)
            else:
                try:
                    evidence.write('scorecard_close_acknowledged', result=close_result)
                except BaseException as exc:
                    problems.append('close_result_log: ' + type(exc).__name__)
    summary = {'schema': 'claude_arc_v1', 'report_revision': 2, 'mode': config.mode, 'stage': config.stage, 'backend': config.backend,
        'model': config.model, 'exposure': config.exposure, 'games': rows, 'problems': problems,
        'scorecard_id': card, 'scorecard_url': 'https://arcprize.org/scorecards/' + card if card else None,
        'official_scorecard': close_result, 'budget': backend.budget.report(), 'elapsed_seconds': now() - start,
        'selected_games': selected, 'games_not_started': [g for g in selected if g not in {r['game_id'] for r in rows}],
        'full_lifecycle_complete': False, 'engine_replay_verified': False,
        'interpretation': 'exposed development unless a separately reviewed evaluation/exposure ledger establishes otherwise'}
    evidence.write('summary', summary=summary)
    # The receipt cannot mark complete before the event file is finalized.
    evidence.close()
    elapsed = now() - start
    summary['elapsed_seconds'] = elapsed
    summary['full_lifecycle_complete'] = not problems and card is not None and close_result is not None and elapsed <= config.run_seconds
    raw = (json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    temporary = evidence.folder / 'summary.json.partial'
    with temporary.open('xb') as stream:
        os.chmod(temporary, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Reject late finalization; do not publish a successful receipt after the limit.
    if now() - start > config.run_seconds:
        summary['full_lifecycle_complete'] = False
        temporary.unlink()
        (evidence.folder / 'failed-finalization.json').write_text(json.dumps({'error': 'finalization_deadline'}))
        return summary
    os.replace(temporary, evidence.folder / 'summary.json')
    if now() - start > config.run_seconds:
        summary['full_lifecycle_complete'] = False
        (evidence.folder / 'summary.json').unlink()
        (evidence.folder / 'failed-finalization.json').write_text(json.dumps({'error': 'finalization_deadline'}))
    return summary
