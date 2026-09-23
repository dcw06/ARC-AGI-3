"""Explicit approval recording, reservation, deterministic packaging and one-shot upload."""
import argparse,base64,hashlib,json,math,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_multimodal_preflight_v2.authority import (SCOPE,REVIEW,SOURCE,COMPUTE,LIMITS,
    approved,source_snapshot,validate_reservation,read,sha,resolve)
EXECUTION='config/phase4_multimodal_preflight_v2_execution/execution_lock.json'
RESERVATION='config/phase4_multimodal_preflight_v2_reservation.json'
CLAIM='config/phase4_multimodal_preflight_v2_launch_claim.json'
PACKAGE='notebooks/phase4-multimodal-preflight-v2-launch-r1'
RECEIPT='reports/phase4_multimodal_preflight_v2_pilot_launch.json'
now=lambda:datetime.now(timezone.utc).isoformat()

def data(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def put(root,name,value):
    path=resolve(root,name);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(data(value));stream.flush();os.fsync(stream.fileno())
def replace(root,name,value):
    path=resolve(root,name);temp=path.with_name(path.name+'.writing')
    with temp.open('xb') as stream:stream.write(data(value));stream.flush();os.fsync(stream.fileno())
    temp.replace(path)

def record_approval(root,kind,text,review_sha):
    # Caller must supply the actual explicit user decision; this function never
    # infers approval from a request to prepare/review/launch infrastructure.
    source_snapshot(root)
    if not isinstance(text,str) or not text.strip() or review_sha!=sha(resolve(root,REVIEW)):
        raise PermissionError('explicit response and exact reviewed hash required')
    if kind not in ('source','compute'):raise ValueError('approval kind')
    value={'approval_kind':kind,'status':'approved','scope':SCOPE,'user_response':text,
        'approved_at':now(),'review_lock_sha256':review_sha}
    if kind=='compute':
        source=read(root,SOURCE)
        if source.get('status')!='approved' or source.get('review_lock_sha256')!=review_sha:
            raise PermissionError('source approval first')
        value.update(LIMITS,source_approval_reference=SOURCE,source_approval_sha256=sha(resolve(root,SOURCE)))
    put(root,SOURCE if kind=='source' else COMPUTE,value)

def reserve(root):
    approved(root)
    if any(resolve(root,p).exists() for p in (RESERVATION,EXECUTION,CLAIM,RECEIPT,PACKAGE)):
        raise PermissionError('attempt already reserved/prepared/consumed; no reuse')
    execution={'scope':SCOPE,'attempt_id':'mm2-'+uuid.uuid4().hex,'review_lock':REVIEW,
        'review_sha256':sha(resolve(root,REVIEW)),'source_approval_sha256':sha(resolve(root,SOURCE)),
        'compute_approval_sha256':sha(resolve(root,COMPUTE))}
    # Exclusive directory is the reservation concurrency guard. A partial failure
    # stays consumed/blocked for manual reconciliation, never silently retried.
    folder=resolve(root,EXECUTION).parent;folder.mkdir(parents=True,exist_ok=False)
    put(root,EXECUTION,execution)
    reservation={'status':'reserved','attempt_id':execution['attempt_id'],'seconds':1800,
        'reserved_at':now(),'execution_sha256':sha(resolve(root,EXECUTION)),
        'source_approval_sha256':execution['source_approval_sha256'],
        'compute_approval_sha256':execution['compute_approval_sha256'],'events':['reserve']}
    put(root,RESERVATION,reservation)
    return execution

def unconsumed(root):
    if resolve(root,CLAIM).exists() or resolve(root,RECEIPT).exists():raise PermissionError('launch already consumed; no retry')
    execution,reservation=read(root,EXECUTION),read(root,RESERVATION)
    validate_reservation(root,execution,reservation)
    return execution,reservation

def materialize(root,execution,reservation):
    validate_reservation(root,execution,reservation)
    review=source_snapshot(root);folder=resolve(root,REVIEW).parent
    if set(review['artifacts'])!={'profile.ipynb','kernel-metadata.json'}:raise ValueError('review artifacts')
    for name,digest in review['artifacts'].items():
        if sha(folder/name)!=digest:raise ValueError('review artifact drift')
    sidecars={
        'certification/phase4_multimodal_preflight_v2/execution_lock.json':data(execution),
        'certification/phase4_multimodal_preflight_v2/reservation.json':data(reservation),
        REVIEW:resolve(root,REVIEW).read_bytes(),SOURCE:resolve(root,SOURCE).read_bytes(),COMPUTE:resolve(root,COMPUTE).read_bytes()}
    encoded={name:base64.b64encode(raw).decode() for name,raw in sidecars.items()}
    hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in sidecars.items()}
    injection=f'''    authority_payload={encoded!r}
    authority_hashes={hashes!r}
    for name,value in authority_payload.items():
        raw=base64.b64decode(value)
        if hashlib.sha256(raw).hexdigest()!=authority_hashes[name]:raise ValueError('authority sidecar drift')
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
'''
    notebook=json.loads((folder/'profile.ipynb').read_bytes())
    code=notebook['cells'][1]['source'];marker='    sys.path.insert(0,str(source))\n'
    if code.count(marker)!=1:raise ValueError('review wrapper marker')
    notebook['cells'][1]['source']=code.replace(marker,injection+marker)
    notebook['cells'][0]['source']='# Multimodal Preflight V2: one separately authorized development attempt\nStartup observability repair. Mount inventory, one text canary and four image-input probes; zero actions or scorecards. No automatic retry or production certification.'
    metadata=json.loads((folder/'kernel-metadata.json').read_bytes())
    if metadata.get('enable_gpu') is not False or metadata.get('enable_internet') is not False or metadata.get('is_private') is not True:
        raise ValueError('review metadata')
    metadata.update(id='daichongwei06/arc3-phase4-multimodal-preflight-v2-r1',title='ARC3 Phase4 Multimodal Preflight V2 R1',
        enable_gpu=True,machine_shape='NvidiaRtxPro6000')
    artifacts={'profile.ipynb':data(notebook),'kernel-metadata.json':data(metadata)}
    if len(artifacts['profile.ipynb'])>=900000:raise ValueError('notebook size ceiling')
    lock={'scope':SCOPE,'attempt_id':execution['attempt_id'],'review_lock_sha256':sha(resolve(root,REVIEW)),
        'sidecars':hashes,'artifacts':{n:hashlib.sha256(b).hexdigest() for n,b in artifacts.items()}}
    artifacts['launch-package-lock.json']=data(lock)
    return artifacts

