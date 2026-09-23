"""Bounded failure context; rejected samples never become valid telemetry."""
import time
from certification.phase4_multimodal_preflight_v3.monitor import RAM, SCRATCH, VRAM, validate_sample


def collect(sample, rss, scratch, uuid, pid, origin, previous, context, clock=time.monotonic):
    persistence=context.get('persistence_seconds')
    writer=context.get('writer')
    context.clear()
    context.update(previous_seconds=previous, phase='gpu', probe_seconds={},
                   previous_persistence_seconds=persistence,writer=writer)
    def probe(name, operation):
        context['phase']=name
        begin=clock()
        try:
            return operation()
        finally:
            context['probe_seconds'][name]=clock()-begin
            context['current_seconds']=clock()-origin
            context['gap_seconds']=context['current_seconds']-previous
    gpu=probe('gpu',lambda:sample(uuid,VRAM))
    context['gpu_used_bytes']=gpu.get('used_bytes')
    context['gpu_uuid']=gpu.get('uuid')
    context['gpu_total_bytes']=gpu.get('total_bytes')
    context['phase']='gpu_validation'
    if type(gpu.get('used_bytes')) is int and gpu['used_bytes']>VRAM:
        context.update(violations=['vram_bytes'],limits={'vram_bytes':VRAM})
    validate_sample(gpu,uuid)
    memory=probe('rss',lambda:rss(pid));context['rss_bytes']=memory
    disk=probe('scratch',scratch);context['scratch_bytes']=disk
    now=clock()-origin
    context.update(current_seconds=now,gap_seconds=now-previous,phase='limits')
    violations=[]
    if type(memory) is not int or not 0<=memory<=RAM: violations.append('rss_bytes')
    if type(disk) is not int or not 0<=disk<=SCRATCH: violations.append('scratch_bytes')
    if not 0<=now-previous<=1: violations.append('sampling_gap_seconds')
    context['violations']=violations
    context['limits']={'rss_bytes':RAM,'scratch_bytes':SCRATCH,'sampling_gap_seconds':1}
    if violations: raise ValueError('monitor limit: '+','.join(violations))
    return {'uuid':uuid,'used_bytes':gpu['used_bytes'],'rss_bytes':memory,
            'scratch_bytes':disk,'elapsed_seconds':now,'monotonic_seconds':now+origin}


def failure_receipt(exc, context):
    # Only fixed keys and small probe values, never telemetry history or process lists.
    return {'error':type(exc).__name__+': '+str(exc)[:256], 'diagnostics':context,
            'rejected_measurement_is_valid_telemetry':False}
