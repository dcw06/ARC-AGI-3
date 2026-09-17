"""Record the user's requested repaired single pilot; reserve without uploading."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):
    with path.open('x',encoding='utf-8') as stream: json.dump(value,stream,indent=2)

import sys
if sys.argv[1:] != ['--authorize-and-launch']:
    raise PermissionError('explicit --authorize-and-launch required')
now=datetime.now(timezone.utc)
review=ROOT/'notebooks/phase4-lifecycle-v10-review-r1/review-source-lock.json'
lock=json.loads(review.read_text())
for name,expected in lock['bindings'].items():
    assert sha(ROOT/name)==expected,name
for name,expected in lock['artifacts'].items():
    assert sha(review.parent/name)==expected,name
old=json.loads((ROOT/'notebooks/phase4-lifecycle-v7-review-r1/review-source-lock.json').read_text())
for name,expected in old['bindings'].items():
    assert sha(ROOT/name)==expected,name
approval='reports/phase4_v10_source_approval.json'
compute='reports/phase4_v10_compute_authorization.json'
put(ROOT/approval,{
    'status':'approved','approved_at':now.isoformat(),
    'user_response':'And after the fix you can launch a new gpu run yourself',
    'approval_basis':'User explicitly authorized implementing the documented repair and then launching one GPU run; agent reviewed and tested this snapshot within that scope.',
    'scope':'v10 bounded asynchronous lossless telemetry repair; historical snapshots preserved',
    'review_lock':review.relative_to(ROOT).as_posix(),
    'review_lock_sha256':sha(review),'artifacts':lock['artifacts'],
    'validation':'28 Linux tests passed; full CPU-only 110-client pilot passed with 7722 requests and request/action invariance',
    'gpu_seconds_authorized':0,'gpu_launch_authorized':False})
put(ROOT/compute,{'approved_at':now.isoformat(),'user_response':'And after the fix you can launch a new gpu run yourself',
    'scope':'One repaired private offline RTX PRO 6000 v10 development pilot',
    'authorized_seconds':28800,'internal_seconds':27540,'maximum_attempts':1,
    'automatic_retries':0,'holdout_runs':0,'scored_submissions':0,
    'source_approval_reference':approval})
folder=ROOT/'config/phase4_v10_pilot_execution';folder.mkdir(exist_ok=False)
attempt='p4-v10-pilot-'+now.strftime('%Y%m%dT%H%M%SZ')
execution={'attempt_id':attempt,'review_lock':review.relative_to(ROOT).as_posix(),
    'review_sha256':sha(review),'source_approval_reference':approval,
    'status':'user_authorized_single_pilot','compute_approval_reference':compute}
put(folder/'execution_lock.json',execution)
reserve={'kind':'reserve','attempt_id':attempt,'seconds':28800,
    'recorded_at':now.isoformat(),'execution_lock_sha256':sha(folder/'execution_lock.json'),
    'released_seconds':0}
ledger={'attempt_id':attempt,'authorized_seconds':28800,'maximum_attempts':1,
    'automatic_retries':0,'approval_reference':compute,'events':[reserve]}
put(ROOT/'config/phase4_v10_pilot_compute_ledger.json',ledger)
ledger['events'].append({'kind':'launch_request_started','attempt_id':attempt,
    'prepared_at':now.isoformat(),'scope':'embedded single-attempt gate; external claim required before upload'})
put(folder/'compute_ledger.json',ledger)
print(attempt)
