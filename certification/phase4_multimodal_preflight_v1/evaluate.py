"""Independent preflight acceptance and outcome classification; no perception or capacity claim."""
import hashlib,math
from certification.phase4_v13.evaluate import monitor_fields  # noqa: F401  (re-exported for pilot.py)
from certification.phase4_v13.measurement import validate_telemetry
from certification.phase4_v13.canary import valid_canary
from certification.phase4_multimodal_preflight_v1.cases import load_cases,image_part
from certification.phase4_multimodal_preflight_v1.action_contract import validate_canary
from certification.phase4_multimodal_preflight_v1.worker import CLASSIFIED,CONFIGURATION
LOCAL_CPU_SMOKE_SECONDS=120
VERDICTS=('image_input_verified','dependency_missing','image_rejected_by_server','token_accounting_mismatch',
    'image_not_consumed','text_control_failed','lifecycle_failure')

def valid_request_window(start,end,cutoff,seconds,live):
    if not all(finite(v,seconds+1) for v in (start,end,cutoff)):return False
    allowance=4*math.ulp(float(seconds+300))
    return start<=end<cutoff<=seconds-(300 if live else 0) and cutoff<=start+300+allowance

def finite(value,limit):return type(value) in (int,float) and math.isfinite(value) and 0<=value<limit

