"""Integrated pilot child roles. Live mode is gated before model imports."""
import argparse
import json
import os
from pathlib import Path
import time

from certification.phase4_multimodal_preflight_v1.evidence import EvidenceStore
from certification.phase4_multimodal_preflight_v1.live_probes import require_live_authority


def read(path):
    return json.loads(path.read_text())


def worker(args):
    store = EvidenceStore(args.output, 'worker')
    try:
        if args.mode == 'live':
            require_live_authority()
        if args.fault == 'worker':
            raise RuntimeError('injected worker failure')
        if args.fault == 'evidence':
            store.save('state.json', {'oversized': 'x' * (33*1024**2)})
        if args.fault == 'cancel':
            while not (args.output/'control/cancel.json').exists():
                time.sleep(.02)
            raise RuntimeError('injected worker acknowledged cancellation')
        from certification.phase4_multimodal_preflight_v1.worker import run_cases, ScriptedService
        service = ScriptedService(os.environ.get('PREFLIGHT_FIXTURE_MODE','verified') if args.mode=='local' else 'verified')
        if args.mode == 'live':
            from certification.phase4_multimodal_preflight_v1.bridge import ModelProxy
            service = ModelProxy(args.scratch,os.environ['P4_MODEL_PYTHON'],
                args.started+args.seconds-args.reserve,args.output/'control/cancel.json')
            service.start()
        store.save('model-ready.json', {'model_inference': args.mode=='live',
            'elapsed_seconds':time.monotonic()-args.started})
        state=run_cases(service,store,started=args.started,
            deadline=args.started+args.seconds-args.reserve,
            cancel=args.output/'control/cancel.json',live=args.mode=='live')
        if state['status'] != 'complete' or state.get('error'):
            raise RuntimeError('worker did not complete')
    except Exception as exc:
        store.save('failure.json', {'error': type(exc).__name__+': '+str(exc)[:512]}, failure_receipt=True)
        raise


def monitor(args):
    from certification.phase4_multimodal_preflight_v1.monitor import validate_binding, validate_sample, VRAM, RAM, SCRATCH
    from certification.phase4_multimodal_preflight_v1.measurement import validate_telemetry
    store = EvidenceStore(args.output, 'monitor')
    from certification.phase4_multimodal_preflight_v1.telemetry import TelemetryWriter
    telemetry_writer = None
    state = {'scope': 'live_resource_monitor' if args.mode=='live' else 'injected_resource_monitor_not_target_evidence',
             'error': None, 'status': 'running', 'samples': [],
             'worker_pid': args.worker_pid, 'first_cell_monotonic': args.started,
             'ready_published': False, 'monitor_started_monotonic': time.monotonic()}
    state['monitor_started_seconds'] = state['monitor_started_monotonic']-args.started
    from certification.phase4_multimodal_preflight_v1.monitor_diagnostics import collect, failure_receipt
    context={'phase':'binding'}
    try:
        if args.mode == 'live':
            from certification.phase4_multimodal_preflight_v1.live_probes import LiveResourceProbes
            probes = LiveResourceProbes(args.worker_pid, args.scratch)
            binding = probes.bind()
            sample, rss, scratch = probes.sample, probes.rss, probes.scratch
        else:
            from evaluation.phase4_runner import group_rss_bytes, tree_bytes
            fixture = {'uuid': 'GPU-INJECTED', 'name': 'RTX PRO 6000',
                       'used_bytes': 1, 'total_bytes': 96*1024**3}
            binding = {'gpu_uuid': fixture['uuid'], 'max_used_vram_bytes': VRAM, 'initial_telemetry': fixture}
            sample, rss, scratch = lambda *_: fixture, group_rss_bytes, lambda: tree_bytes(args.scratch)
        uuid = validate_binding(binding)
        state['gpu_binding'] = binding
        # Probe imports/binding are startup, not missing post-readiness samples.
        state['monitor_started_monotonic'] = time.monotonic()
        state['monitor_started_seconds'] = state['monitor_started_monotonic']-args.started
        previous = state['monitor_started_seconds']
        from certification.phase4_multimodal_preflight_v1.async_telemetry import AsyncTelemetry
        telemetry_writer=AsyncTelemetry(store, {'nonce':args.nonce,'worker_pid':args.worker_pid,
            'monitor_pid':os.getpid(),'scope':state['scope'],'gpu_binding':binding},
            acknowledgement=args.output/'control/monitor-ready-ack.json')
        while True:
            if args.fault == 'monitor':
                raise RuntimeError('injected monitor failure')
            record=collect(sample,rss,scratch,uuid,args.worker_pid,args.started,previous,context)
            state['samples'].append(record)
            context['phase']='telemetry_writer_health'
            context['writer']=telemetry_writer.health()
            context['phase']='telemetry_enqueue'
            state['ready_published']=True
            telemetry_writer.submit(record,{k:v for k,v in state.items() if k!='samples'})
            previous = record['elapsed_seconds']
            if (args.output/'control/stop-monitor.json').exists():
                context['phase']='monitor_gpu_cleanup'
                state['gpu_cleanup_verified'] = args.mode=='live' and not probes.gpu_processes()
                if args.mode=='live' and not state['gpu_cleanup_verified']:
                    raise RuntimeError('GPU processes remain after worker group cleanup')
                state['status'] = 'live_monitor_completed' if args.mode=='live' else 'injected_monitor_completed'
                break
            time.sleep(.25)
        state['monitor_ended_monotonic'] = time.monotonic()
        state['monitor_ended_seconds'] = state['monitor_ended_monotonic']-args.started
        state['samples_attempted'] = len(state['samples'])
        validate_telemetry(state['samples'], state['monitor_started_seconds'], state['monitor_ended_seconds'], uuid)
        context['phase']='telemetry_drain'
        telemetry_writer.finish({k:v for k,v in state.items() if k!='samples'},args.started+args.seconds-3)
        state['persistence']=telemetry_writer.health()
        store.save('monitor-result.json', {k:v for k,v in state.items() if k!='samples'})
    except Exception as exc:
        store.save('failure.json', failure_receipt(exc,context), failure_receipt=True)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('role', choices=['worker','monitor'])
    p.add_argument('--mode', choices=['local','live'], required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--scratch', type=Path, required=True)
    p.add_argument('--environments', type=Path, required=True)
    p.add_argument('--started', type=float, required=True)
    p.add_argument('--seconds', type=float, required=True)
    p.add_argument('--reserve', type=float, required=True)
    p.add_argument('--fault', default='none')
    p.add_argument('--worker-pid', type=int)
    p.add_argument('--nonce')
    args = p.parse_args()
    if args.mode == 'live': require_live_authority()
    (worker if args.role=='worker' else monitor)(args)
