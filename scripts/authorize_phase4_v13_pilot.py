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
review=ROOT/'notebooks/phase4-lifecycle-v13-review-r1/review-source-lock.json'
lock=json.loads(review.read_text())
for name,expected in lock['bindings'].items():
    assert sha(ROOT/name)==expected,name
for name,expected in lock['artifacts'].items():
    assert sha(review.parent/name)==expected,name
old=json.loads((ROOT/'notebooks/phase4-lifecycle-v7-review-r1/review-source-lock.json').read_text())
for name,expected in old['bindings'].items():
    assert sha(ROOT/name)==expected,name
approval='reports/phase4_v13_source_approval.json'
compute='reports/phase4_v13_compute_authorization.json'
approved=json.loads((ROOT/approval).read_text())
assert approved['status']=='approved' and approved['review_lock_sha256']==sha(review)
put(ROOT/compute,{'approved_at':now.isoformat(),'user_response':'Explicit invocation of start_phase4_v13_pilot.py --authorize-and-launch',
    'scope':'One private offline RTX PRO 6000 v13 R1 pilot using reviewed lossless compact packaging',
    'authorized_seconds':28800,'internal_seconds':27540,'maximum_attempts':1,
    'automatic_retries':0,'holdout_runs':0,'scored_submissions':0,
    'source_approval_reference':approval})
folder=ROOT/'config/phase4_v13_pilot_execution';folder.mkdir(exist_ok=False)
attempt='p4-v13-pilot-'+now.strftime('%Y%m%dT%H%M%SZ')
execution={'attempt_id':attempt,'review_lock':review.relative_to(ROOT).as_posix(),
    'review_sha256':sha(review),'source_approval_reference':approval,
    'status':'user_authorized_single_pilot','compute_approval_reference':compute}
put(folder/'execution_lock.json',execution)
reserve={'kind':'reserve','attempt_id':attempt,'seconds':28800,
    'recorded_at':now.isoformat(),'execution_lock_sha256':sha(folder/'execution_lock.json'),
    'released_seconds':0}
ledger={'attempt_id':attempt,'authorized_seconds':28800,'maximum_attempts':1,
    'automatic_retries':0,'approval_reference':compute,'events':[reserve]}
put(ROOT/'config/phase4_v13_pilot_compute_ledger.json',ledger)
ledger['events'].append({'kind':'launch_request_started','attempt_id':attempt,
    'prepared_at':now.isoformat(),'scope':'embedded single-attempt gate; external claim required before upload'})
put(folder/'compute_ledger.json',ledger)
print(attempt)
