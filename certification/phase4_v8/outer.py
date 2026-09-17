"""Local POSIX ownership/deadline prototype, not an approved target launcher.

The outer process alone creates and kills the two session groups. Monitor code
must observe the supplied PID, not create workers or reparent model processes.
Work that deliberately detaches into another session is outside this contract.
"""
import math
import os
from pathlib import Path
import signal
import secrets
import subprocess
import sys
import time

from certification.phase4_v8.measurement import save_bounded
from certification.phase4_v8.handshake import read_local_ready


def group_present(pgid):
    result = subprocess.run(['ps', '-axo', 'pgid='], capture_output=True,
                            text=True, timeout=1, check=True)
    return str(pgid) in result.stdout.split()


def signal_owned(process, sig):
    # Only Popen handles created with start_new_session=True enter this function.
    if process.pid == os.getpgrp():
        raise RuntimeError('refusing to signal own process group')
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def run_local(worker_command, monitor_factory, output, *, seconds=10, reserve=3,
              grace=.2, verification_seconds=1.5, interval=.02, started=None,
              readiness_seconds=1):
    """Exercise outer supervision with explicitly supplied local commands.

    This API grants no target authority. A future notebook must apply its reviewed
    authority gate BEFORE calling any process launcher, including this function.
    """
    values = (seconds, reserve, grace, verification_seconds, interval, readiness_seconds)
    if (any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values)
            or not grace + verification_seconds < reserve < seconds):
        raise ValueError('invalid outer lifecycle/reserve/cleanup limits')
    started = time.monotonic() if started is None else started
    if (type(started) not in (float, int) or not math.isfinite(started)
            or not 0 <= time.monotonic() - started < seconds - reserve):
        raise ValueError('invalid or exhausted first-cell clock')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'scope': 'local_outer_ownership_probe',
              'first_cell_monotonic': started,
              'status': 'failed', 'error': None, 'worker_released': False,
              'owned_groups': [], 'cleanup_verified': False,
              'phase4_complete': False, 'target_gpu_certified': False}
    processes = []
    read_fd = write_fd = None
    try:
        read_fd, write_fd = os.pipe()
        bootstrap = Path(__file__).with_name('gated_exec.py')
        worker = subprocess.Popen([sys.executable, str(bootstrap), str(read_fd), *worker_command],
            pass_fds=(read_fd,), start_new_session=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        processes.append(worker)
        os.close(read_fd); read_fd = None
        nonce = secrets.token_hex(32)
        ready_path = output / 'monitor-ready.json'
        environment = {**os.environ, 'P4_READY_NONCE': nonce,
                       'P4_READY_PATH': str(ready_path.resolve()), 'P4_WORKER_PID': str(worker.pid)}
        monitor = subprocess.Popen(monitor_factory(worker.pid, output), env=environment,
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(monitor)
        report['owned_groups'] = [p.pid for p in processes]
        save_bounded(output / 'ownership.json', report, byte_limit=65536)
        ready_deadline = min(time.monotonic() + readiness_seconds, started + seconds - reserve)
        while True:
            if time.monotonic() >= ready_deadline:
                raise TimeoutError('monitor readiness deadline')
            if monitor.poll() is not None or worker.poll() is not None:
                raise RuntimeError('monitor/worker exited before worker release')
            if ready_path.exists() or ready_path.is_symlink():
                report['monitor_ready'] = read_local_ready(ready_path, nonce=nonce,
                    worker_pid=worker.pid, monitor_pid=monitor.pid)
                save_bounded(output / 'ownership.json', report, byte_limit=65536)
                # Account for validation and publication time before releasing work.
                if time.monotonic() >= ready_deadline or monitor.poll() is not None:
                    raise RuntimeError('monitor readiness expired before release')
                break
            time.sleep(interval)
        os.write(write_fd, b'G')
        os.close(write_fd); write_fd = None
        report['worker_released'] = True
        report['worker_started_seconds'] = time.monotonic() - started
        while True:
            elapsed = time.monotonic() - started
            codes = [p.poll() for p in processes]
            if codes[0] is not None and 'worker_stopped_seconds' not in report:
                report['worker_stopped_seconds'] = time.monotonic() - started
            if any(code not in (None, 0) for code in codes):
                raise RuntimeError('worker/monitor exited with failure: ' + str(codes))
            if codes[1] == 0 and codes[0] is None:
                raise RuntimeError('monitor stopped while worker still active')
            if elapsed >= seconds - reserve:
                (output / 'cancel').touch(exist_ok=True)
                report['admission_canceled'] = True
            if elapsed >= seconds - grace - verification_seconds:
                raise TimeoutError('outer deadline reserves process cleanup')
            if codes == [0, 0]:
                report['status'] = 'local_commands_completed_pending_evidence_review'
                break
            time.sleep(interval)
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        for fd in (read_fd, write_fd):
            if fd is not None:
                os.close(fd)
        report['owned_groups'] = [p.pid for p in processes]
        cleanup = time.monotonic()
        try:
            # Signal even after leader exit: descendants can still occupy its group.
            for process in processes:
                signal_owned(process, signal.SIGTERM)
            until = cleanup + grace
            while time.monotonic() < until and any(p.poll() is None for p in processes):
                time.sleep(min(interval, max(0, until - time.monotonic())))
            for process in processes:
                signal_owned(process, signal.SIGKILL)
            deadline = cleanup + grace + verification_seconds
            for process in processes:
                process.wait(timeout=max(.001, deadline - time.monotonic()))
            while time.monotonic() < deadline:
                if not any(group_present(p.pid) for p in processes):
                    report['cleanup_verified'] = True
                    break
                time.sleep(interval)
            if not report['cleanup_verified']:
                raise RuntimeError('owned process group still present')
        except Exception as exc:
            report['error'] = report['error'] or 'cleanup: ' + type(exc).__name__
        report['cleanup_seconds'] = time.monotonic() - cleanup
        report['returncodes'] = [p.poll() for p in processes]
        report['elapsed_seconds'] = time.monotonic() - started
        if (report['error'] or report.get('admission_canceled')
                or report['elapsed_seconds'] >= seconds or not report['cleanup_verified']):
            report['status'] = 'failed'
        save_bounded(output / 'outer.json', report, byte_limit=65536)
    return report
