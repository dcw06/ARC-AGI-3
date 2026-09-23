"""Separate exact source/compute approvals and a bound single-attempt reservation."""
import hashlib,json,os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCOPE='phase4-multimodal-preflight-v3'
REVIEW='notebooks/phase4-multimodal-preflight-v3-review-r1/review-source-lock.json'
SOURCE='reports/phase4_multimodal_preflight_v3_source_approval.json'
COMPUTE='reports/phase4_multimodal_preflight_v3_compute_authorization.json'
LIMITS={'authorized_seconds':1800,'internal_seconds':1680,'maximum_attempts':1,
    'maximum_probe_calls':4,'maximum_total_completions':5,'maximum_environment_actions':0,
    'maximum_scorecards':0,'automatic_retries':0,'holdout_runs':0,'scored_submissions':0}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def resolve(root,name):
    if not isinstance(name,str) or not name or '\\' in name:raise ValueError('unsafe reference')
    path=(Path(root)/name).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise ValueError('reference escapes root')
    return path
def read(root,name):return json.loads(resolve(root,name).read_bytes())

def source_snapshot(root):
    review=read(root,REVIEW)
    required={'certification/phase4_multimodal_preflight_v3/'+name for name in
        ('authority.py','worker.py','probes.py','cases.py','cases.json','images.py','service.py','evaluate.py','entry.py','protocol.json')}
    required.update(p.relative_to(root).as_posix() for p in (Path(root)/'certification/phase4_multimodal_preflight_v3').glob('*.py'))
    required.add('scripts/phase4_multimodal_preflight_v3_launch.py')
    if not required<=set(review['bindings']):raise ValueError('incomplete reviewed sources')
    for name,digest in review['bindings'].items():
        if sha(resolve(root,name))!=digest:raise ValueError('source drift: '+name)
    return review

def approved(root):
    source_snapshot(root)
    source,compute=read(root,SOURCE),read(root,COMPUTE)
    lock_hash=sha(resolve(root,REVIEW))
    for value,kind in ((source,'source'),(compute,'compute')):
        if (value.get('status')!='approved' or value.get('approval_kind')!=kind or value.get('scope')!=SCOPE
            or value.get('review_lock_sha256')!=lock_hash or not isinstance(value.get('user_response'),str)
            or not value['user_response'].strip() or not value.get('approved_at')):raise ValueError(kind+' approval')
    if compute.get('source_approval_sha256')!=sha(resolve(root,SOURCE)):raise ValueError('compute/source binding')
    if compute.get('source_approval_reference')!=SOURCE:raise ValueError('compute/source reference')
    for name,expected in LIMITS.items():
        if type(compute.get(name)) is not int or compute[name]!=expected:raise ValueError('compute limit: '+name)
    return source,compute

def validate_reservation(root,execution,reservation):
    approved(root)
    if (execution.get('scope')!=SCOPE or execution.get('review_lock')!=REVIEW
        or execution.get('review_sha256')!=sha(resolve(root,REVIEW))
        or execution.get('source_approval_sha256')!=sha(resolve(root,SOURCE))
        or execution.get('compute_approval_sha256')!=sha(resolve(root,COMPUTE))):raise ValueError('execution approval binding')
    attempt=execution.get('attempt_id')
    if not isinstance(attempt,str) or not re.fullmatch(r'mm3-[a-zA-Z0-9-]{8,80}',attempt):raise ValueError('attempt id')
    if (reservation.get('status')!='reserved' or reservation.get('attempt_id')!=attempt
        or type(reservation.get('seconds')) is not int or reservation['seconds']!=1800
        or reservation.get('source_approval_sha256')!=execution['source_approval_sha256']
        or reservation.get('compute_approval_sha256')!=execution['compute_approval_sha256']
        or reservation.get('execution_sha256')!=hashlib.sha256(json.dumps(execution,sort_keys=True,indent=2).encode()+b'\n').hexdigest()
        or reservation.get('events')!=['reserve']):raise ValueError('unconsumed reservation binding')
    return execution

def require(root=None):
    root=ROOT if root is None else Path(root)
    try:
        folder='certification/phase4_multimodal_preflight_v3/'
        return validate_reservation(root,read(root,folder+'execution_lock.json'),read(root,folder+'reservation.json'))
    except (OSError,KeyError,ValueError,TypeError) as exc:
        raise PermissionError('multimodal preflight v3 requires matching source/compute approvals and an unconsumed reservation') from exc

def consume_runtime(root,working):
    execution=require(root)
    marker=Path(working)/('.'+execution['attempt_id']+'.runtime-consumed.json')
    # Persistent within the provider working directory; separate from upload claim.
    with marker.open('x',encoding='utf-8') as stream:
        json.dump({'attempt_id':execution['attempt_id'],'status':'consumed'},stream)
        stream.flush();os.fsync(stream.fileno())
    return marker
