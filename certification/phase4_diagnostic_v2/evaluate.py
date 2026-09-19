"""Independent diagnostic acceptance; no capacity or game-success claim."""
import hashlib,math
from certification.phase4_v13.evaluate import monitor_fields
from certification.phase4_v13.measurement import validate_telemetry
from certification.phase4_v13.canary import valid_canary
from certification.phase4_diagnostic_v2.cases import load_cases
from certification.phase4_diagnostic_v2.action_contract import validate_action,request_legal_actions,validate_canary
LOCAL_CPU_SMOKE_SECONDS=120

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
    if worker.get('environment_actions')!=0 or worker.get('scorecards')!=0:errors.append('environment work forbidden')
    if worker.get('configuration')!='E1S-R-derived arc_action_v12 three-arm diagnostic':errors.append('configuration binding')
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
    cases=load_cases();actual=worker.get('cases',[])
    if worker.get('requests_started')!=45 or len(actual)!=45:errors.append('45-call inventory')
    for index,(planned,row) in enumerate(zip(cases,actual)):
        try:
            begin=row['started_seconds'];end=row['returned_seconds']
            if not (finite(begin,seconds) and finite(end,seconds)
                and worker['request_window_started_seconds']<=begin<=end<=worker['ended_seconds']
                and (index==0 or actual[index-1]['returned_seconds']<=begin)):
                raise ValueError('sequential timeline')
            if row['index']!=index or any(row[k]!=planned[k] for k in ('game_id','arm','request_sha256')):raise ValueError('request binding')
            if row['status']!='complete' or row['error'] is not None or row['response_truncated']:raise ValueError('incomplete response')
            raw=row['response_content'].encode()
            if len(raw)>8192 or len(raw)!=row['response_bytes'] or hashlib.sha256(raw).hexdigest()!=row['response_sha256']:raise ValueError('response hash')
            action=validate_action(row['response_content'],request_legal_actions(planned['request']['messages']))
            if action!=row['action']:raise ValueError('action binding')
            a=row['audit'];p=a['server_prompt_tokens'];c=a['server_completion_tokens']
            if (a['request_sha256']!=planned['request_sha256'] or type(p) is not int or not 0<p<=65408
                or type(a['tokenizer_prompt_tokens']) is not int or a['tokenizer_prompt_tokens']!=p
                or type(c) is not int or not 1<=c<=128 or not finite(a['service_seconds'],180)):
                raise ValueError('token/service audit')
        except (KeyError,TypeError,ValueError):errors.append(f'case {index} invalid')
    try:
        start=worker['request_window_started_seconds'];end=worker['ended_seconds'];cutoff=worker['request_window_cutoff_seconds']
        if not (start<=end<cutoff<=min(start+1200,seconds-(300 if live else 0))):raise ValueError('request deadline')
    except (KeyError,TypeError,ValueError):errors.append('request window')
    comparison=None
    if not errors:
        groups={}
        for planned,row in zip(cases,actual):
            group=groups.setdefault(row['game_id'],{'click_legal':6 in request_legal_actions(planned['request']['messages'])})
            group[row['arm']]=row['action']['action']
        comparison={'per_game':groups,'arms':{}}
        for arm in ('baseline','relocated_example','no_concrete_examples'):
            clicks=[g[arm]['action_data'] for g in groups.values() if g[arm]['action_id']==6]
            comparison['arms'][arm]={'cases':15,'click_legal_cases':sum(g['click_legal'] for g in groups.values()),
                'clicks':len(clicks),'at_original_example':clicks.count({'x':12,'y':34}),
                'at_relocated_example':clicks.count({'x':47,'y':9}),
                'same_action_as_baseline':sum(g[arm]==g['baseline'] for g in groups.values()),
                'action_type_switches_from_baseline':sum(g[arm]['action_id']!=g['baseline']['action_id'] for g in groups.values())}
    return {'passed':not errors,'errors':errors,'scope':'three_arm_diagnostic_live' if live else 'scripted_cpu_only',
        'comparison':comparison,'comparison_is_scripted':not live,
        'model_inference':live,'capacity_candidate':None,'C_nominal':None,'C_admit':None,
        'development_model_lifecycle_passed':not errors,'phase4_complete':False}

def evaluate_local_smoke(report,rows=None,*,seconds=LOCAL_CPU_SMOKE_SECONDS):
    return evaluate(report,live=False,seconds=seconds)
