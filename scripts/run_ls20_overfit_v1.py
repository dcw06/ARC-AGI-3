"""Run the fitted ls20 policy on a fresh local engine, then reconstruct it once.

CPU-only, no online calls or model inference. Requires pinned existing local
game assets. No implicit reset, fallback action, retry or output overwrite.
"""
import argparse
from copy import deepcopy
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run_episode(program, engine, journal, deadline):
    from research.ls20_overfit_v1.policy import OverfitPolicy
    from research.initial_geometry_assistance_v1.policy import check_observation
    from research.initial_geometry_assistance_v1.geometry import digest
    policy = OverfitPolicy(program)
    events, boundaries, error, current = [], [], None, None
    moves = 0
    def emit(kind, **values):
        event = deepcopy(dict(kind=kind, **values))
        journal(event)
        events.append(event)
    def check():
        if time.monotonic() >= deadline:
            raise TimeoutError('ls20 overfit admission closed')
    try:
        check(); emit('bootstrap_intent', seed=program['seed']); check()
        current = check_observation(engine.bootstrap())
        emit('initial', observation=current)
        while not policy.completed:
            check()
            action = policy.select(program['game_id'], current)
            before = current
            emit('dispatch_intent', index=policy.cursor, before_sha256=digest(before), action=action)
            check()
            current = check_observation(engine.dispatch(action))
            moves += 1
            emit('transition', index=policy.cursor, before=before, action=action, after=current)
            policy.acknowledge(action, current)
            if current['levels_completed'] > before['levels_completed']:
                boundary = dict(level=current['levels_completed'], after_moves=moves,
                    moves=moves-(boundaries[-1]['after_moves'] if boundaries else 0))
                boundaries.append(boundary)
                emit('level_completed', **boundary)
        if current['levels_completed'] < 3:
            raise ValueError('policy exhausted without three observed completions')
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        try:
            emit('closed', receipt=engine.close())
        except BaseException as exc:
            error = (error + '; ' if error else '') + 'cleanup: ' + type(exc).__name__ + ': ' + str(exc)
    result = dict(success=error is None and policy.completed and current is not None
                  and current['levels_completed'] >= 3,
        moves=moves, levels_completed=None if current is None else current['levels_completed'],
        level_boundaries=boundaries, error=error, final_observation=current,
        model_generations=0, reason='three_levels_completed' if error is None else 'stopped_on_error')
    emit('summary', **result)
    return result, events


