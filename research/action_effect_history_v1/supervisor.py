"""External ownership of the worker and monitor process groups, on one shared first-cell clock."""
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time

from certification.phase4_integrated_v2.evidence import EvidenceStore
from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.scratch import worker_environment
from certification.phase4_integrated_v2.telemetry import read_telemetry
from .resources import independent_cleanup, probes_for

ROOT = Path(__file__).resolve().parents[2]
LIVE_INTERNAL_SECONDS = 3300
CLEANUP_RESERVE_SECONDS = 300
SUPERVISOR_FAULTS = ('none', 'monitor_exit', 'cancel')


def gate(mode):
    from .worker import gate as worker_gate
    return worker_gate(mode)


def run(output, working, game_python, model_python, environments, *, started, mode='live',
        internal_seconds=LIVE_INTERNAL_SECONDS, fault='none', claimed=False, prepared=False, spawn=subprocess.Popen):
    """One supervised attempt. Installation, startup, episodes, evidence and cleanup share `started`."""
    gate(mode)  # before output, subprocess or GPU query
    from .worker import FAULTS as WORKER_FAULTS
    if mode == 'live' and (fault != 'none' or internal_seconds != LIVE_INTERNAL_SECONDS):
        raise PermissionError('live mode uses the frozen lifecycle and no faults')
    if fault not in WORKER_FAULTS + SUPERVISOR_FAULTS or not 60 <= internal_seconds <= LIVE_INTERNAL_SECONDS:
        raise ValueError('supervisor limits')
    admission = internal_seconds - CLEANUP_RESERVE_SECONDS
    if type(started) not in (float, int) or not math.isfinite(started) or not 0 <= time.monotonic() - started < admission:
        raise ValueError('exhausted first-cell clock')
    game_python, model_python = Path(game_python).absolute(), Path(model_python).absolute()
    if mode == 'live' and (not game_python.is_file() or not model_python.is_file() or game_python == model_python):
        raise ValueError('distinct pinned game/model interpreters required')
    if mode == 'live':
        from .authority import consume_runtime, verify_runtime_claim
        verify_runtime_claim(working) if claimed else consume_runtime(working)
    output = Path(output).resolve()
    if prepared:
        if not output.is_dir() or (output / 'control/ownership.json').exists():
            raise ValueError('invalid prepared output')
    else:
        output.mkdir(parents=True, exist_ok=False)
    control, logs = EvidenceStore(output, 'control'), EvidenceStore(output, 'logs')
    report = {'scope': 'action_effect_history_' + mode, 'mode': mode, 'status': 'failed', 'error': None,
              'first_cell_monotonic': started, 'internal_seconds': internal_seconds, 'admission_cutoff_seconds': admission,
              'worker_released': False, 'process_groups_exited': False, 'independent_gpu_cleanup_verified': False,
              'phase4_complete': False, 'target_gpu_certified': False, 'fault': fault}
    processes, drains, log_errors = [], [], []
    rfd = wfd = None
    uuid = None

    def drain(process, label):
        data = bytearray()
        try:
            while chunk := process.stdout.read(4096):
                if len(data) + len(chunk) > 3 * 1024**2:
                    raise ValueError('bounded process log exhausted')
                data.extend(chunk)
                logs.write(label + '.json', bytes(data))
        except Exception as exc:
            log_errors.append(type(exc).__name__ + ': ' + str(exc)[:200])
        finally:
            process.stdout.close()

    def launch(argv, *, env=None, pass_fds=()):
        process = spawn(argv, cwd=ROOT, env=env, pass_fds=pass_fds, start_new_session=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        processes.append(process)
        thread = threading.Thread(target=drain, args=(process, str(process.pid)), daemon=True)
        thread.start()
        drains.append(thread)
        return process

    def check():
        elapsed = time.monotonic() - started
        if log_errors:
            raise RuntimeError('log retention failed: ' + log_errors[0])
        if elapsed >= admission:
            control.save('cancel.json', {'elapsed_seconds': elapsed, 'reason': 'admission cutoff'})
            raise TimeoutError('admission cutoff reserves cleanup')

    with tempfile.TemporaryDirectory(prefix='action-effect-history-') as folder:
        scratch = Path(folder)
        try:
            env = worker_environment(os.environ, scratch)
            for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
                env.pop(key, None)
            env['PYTHONNOUSERSITE'] = '1'
            if mode == 'rehearsal':
                env['PYTHONPATH'] = str(ROOT)  # rehearsal runs the checkout's sources in the current interpreter
                env['AEH_REHEARSAL'] = '1'
            if 'CUDA_VISIBLE_DEVICES' in env and mode == 'live':
                env['P4_MODEL_CUDA_VISIBLE_DEVICES'] = env['CUDA_VISIBLE_DEVICES']
            else:
                env.pop('P4_MODEL_CUDA_VISIBLE_DEVICES', None)
            env['CUDA_VISIBLE_DEVICES'] = ''
            rfd, wfd = os.pipe()
            worker_fault = fault if fault in WORKER_FAULTS else 'none'
            worker = launch([sys.executable, str(ROOT / 'certification/phase4_integrated_v2/gated_exec.py'),
                             str(rfd), str(game_python), '-m', 'research.action_effect_history_v1.worker',
                             '--output', str(output), '--scratch', str(scratch),
                             '--environments', str(Path(environments).resolve()), '--model-python', str(model_python),
                             '--deadline', str(started + admission), '--mode', mode, '--fault', worker_fault],
                            env=env, pass_fds=(rfd,))
            os.close(rfd)
            rfd = None
            nonce = secrets.token_hex(32)
            monitor = launch([str(game_python), '-m', 'research.action_effect_history_v1.monitor',
                              '--worker-pid', str(worker.pid), '--scratch', str(scratch), '--output', str(output),
                              '--started', str(started), '--deadline', str(started + internal_seconds - 3),
                              '--stop', str(output / 'control/stop-monitor.json'), '--nonce', nonce, '--mode', mode,
                              '--fault', 'exit' if fault == 'monitor_exit' else 'none'], env=env)
            control.save('ownership.json', {'worker_pgid': worker.pid, 'monitor_pgid': monitor.pid, 'nonce': nonce,
                                            'first_cell_monotonic': started})
            ready_path = output / 'monitor/ready.json'
            ready_deadline = min(time.monotonic() + 30, started + admission)
            while not ready_path.exists():
                check()
                if worker.poll() is not None or monitor.poll() is not None:
                    raise RuntimeError('worker/monitor exited before readiness')
                if time.monotonic() >= ready_deadline:
                    raise TimeoutError('monitor readiness deadline')
                time.sleep(.02)
            ready = json.loads(ready_path.read_bytes())
            uuid = validate_binding(ready['gpu_binding'])
            telemetry = read_telemetry(output / 'monitor')
            if (ready.get('nonce') != nonce or ready.get('worker_pid') != worker.pid or ready.get('monitor_pid') != monitor.pid
                    or not telemetry['samples'] or ready.get('sample') != telemetry['samples'][0]):
                raise ValueError('unbacked monitor readiness')
            control.save('monitor-ready-ack.json', {'nonce': nonce})
            os.write(wfd, b'G')
            os.close(wfd)
            wfd = None
            report['worker_released'] = True
            released = time.monotonic()
            while worker.poll() is None:
                check()
                if fault == 'cancel' and time.monotonic() - released >= 12:
                    control.save('cancel.json', {'reason': 'rehearsal cancellation'})
                if monitor.poll() is not None:
                    raise RuntimeError('monitor stopped before worker')
                if not (output / 'worker/model-ready.json').exists() and time.monotonic() - released >= 900:
                    raise TimeoutError('model startup ceiling')
                time.sleep(.05)
            if worker.returncode != 0:
                raise RuntimeError('game worker failed')
            from scripts.run_grounded_action_v1_engine_local import terminate_group
            terminate_group(worker, grace=.5, verification_seconds=3)
            control.save('stop-monitor.json', {'worker_group_exited': True})
            monitor.wait(timeout=max(.01, min(10, started + internal_seconds - 4 - time.monotonic())))
            if monitor.returncode != 0:
                raise RuntimeError('resource monitor failed')
            report['status'] = 'worker_complete_pending_cleanup'
        except Exception as exc:
            report['error'] = type(exc).__name__ + ': ' + str(exc)[:256]
            try:
                control.save('cancel.json', {'reason': 'supervisor failure'})
            except Exception:
                pass
        finally:
            for fd in (rfd, wfd):
                if fd is not None:
                    os.close(fd)
            from scripts.run_grounded_action_v1_engine_local import terminate_group, group_exited
            cleanup_errors = []
            for process in processes:
                try:
                    terminate_group(process, grace=.5, verification_seconds=3)
                except Exception as exc:
                    cleanup_errors.append(type(exc).__name__ + ': ' + str(exc)[:128])
            try:
                report['process_groups_exited'] = not cleanup_errors and all(group_exited(p.pid) for p in processes)
            except Exception as exc:
                cleanup_errors.append(type(exc).__name__ + ': ' + str(exc)[:128])
            try:
                probes = probes_for(mode)(processes[0].pid if processes else 1, scratch)
                if uuid is None:
                    uuid = validate_binding(probes.bind())
                receipt = independent_cleanup(probes, expected_uuid=uuid, groups_absent=report['process_groups_exited'],
                                              deadline=started + internal_seconds - 2)
                control.save('gpu-cleanup.json', receipt)
                report['independent_gpu_cleanup_verified'] = receipt['gpu_cleanup_verified']
            except Exception as exc:
                report['cleanup_error'] = type(exc).__name__ + ': ' + str(exc)[:256]
            for thread in drains:
                thread.join(timeout=2)
            if cleanup_errors or log_errors or any(t.is_alive() for t in drains):
                report['error'] = report['error'] or 'process/log cleanup failure'
    report['scratch_removed'] = not scratch.exists()
    # Verify retained run evidence independently of the worker's own status; partial evidence stays partial.
    try:
        from .evidence import load_verified
        run_report = load_verified(output / 'worker/run')
        report['run_evidence'] = {'verified': True, 'run_status': run_report['status'], 'calls': run_report['calls'],
                                  'dispatches': run_report['dispatches'], 'episodes': len(run_report['episodes'])}
    except Exception as exc:
        report['run_evidence'] = {'verified': False, 'error': type(exc).__name__ + ': ' + str(exc)[:256]}
    report['elapsed_seconds'] = time.monotonic() - started
    complete = (not report['error'] and report['process_groups_exited'] and report['independent_gpu_cleanup_verified']
                and report['scratch_removed'] and report['elapsed_seconds'] < internal_seconds
                and report['status'] == 'worker_complete_pending_cleanup' and report['run_evidence']['verified']
                and report['run_evidence']['run_status'] == 'complete')
    report['status'] = 'study_complete_pending_independent_evaluation' if complete else 'failed'
    control.save('outer.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--output', '--working', '--game-python', '--model-python', '--environments'):
        parser.add_argument(name, type=Path, required=True)
    parser.add_argument('--started', type=float, required=True)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), required=True)
    parser.add_argument('--internal-seconds', type=int, default=LIVE_INTERNAL_SECONDS)
    parser.add_argument('--fault', default='none')
    args = parser.parse_args()
    gate(args.mode)
    report = run(args.output, args.working, args.game_python, args.model_python, args.environments,
                 started=args.started, mode=args.mode, internal_seconds=args.internal_seconds, fault=args.fault,
                 claimed=args.mode == 'live', prepared=True)
    raise SystemExit(0 if report['status'] == 'study_complete_pending_independent_evaluation' else 1)


if __name__ == '__main__':
    main()
