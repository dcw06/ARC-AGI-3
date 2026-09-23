"""Independent preflight acceptance and outcome classification; no perception or capacity claim."""
import hashlib,math
from certification.phase4_v13.evaluate import monitor_fields  # noqa: F401  (re-exported for pilot.py)
from certification.phase4_v13.measurement import validate_telemetry
from certification.phase4_v13.canary import valid_canary
from certification.phase4_perception_v1.cases import load_cases,image_part
from certification.phase4_perception_v1.action_contract import validate_canary
from certification.phase4_perception_v1.worker import CLASSIFIED,CONFIGURATION
LOCAL_CPU_SMOKE_SECONDS=120
VERDICTS=('image_input_verified','dependency_missing','image_rejected_by_server','token_accounting_mismatch',
    'image_not_consumed','text_control_failed','lifecycle_failure','processor_execution_failure')

def valid_request_window(start,end,cutoff,seconds,live):
    if not all(finite(v,seconds+1) for v in (start,end,cutoff)):return False
    allowance=4*math.ulp(float(seconds+600))
    return start<=end<cutoff<=seconds-(300 if live else 0) and cutoff<=start+600+allowance

def finite(value,limit):return type(value) in (int,float) and math.isfinite(value) and 0<=value<limit

def check_row(planned,row,preflight):
    from certification.phase4_perception_v1.cases import score
    if row['probe_id']!=planned['probe_id'] or row['request']!=planned['request'] or row['request_sha256']!=planned['request_sha256']:
        raise ValueError('request binding')
    if row['status']!='complete' or row['error'] is not None or row['response_truncated']:raise ValueError('incomplete response')
    raw=row['response_content'].encode()
    if len(raw)>32768 or len(raw)!=row['response_bytes'] or hashlib.sha256(raw).hexdigest()!=row['response_sha256']:raise ValueError('response hash')
    a=row['audit'];e=a['expectation'];p=a['server_prompt_tokens'];c=a['server_completion_tokens']
    frozen=planned['frozen_local_expectation']
    if (a.get('transport_attempted') is not True or a['request_sha256']!=planned['request_sha256']
        or type(p) is not int or not 0<p<=16000 or a['tokenizer_prompt_tokens']!=p or e['expected_prompt_tokens']!=p
        or type(c) is not int or not 1<=c<=planned['request']['max_tokens'] or 'finish_reason' not in a
        or not finite(a['service_seconds'],180) or e!=frozen):raise ValueError('token/processor audit')
    if image_part(planned['request']) is not None and (e['processor_full_prompt_tokens']!=e['manual_prompt_tokens']
        or e['image_tokens_processor']!=e['image_grid_thw'][0]*e['image_grid_thw'][1]*e['image_grid_thw'][2]//4):
        raise ValueError('image count parity')
    if row['answer']!=score(planned,row['response_content'],a['finish_reason']):raise ValueError('independent score')

def classify(worker,cases,lifecycle_ok):
    planned={c['probe_id']:c for c in cases}
    summaries=[]
    for r in worker.get('cases',[]):
        c=planned.get(r.get('probe_id'),{})
        summaries.append({'id':r.get('probe_id'),'kind':c.get('kind'),'source_group':c.get('source_group'),
            'representation':c.get('representation'),'status':r.get('status'),'answer':r.get('answer'),
            'failure_kind':r.get('failure_kind'),'audit':r.get('audit')})
    return {'rows':summaries,'verdict':'completed' if lifecycle_ok else 'technical_failure',
        'interpretation':'Five descriptive board pairs, correlated within source; no automatic promotion or solving claim.'}

def evaluate(report,rows=None,*,live=True,seconds=2280):
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
    if not finite(worker.get('model_startup_seconds'),900.000001):errors.append('startup deadline')
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
    return {'passed':not errors,'errors':errors,'scope':'paired_perception_live' if live else 'scripted_cpu_only',
        'comparison':comparison,'comparison_is_scripted':not live,
        'model_inference':live,'capacity_candidate':None,'C_nominal':None,'C_admit':None,
        'development_model_lifecycle_passed':not errors,'phase4_complete':False}

def evaluate_local_smoke(report,rows=None,*,seconds=LOCAL_CPU_SMOKE_SECONDS):
    return evaluate(report,live=False,seconds=seconds)
