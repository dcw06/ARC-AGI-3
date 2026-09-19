"""Submit the approved diagnostic v4 pilot once; record ownership before any upload request."""
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
from phase4_install_kaggle import ROOT,environment

FOLDER=ROOT/'notebooks/phase4-diagnostic-v4-pilot-launch-ready-r1'
LEDGER=ROOT/'config/phase4_diagnostic_v4_pilot_compute_ledger.json'
CLAIM=ROOT/'config/phase4_diagnostic_v4_pilot_launch_claim.json'
EXECUTION=ROOT/'config/phase4_diagnostic_v4_pilot_execution/execution_lock.json'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def write(path,value):
    temp=path.with_suffix('.writing')
    with temp.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    temp.replace(path)

def validate():
    if (FOLDER/'profile.ipynb').stat().st_size>=900000:
        raise PermissionError('notebook exceeds upload size guard')
    ledger=json.loads(LEDGER.read_text())
    if CLAIM.exists() or len(ledger['events'])!=1: raise PermissionError('pilot already claimed; no retry')
    if ledger['authorized_seconds']!=3600 or ledger['maximum_attempts']!=1: raise PermissionError('budget')
    execution=json.loads(EXECUTION.read_text())
    reserve=ledger['events'][0]
    if (reserve['kind']!='reserve' or reserve['seconds']!=3600
        or reserve['execution_lock_sha256']!=sha(EXECUTION)
        or reserve['attempt_id']!=execution['attempt_id']): raise PermissionError('reservation binding')
    package=json.loads((FOLDER/'launch-package-lock.json').read_text())
    for name,expected in package['artifacts'].items():
        if sha(FOLDER/name)!=expected: raise PermissionError('launch artifact drift')
    if package['packager_sha256']!=sha(ROOT/'scripts/prepare_phase4_diagnostic_v4_launch.py'): raise PermissionError('packager drift')
    review_path=ROOT/execution['review_lock']
    if sha(review_path)!=execution['review_sha256']: raise PermissionError('review drift')
    approval=json.loads((ROOT/execution['source_approval_reference']).read_text())
    requirements=ROOT/approval['requirements_lock']
    if sha(requirements)!=approval['requirements_lock_sha256']:raise PermissionError('requirements lock drift')
    document=json.loads(requirements.read_text())
    if sha(ROOT/document['requirements_document'])!=document['requirements_document_sha256']:
        raise PermissionError('requirements document drift')
    compute=json.loads((ROOT/execution['compute_approval_reference']).read_text())
    if (compute.get('scope')!='phase4-action-diagnostic-v4' or compute.get('authorized_seconds')!=3600
        or compute.get('internal_seconds')!=3300 or compute.get('maximum_total_completions')!=46
        or compute.get('maximum_attempts')!=1 or compute.get('automatic_retries')!=0):
        raise PermissionError('diagnostic compute scope drift')
    for name,expected in json.loads(review_path.read_text())['bindings'].items():
        if sha(ROOT/name)!=expected: raise PermissionError('source drift: '+name)
    metadata=json.loads((FOLDER/'kernel-metadata.json').read_text())
    if (metadata['id']!='daichongwei06/arc3-phase4-action-diagnostic-v4-r1'
        or not metadata['is_private'] or metadata['enable_internet'] or not metadata['enable_gpu']
        or metadata['machine_shape']!='NvidiaRtxPro6000'
        or metadata['model_sources']!=['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']):
        raise PermissionError('pilot metadata scope')
    return ledger,execution

def main():
    import sys
    ledger,execution=validate()
    if sys.argv[1:]==['--verify-only']:
        print('Approved diagnostic v4 source, package, reservation and unconsumed claim verified.');return
    if sys.argv[1:]: raise ValueError('unexpected arguments')
    env=environment()
    for key in ('KAGGLE_API_TOKEN','KAGGLE_USERNAME','KAGGLE_KEY'):
        if env.get(key): os.environ[key]=env[key]
    import requests
    original=requests.Session.send
    def send(self,request,**kwargs):
        kwargs.update(timeout=(60,120),allow_redirects=False)
        return original(self,request,**kwargs)
    requests.Session.send=send
    from kaggle import api
    quota=api.quota_view()
    seconds={key:getattr(quota.gpu_quota,key).total_seconds()
             for key in ('time_used','time_reserved','total_time_allowed')}
    if seconds['total_time_allowed']-seconds['time_used']-seconds['time_reserved']<3600:
        raise RuntimeError('insufficient quota; no upload sent')
    write(ROOT/'reports/phase4_diagnostic_v4_pilot_prelaunch.json',{'recorded_at':now(),'gpu_quota_seconds':seconds})
    ledger,execution=validate()
    event={'kind':'launch_request_started','attempt_id':execution['attempt_id'],'recorded_at':now(),
           'attempt_consumed':True,'package_sha256':sha(FOLDER/'launch-package-lock.json'),
           'charged_or_reserved_seconds':3600,'automatic_retries':0}
    with CLAIM.open('x',encoding='utf-8') as stream:
        json.dump(event,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    ledger['events'].append(event);write(LEDGER,ledger)
    receipt={'attempt_id':execution['attempt_id'],'recorded_at':now(),'attempt_consumed':True,
             'provider_timeout_requested_seconds':3600,'exact_provider_billed_seconds':None,
             'automatic_retry_authorized':False}
    try:
        response=api.kernels_push(str(FOLDER),timeout='3600',acc='NvidiaRtxPro6000')
        receipt.update(status='provider_response_received',error=response.error,url=response.url,
                       provider_version=response.version_number)
        for field in ('invalid_dataset_sources','invalid_competition_sources','invalid_kernel_sources'):
            receipt[field]=getattr(response,field,None)
    except Exception as exc:
        message=str(exc)
        response=getattr(exc,'response',None)
        if response is not None:
            receipt['http_status']=response.status_code
            detail=response.text
            for key in ('KAGGLE_API_TOKEN','KAGGLE_KEY'):
                if env.get(key): detail=detail.replace(env[key],'[REDACTED]')
            receipt['provider_error_detail']=detail[:4096]
        for key in ('KAGGLE_API_TOKEN','KAGGLE_KEY'):
            if env.get(key): message=message.replace(env[key],'[REDACTED]')
        receipt.update(status='launch_outcome_unknown_no_retry',error=type(exc).__name__+': '+message[:1000])
    receipt['response_received_at']=now()
    write(ROOT/'reports/phase4_diagnostic_v4_pilot_launch.json',receipt)
    ledger['events'].append({'kind':'launch_receipt','attempt_id':execution['attempt_id'],
        'reference':'reports/phase4_diagnostic_v4_pilot_launch.json','status':receipt['status'],
        'charged_or_reserved_seconds':3600,'released_seconds':0})
    write(LEDGER,ledger)
    print(json.dumps(receipt))
    if receipt.get('error'): raise SystemExit(1)

if __name__=='__main__': main()
