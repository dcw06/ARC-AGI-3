"""External process supervisor for development lifecycle integration.

No GPU authority: target integration must add a separately reviewed execution gate.
The child and its descendants share a dedicated process group, never ours.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from evaluation.phase4_runner import group_rss_bytes, tree_bytes, terminate_group


def save(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def group_exists(pgid):
    r = subprocess.run(['ps', '-axo', 'pgid='], capture_output=True,
                       text=True, check=True, timeout=1)
    return str(pgid) in r.stdout.split()


def supervise(command_factory, output, *, seconds=60, reserve=10,
              memory_bytes=4 * 1024**3, scratch_bytes=64 * 1024**2,
              evidence_bytes=64 * 1024**2, grace=1, interval=.05):
    if not 0 < reserve < seconds or min(memory_bytes, scratch_bytes, evidence_bytes, grace, interval) <= 0:
        raise ValueError('invalid supervisor limits')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {'status': 'failed', 'scope': 'local_development_integration_only',
              'phase4_complete': False, 'target_gpu_certified': False,
              'peak_rss_bytes': 0, 'peak_scratch_bytes': 0, 'cleanup_verified': False,
              'error': None, 'worker': None}
    with tempfile.TemporaryDirectory(prefix='p4-lifecycle-v2-') as directory:
        scratch = Path(directory)
        checkpoint = scratch / 'state.json'
        process = None
        try:
            with (scratch / 'worker.log').open('wb') as log:
                process = subprocess.Popen(command_factory(scratch), start_new_session=True,
                                           stdout=log, stderr=subprocess.STDOUT)
                while process.poll() is None:
                    elapsed = time.monotonic() - started
                    if elapsed >= seconds - reserve and not (scratch / 'cancel').exists():
                        (scratch / 'cancel').touch(exist_ok=False)
                        report['admission_canceled'] = True
                    if elapsed >= seconds:
                        raise TimeoutError('external lifecycle deadline')
                    report['peak_rss_bytes'] = max(report['peak_rss_bytes'], group_rss_bytes(process.pid))
                    report['peak_scratch_bytes'] = max(report['peak_scratch_bytes'], tree_bytes(scratch))
                    if report['peak_rss_bytes'] > memory_bytes or report['peak_scratch_bytes'] > scratch_bytes:
                        raise MemoryError('resource ceiling')
                    time.sleep(interval)
        except Exception as exc:
            report['error'] = type(exc).__name__ + ': ' + str(exc)
        finally:
            if process is not None:
                report['child_returncode_before_cleanup'] = process.poll()
                cleanup = time.monotonic()
                try:
                    terminate_group(process, grace)
                    deadline = cleanup + grace + 5
                    while group_exists(process.pid) and time.monotonic() < deadline:
                        time.sleep(.05)
                    report['cleanup_verified'] = not group_exists(process.pid)
                except Exception as exc:
                    report['error'] = report['error'] or 'cleanup: ' + type(exc).__name__
                report['cleanup_seconds'] = time.monotonic() - cleanup
            # Final checkpoint is read AFTER termination, including immediate child errors.
            try:
                if checkpoint.stat().st_size > evidence_bytes:
                    raise ValueError('oversized checkpoint')
                worker = json.loads(checkpoint.read_text())
                if not isinstance(worker, dict):
                    raise ValueError('checkpoint must be an object')
                report['worker'] = worker
                save(output / 'worker.json', report['worker'])
            except Exception as exc:
                report['error'] = report['error'] or 'checkpoint: ' + type(exc).__name__
            report['final_scratch_bytes'] = tree_bytes(scratch)
            if report['final_scratch_bytes'] > scratch_bytes:
                report['error'] = report['error'] or 'final scratch ceiling'
            worker = report['worker'] or {}
            if worker.get('error'):
                report['error'] = report['error'] or worker['error']
            if (report.get('child_returncode_before_cleanup') == 0 and not report['error']
                    and report['cleanup_verified'] and worker.get('status') == 'complete'
                    and not report.get('admission_canceled')):
                report['status'] = 'worker_completed_pending_independent_evaluation'
    report['elapsed_seconds'] = time.monotonic() - started
    report['scratch_removed'] = not scratch.exists()
    if report['elapsed_seconds'] >= seconds:
        report['status'] = 'failed'
        report['error'] = report['error'] or 'lifecycle including cleanup exceeded'
    save(output / 'supervisor.json', report)
    return report
