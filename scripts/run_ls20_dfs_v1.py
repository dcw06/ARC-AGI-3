"""Linux CPU-only DFS episode plus independent engine replay; no model/provider calls.

Requires an existing pinned game interpreter and local game environment. New
VLM inference belongs to a separately reviewed package; --assessment consumes
a local color answer only. Existing files are never overwritten.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial', type=Path, required=True)
    parser.add_argument('--initial-sha256', required=True)
    parser.add_argument('--game-environment', type=Path, required=True)
    parser.add_argument('--game-receipt-sha256', required=True)
    parser.add_argument('--game-python', type=Path, required=True)
    parser.add_argument('--assessment', type=Path, help='Optional {"path_color_id": integer or null}; no model call')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=300, choices=range(60, 601))
    parser.add_argument('--action-cap', type=int, default=24, choices=range(1, 25))
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--work-deadline', type=float, help=argparse.SUPPRESS)
    return parser.parse_args()


def worker(args):
    from research.initial_geometry_assistance_v1.live_io import Journal, write_new, sha
    from research.initial_geometry_assistance_v1.live_resources import environment
    from research.initial_geometry_assistance_v1.geometry import digest
    from research.verified_feedback_live_v1.engine import FeedbackEngine
    from research.ls20_dfs_v1.controller import run_episode
    from research.ls20_dfs_v1.audit import audit_episode
    from research.ls20_knn_path_v1.policy import parse_assessment
    if sha(args.initial) != args.initial_sha256: raise ValueError('initial board changed')
    initial = json.loads(args.initial.read_bytes())
    assessment = parse_assessment(args.assessment.read_text()) if args.assessment else None
    journal = Journal(args.output/'events.jsonl')
    effects = {'study': [], 'replay': []}
    def engine(phase):
        return FeedbackEngine(args.game_python, 'ls20-9607627b', args.game_environment/'environment_files',
            args.output/(phase+'-recordings'), args.output/(phase+'-engine.log'), args.work_deadline,
            cleanup_deadline=args.work_deadline+30,
            env=dict(environment(), PYTHONPATH=str(ROOT), CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void'),
            on_effect=effects[phase].append)
    try:
        result = run_episode(initial, engine('study'), journal, assessment=assessment,
                             deadline=args.work_deadline, action_cap=args.action_cap)
    finally: journal.close()
    retained = [json.loads(line) for line in (args.output/'events.jsonl').read_text().splitlines()]
    audit = audit_episode(initial, retained, lambda: engine('replay'), assessment=assessment,
                          action_cap=args.action_cap, model_enabled=False)
    if result != audit['result']: raise ValueError('independent DFS replay differs')
    expected = ['bootstrap']+['dispatch']*result['new_dispatches']+['close']
    if effects['study'] != expected or effects['replay'] != expected:
        raise ValueError('real engine operations differ from retained accounting')
    receipt = dict(result=result, independent_audit=audit,
        initial_sha256=args.initial_sha256, assessment_sha256=sha(args.assessment) if args.assessment else None,
        events_sha256=sha(args.output/'events.jsonl'), effects=effects,
        # The parent still captures stdout in CPU-worker.log until this worker
        # exits. The parent seals that log afterward, never with a premature hash.
        run_files_sha256={p.relative_to(args.output).as_posix():sha(p) for p in args.output.rglob('*')
                          if p.is_file() and p.name != 'CPU-worker.log'},
        content_sha256=digest(retained), GPU_jobs=0, neural_generations=0, provider_writes=0,
        qualification='Real-engine CPU navigation and independent replay; not a VLM navigation result.')
    write_new(args.output/'CPU-result.json', receipt)
    if time.monotonic() >= args.work_deadline: raise TimeoutError('CPU evidence finalization exceeded deadline')
    print(json.dumps(dict(cross_reached=result['cross_reached'],reason=result['reason'],
                         actions=result['new_dispatches'],model_calls=0,independent_replay=True)), flush=True)


def main():
    args = arguments()
    if args.worker:
        if (os.environ.get('LS20_DFS_CPU_OWNED') != '1' or args.work_deadline is None or
                not args.output.is_dir()): raise PermissionError('owned CPU worker required')
        worker(args); return
    if os.name != 'posix' or not Path('/proc').is_dir(): raise ValueError('use a Linux/WSL interpreter')
    from research.initial_geometry_assistance_v1.live_resources import HardDeadline, Processes, environment
    from research.initial_geometry_assistance_v1.live_io import sha, write_new
    from research.initial_geometry_assistance_v1.engine import verify_game_environment
    from research.feedback_probe_v1.source_closure import source_inventory
    if args.initial.stat().st_size > 100_000 or sha(args.initial) != args.initial_sha256:
        raise ValueError('pinned initial board differs or exceeds size limit')
    if args.assessment and args.assessment.stat().st_size > 1024: raise ValueError('color assessment exceeds size limit')
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); deadline = started+args.seconds; work = deadline-30
    watchdog = HardDeadline(deadline); watchdog.start(); processes = Processes(watchdog)
    passed = False
    def check():
        if time.monotonic() >= work: raise TimeoutError('CPU work deadline')
    try:
        game = verify_game_environment(args.game_environment, args.game_receipt_sha256, check=check)
        inventory = source_inventory(ROOT, ['scripts/run_ls20_dfs_v1.py', 'research/ls20_dfs_v1/audit.py'])
        write_new(args.output/'source-manifest.json', inventory)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:], '--worker', '--work-deadline', str(work)]
        processes.command(command, args.output/'CPU-worker.log', work,
            dict(environment(), PYTHONPATH=str(ROOT), CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void',
                 LS20_DFS_CPU_OWNED='1'), 'Owned offline DFS and independent replay')
        if any(sha(ROOT/name) != pin for name,pin in inventory.items()): raise ValueError('source changed during CPU test')
        passed = True
    finally:
        cleanup = processes.stop(deadline)
        if not cleanup['groups_absent'] or cleanup['error'] or cleanup['interrupted']:
            raise ValueError('CPU process cleanup not verified')
        watchdog.close()
        if time.monotonic() >= deadline: raise TimeoutError('CPU cleanup exceeded final deadline')
        write_new(args.output/'CPU-lifecycle.json', dict(passed=passed, elapsed_seconds=time.monotonic()-started,
            process_cleanup=cleanup, GPU_jobs=0, neural_generations=0, provider_writes=0,
            run_files_sha256={p.relative_to(args.output).as_posix():sha(p) for p in args.output.rglob('*') if p.is_file()},
            worker_result_sha256=sha(args.output/'CPU-result.json') if (args.output/'CPU-result.json').exists() else None))
        if time.monotonic() >= deadline: raise TimeoutError('CPU final receipt exceeded deadline')
    print(json.dumps(dict(passed=passed, result=str(args.output/'CPU-result.json'), GPU_jobs=0,
                         neural_generations=0, provider_writes=0)), flush=True)


if __name__ == '__main__': main()
