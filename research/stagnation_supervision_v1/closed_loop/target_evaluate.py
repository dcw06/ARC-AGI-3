"""Independent target-level replay. Trajectory completion alone cannot pass a target run.

Reads retained receipts and lossless telemetry; does not query a GPU, execute a
model, repair evidence, or reuse the supervisor's completion verdict as proof.
"""
import json
import math
from pathlib import Path

from certification.phase4_integrated_v2.evidence import LIMITS, TOTAL
from certification.phase4_integrated_v2.monitor import RAM, SCRATCH, VRAM, validate_binding
from certification.phase4_integrated_v2.telemetry import read_telemetry
from . import evaluate as trajectories
from .model_service import validate_ready
from .server_config import validate as validate_configuration

VERSION = 'stagnation_supervision_target_evaluation_r1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'invalid clock/count value')
    return value


def read(root, name):
    path = root / name
    require(not path.is_symlink() and path.is_file() and path.stat().st_size <= 1024**2,
            'missing/linked/oversized lifecycle receipt: ' + name)
    value = json.loads(path.read_bytes())
    require(type(value) is dict, 'lifecycle receipt must be an object: ' + name)
    return value


def lifecycle(root, spec, *, mode, session, internal_seconds):
    from .authority import SESSION_LIMITS
    from .evidence import load_verified
    require(mode in ('live', 'rehearsal') and session in SESSION_LIMITS, 'mode/session')
    ceiling = SESSION_LIMITS[session]['internal_seconds']
    if mode == 'live':
        require(internal_seconds in (None, ceiling), 'live budget override')
        internal_seconds = ceiling
        from .bridge import session_spec
        from .runner import protocol
        require(spec == session_spec(protocol(), session), 'target schedule differs from frozen session')
    else:
        require(type(internal_seconds) is int and 300 < internal_seconds <= ceiling, 'explicit rehearsal budget required')
    sizes = dict.fromkeys(LIMITS, 0)
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'linked lifecycle evidence')
        if path == root / '.evidence.lock':
            require(path.is_file() and path.stat().st_size == 0, 'invalid shared evidence lock')
        elif path.is_file():
            component = path.relative_to(root).parts[0]
            require(component in sizes, 'unbudgeted lifecycle evidence')
            sizes[component] += path.stat().st_size
    require(sum(sizes.values()) <= TOTAL and all(sizes[k] <= LIMITS[k] for k in sizes), 'lifecycle evidence budget')
    for name in ('control/failure.json', 'monitor/failure.json', 'worker/failure.json', 'worker/model-exit-pending.json'):
        require(not (root / name).exists(), 'failure receipt present: ' + name)

    outer = read(root, 'control/outer.json')
    first = read(root, 'control/notebook-cost.json')
    owned = read(root, 'control/ownership.json')
    cleanup = read(root, 'control/first-cell-supervisor-cleanup.json')
    gpu = read(root, 'control/gpu-cleanup.json')
    monitor = read(root, 'monitor/monitor-result.json')
    ready = read(root, 'monitor/ready.json')
    ack = read(root, 'control/monitor-ready-ack.json')
    stop = read(root, 'control/stop-monitor.json')
    telemetry = read_telemetry(root / 'monitor')
    host = read(root, 'worker/host-status.json')
    model = read(root, 'worker/model-ready.json')
    process = read(root, 'worker/model-process.json')
    worker = read(root, 'worker/worker-result.json')
    canary = read(root, 'worker/canary.json')
    config = read(root, 'worker/server-configuration.json')
    run = load_verified(root / 'worker/run')

    start = number(first['first_cell_monotonic'])
    end = number(first['elapsed_seconds'])
    outer_end = number(outer['elapsed_seconds'])
    cutoff = internal_seconds - 300
    require(0 <= outer_end <= end < internal_seconds, 'first-cell deadline/outer duration')
    require(first['internal_seconds'] == outer['internal_seconds'] == internal_seconds
            and outer['admission_cutoff_seconds'] == cutoff, 'independently expected lifecycle budget')
    require(first['mode'] == outer['mode'] == worker['mode'] == model['mode'] == mode
            and first['session'] == outer['session'] == session, 'lifecycle mode/session binding')
    require(all(x['first_cell_monotonic'] == start for x in (outer, owned, monitor, telemetry)), 'first-cell origin binding')
    require(first['scope'] == 'stagnation_supervision_first_cell' and outer['scope'] == 'stagnation_supervision_' + mode,
            'lifecycle scope')
    require(first['error'] is None and outer['error'] is None and not outer.get('cleanup_error'), 'lifecycle error')
    require(first['study_status'] == outer['status'] == 'study_complete_pending_independent_evaluation', 'lifecycle status')
    require(all(outer.get(k) is True for k in ('worker_released', 'process_groups_exited',
                    'independent_gpu_cleanup_verified', 'scratch_removed')) and first['first_cell_cleanup_verified'] is True,
            'lifecycle closure claims')
    require(first['dependency_trees_removed'] is (True if mode == 'live' else None), 'dependency cleanup')
    require(cleanup['drain_finished'] is True and cleanup['returncode'] == 0 and cleanup['errors'] == [], 'first-cell process/log cleanup')
    groups = cleanup['groups']
    require(type(groups) is dict and len(groups) == 3 and all(v is True for v in groups.values())
            and all(k.isdigit() and int(k) > 0 for k in groups), 'owned group closure inventory')
    require(str(owned['worker_pgid']) in groups and str(owned['monitor_pgid']) in groups
            and owned['worker_pgid'] != owned['monitor_pgid'], 'owned process groups')
    require(outer_end <= number(cleanup['checked_monotonic']) - start <= end, 'first-cell cleanup chronology')

    expected_scope = ('stagnation_supervision_live_resource_monitor' if mode == 'live'
                      else 'stagnation_supervision_rehearsal_monitor_injected_gpu')
    require(monitor['scope'] == telemetry['scope'] == ready['scope'] == expected_scope, 'monitor scope')
    require(monitor['status'] == telemetry['status'] == 'monitor_completed'
            and monitor['error'] is None and telemetry['error'] is None, 'monitor completion')
    require(ready['nonce'] == ack['nonce'] == owned['nonce'] and len(owned['nonce']) == 64
            and ready['monitor_pid'] == owned['monitor_pgid']
            and ready['worker_pid'] == monitor['worker_pid'] == telemetry['worker_pid'] == owned['worker_pgid'], 'monitor handshake binding')
    uuid = validate_binding(ready['gpu_binding'])
    require(monitor['gpu_binding'] == telemetry['gpu_binding'] == ready['gpu_binding'], 'monitor GPU binding')
    if mode == 'live':
        require('REHEARSAL' not in uuid, 'injected GPU cannot certify live lifecycle')
    require(monitor.get('sampling_interval_seconds') == telemetry.get('sampling_interval_seconds') == .5,
            'frozen telemetry sampling interval')
    samples = telemetry['samples']
    require(bool(samples) and ready['sample'] == samples[0], 'monitor readiness sample')
    previous = number(monitor['monitor_started_seconds'])
    require(previous == telemetry['monitor_started_seconds'], 'monitor startup binding')
    for sample in samples:
        elapsed = number(sample['elapsed_seconds'])
        require(0 <= elapsed - previous <= 1 and elapsed <= outer_end
                and math.isclose(number(sample['monotonic_seconds']), start + elapsed, abs_tol=1e-6, rel_tol=0),
                'monitor clock/gap/deadline')
        require(sample['uuid'] == uuid, 'sample GPU identity')
        for key, cap in (('used_bytes', VRAM), ('rss_bytes', RAM), ('scratch_bytes', SCRATCH)):
            require(type(sample[key]) is int and 0 <= sample[key] <= cap, 'sample resource limit: ' + key)
        previous = elapsed
    released, completed = number(outer['worker_released_seconds']), number(outer['worker_completed_seconds'])
    stopped, monitor_end = number(stop['elapsed_seconds']), number(monitor['monitor_ended_seconds'])
    require(number(samples[0]['elapsed_seconds']) <= released <= completed < cutoff
            and completed <= stopped <= previous <= monitor_end <= outer_end
            and telemetry['monitor_ended_seconds'] == monitor_end and stop['worker_group_exited'] is True,
            'monitor coverage through worker cleanup')
    require(gpu['scope'] == 'stagnation_supervision_independent_gpu_cleanup'
            and gpu['evidence_class'] == ('live' if mode == 'live' else 'rehearsal_injected_gpu_not_target_evidence')
            and gpu['gpu_uuid'] == uuid and gpu['gpu_cleanup_verified'] is True
            and gpu['groups_absent'] is True and type(gpu['remaining_gpu_pids']) is int
            and gpu['remaining_gpu_pids'] == 0 and gpu['error'] is None, 'independent GPU cleanup')
    require(monitor_end <= number(gpu['checked_monotonic']) - start <= outer_end, 'independent cleanup chronology')

    from .host import expected_artifact
    artifact = expected_artifact() if mode == 'live' else {'rehearsal': 'scripted_model_not_target_evidence'}
    validate_ready({'artifact': model['artifact'], 'startup_seconds': model['startup_seconds'], 'canary_audit': canary}, artifact)
    require(model['canary_sha256'] == canary['response_sha256'] and host['startup_seconds'] == model['startup_seconds'], 'canary/ready binding')
    require(host['status'] == 'stopped' and host['error'] == 'canceled', 'model host finalization')
    host_start = number(host['started_monotonic']) - start
    model_ready = number(model['ready_monotonic']) - start
    require(released <= host_start <= model_ready <= completed
            and host_start + number(host['startup_seconds']) <= model_ready
            and host_start + number(host['ended_seconds']) <= completed, 'model startup/closure chronology')
    require(type(process['pid']) is int and process['pid'] > 0 and worker['host_pid'] == process['pid']
            and released <= number(process['started_monotonic']) - start <= model_ready, 'model process binding')
    validate_configuration(config, mode=mode)
    require(host_start <= number(config['checked_monotonic']) - start <= model_ready, 'server configuration precedes readiness')
    require(worker['run_status'] == run['status'] == 'complete' and worker['error'] is None
            and worker.get('evidence_error') is None and worker['calls'] == host['policy_calls'] == run['calls']
            and worker['dispatches'] == run['dispatches'] and host['reflection_calls'] == run['reflection_calls'], 'worker/host/run reconciliation')
    require(outer['run_evidence'] == {'verified': True, 'run_status': run['status'], 'calls': run['calls'],
            'dispatches': run['dispatches'], 'episodes': len(run['episodes'])}, 'outer/run binding')
    require(number(run['ended_at']) <= number(run['deadline_seconds']) <= cutoff, 'trajectory deadline')
    cancel = read(root, 'control/cancel.json')
    require(cancel == {'reason': 'worker_finalization', 'host_pid': process['pid']}, 'normal finalization cancellation')
    return {'verified': True, 'mode': mode, 'session': session, 'internal_seconds': internal_seconds,
            'elapsed_seconds': end, 'telemetry_samples': len(samples), 'gpu_uuid': uuid,
            'prefix_caching_disabled': True, 'problems': []}


def evaluate_target(folder, spec, *, mode='live', session='1', internal_seconds=None):
    root = Path(folder)
    trajectory = trajectories.evaluate_output(root / 'worker/run', spec)
    try:
        require(root.is_dir() and not root.is_symlink(), 'target evidence root')
        result = lifecycle(root, spec, mode=mode, session=str(session), internal_seconds=internal_seconds)
    except (ValueError, OSError, KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        result = {'verified': False, 'problems': [f'{type(exc).__name__}: {exc}']}
    complete = trajectory['technically_complete'] and result['verified']
    return {'version': VERSION, 'technically_complete': complete, 'trajectory_complete': trajectory['technically_complete'],
            'lifecycle_verified': result['verified'], 'target_accepted': complete and mode == 'live',
            'evidence_scope': 'live_target' if mode == 'live' else 'scripted_cpu_injected_gpu',
            'trajectory': trajectory, 'lifecycle': result,
            'problems': trajectory.get('problems', []) + result['problems'], 'phase4_complete': False}
