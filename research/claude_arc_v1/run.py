"""Fresh-memory, sequential controller. No launch or inference at import time."""
import hashlib
import json
import os
from pathlib import Path
import time

from agent.framework_adapter import OutcomeUnknown
from .backends import BudgetExceeded
from .policy import Policy, observation_value


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
        self.sequence += 1
        body = {'sequence': self.sequence, 'previous_sha256': self.previous, 'kind': kind, **value}
        raw = json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False)
        self.previous = hashlib.sha256(raw.encode()).hexdigest()
        self.stream.write(json.dumps({**body, 'sha256': self.previous}, separators=(',', ':'), allow_nan=False) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


def evaluate(config, backend, adapter, evidence, *, now=time.monotonic, started_at=None):
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
        evidence.write('scorecard_open_entered')
        card = adapter.open_scorecard(tags=['claude-arc-v1', config.stage, config.mode])
        evidence.write('scorecard_open_acknowledged', card_id=card)
        for game in selected:
            if remaining() <= 0:
                problems.append('study_deadline')
                break
            backend.budget.check()  # do not consume a new environment when no model call can be admitted
            policy = Policy(config)  # deliberately fresh for each independent game
            row = {'game_id': game, 'actions_acknowledged': 0, 'actions_uncertain': 0,
                   'levels_completed': None, 'stop_reason': 'action_cap', 'same_action_unchanged_final_repeats': 0,
                   'prediction_scored': 0, 'prediction_correct': 0, 'prediction_abstained_or_unobservable': 0}
            client = None
            previous_action = None
            try:
                evidence.write('make_entered', game_id=game)
                client = adapter.bootstrap(game)
                initial = client.observation.levels_completed
                row['levels_completed'] = 0
                evidence.write('initial_observation', game_id=game, observation=observation_value(client.observation))
                for index in range(config.max_actions_per_game):
                    if client.observation.state.name in ('WIN', 'GAME_OVER'):
                        row['stop_reason'] = client.observation.state.name.lower()
                        break
                    if remaining() <= 0:
                        row['stop_reason'] = 'study_deadline'
                        break
                    before = client.observation
                    request = policy.request(before)
                    backend.budget.check()
                    evidence.write('model_entered', game_id=game, action_index=index, request=request)
                    result = backend.complete(request)
                    evidence.write('model_returned', game_id=game, content=result.content,
                                   metadata=backend.last_record, elapsed_seconds=result.elapsed_seconds)
                    decision, answer = policy.parse(result.content, before)
                    if remaining() <= 0:
                        raise TimeoutError('no action after study cutoff')
                    evidence.write('dispatch_entered', game_id=game, action_index=index,
                                   action={'action_id': decision.action_id, 'action_data': dict(decision.action_data)})
                    try:
                        after = adapter.dispatch(client, decision)
                    except OutcomeUnknown:
                        row['actions_uncertain'] += 1
                        raise
                    row['actions_acknowledged'] += 1
                    transition = policy.observe(before, decision, after, answer)
                    row['levels_completed'] = after.levels_completed - initial
                    if previous_action == transition['action'] and transition['observed']['final_frame_changed'] is False:
                        row['same_action_unchanged_final_repeats'] += 1
                    previous_action = transition['action']
                    for check in transition['prediction_checks'].values():
                        if check['correct'] is None:
                            row['prediction_abstained_or_unobservable'] += 1
                        else:
                            row['prediction_scored'] += 1
                            row['prediction_correct'] += check['correct']
                    evidence.write('transition', game_id=game, **transition)
                row['levels_completed'] = client.observation.levels_completed - initial
                if row['levels_completed'] < 0:
                    raise ValueError('level counter decreased')
            except Exception as exc:
                row['stop_reason'] = type(exc).__name__
                evidence.write('game_failed', game_id=game, error_type=type(exc).__name__,
                               backend_record=backend.last_record)
                # Unknown model billing, invalid output or uncertain game execution stops the entire attempt.
                problems.append(game + ': ' + type(exc).__name__)
                rows.append(row)
                break
            finally:
                if client is not None:
                    adapter.finalize_client(client)
            rows.append(row)
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
    summary = {'schema': 'claude_arc_v1', 'mode': config.mode, 'stage': config.stage, 'backend': config.backend,
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
