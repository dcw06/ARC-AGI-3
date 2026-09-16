"""External process supervisor for development lifecycle integration.

Separate explicit readiness/approval gate precedes any GPU query or child start.
The child and its descendants share a dedicated process group, never ours.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from evaluation.phase4_runner import group_rss_bytes, tree_bytes, terminate_group
from evaluation.phase4_target import bind_gpu, gpu_pids
from evaluation.phase4_preflight import sample_gpu
from certification.phase4_v4.authority import authority


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


def supervise(command_factory, output, *, started=None, seconds=27540, reserve=600,
              memory_bytes=128 * 1024**3, scratch_bytes=4 * 1024**3,
              evidence_bytes=64 * 1024**2, grace=10, interval=.25):
    reservation = authority()
    if not 0 < reserve < seconds or min(memory_bytes, scratch_bytes, evidence_bytes, grace, interval) <= 0:
        raise ValueError('invalid supervisor limits')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic() if started is None else started
    report = {'status': 'failed', 'scope': 'model_backed_development_integration_not_production_certification',
              'phase4_complete': False, 'target_gpu_certified': False,
              'peak_rss_bytes': 0, 'peak_scratch_bytes': 0, 'cleanup_verified': False,
              'error': None, 'worker': None, 'attempt_id': reservation['attempt_id'],
              'charged_or_reserved_seconds': 28800, 'gpu_samples': 0, 'peak_vram_bytes': 0,
              'gpu_telemetry': []}
    with tempfile.TemporaryDirectory(prefix='p4-lifecycle-v2-') as directory:
        scratch = Path(directory)
        checkpoint = scratch / 'state.json'
        process = None
        try:
            binding = bind_gpu(86 * 1024**3)
            report['gpu_binding'] = binding
            save(output / 'gpu_binding.json', binding)
            with (scratch / 'worker.log').open('wb') as log:
                process = subprocess.Popen(command_factory(scratch), start_new_session=True,
                                           stdout=log, stderr=subprocess.STDOUT)
                worker_started = time.monotonic()
                while process.poll() is None:
                    if not (scratch / "model-ready").exists() and time.monotonic() - worker_started >= 900:
                        raise TimeoutError("model startup/preflight ceiling")
                    gpu = sample_gpu(binding["gpu_uuid"], 86 * 1024**3)
                    report["gpu_samples"] += 1
                    report['gpu_telemetry'].append({'uuid': gpu['uuid'], 'used_bytes': gpu['used_bytes'],
                                                    'elapsed_seconds': time.monotonic() - started})
                    report["peak_vram_bytes"] = max(report["peak_vram_bytes"], gpu["used_bytes"])
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
                    while (group_exists(process.pid) or gpu_pids()) and time.monotonic() < deadline:
                        time.sleep(.05)
                    report['cleanup_verified'] = not group_exists(process.pid) and not gpu_pids()
                except Exception as exc:
                    report['error'] = report['error'] or 'cleanup: ' + type(exc).__name__
                report['cleanup_seconds'] = time.monotonic() - cleanup
            # Final checkpoint is read AFTER termination, including immediate child errors.
            try:
                if checkpoint.stat().st_size > evidence_bytes // 3:
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
    report['provider_reconciliation_required'] = True
    save(output / 'supervisor.json', report)
    return report