def worker(args):
    from research.initial_geometry_assistance_v1.live_io import Journal, sha, write_new
    from research.initial_geometry_assistance_v1.live_resources import environment
    from research.initial_geometry_assistance_v1.geometry import digest
    from research.verified_feedback_live_v1.engine import FeedbackEngine
    program = json.loads(args.program.read_bytes())
    phases = {}
    for phase in ('study', 'fresh_reconstruction'):
        if time.monotonic() >= args.work_deadline:
            raise TimeoutError('episode admission closed')
        directory = args.output/phase
        directory.mkdir(exist_ok=False)
        operations = []
        engine = FeedbackEngine(args.game_python, program['game_id'],
            args.game_environment/'environment_files', directory/'recordings',
            directory/'engine.log', args.work_deadline,
            cleanup_deadline=args.work_deadline+20,
            env=dict(environment(), PYTHONPATH=str(ROOT), CUDA_VISIBLE_DEVICES='',
                     NVIDIA_VISIBLE_DEVICES='void'), on_effect=operations.append)
        journal = Journal(directory/'events.jsonl')
        try:
            result, events = run_episode(program, engine, journal, args.work_deadline)
        finally:
            journal.close()
        if operations != ['bootstrap'] + ['dispatch']*result['moves'] + ['close']:
            raise ValueError('actual engine operations differ')
        closed = [e['receipt'] for e in events if e['kind'] == 'closed']
        if closed != [dict(closed=True, local_scorecard_opened=True,
                           local_scorecard_closed=True, online_calls=0)]:
            raise ValueError('local engine did not close its scorecard')
        phases[phase] = dict(result=result, events=events, operations=operations)
        write_new(directory/'result.json', dict(result=result, operations=operations,
            events_sha256=sha(directory/'events.jsonl'), event_content_sha256=digest(events)))
        print(json.dumps(dict(phase=phase,success=result['success'],moves=result['moves'],
            levels_completed=result['levels_completed'],error=result['error'])), flush=True)
        if not result['success']:
            raise ValueError('episode did not reproduce the fitted demonstration; no retry')
    if phases['study'] != phases['fresh_reconstruction']:
        raise ValueError('fresh-engine reconstruction differs')
    result = phases['study']['result']
    if result['level_boundaries'] != program['level_boundaries']:
        raise ValueError('observed level boundaries differ from training trace')
    write_new(args.output/'results.json', dict(schema='ls20_overfit_v1_CPU_results',
        success=True, game_id=program['game_id'], seed=program['seed'],
        levels_completed=result['levels_completed'], moves=result['moves'],
        level_boundaries=result['level_boundaries'], fresh_reconstruction_matches=True,
        program_sha256=args.program_sha256, source_demo_sha256=program['source_demo_sha256'],
        event_files_sha256={phase:sha(args.output/phase/'events.jsonl') for phase in phases},
        event_content_sha256=digest(phases['study']['events']),
        total_directional_actions_including_reconstruction=2*result['moves'],
        resets=2, local_scorecards=2, online_calls=0, GPU_jobs=0,
        model_generations=0, provider_writes=0, automatic_retries=0,
        package_versions={name:importlib.metadata.version(name) for name in ('arc-agi','arcengine')},
        qualification='Deliberately fitted to the owner demonstration on this exact game and seed. No VLM training, new rule discovery or transfer claim.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program', type=Path, required=True)
    parser.add_argument('--program-sha256', required=True)
    parser.add_argument('--game-environment', type=Path, required=True)
    parser.add_argument('--game-receipt-sha256', required=True)
    parser.add_argument('--game-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--work-deadline', type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    from research.initial_geometry_assistance_v1.live_io import sha, write_new
    if sha(args.program) != args.program_sha256:
        raise ValueError('fitted policy changed')
    if args.worker:
        if os.environ.get('LS20_OVERFIT_OWNED') != '1' or args.work_deadline is None:
            raise PermissionError('owned worker required')
        worker(args)
        return
    if os.name != 'posix' or not Path('/proc').is_dir():
        raise ValueError('Linux/WSL required')
    from research.ls20_overfit_v1.policy import OverfitPolicy
    from research.initial_geometry_assistance_v1.engine import verify_game_environment
    from research.initial_geometry_assistance_v1.live_resources import HardDeadline, Processes, environment
    from research.feedback_probe_v1.source_closure import source_inventory
    OverfitPolicy(json.loads(args.program.read_bytes()))
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    final_deadline = started+600
    work_deadline = final_deadline-30
    watchdog = HardDeadline(final_deadline)
    watchdog.start()
    processes = Processes(watchdog)
    completed = False
    try:
        def check():
            if time.monotonic() >= work_deadline:
                raise TimeoutError('CPU verification deadline')
        verify_game_environment(args.game_environment, args.game_receipt_sha256, check=check)
        inventory = source_inventory(ROOT, ['scripts/run_ls20_overfit_v1.py'])
        write_new(args.output/'source-manifest.json', inventory)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:],
                   '--worker', '--work-deadline', str(work_deadline)]
        processes.command(command,args.output/'worker.log',work_deadline,
            dict(environment(),PYTHONPATH=str(ROOT),PYTHONDONTWRITEBYTECODE='1',
                 CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void',LS20_OVERFIT_OWNED='1'),
            'Fitted ls20 three-level CPU run and fresh reconstruction')
        if sha(args.program) != args.program_sha256 or any(sha(ROOT/n)!=h for n,h in inventory.items()):
            raise ValueError('policy or source changed during run')
        completed = True
    finally:
        cleanup = processes.stop(final_deadline)
        if cleanup['groups_absent'] is not True or cleanup['error'] or cleanup['interrupted']:
            raise ValueError('process cleanup unverified')
        if time.monotonic() >= final_deadline:
            raise TimeoutError('CPU lifecycle deadline')
        write_new(args.output/'lifecycle.json',dict(worker_finished=completed,
            process_cleanup=cleanup, elapsed_seconds=time.monotonic()-started,
            source_manifest_sha256=sha(args.output/'source-manifest.json')
                if (args.output/'source-manifest.json').exists() else None,
            program_sha256=args.program_sha256, game_receipt_sha256=args.game_receipt_sha256,
            results_sha256=sha(args.output/'results.json') if (args.output/'results.json').exists() else None))
        if time.monotonic() >= final_deadline:
            raise TimeoutError('CPU final receipt deadline')
        watchdog.close()
        if time.monotonic() >= final_deadline:
            raise TimeoutError('CPU final deadline')
    print('Three-level ls20 policy validated; CPU lifecycle closed.', flush=True)


if __name__ == '__main__':
    main()
