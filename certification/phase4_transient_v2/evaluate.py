"""Independent diagnostic acceptance; no capacity or game-success claim."""
import hashlib,math
from certification.phase4_v13.evaluate import monitor_fields
from certification.phase4_v13.measurement import validate_telemetry
from certification.phase4_v13.canary import valid_canary
from certification.phase4_transient_v2.contract import protocol
from certification.phase4_transient_v2.action_contract import validate_action,request_legal_actions,validate_canary
LOCAL_CPU_SMOKE_SECONDS=120

def valid_request_window(start,end,cutoff,seconds,live):
    # The worker stores (began + 1200) - origin and began - origin.
    # Reassociation can differ by a few binary64 ULPs. Apply a fixed,
    # sub-nanosecond representation allowance ONLY to the duration bound.
    # Absolute cleanup reserve and actual end-before-cutoff stay strict.
    if not all(finite(v,seconds+1) for v in (start,end,cutoff)):
        return False
    duration_limit=start+1200
    allowance=4*math.ulp(float(seconds+1200))
    return (start<=end<cutoff<=seconds-(300 if live else 0)
            and cutoff<=duration_limit+allowance)


def finite(value,limit):return type(value) in (int,float) and math.isfinite(value) and 0<=value<limit

def evaluate(report,rows=None,*,live=True,seconds=3300):
    errors=[]; worker=report.get('worker') or {}
    if report.get('error') or report.get('status')!='worker_completed_pending_independent_evaluation':errors.append('supervisor failure')
    for key in ('cleanup_verified','scratch_removed'):
        if report.get(key) is not True:errors.append(key)
    if report.get('admission_canceled'):errors.append('admission canceled')
    for key,limit in [('elapsed_seconds',seconds),('peak_rss_bytes',128*1024**3),
        ('peak_scratch_bytes',4*1024**3),('final_scratch_bytes',4*1024**3),('cleanup_seconds',15)]:
        if not finite(report.get(key),limit):errors.append(key)
    if worker.get('model_inference') is not live or worker.get('status')!='complete' or worker.get('error'):errors.append('worker completion/class')
    if worker.get('configuration')!=protocol()['configuration']:errors.append('configuration binding')
    if not finite(worker.get('model_startup_seconds'),900.000001):errors.append('startup deadline')
    if live:
        for key in ('gpu_cleanup_verified','independent_gpu_cleanup_verified'):
            if report.get(key) is not True:errors.append(key)
        if report.get('resource_evidence_class')!='live_resource_monitor':errors.append('actual monitor required')
        canary=worker.get('canary_audit') or {}
        if (not valid_canary(canary) or canary.get('request_sha256')!='06853cc44e570cebee4b4623655b73c43072ee040d025e87e47696b3e15fac38'):
            errors.append('canary audit')
        try:
            validate_canary(canary['response_content'])
            if hashlib.sha256(canary['response_content'].encode()).hexdigest()!=canary['response_sha256']:raise ValueError('canary hash')
        except (KeyError,ValueError,TypeError):errors.append('canary body')
        if worker.get('model_artifact',{}).get('tree_sha256')!='052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627':errors.append('model binding')
    try:
        from certification.phase4_v13.monitor import validate_binding
        validate_binding(report['gpu_binding'])
        samples=report['gpu_telemetry']
        if len(samples)!=report['gpu_samples'] or max(s['used_bytes'] for s in samples)!=report['peak_vram_bytes']:
            raise ValueError('telemetry inventory/peak')
        for sample in samples:
            if not finite(sample['rss_bytes'],128*1024**3+1) or not finite(sample['scratch_bytes'],4*1024**3+1):raise ValueError('resource sample')
        validate_telemetry(report['gpu_telemetry'],report['monitor_started_seconds'],report['monitor_ended_seconds'],report['gpu_binding']['gpu_uuid'])
        if not report['monitor_started_seconds']<=report['worker_started_seconds']<report['worker_stopped_seconds']<=report['monitor_ended_seconds']<=report['elapsed_seconds']:raise ValueError('coverage')
    except (KeyError,ValueError,TypeError):errors.append('monitor coverage')
    try:
        start=worker['request_window_started_seconds'];end=worker['ended_seconds'];cutoff=worker['request_window_cutoff_seconds']
        if not valid_request_window(start,end,cutoff,seconds,live):raise ValueError('request deadline')
    except (KeyError,TypeError,ValueError):errors.append('request window')
    comparison=None
    try:
        from pathlib import Path
        from certification.phase4_transient_v2.trajectory import evaluate_trajectories
        comparison=evaluate_trajectories(worker,Path(report['evidence_root'])/'worker',seconds=seconds)
    except (OSError,KeyError,ValueError,TypeError,IndexError) as exc:
        errors.append('trajectory: '+str(exc)[:256])
    return {'passed':not errors,'errors':errors,'scope':'closed_loop_development_live' if live else 'scripted_cpu_only',
        'comparison':comparison,'comparison_is_scripted':not live,
        'model_inference':live,'capacity_candidate':None,'C_nominal':None,'C_admit':None,
        'development_model_lifecycle_passed':not errors,'phase4_complete':False}

def evaluate_local_smoke(report,rows=None,*,seconds=LOCAL_CPU_SMOKE_SECONDS):
    return evaluate(report,live=False,seconds=seconds)
