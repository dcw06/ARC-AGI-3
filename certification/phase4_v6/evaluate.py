"""Additional v6 checks; always require the v4 model/lifecycle evidence first."""
from collections import Counter
import math

from certification.phase4_v4.evaluate import evaluate as evaluate_v4
from certification.phase4_v5.capacity import estimate
from certification.phase4_v6.measurement import validate_telemetry
from certification.phase4_v6.monitor import validate_binding


def monitor_fields(receipt, telemetry, *, first_cell_monotonic):
    """Convert retained monitor evidence without rebasing or dropping samples."""
    if (type(first_cell_monotonic) not in (float, int)
            or not math.isfinite(first_cell_monotonic) or first_cell_monotonic < 0):
        raise ValueError('invalid common clock')
    if (receipt.get('error') or telemetry.get('error')
            or receipt.get('first_cell_monotonic') != first_cell_monotonic
            or telemetry.get('first_cell_monotonic') != first_cell_monotonic
            or receipt.get('scope') != telemetry.get('scope')
            or receipt.get('worker_pid') != telemetry.get('worker_pid')
            or receipt.get('ready_published') is not True
            or telemetry.get('ready_published') is not True
            or receipt.get('status') != telemetry.get('status')
            or receipt.get('status') not in ('injected_monitor_completed', 'live_monitor_completed')):
        raise ValueError('monitor identity/clock/status mismatch')
    samples = telemetry['samples']
    if len(samples) != receipt['samples_attempted']:
        raise ValueError('monitor samples missing')
    start, end = receipt['monitor_started_seconds'], receipt['monitor_ended_seconds']
    if (receipt['monitor_started_monotonic']-first_cell_monotonic != start
            or receipt['monitor_ended_monotonic']-first_cell_monotonic != end
            or telemetry['monitor_started_seconds'] != start):
        raise ValueError('monitor clock conversion mismatch')
    for sample in samples:
        if sample['monotonic_seconds']-first_cell_monotonic != sample['elapsed_seconds']:
            raise ValueError('sample clock mismatch')
        for key, limit in [('rss_bytes', 128*1024**3), ('scratch_bytes', 4*1024**3)]:
            if type(sample.get(key)) is not int or not 0 <= sample[key] <= limit:
                raise ValueError('monitor resource evidence missing/invalid')
    uuid = validate_binding(telemetry['gpu_binding'])
    validate_telemetry(samples, start, end, uuid)
    return {'gpu_binding': telemetry['gpu_binding'], 'gpu_telemetry': samples,
            'gpu_samples': len(samples), 'peak_vram_bytes': max(s['used_bytes'] for s in samples),
            'peak_rss_bytes': max(s['rss_bytes'] for s in samples),
            'peak_scratch_bytes': max(s['scratch_bytes'] for s in samples),
            'monitor_started_seconds': start, 'monitor_ended_seconds': end,
            'resource_evidence_class': receipt['scope']}


def capacity_from_worker(worker):
    requests = worker['requests']
    events = worker['request_timeline']
    if Counter(r.get('request_id') for r in requests) != Counter(e.get('request_id') for e in events):
        raise ValueError('timeline/request inventory mismatch')
    by_id = {e['request_id']: e for e in events}
    for request in requests:
        event = by_id[request['request_id']]
        if event['client_id'] != request['client_id'] or request.get('error') is not None:
            raise ValueError('request identity/error mismatch')
        returned = event.get('returned_seconds')
        completed = event.get('completed_seconds')
        if (type(returned) not in (float, int) or not math.isfinite(returned)
                or type(completed) not in (float, int) or not math.isfinite(completed)
                or not completed <= returned <= worker['workload_ended_seconds']):
            raise ValueError('incomplete caller timeline')
    return estimate(worker['workload_started_seconds'], worker['workload_ended_seconds'], events)


def evaluate(report, rows):
    result = evaluate_v4(report, rows)
    result['capacity_candidate'] = None
    if report.get('resource_evidence_class') != 'live_resource_monitor':
        result['errors'].append('live resource monitor evidence required; injected probes cannot certify')
    try:
        validate_telemetry(report['gpu_telemetry'], report['monitor_started_seconds'],
                           report['monitor_ended_seconds'], report['gpu_binding']['gpu_uuid'])
        # Sampling must encompass worker/model lifetime; window supplied by the
        # producer is not free to shrink to fit sparse observations.
        if not (report['monitor_started_seconds'] <= report['worker_started_seconds']
                < report['worker_stopped_seconds'] <= report['monitor_ended_seconds']
                <= report['elapsed_seconds']):
            raise ValueError('telemetry does not enclose worker lifetime')
        candidate = capacity_from_worker(report['worker'])
        if not result['errors']:
            result['capacity_candidate'] = candidate
    except (ValueError, KeyError, TypeError) as exc:
        result['errors'].append('v6 measurement: ' + str(exc))
    result['passed'] = not result['errors']
    result['development_model_lifecycle_passed'] = result['passed']
    result['C_admit'] = None
    return result
