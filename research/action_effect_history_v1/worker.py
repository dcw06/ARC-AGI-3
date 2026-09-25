"""Game worker (game interpreter): model host, bridge admission, and the comparison run."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from certification.phase4_integrated_v2.bridge import ModelProxy
from certification.phase4_integrated_v2.evidence import EvidenceStore
from .service import ProxyService

ROOT = Path(__file__).resolve().parents[2]
FAULTS = ('none', 'model_startup', 'transport', 'slow', 'invalid_history', 'storage', 'surviving_child')
REHEARSAL_ARTIFACT = {'rehearsal': 'scripted_model_not_target_evidence'}


def gate(mode):
    if mode == 'live':
        from .authority import require
        return require()
    if mode == 'rehearsal':
        from .authority import rehearsal_gate
        return rehearsal_gate()
    raise ValueError('mode')


def stage_games(mode, environments, scratch):
    from research.grounded_action_v1.engine import restore_game_mount, verified_game_mount
    if mode == 'live':
        from certification.phase4_v2.package import verify_environment_mount
        manifest = json.loads((ROOT / 'reports/phase4_v2_offline_package.json').read_bytes())
        verify_environment_mount(Path(environments), manifest)
        return verified_game_mount(Path(environments), scratch / 'staged-games')
    supplied = Path(environments)
    if supplied.is_dir():  # rehearsal harness pre-stages the manifest-verified development games
        return verified_game_mount(supplied, scratch / 'staged-games')
    return verified_game_mount(restore_game_mount(scratch / 'restored-games'), scratch / 'staged-games')


def run_worker(output, scratch, environments, model_python, *, deadline, mode, fault='none'):
    gate(mode)  # before model subprocess, game import or GPU access
    if fault not in FAULTS or (mode == 'live' and fault != 'none'):
        raise PermissionError('faults are rehearsal-only')
    output, scratch = Path(output), Path(scratch)
    model_python = Path(model_python).absolute()
    if mode == 'live' and (model_python == Path(sys.executable).absolute() or not model_python.is_file()):
        raise ValueError('distinct pinned model and game interpreters required')
    if time.monotonic() >= deadline:
        raise TimeoutError('worker admission closed')
    games = stage_games(mode, environments, scratch)
    store = EvidenceStore(output, 'worker')
    cancel = output / 'control/cancel.json'
    env = dict(os.environ)
    restored = env.pop('P4_MODEL_CUDA_VISIBLE_DEVICES', None)
    if restored is None:
        env.pop('CUDA_VISIBLE_DEVICES', None)
    else:
        env['CUDA_VISIBLE_DEVICES'] = restored
    if mode == 'rehearsal':
        env['CUDA_VISIBLE_DEVICES'] = ''
    host_fault = fault if fault in ('model_startup', 'transport', 'slow', 'invalid_history') else 'none'
    host = subprocess.Popen([str(model_python), '-m', 'research.action_effect_history_v1.host',
                             '--socket', str(scratch / 'model.sock'), '--evidence', str(output),
                             '--cancel', str(cancel), '--deadline', str(deadline), '--mode', mode,
                             '--fault', host_fault], env=env, cwd=ROOT)  # inherits the owned worker group
    store.save('model-process.json', {'pid': host.pid, 'started_monotonic': time.monotonic()})
    if fault == 'surviving_child':  # rehearsal: a descendant that ignores SIGTERM and outlives the worker
        subprocess.Popen([sys.executable, '-c', 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(600)'])
    try:
        until = min(deadline, time.monotonic() + 900)
        while not (scratch / 'model.sock').exists():
            if host.poll() is not None:
                raise RuntimeError('model host exited before bridge readiness')
            if cancel.exists() or time.monotonic() >= until:
                raise TimeoutError('model startup ceiling/cancellation')
            time.sleep(.05)
        proxy = ModelProxy(scratch, str(model_python), deadline, cancel)
        expected = REHEARSAL_ARTIFACT if mode == 'rehearsal' else __import__(
            'research.action_effect_history_v1.host', fromlist=['expected_artifact']).expected_artifact()
        ready = ProxyService(proxy).connect_ready(expected_artifact=expected)
        store.save('model-ready.json', {'artifact': ready['artifact'], 'startup_seconds': ready['startup_seconds'],
                                        'canary_sha256': ready['canary_audit']['response_sha256'], 'mode': mode})
        from .engine import DevelopmentAdapter
        from .runner import run
        report = run(output / 'worker/run', ProxyService(proxy),
                     lambda game_id, arm, episode_id: DevelopmentAdapter(game_id, arm, episode_id, games,
                                                                         scratch / 'recordings'),
                     deadline_seconds=max(.01, deadline - time.monotonic()), cancel=cancel,
                     kind='offline_development_engine' if mode == 'live' else 'rehearsal_scripted_model_offline_engine',
                     evidence_budget_bytes=200_000 if fault == 'storage' else 64 * 1024**2,
                     evidence_lock_root=output)
        store.save('worker-result.json', {'run_status': report['status'], 'error': report.get('error'),
                                          'evidence_error': report.get('evidence_error'), 'calls': report['calls'],
                                          'dispatches': report['dispatches'], 'host_pid': host.pid, 'mode': mode})
        if report['status'] != 'complete':
            raise RuntimeError('comparison run did not complete: ' + str(report['status']))
        return report
    except Exception as exc:
        store.save('failure.json', {'error': type(exc).__name__ + ': ' + str(exc)[:256]}, failure_receipt=True)
        raise
    finally:
        EvidenceStore(output, 'control').save('cancel.json', {'reason': 'worker_finalization', 'host_pid': host.pid})
        try:
            host.wait(timeout=5)
        except subprocess.TimeoutExpired:
            store.save('model-exit-pending.json', {'pid': host.pid})  # the external owner kills the group


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--environments', type=Path, required=True)
    parser.add_argument('--model-python', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), required=True)
    parser.add_argument('--fault', default='none')
    args = parser.parse_args()
    gate(args.mode)
    run_worker(args.output, args.scratch, args.environments, args.model_python, deadline=args.deadline,
               mode=args.mode, fault=args.fault)


if __name__ == '__main__':
    main()
