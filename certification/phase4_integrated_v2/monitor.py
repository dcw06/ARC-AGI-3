"""Resource-monitor integration seam. CLI exercises injected telemetry only.

No model, CUDA or provider API is called here. Live probes require a separately
reviewed/authorized target adapter; injected records are never target evidence.
"""
import json
import math
import os
from pathlib import Path
import sys
import time

from certification.phase4_integrated_v2.handshake import publish_local_ready
from certification.phase4_integrated_v2.measurement import save_bounded

VRAM = 86 * 1024**3
RAM = 128 * 1024**3
SCRATCH = 4 * 1024**3


def validate_binding(binding):
    if not isinstance(binding, dict):
        raise ValueError('missing GPU binding')
    uuid = binding.get('gpu_uuid')
    initial = binding.get('initial_telemetry')
    if not isinstance(uuid, str) or not uuid or not isinstance(initial, dict):
        raise ValueError('missing GPU identity')
    validate_sample(initial, uuid)
    if binding.get('max_used_vram_bytes') != VRAM:
        raise ValueError('VRAM budget drift')
    return uuid


def validate_sample(sample, uuid):
    if not isinstance(sample, dict):
        raise ValueError('missing telemetry')
    used, total = sample.get('used_bytes'), sample.get('total_bytes')
    if (sample.get('uuid') != uuid or not isinstance(sample.get('name'), str)
            or 'RTX PRO 6000' not in sample['name'] or type(used) is not int
            or type(total) is not int or not 0 <= used <= VRAM <= total):
        raise ValueError('GPU identity or resource violation')


def observe_injected(worker_pid, output, *, bind, sample, rss, scratch, alive,
                     ready, clock=time.monotonic, sleep=time.sleep,
                     interval=.25, maximum_gap=1.0, evidence_bytes=16 * 1024**2,
                     origin=None, evidence_store=None):
    """Single writer owns this dedicated evidence directory, including temp peaks.

    All probes are injected. Readiness follows validated binding AND a complete,
    durably retained first sample. Errors remain terminal; no probe retries.
    """
    if (type(worker_pid) is not int or worker_pid <= 0
            or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
                   for v in (interval, maximum_gap)) or interval > maximum_gap
            or type(evidence_bytes) is not int or evidence_bytes < 8192):
        raise ValueError('invalid monitor limits')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    state = {'scope': 'injected_resource_monitor_not_target_evidence',
             'status': 'failed', 'error': None, 'gpu_binding': None,
             'samples': [], 'worker_pid': worker_pid, 'ready_published': False,
             'phase4_complete': False, 'target_gpu_certified': False}
    started = clock()
    origin = started if origin is None else origin
    if type(origin) not in (int, float) or not math.isfinite(origin) or not 0 <= origin <= started:
        raise ValueError('invalid first-cell monotonic origin')
    state['first_cell_monotonic'] = origin
    state['monitor_started_seconds'] = started - origin
    def retain(name, value, *, failure=False):
        if evidence_store is not None:
            return evidence_store.save('failure.json' if failure else name, value,
                                       failure_receipt=failure)
        return save_bounded(output / name, value,
                            byte_limit=evidence_bytes if failure else evidence_bytes-4096)
    last = started
    try:
        binding = bind()
        uuid = validate_binding(binding)
        state['gpu_binding'] = binding
        if not alive():
            raise RuntimeError('worker disappeared before readiness')
        while True:
            gpu = sample(uuid, VRAM)
            validate_sample(gpu, uuid)
            memory, disk = rss(worker_pid), scratch()
            if (type(memory) is not int or not 0 <= memory <= RAM
                    or type(disk) is not int or not 0 <= disk <= SCRATCH):
                raise ValueError('RAM/scratch resource violation')
            now = clock()
            if not math.isfinite(now) or not 0 <= now - last <= maximum_gap:
                raise ValueError('monitor sampling gap or clock reversal')
            state['samples'].append({'uuid': uuid, 'used_bytes': gpu['used_bytes'],
                                    'rss_bytes': memory, 'scratch_bytes': disk,
                                    'monotonic_seconds': now, 'elapsed_seconds': now-origin})
            # Reserve space for a small failure receipt. Reject the whole update;
            # the previous complete checkpoint remains intact, never truncated.
            retain('telemetry.json', state)
            last = now
            if not state['ready_published']:
                ready()
                state['ready_published'] = True
            if not alive():
                state['status'] = 'injected_monitor_completed'
                break
            sleep(interval)
        retain('telemetry.json', state)
    except Exception as exc:
        state['error'] = type(exc).__name__ + ': ' + str(exc)[:512]
        state['status'] = 'failed'
    finally:
        receipt = {key: state[key] for key in ('scope', 'status', 'error',
                   'worker_pid', 'ready_published', 'phase4_complete', 'target_gpu_certified')}
        receipt['monitor_started_monotonic'] = started
        receipt['monitor_ended_monotonic'] = clock()
        receipt['first_cell_monotonic'] = origin
        receipt['monitor_started_seconds'] = started-origin
        receipt['monitor_ended_seconds'] = receipt['monitor_ended_monotonic']-origin
        receipt['samples_attempted'] = len(state['samples'])
        retain('monitor-result.json', receipt, failure=state['status']=='failed')
    return receipt


if __name__ == '__main__':
    # Explicit fixture-only command used by subprocess tests. No live GPU mode.
    if len(sys.argv) != 4 or sys.argv[1] != '--injected':
        raise PermissionError('live resource monitor is not authorized or packaged')
    pid, output = int(sys.argv[2]), Path(sys.argv[3])
    fixture = {'uuid': 'GPU-INJECTED', 'name': 'RTX PRO 6000',
               'total_bytes': 96 * 1024**3, 'used_bytes': 1}
    def alive():
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
    result = observe_injected(pid, output, bind=lambda: {'gpu_uuid': fixture['uuid'],
        'max_used_vram_bytes': VRAM, 'initial_telemetry': fixture},
        sample=lambda *_: fixture, rss=lambda _: 1, scratch=lambda: 1,
        alive=alive, ready=publish_local_ready, interval=.02)
    raise SystemExit(0 if result['status'] == 'injected_monitor_completed' else 1)
