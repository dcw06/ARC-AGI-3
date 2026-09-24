"""Stage B external ownership; review fixture plus gated target lifecycle."""
import json
import math
import os
from pathlib import Path
import secrets
import sys
import subprocess
import tempfile
import threading
import time

from certification.phase4_integrated_v2.evidence import EvidenceStore
from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.outer import run_local
from certification.phase4_integrated_v2.scratch import worker_environment
from certification.phase4_integrated_v2.telemetry import read_telemetry
from .authority import consume_runtime
from .replay import replay_file
from .target_resources import LiveProbes, independent_cleanup

ROOT = Path(__file__).resolve().parents[2]


def run_review(output, *, seconds=90, fault='none'):
    if fault not in ('none', 'startup', 'cancel', 'evidence') or not 20 <= seconds <= 180:
        raise ValueError('review fixture limits')
    started = time.monotonic()
    output = Path(output)
    data_root = output.with_name(output.name + '-data')
    data_root.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='stage-b-owned-fixture-') as folder:
        scratch = Path(folder)
        command = [sys.executable, '-m', 'research.grounded_action_v1.target_fixture', 'worker',
                   '--output', str(output), '--data-root', str(data_root), '--scratch', str(scratch),
                   '--deadline', str(started + seconds - 10), '--fault', fault]
        def monitor(pid, root):
            return [sys.executable, '-m', 'certification.phase4_integrated_v2.monitor',
                    '--injected', str(pid), str(root / 'monitor')]
        report = run_local(command, monitor, output, seconds=seconds, reserve=10,
                           started=started, readiness_seconds=10)
    report['scratch_removed'] = not scratch.exists()
    report['data_root'] = str(data_root)
    if report['status'] == 'local_commands_completed_pending_evidence_review':
        try:
            replay = replay_file(data_root / 'record.json')
            report['replay_status'] = replay['status']
            report['calls'] = replay['calls']
            report['dispatches'] = replay['dispatches']
            report['status'] = 'review_cpu_fixture_verified'
        except Exception as exc:
            report.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
    (output / 'review-result.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


def run_live(output, working, game_python, model_python, environments, *, started,
             claimed=False, prepared=False, spawn=subprocess.Popen):
    """One gated 3,300-second attempt; no historical authority is accepted."""
    from .authority import require, verify_runtime_claim
    require()  # Before output, installation, subprocess or GPU query.
    if (type(started) not in (float, int) or not math.isfinite(started) or
            not 0 <= time.monotonic() - started < 3000):
        raise ValueError('exhausted first-cell clock')
    game_python, model_python = Path(game_python).absolute(), Path(model_python).absolute()
    if (not game_python.is_file() or not model_python.is_file() or
            game_python == model_python):
        raise ValueError('distinct pinned game/model interpreters required')
    if claimed:
        verify_runtime_claim(working)
    else:
        consume_runtime(working)
    output = Path(output).resolve()
    if prepared:
        if not output.is_dir() or (output / 'control/ownership.json').exists():
            raise ValueError('invalid prepared output')
    else:
        output.mkdir(parents=True, exist_ok=False)
    control, logs = EvidenceStore(output, 'control'), EvidenceStore(output, 'logs')
    report = {'scope': 'stage_b_live_development_study', 'status': 'failed',
              'error': None, 'first_cell_monotonic': started, 'worker_released': False,
              'process_groups_exited': False, 'independent_gpu_cleanup_verified': False,
              'phase4_complete': False, 'target_gpu_certified': False,
              'internal_seconds': 3300, 'admission_cutoff_seconds': 3000}
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
        process = spawn(argv, cwd=ROOT, env=env, pass_fds=pass_fds,
            start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        processes.append(process)
        thread = threading.Thread(target=drain, args=(process, str(process.pid)), daemon=True)
        thread.start(); drains.append(thread)
        return process

    def check():
        elapsed = time.monotonic() - started
        if log_errors:
            raise RuntimeError('log retention failed: ' + log_errors[0])
        if elapsed >= 3000:
            control.save('cancel.json', {'elapsed_seconds': elapsed})
            raise TimeoutError('admission cutoff reserves cleanup')
        if elapsed >= 3296:
            raise TimeoutError('hard lifecycle deadline')

    with tempfile.TemporaryDirectory(prefix='stage-b-live-') as folder:
        scratch = Path(folder)
        try:
            worker_env = worker_environment(os.environ, scratch)
            for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
                worker_env.pop(key, None)
            worker_env['PYTHONNOUSERSITE'] = '1'
            if 'CUDA_VISIBLE_DEVICES' in worker_env:
                worker_env['P4_MODEL_CUDA_VISIBLE_DEVICES'] = worker_env['CUDA_VISIBLE_DEVICES']
            else:
                worker_env.pop('P4_MODEL_CUDA_VISIBLE_DEVICES', None)
            worker_env['CUDA_VISIBLE_DEVICES'] = ''
            rfd, wfd = os.pipe()
            worker = launch([sys.executable, str(ROOT / 'certification/phase4_integrated_v2/gated_exec.py'),
                str(rfd), str(game_python), '-m', 'research.grounded_action_v1.target_worker',
                '--output', str(output), '--scratch', str(scratch),
                '--environments', str(Path(environments).resolve()),
                '--model-python', str(model_python), '--deadline', str(started + 3000)],
                env=worker_env, pass_fds=(rfd,))
            os.close(rfd); rfd = None
            nonce = secrets.token_hex(32)
            monitor_env = worker_environment(os.environ, scratch)
            for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
                monitor_env.pop(key, None)
            monitor_env['PYTHONNOUSERSITE'] = '1'
            monitor = launch([str(game_python), '-m', 'research.grounded_action_v1.target_monitor',
                '--worker-pid', str(worker.pid), '--scratch', str(scratch),
                '--output', str(output), '--started', str(started),
                '--deadline', str(started + 3297), '--stop',
                str(output / 'control/stop-monitor.json'), '--nonce', nonce],
                env=monitor_env)
            control.save('ownership.json', {'worker_pgid': worker.pid,
                'monitor_pgid': monitor.pid, 'nonce': nonce, 'first_cell_monotonic': started})
            ready_path = output / 'monitor/ready.json'
            ready_deadline = min(time.monotonic() + 30, started + 3000)
            while not ready_path.exists():
                check()
                if worker.poll() is not None or monitor.poll() is not None:
                    raise RuntimeError('worker/monitor exited before readiness')
                if time.monotonic() >= ready_deadline:
                    raise TimeoutError('monitor readiness deadline')
                time.sleep(.02)
            if ready_path.is_symlink() or ready_path.stat().st_size > 8192:
                raise ValueError('invalid monitor readiness evidence')
            ready = json.loads(ready_path.read_bytes())
            uuid = validate_binding(ready['gpu_binding'])
            telemetry = read_telemetry(output / 'monitor')
            if (ready.get('scope') != 'stage_b_live_resource_monitor' or
                    ready.get('nonce') != nonce or ready.get('worker_pid') != worker.pid or
                    ready.get('monitor_pid') != monitor.pid or
                    not telemetry['samples'] or ready.get('sample') != telemetry['samples'][0]):
                raise ValueError('unbacked monitor readiness')
            check()
            if monitor.poll() is not None or time.monotonic() >= ready_deadline:
                raise RuntimeError('monitor readiness expired')
            control.save('monitor-ready-ack.json', {'nonce': nonce})
            os.write(wfd, b'G'); os.close(wfd); wfd = None
            report['worker_released'] = True
            released = time.monotonic()
            while worker.poll() is None:
                check()
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
            monitor.wait(timeout=max(.01, min(10, started + 3296 - time.monotonic())))
            if monitor.returncode != 0:
                raise RuntimeError('resource monitor failed')
            terminate_group(monitor, grace=.5, verification_seconds=3)
            report['replay'] = replay_file(output / 'worker/trajectory.json')
            report['status'] = 'worker_complete_pending_independent_cleanup'
        except Exception as exc:
            report['error'] = type(exc).__name__ + ': ' + str(exc)[:256]
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
                report['process_groups_exited'] = False
            try:
                probes = LiveProbes(processes[0].pid if processes else 1, scratch)
                if uuid is None:
                    uuid = validate_binding(probes.bind())
                receipt = independent_cleanup(probes, expected_uuid=uuid,
                    groups_absent=report['process_groups_exited'], deadline=started + 3298)
                control.save('gpu-cleanup.json', receipt)
                report['independent_gpu_cleanup_verified'] = receipt['gpu_cleanup_verified']
            except Exception as exc:
                report['cleanup_error'] = type(exc).__name__ + ': ' + str(exc)[:256]
                try:
                    control.save('gpu-cleanup.json', {'gpu_cleanup_verified': False,
                        'groups_absent': report['process_groups_exited'],
                        'error': report['cleanup_error']})
                except Exception:
                    control.save('failure.json', {'error': 'GPU cleanup receipt unavailable'},
                                 failure_receipt=True)
            for thread in drains:
                thread.join(timeout=2)
            if (cleanup_errors or log_errors or any(t.is_alive() for t in drains)):
                report['error'] = report['error'] or 'process/log cleanup failure'
    report['scratch_removed'] = not scratch.exists()
    report['elapsed_seconds'] = time.monotonic() - started
    if (report['error'] or not report['process_groups_exited'] or
            not report['independent_gpu_cleanup_verified'] or
            not report['scratch_removed'] or report['elapsed_seconds'] >= 3300 or
            report['status'] != 'worker_complete_pending_independent_cleanup'):
        report['status'] = 'failed'
    else:
        report['status'] = 'development_study_complete_pending_archive_review'
    try:
        control.save('outer.json', report)
    except Exception as exc:
        control.save('failure.json', {'error': 'outer evidence retention: ' + type(exc).__name__},
                     failure_receipt=True)
        report['status'] = 'failed'
    return report


def main():
    from .authority import require
    require()  # No target side effects before Stage B-specific authority.
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--working', type=Path, required=True)
    parser.add_argument('--game-python', type=Path, required=True)
    parser.add_argument('--model-python', type=Path, required=True)
    parser.add_argument('--environments', type=Path, required=True)
    parser.add_argument('--started', type=float, required=True)
    args = parser.parse_args()
    report = run_live(args.output, args.working, args.game_python, args.model_python,
                      args.environments, started=args.started, claimed=True, prepared=True)
    raise SystemExit(0 if report['status'] == 'development_study_complete_pending_archive_review' else 1)


if __name__ == '__main__':
    main()
