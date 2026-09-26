"""Questionnaire worker (worker interpreter): model host, bridge admission, server verification, the run.

No game is played. The worker starts the model host, admits the bridge after one validated canary,
validates the host's retained server evidence (prefix caching verified disabled; live launch flags),
then runs the frozen questionnaire on the shared first-cell clock.

Exit status: 0 when every scheduled call ran, or when the run stopped only at the admission cutoff
(an incomplete gate is a reported result, not a lifecycle failure). Any other stop (timeouts, a
server that did not become idle, transport failure, storage limit, cancellation) exits non-zero;
the retained evidence is kept either way and evaluated as partial.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from certification.phase4_integrated_v2.bridge import ModelProxy
from certification.phase4_integrated_v2.evidence import EvidenceStore
from . import schedule
from .service import ProxyService, validate_server_config

ROOT = Path(__file__).resolve().parents[2]
HOST_FAULTS = ('model_startup', 'prefix_cache_enabled', 'hang_once', 'no_abort', 'http_error')
FAULTS = ('none', 'storage', 'surviving_child', 'log_flood', 'slow_gate_pass_1', 'slow_gate_pass_2') + HOST_FAULTS
REHEARSAL_ARTIFACT = {'rehearsal': 'scripted_model_not_target_evidence'}
# Rehearsal per-call latencies chosen so the admission cutoff falls inside gate pass 1 or gate pass 2.
SLOW_LATENCY = {'slow_gate_pass_1': 0.35, 'slow_gate_pass_2': 0.12}


def gate(mode):
    if mode == 'live':
        from .authority import require
        return require()
    if mode == 'rehearsal':
        from .authority import rehearsal_gate
        return rehearsal_gate()
    raise ValueError('mode')


def timing(mode, fault):
    """(call timeout, idle-verification window, fake latency). Live uses the frozen values only."""
    if mode == 'live':
        return schedule.PER_CALL_TIMEOUT_SECONDS, schedule.CANCELLATION_VERIFY_SECONDS, 0.0
    return 2.0, 3.0, SLOW_LATENCY.get(fault, 0.0)


def run_worker(output, scratch, model_python, *, started, cutoff_seconds, mode, fault='none'):
    gate(mode)  # before model subprocess or GPU access
    if fault not in FAULTS or (mode == 'live' and fault != 'none'):
        raise PermissionError('faults are rehearsal-only')
    output, scratch = Path(output), Path(scratch)
    model_python = Path(model_python).absolute()
    if mode == 'live' and (model_python == Path(sys.executable).absolute() or not model_python.is_file()):
        raise ValueError('distinct pinned model and worker interpreters required')
    deadline = started + cutoff_seconds
    if time.monotonic() >= deadline:
        raise TimeoutError('worker admission closed')
    call_timeout, verify_seconds, latency = timing(mode, fault)
    bound = call_timeout + verify_seconds + schedule.BRIDGE_MARGIN_SECONDS
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
    host = subprocess.Popen([str(model_python), '-m', 'research.evidence_comprehension_v1.host',
                             '--socket', str(scratch / 'model.sock'), '--evidence', str(output),
                             '--cancel', str(cancel), '--deadline', str(deadline), '--mode', mode,
                             '--fault', fault if fault in HOST_FAULTS else 'none',
                             '--call-timeout', str(call_timeout), '--verify-seconds', str(verify_seconds),
                             '--latency', str(latency)], env=env, cwd=ROOT)  # inherits the owned worker group
    store.save('model-process.json', {'pid': host.pid, 'started_monotonic': time.monotonic()})
    if fault == 'log_flood':  # rehearsal: exceed the supervisor's bounded log retention (3 MiB)
        for _ in range(64):
            sys.stdout.write('x' * 65536 + '\n')
        sys.stdout.flush()
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
            'research.evidence_comprehension_v1.host', fromlist=['expected_artifact']).expected_artifact()
        ready = ProxyService(proxy).connect_ready(expected_artifact=expected)
        from .probes import load_frozen
        _, probe_set_sha256 = load_frozen()
        config_path = output / 'worker/server-config.json'
        if config_path.is_symlink() or not config_path.is_file() or config_path.stat().st_size > 65536:
            raise ValueError('host server evidence missing')
        validate_server_config(json.loads(config_path.read_bytes()), mode, probe_set_sha256)
        store.save('model-ready.json', {'artifact': ready['artifact'], 'startup_seconds': ready['startup_seconds'],
                                        'canary_sha256': ready['canary_audit']['response_sha256'], 'mode': mode,
                                        'server_config_verified': True})
        from .runner import run
        report = run(output / 'worker/run', ProxyService(proxy), started=started,
                     kind='target_model_questionnaire' if mode == 'live' else 'rehearsal_fake_server_questionnaire',
                     cutoff_seconds=cutoff_seconds, bound_seconds=bound,
                     evidence_budget_bytes=120_000 if fault == 'storage' else 32 * 1024**2,
                     cancel=cancel, evidence_lock_root=output)
        store.save('worker-result.json', {'run_status': report['status'], 'stop_reason': report['stop_reason'],
                                          'calls_recorded': report['calls_recorded'], 'counts': report['counts'],
                                          'host_pid': host.pid, 'mode': mode})
        if report['status'] != 'complete' and report['stop_reason'] != 'admission_cutoff':
            raise RuntimeError('questionnaire run stopped: ' + str(report['stop_reason']))
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
    parser.add_argument('--model-python', type=Path, required=True)
    parser.add_argument('--started', type=float, required=True)
    parser.add_argument('--cutoff-seconds', type=float, required=True)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), required=True)
    parser.add_argument('--fault', default='none')
    args = parser.parse_args()
    gate(args.mode)
    if args.mode == 'live' and args.cutoff_seconds != schedule.ADMISSION_CUTOFF_SECONDS:
        raise PermissionError('live mode uses the frozen admission cutoff')
    run_worker(args.output, args.scratch, args.model_python, started=args.started, cutoff_seconds=args.cutoff_seconds,
               mode=args.mode, fault=args.fault)


if __name__ == '__main__':
    main()
