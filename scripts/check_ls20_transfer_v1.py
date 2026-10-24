"""Bounded unchanged-controller transfer check, with an ls20 positive control.

Uses existing pinned local game assets and interpreter. No model, GPU, online
game calls, policy adaptation, hidden-state inspection or automatic retry.
Each game runs once and is independently reconstructed in a fresh engine.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GAME_IDS = ('ls20-9607627b', 'ka59-38d34dbb')


def contract(observation):
    """Diagnose the existing recognizers without changing the policy."""
    from research.ls20_knn_path_v1.geometry import player, cross
    from research.ls20_pattern_goal_v1.patterns import locate_panels
    result = {}
    for name, function in (('player', player), ('cross', cross), ('panels', locate_panels)):
        try:
            function(observation['grid'])
            result[name] = {'supported': True, 'error': None}
        except ValueError as exc:
            result[name] = {'supported': False, 'error': str(exc)}
    return result


def episode(initial, engine, journal, deadline):
    """Retain expected policy refusals as outcomes, never as engine successes."""
    from research.ls20_object_memory_v1.controller import run_levels
    events = []
    def emit(event):
        events.append(deepcopy(event))
        journal(event)
    raised = None
    try:
        result = run_levels(initial, engine, emit, deadline=deadline,
                            max_levels=1, action_cap=96, per_level_cap=96)
    except ValueError as exc:
        raised = type(exc).__name__ + ': ' + str(exc)
        summaries = [e for e in events if e['kind'] == 'summary']
        if (len(summaries) != 1 or summaries[0]['reason'] != 'exception'
                or summaries[0]['error'] != raised):
            raise
        result = {k: v for k, v in summaries[0].items() if k != 'kind'}
    return result, events, raised


def worker(args):
    from research.initial_geometry_assistance_v1.geometry import digest
    from research.initial_geometry_assistance_v1.live_io import Journal, write_new, sha
    from research.initial_geometry_assistance_v1.live_resources import environment
    from research.verified_feedback_live_v1.engine import FeedbackEngine
    inputs = json.loads(args.inputs.read_bytes())
    if set(inputs) != set(GAME_IDS):
        raise ValueError('exact positive-control and transfer inputs required')
    outcomes = []
    for game_id in GAME_IDS:
        initial = inputs[game_id]
        recognizers = contract(initial)
        by_phase = {}
        for phase in ('study', 'independent_replay'):
            if time.monotonic() >= args.work_deadline:
                raise TimeoutError('transfer check admission closed')
            directory = args.output / game_id / phase
            directory.mkdir(parents=True, exist_ok=False)
            operations = []
            engine = FeedbackEngine(args.game_python, game_id,
                args.game_environment/'environment_files', directory/'recordings',
                directory/'engine.log', args.work_deadline,
                cleanup_deadline=args.work_deadline+20,
                env=dict(environment(), PYTHONPATH=str(ROOT), CUDA_VISIBLE_DEVICES='',
                         NVIDIA_VISIBLE_DEVICES='void'), on_effect=operations.append)
            journal = Journal(directory/'events.jsonl')
            try:
                result, events, raised = episode(initial, engine, journal, args.work_deadline)
            finally:
                journal.close()
            if operations != ['bootstrap'] + ['dispatch']*result['new_dispatches'] + ['close']:
                raise ValueError('engine operation accounting differs')
            if not any(e['kind'] == 'closed' and e['receipt'] == dict(
                    closed=True, local_scorecard_opened=True, local_scorecard_closed=True,
                    online_calls=0) for e in events):
                raise ValueError('local engine scorecard not closed')
            by_phase[phase] = dict(result=result, events=events, raised=raised,
                                   operations=operations)
            write_new(directory/'result.json', dict(result=result, raised=raised,
                operations=operations, event_content_sha256=digest(events),
                events_file_sha256=sha(directory/'events.jsonl')))
        study, replay = by_phase['study'], by_phase['independent_replay']
        if study != replay:
            raise ValueError('fresh-engine reconstruction differs')
        result = study['result']
        outcome = dict(game_id=game_id, recognizers=recognizers,
            initial_observation_sha256=digest(initial),
            legal_actions=initial['legal_actions'], completed=result['success'],
            levels_gained=result['levels_gained'], moves=result['new_dispatches'],
            encounters=len(result['memory']['events']), stop_reason=result['reason'],
            error=result['error'], independent_replay_verified=True,
            event_content_sha256=digest(study['events']),
            study_events_sha256=sha(args.output/game_id/'study/events.jsonl'),
            replay_events_sha256=sha(args.output/game_id/'independent_replay/events.jsonl'))
        outcomes.append(outcome)
        print(json.dumps(outcome), flush=True)
    write_new(args.output/'comparison.json', dict(schema='ls20_transfer_v1',
        unchanged_controller=True, controller_base_commit='cbed4373190a0b7958b0598d9312aef507d88fa7',
        per_episode_action_cap=96, max_levels=1, outcomes=outcomes,
        total_directional_moves_including_replay=2*sum(o['moves'] for o in outcomes),
        resets=4, local_scorecards=4, model_generations=0, GPU_jobs=0,
        online_game_calls=0, provider_writes=0, automatic_retries=0,
        qualification='Unchanged supplied-rule deterministic controller; not a VLM transfer test.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--game-environment', type=Path, required=True)
    parser.add_argument('--game-receipt-sha256', required=True)
    parser.add_argument('--game-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--work-deadline', type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    from research.initial_geometry_assistance_v1.live_io import sha, write_new
    if sha(args.inputs) != args.inputs_sha256:
        raise ValueError('frozen input observations changed')
    if args.worker:
        if os.environ.get('LS20_TRANSFER_OWNED') != '1' or args.work_deadline is None:
            raise PermissionError('owned worker required')
        worker(args)
        return
    if os.name != 'posix' or not Path('/proc').is_dir():
        raise ValueError('Linux/WSL required')
    from research.initial_geometry_assistance_v1.live_resources import HardDeadline, Processes, environment
    from research.initial_geometry_assistance_v1.engine import verify_game_environment
    from research.feedback_probe_v1.source_closure import source_inventory
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    final_deadline = started + 300
    work_deadline = final_deadline - 30
    watchdog = HardDeadline(final_deadline)
    watchdog.start()
    processes = Processes(watchdog)
    try:
        def check():
            if time.monotonic() >= work_deadline:
                raise TimeoutError('transfer verification deadline')
        verify_game_environment(args.game_environment, args.game_receipt_sha256, check=check)
        inventory = source_inventory(ROOT, ['scripts/check_ls20_transfer_v1.py'])
        write_new(args.output/'source-manifest.json', inventory)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:],
                   '--worker', '--work-deadline', str(work_deadline)]
        processes.command(command, args.output/'worker.log', work_deadline,
            dict(environment(), PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1',
                 CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', LS20_TRANSFER_OWNED='1'),
            'Unchanged-controller real-engine transfer and positive control')
        if any(sha(ROOT/name) != pin for name, pin in inventory.items()):
            raise ValueError('source changed during test')
    finally:
        cleanup = processes.stop(final_deadline)
        if cleanup['groups_absent'] is not True or cleanup['error'] or cleanup['interrupted']:
            raise ValueError('CPU process cleanup not verified')
        if time.monotonic() >= final_deadline:
            raise TimeoutError('transfer lifecycle deadline')
        write_new(args.output/'lifecycle.json', dict(
            process_cleanup=cleanup, elapsed_seconds=time.monotonic()-started,
            inputs_sha256=args.inputs_sha256, game_receipt_sha256=args.game_receipt_sha256,
            comparison_sha256=sha(args.output/'comparison.json') if (args.output/'comparison.json').exists() else None))
        if time.monotonic() >= final_deadline:
            raise TimeoutError('transfer final receipt deadline')
        watchdog.close()
        if time.monotonic() >= final_deadline:
            raise TimeoutError('transfer final deadline')
    print('Local transfer check and cleanup finished; see comparison.json.', flush=True)


if __name__ == '__main__':
    main()
