"""Stage B game worker; source authority is checked before target side effects."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from certification.phase4_integrated_v2.bridge import ModelProxy
from certification.phase4_integrated_v2.evidence import EvidenceStore
from .authority import require
from .bridge_service import ProxyService
from .engine import DevelopmentAdapter, verified_game_mount
from .local import run
from .replay import replay_file

ROOT = Path(__file__).resolve().parents[2]


def expected_artifact():
    from certification.phase4_integrated_v2.model_process import load_operational_primary
    primary = load_operational_primary(ROOT)
    profile = json.loads((ROOT / 'reports/m0_profiles/m0-q3vl30-instruct.json').read_bytes())
    artifact = profile['artifact']
    if (artifact['tree_sha256'] != primary.model_tree_sha256 or
            type(artifact['file_count']) is not int or artifact['file_count'] <= 0):
        raise ValueError('pinned model artifact identity drift')
    return {'tree_sha256': artifact['tree_sha256'], 'file_count': artifact['file_count']}


def run_worker(output, scratch, environments, model_python, *, deadline):
    require()  # Before model subprocess, game import, or GPU access.
    output, scratch, environments = Path(output), Path(scratch), Path(environments)
    model_python = Path(model_python).absolute()
    if model_python == Path(sys.executable).absolute() or not model_python.is_file():
        raise ValueError('distinct pinned model and game interpreters required')
    if time.monotonic() >= deadline:
        raise TimeoutError('worker admission closed')
    from certification.phase4_v2.package import verify_environment_mount
    manifest = json.loads((ROOT / 'reports/phase4_v2_offline_package.json').read_bytes())
    verify_environment_mount(environments, manifest)
    games = verified_game_mount(environments, scratch / 'staged-games')
    store = EvidenceStore(output, 'worker')
    cancel = output / 'control/cancel.json'
    env = dict(os.environ)
    restored = env.pop('P4_MODEL_CUDA_VISIBLE_DEVICES', None)
    if restored is None:
        env.pop('CUDA_VISIBLE_DEVICES', None)
    else:
        env['CUDA_VISIBLE_DEVICES'] = restored
    host = subprocess.Popen([str(model_python), '-m', 'research.grounded_action_v1.target_host',
        '--socket', str(scratch / 'model.sock'), '--evidence', str(output),
        '--cancel', str(cancel), '--deadline', str(deadline)], env=env)
    # The model process inherits this worker's externally owned process group.
    store.save('model-process.json', {'pid': host.pid, 'started_monotonic': time.monotonic()})
    try:
        until = min(deadline, time.monotonic() + 900)
        while not (scratch / 'model.sock').exists():
            if host.poll() is not None:
                raise RuntimeError('model host exited before bridge readiness')
            if cancel.exists() or time.monotonic() >= until:
                raise TimeoutError('Stage B model startup ceiling/cancellation')
            time.sleep(.05)
        proxy = ModelProxy(scratch, str(model_python), deadline, cancel)
        ProxyService(proxy).connect_ready(expected_artifact=expected_artifact())
        store.save('model-ready.json', {'artifact': proxy.artifact,
                                       'startup_seconds': proxy.startup_seconds,
                                       'canary_sha256': proxy.canary_audit['response_sha256']})
        record = output / 'worker/trajectory.json'
        state = run(record, ProxyService(proxy),
                    lambda arm: DevelopmentAdapter(arm, games, scratch / 'recordings'),
                    deadline_seconds=max(.01, deadline - time.monotonic()),
                    kind='offline_development_engine',
                    writer=lambda _path, value: store.save('trajectory.json', value))
        if state['status'] != 'complete':
            raise RuntimeError('Stage B study failed: ' + str(state['error']))
        replay = replay_file(record)
        store.save('worker-result.json', {'status': 'complete', 'replay': replay,
                                          'host_pid': host.pid})
        return replay
    except Exception as exc:
        store.save('failure.json', {'error': type(exc).__name__ + ': ' + str(exc)[:256]},
                   failure_receipt=True)
        raise
    finally:
        EvidenceStore(output, 'control').save('cancel.json',
            {'reason': 'worker_finalization', 'host_pid': host.pid})
        try:
            host.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # The external owner kills and verifies the entire process group.
            store.save('model-exit-pending.json', {'pid': host.pid})


def main():
    import argparse
    require()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--environments', type=Path, required=True)
    parser.add_argument('--model-python', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    args = parser.parse_args()
    run_worker(args.output, args.scratch, args.environments, args.model_python,
               deadline=args.deadline)


if __name__ == '__main__':
    main()