def package(root):
    execution,reservation=unconsumed(root);artifacts=materialize(root,execution,reservation)
    folder=resolve(root,PACKAGE);folder.mkdir(parents=True,exist_ok=False)
    for name,raw in artifacts.items():
        with (folder/name).open('xb') as stream:stream.write(raw)
    return validate(root)

def validate(root):
    try:
        execution,reservation=unconsumed(root)
        artifacts=materialize(root,execution,reservation);folder=resolve(root,PACKAGE)
        if {p.name for p in folder.iterdir()}!=set(artifacts):raise ValueError('package inventory')
        for name,raw in artifacts.items():
            if (folder/name).is_symlink() or (folder/name).read_bytes()!=raw:raise ValueError('package bytes: '+name)
        return execution,reservation
    except (OSError,KeyError,ValueError,TypeError) as exc:raise PermissionError('launch validation failed: '+str(exc)) from exc

def launch(root,backend):
    execution,reservation=validate(root)
    quota=backend.quota() # Read only; no claim until validated quota is sufficient.
    for name in ('total_time_allowed','time_used','time_reserved'):
        value=quota.get(name)
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise PermissionError('invalid account quota')
    if quota['total_time_allowed']-quota['time_used']-quota['time_reserved']<1800:raise PermissionError('insufficient account quota')
    put(root,'reports/phase4_multimodal_preflight_v2_pilot_prelaunch.json',{'recorded_at':now(),'gpu_quota_seconds':quota})
    execution,reservation=validate(root)
    claim={'attempt_id':execution['attempt_id'],'status':'consumed_before_upload','recorded_at':now(),
        'package_sha256':sha(resolve(root,PACKAGE)/'launch-package-lock.json'),'seconds_charged_or_reserved':1800}
    put(root,CLAIM,claim) # Atomic exclusive creation wins any upload race.
    reservation.update(status='consumed',events=['reserve','launch_request_started'])
    replace(root,RESERVATION,reservation)
    receipt={'attempt_id':execution['attempt_id'],'recorded_at':now(),'attempt_consumed':True,
        'provider_timeout_requested_seconds':1800,'exact_provider_billed_seconds':None,'automatic_retry_authorized':False}
    try:
        response=backend.push(resolve(root,PACKAGE))
        receipt.update(status='provider_response_received',url=response.url,provider_version=response.version_number,error=response.error)
        for name in ('invalid_dataset_sources','invalid_competition_sources','invalid_kernel_sources'):
            receipt[name]=getattr(response,name,None)
    except Exception as exc:
        # Avoid credential-bearing provider exception text; unknown outcome consumes authority.
        receipt.update(status='launch_outcome_unknown_no_retry',error=type(exc).__name__)
    receipt['response_received_at']=now();put(root,RECEIPT,receipt)
    return receipt

class KaggleBackend:
    def __init__(self):
        from scripts.phase4_install_kaggle import environment
        env=environment()
        for key in ('KAGGLE_API_TOKEN','KAGGLE_USERNAME','KAGGLE_KEY'):
            if env.get(key):os.environ[key]=env[key]
        import requests
        original=requests.Session.send
        def send(session,request,**kwargs):
            kwargs.update(timeout=(60,120),allow_redirects=False)
            return original(session,request,**kwargs)
        requests.Session.send=send
        from kaggle import api
        self.api=api
    def quota(self):
        value=self.api.quota_view().gpu_quota
        return {n:getattr(value,n).total_seconds() for n in ('time_used','time_reserved','total_time_allowed')}
    def push(self,folder):return self.api.kernels_push(str(folder),timeout='1800',acc='NvidiaRtxPro6000')

def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['record-source','record-compute','reserve','package','verify','launch'])
    p.add_argument('--user-response');p.add_argument('--review-sha256');args=p.parse_args()
    if args.operation.startswith('record-'):
        record_approval(ROOT,args.operation.removeprefix('record-'),args.user_response,args.review_sha256)
    elif args.operation=='reserve':print(json.dumps(reserve(ROOT)))
    elif args.operation=='package':package(ROOT);print('Package verified; no upload sent')
    elif args.operation=='verify':validate(ROOT);print('Unconsumed package/approvals/reservation verified')
    else:
        validate(ROOT) # Reject locally before authentication or provider queries.
        receipt=launch(ROOT,KaggleBackend());print(json.dumps(receipt))
        if receipt.get('error'):raise SystemExit(1)

if __name__=='__main__':main()
