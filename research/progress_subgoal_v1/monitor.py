# Derived from research/ws3_questionnaire_v1/monitor.py by research/progress_subgoal_v1/derive.py; edit the derivation, not this file.
"""Resource monitor; live probes require this experiment's authority, rehearsal probes inject only the GPU."""
import os
from pathlib import Path
import time

from certification.phase4_integrated_v2.async_telemetry import AsyncTelemetry
from certification.phase4_integrated_v2.evidence import EvidenceStore
from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.monitor_diagnostics import collect, failure_receipt
from .resources import probes_for

SCOPES = {'live': 'evidence_comprehension_live_resource_monitor',
          'rehearsal': 'evidence_comprehension_rehearsal_monitor_injected_gpu'}
MONITOR_FAULTS = ('none', 'exit', 'exit_before_ready')
MID_STUDY_HANDSHAKE_SECONDS = 120


def exit_mid_study(output, bound=MID_STUDY_HANDSHAKE_SECONDS, clock=time.monotonic, sleep=time.sleep):
    """Rehearsal only: exit once study evidence exists (run manifest and first call), or at the bound."""
    output = Path(output)
    begun = clock()
    while clock() - begun < bound:
        if (output / 'worker/run/manifest.json').exists() and (output / 'worker/run/calls.jsonl').exists():
            os._exit(3)
        sleep(0.05)
    EvidenceStore(output, 'monitor').save('handshake-timeout.json', {
        'fault': 'exit', 'bound_seconds': bound,
        'reason': 'study evidence did not appear before the mid-study handshake bound'})
    os._exit(4)


def observe(worker_pid, scratch, output, *, started, deadline, stop, nonce, mode='live',
            interval=.25, clock=time.monotonic, sleep=time.sleep):
    """Retain each measured sample; publish readiness after a durable first sample."""
    if type(worker_pid) is not int or worker_pid <= 0 or not 0 < interval <= 1:
        raise ValueError('monitor limits')
    output, stop = Path(output), Path(stop)
    store = EvidenceStore(output, 'monitor')
    state = {'scope': SCOPES[mode], 'status': 'running', 'error': None, 'worker_pid': worker_pid,
             'first_cell_monotonic': started, 'samples': []}
    context = {'phase': 'binding'}
    try:
        probes = probes_for(mode)(worker_pid, scratch)  # live: authority checked before any GPU probe
        binding = probes.bind()
        uuid = validate_binding(binding)
        state['gpu_binding'] = binding
        state['monitor_started_seconds'] = clock() - started
        writer = AsyncTelemetry(store, {'nonce': nonce, 'worker_pid': worker_pid, 'monitor_pid': os.getpid(),
                                        'scope': state['scope'], 'gpu_binding': binding},
                                acknowledgement=output / 'control/monitor-ready-ack.json')
        previous = state['monitor_started_seconds']
        while True:
            if clock() >= deadline:
                raise TimeoutError('monitor deadline')
            context['writer'] = writer.health()
            record = collect(lambda identity, _limit: probes.sample(identity), lambda pid: probes.rss(pid),
                             probes.scratch_bytes, uuid, worker_pid, started, previous, context, clock=clock)
            state['samples'].append(record)
            previous = record['elapsed_seconds']
            writer.submit(record, {k: v for k, v in state.items() if k != 'samples'})
            if stop.exists():
                if probes.gpu_pids():
                    raise RuntimeError('GPU processes remain at monitor stop')
                state['status'] = 'monitor_completed'
                break
            sleep(interval)
        state['monitor_ended_seconds'] = clock() - started
        writer.finish({k: v for k, v in state.items() if k != 'samples'}, deadline - 3)
        store.save('monitor-result.json', {k: v for k, v in state.items() if k != 'samples'})
    except Exception as exc:
        state.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
        store.save('failure.json', failure_receipt(exc, context), failure_receipt=True)
    return {k: v for k, v in state.items() if k != 'samples'}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-pid', type=int, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--started', type=float, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--stop', type=Path, required=True)
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), required=True)
    parser.add_argument('--fault', choices=MONITOR_FAULTS, default='none')
    args = parser.parse_args()
    if args.mode == 'live':
        from .authority import require
        require()
        if args.fault != 'none':
            raise PermissionError('faults are rehearsal-only')
    if args.fault == 'exit_before_ready':
        # Rehearsal: the monitor dies before publishing readiness, so the supervisor never releases the worker
        # and no study evidence can exist. Deterministic: no timing race is involved.
        os._exit(3)
    if args.fault == 'exit':
        # Rehearsal: the monitor dies mid-study. Bounded readiness handshake: it waits until the worker's run
        # evidence and first retained call exist, then exits; if they do not appear within the bound it exits
        # anyway and leaves a receipt saying so, so a slow start is visible rather than silently changing the case.
        import threading
        threading.Thread(target=exit_mid_study, args=(args.output,), daemon=True).start()
    state = observe(args.worker_pid, args.scratch, args.output, started=args.started, deadline=args.deadline,
                    stop=args.stop, nonce=args.nonce, mode=args.mode)
    raise SystemExit(0 if state['status'] == 'monitor_completed' else 1)


if __name__ == '__main__':
    main()
