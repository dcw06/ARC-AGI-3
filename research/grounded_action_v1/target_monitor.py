"""Stage B monitor with real-probe mode gated by Stage B authority."""
import os
from pathlib import Path
import time

from certification.phase4_integrated_v2.async_telemetry import AsyncTelemetry
from certification.phase4_integrated_v2.evidence import EvidenceStore
from certification.phase4_integrated_v2.monitor import VRAM, validate_binding
from certification.phase4_integrated_v2.monitor_diagnostics import collect, failure_receipt
from .authority import require
from .target_resources import LiveProbes


def observe(worker_pid, scratch, output, *, started, deadline, stop, nonce,
            probes_factory=None, interval=.25, clock=time.monotonic, sleep=time.sleep):
    """Retain each measured sample; publish readiness after durable first sample."""
    live = probes_factory is None
    if live:
        require()  # Before construction of any real GPU probe.
        probes_factory = LiveProbes
    if type(worker_pid) is not int or worker_pid <= 0 or not 0 < interval <= 1:
        raise ValueError('monitor limits')
    output, stop = Path(output), Path(stop)
    store = EvidenceStore(output, 'monitor')
    probes = probes_factory(worker_pid, scratch)
    state = {'scope': 'stage_b_live_resource_monitor' if live else 'stage_b_injected_review_monitor',
             'status': 'running', 'error': None, 'worker_pid': worker_pid,
             'first_cell_monotonic': started, 'samples': []}
    context = {'phase': 'binding'}
    writer = None
    try:
        binding = probes.bind()
        uuid = validate_binding(binding)
        state['gpu_binding'] = binding
        state['monitor_started_seconds'] = clock() - started
        writer = AsyncTelemetry(store, {'nonce': nonce, 'worker_pid': worker_pid,
            'monitor_pid': os.getpid(), 'scope': state['scope'], 'gpu_binding': binding},
            acknowledgement=output / 'control/monitor-ready-ack.json')
        previous = state['monitor_started_seconds']
        while True:
            if clock() >= deadline:
                raise TimeoutError('Stage B monitor deadline')
            context['writer'] = writer.health()
            record = collect(lambda identity, _limit: probes.sample(identity),
                             lambda pid: probes.rss(pid), probes.scratch_bytes,
                             uuid, worker_pid, started, previous, context, clock=clock)
            state['samples'].append(record)
            previous = record['elapsed_seconds']
            writer.submit(record, {k: v for k, v in state.items() if k != 'samples'})
            if stop.exists():
                if live and probes.gpu_pids():
                    raise RuntimeError('GPU processes remain at monitor stop')
                state['status'] = 'live_monitor_completed' if live else 'injected_monitor_completed'
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
    from .authority import require
    require()  # Before any live GPU probe.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-pid', type=int, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--started', type=float, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--stop', type=Path, required=True)
    parser.add_argument('--nonce', required=True)
    args = parser.parse_args()
    state = observe(args.worker_pid, args.scratch, args.output,
                    started=args.started, deadline=args.deadline,
                    stop=args.stop, nonce=args.nonce)
    raise SystemExit(0 if state['status'] == 'live_monitor_completed' else 1)


if __name__ == '__main__':
    main()