def check_row(planned,row,preflight):
    """Binding and internal-consistency checks for one retained probe row."""
    if row['probe_id']!=planned['probe_id'] or row['request_sha256']!=planned['request_sha256'] or row.get('request')!=planned['request']:
        raise ValueError('request binding')
    image=image_part(planned['request']) is not None
    if row['status']=='classified_failure':
        kind=row['failure_kind'];audit=row.get('audit',{})
        if kind not in CLASSIFIED or audit.get('failure_kind')!=kind or audit.get('request_sha256')!=planned['request_sha256']:
            raise ValueError('classified failure evidence')
        if kind=='dependency_missing' and (not image or preflight['processor']['available'] is not False):raise ValueError('dependency claim')
        if kind in ('image_rejected_by_server','server_rejected') and (type(audit.get('http_status')) is not int or audit['http_status']<400
            or (kind=='image_rejected_by_server')!=image):raise ValueError('rejection claim')
        if kind=='token_accounting_mismatch' and 'server_prompt_tokens' in audit and audit['server_prompt_tokens']==audit.get('tokenizer_prompt_tokens'):
            raise ValueError('mismatch claim without a mismatch')
        return
    if row['status']!='complete' or row['error'] is not None or row['response_truncated']:raise ValueError('incomplete response')
    raw=row['response_content'].encode()
    if len(raw)>8192 or len(raw)!=row['response_bytes'] or hashlib.sha256(raw).hexdigest()!=row['response_sha256']:raise ValueError('response hash')
    a=row['audit'];p=a['server_prompt_tokens'];c=a['server_completion_tokens']
    if (a['request_sha256']!=planned['request_sha256'] or type(p) is not int or not 0<p<=65472
        or a['tokenizer_prompt_tokens']!=p or a['expectation']['expected_prompt_tokens']!=p
        or type(c) is not int or not 1<=c<=64 or 'finish_reason' not in a or not finite(a['service_seconds'],180)):
        raise ValueError('token/service audit')
    e=a['expectation']
    if image and (e['processor_full_prompt_tokens']!=p or e['manual_prompt_tokens']!=p
        or e['image_tokens_processor']!=e['image_grid_thw'][0]*e['image_grid_thw'][1]*e['image_grid_thw'][2]//4):
        raise ValueError('processor evidence')
    from certification.phase4_multimodal_preflight_v1.probes import score
    if row['answer']!=score(planned,row['response_content'],a['finish_reason']):raise ValueError('answer score binding')

def classify(worker,cases,lifecycle_ok):
    rows={r['probe_id']:r for r in worker.get('cases',[])};planned={c['probe_id']:c for c in cases}
    from certification.phase4_multimodal_preflight_v1.probes import behavioural
    images=[p for p in ('I1','I2','I3')]
    kinds={p:rows.get(p,{}).get('failure_kind') for p in planned}
    summary={'probes':{},'flags':[],'consumption':None,'behavioural':None,
        'mount_processor_files':(worker.get('preflight') or {}).get('mount_inventory',{}).get('processor_files'),
        'processor':(worker.get('preflight') or {}).get('processor')}
    for p,row in rows.items():
        a=row.get('audit',{});e=a.get('expectation') or {}
        summary['probes'][p]={'status':row.get('status'),'failure_kind':row.get('failure_kind'),
            'server_prompt_tokens':a.get('server_prompt_tokens'),'expected_prompt_tokens':e.get('expected_prompt_tokens'),
            'image_grid_thw':e.get('image_grid_thw'),'processed':[e.get('processed_width'),e.get('processed_height')] if 'processed_width' in e else None,
            'image_tokens_processor':e.get('image_tokens_processor'),'finish_reason':a.get('finish_reason'),
            'answer':row.get('answer'),'http_status':a.get('http_status')}
    if not lifecycle_ok or any(p not in rows for p in planned):verdict='lifecycle_failure'
    elif (summary['processor'] or {}).get('available') is not True or any(kinds[p]=='dependency_missing' for p in images):verdict='dependency_missing'
    elif any(kinds[p]=='image_rejected_by_server' for p in images):verdict='image_rejected_by_server'
    elif rows['T0'].get('status')!='complete':verdict='text_control_failed'
    else:
        t0=rows['T0']['audit']['server_prompt_tokens']
        def server(p):return rows[p].get('audit',{}).get('server_prompt_tokens')
        # Consumption: I2 and T0 differ only by the image part (checked in load_cases).
        i2=rows['I2'];e2=i2.get('audit',{}).get('expectation') or {}
        delta=server('I2')-t0 if type(server('I2')) is int else None
        expected=e2.get('image_tokens_processor')+2 if e2.get('image_tokens_processor') is not None else None
        summary['consumption']={'server_delta_I2_minus_T0':delta,'expected_image_tokens_plus_markers':expected}
        if delta is not None and expected is not None and delta!=expected and delta<=3:verdict='image_not_consumed'
        elif any(kinds[p]=='token_accounting_mismatch' for p in images) or delta!=expected:verdict='token_accounting_mismatch'
        elif server('I2')!=server('I3'):verdict='token_accounting_mismatch'  # same text, same image size
        else:verdict='image_input_verified'
    summary['verdict']=verdict
    if verdict=='image_input_verified':
        summary['behavioural']=behavioural(rows['I2'].get('answer'),rows['I3'].get('answer'))
        if summary['behavioural']!='answers_differ_both_correct' and summary['behavioural']!='answers_differ':
            summary['flags'].append('review_required_behavioural')
        for p in images:
            e=rows[p]['audit']['expectation'];arith=planned[p]['image']['provisional_arithmetic']
            frozen=rows[p]['audit'].get('frozen_local_expected_prompt_tokens')
            if (e['image_grid_thw']!=arith['grid_thw'] or e['image_tokens_processor']!=arith['image_tokens']
                or frozen!=e['expected_prompt_tokens']):
                if 'arithmetic_revision_required' not in summary['flags']:summary['flags'].append('arithmetic_revision_required')
    # Any review flag blocks the comparison: behavioural concerns, and measured processor
    # geometry/counts that must first be reviewed into the frozen perception protocol.
    summary['representation_comparison_unblocked']=verdict=='image_input_verified' and not summary['flags']
    return summary

def evaluate(report,rows=None,*,live=True,seconds=1680):
    errors=[]; worker=report.get('worker') or {}
    if report.get('error') or report.get('status')!='worker_completed_pending_independent_evaluation':errors.append('supervisor failure')
    for key in ('cleanup_verified','scratch_removed'):
        if report.get(key) is not True:errors.append(key)
    if report.get('admission_canceled'):errors.append('admission canceled')
    for key,limit in [('elapsed_seconds',seconds),('peak_rss_bytes',128*1024**3),
        ('peak_scratch_bytes',4*1024**3),('final_scratch_bytes',4*1024**3),('cleanup_seconds',15)]:
        if not finite(report.get(key),limit):errors.append(key)
    if worker.get('model_inference') is not live or worker.get('status')!='complete' or worker.get('error'):errors.append('worker completion/class')
    if worker.get('environment_actions')!=0 or worker.get('scorecards')!=0:errors.append('environment work forbidden')
    if worker.get('configuration')!=CONFIGURATION:errors.append('configuration binding')
    if not finite(worker.get('model_startup_seconds'),750.000001):errors.append('startup deadline')
    preflight=worker.get('preflight') or {}
    if not isinstance(preflight.get('processor'),dict) or 'processor_files' not in preflight.get('mount_inventory',{}):errors.append('mount/processor evidence')
    if live:
        for key in ('gpu_cleanup_verified','independent_gpu_cleanup_verified'):
            if report.get(key) is not True:errors.append(key)
        if report.get('resource_evidence_class')!='live_resource_monitor':errors.append('actual monitor required')
        canary=worker.get('canary_audit') or {}
        if (not valid_canary(canary) or canary.get('finish_reason')!='stop'
            or canary.get('request_sha256')!='06853cc44e570cebee4b4623655b73c43072ee040d025e87e47696b3e15fac38'):
            errors.append('canary audit')
        try:
            validate_canary(canary['response_content'])
            if hashlib.sha256(canary['response_content'].encode()).hexdigest()!=canary['response_sha256']:raise ValueError('canary hash')
        except (KeyError,ValueError,TypeError):errors.append('canary body')
        if worker.get('model_artifact',{}).get('tree_sha256')!='052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627':errors.append('model binding')
        inventory=preflight.get('mount_inventory',{})
        if inventory.get('file_count')!=81 or len(inventory.get('files',[]))!=81:errors.append('mount inventory completeness')
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
    cases=load_cases();actual=worker.get('cases',[])
    if worker.get('requests_started')!=len(cases) or len(actual)!=len(cases):errors.append('probe inventory')
    for index,(planned,row) in enumerate(zip(cases,actual)):
        try:
            begin=row['started_seconds'];end=row['returned_seconds']
            if not (finite(begin,seconds) and finite(end,seconds)
                and worker['request_window_started_seconds']<=begin<=end<=worker['ended_seconds']
                and (index==0 or actual[index-1]['returned_seconds']<=begin)):raise ValueError('sequential timeline')
            if row['index']!=index:raise ValueError('index')
            check_row(planned,row,preflight)
        except (KeyError,TypeError,ValueError) as exc:errors.append(f'probe {index} invalid: {str(exc)[:96]}')
    try:
        start=worker['request_window_started_seconds'];end=worker['ended_seconds'];cutoff=worker['request_window_cutoff_seconds']
        if not valid_request_window(start,end,cutoff,seconds,live):raise ValueError('request deadline')
    except (KeyError,TypeError,ValueError):errors.append('request window')
    comparison=classify(worker,cases,lifecycle_ok=not errors)
    return {'passed':not errors,'errors':errors,'scope':'multimodal_preflight_live' if live else 'scripted_cpu_only',
        'comparison':comparison,'comparison_is_scripted':not live,
        'model_inference':live,'capacity_candidate':None,'C_nominal':None,'C_admit':None,
        'development_model_lifecycle_passed':not errors,'phase4_complete':False}

def evaluate_local_smoke(report,rows=None,*,seconds=LOCAL_CPU_SMOKE_SECONDS):
    return evaluate(report,live=False,seconds=seconds)
