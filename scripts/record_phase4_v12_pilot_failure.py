"""Archive v12 evidence and record the stale canary acceptance limit."""
import hashlib,json,zipfile
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
run=ROOT/'reports/runs/phase4-v12-pilot-20260918'
out=run/'download/phase4-development-v12'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
w=read(out/'worker/state.json'); final=read(out/'evaluation/notebook-result.json')
evaluation=read(out/'evaluation/result.json'); outer=read(out/'control/outer.json')
cost=read(out/'control/notebook-cost.json')
before=read(ROOT/'reports/phase4_v12_pilot_prelaunch.json')
after=json.loads((run/'provider-observations.jsonl').read_text().splitlines()[-1])
launch=read(ROOT/'reports/phase4_v12_pilot_launch.json')
metrics={key:sum(c['result'][key] for c in w['clients']) for key in
 ('policy_failures','parser_repairs','inference_queue_failures','inference_transport_failures','acknowledged_actions')}
assert w['status']=='complete' and len(w['clients'])==110
assert w['canary_audit']['status']=='passed' and w['canary_audit']['server_completion_tokens']==29
assert 'single audited canary evidence missing' in evaluation['errors']
assert after['status'].endswith('.ERROR')
archive=ROOT/'evidence/phase4-v12-pilot-failed-v1.zip'
files=sorted(p for p in run.rglob('*') if p.is_file())
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(run).as_posix())
record={'recorded_at':datetime.now(timezone.utc).isoformat(),'attempt_id':launch['attempt_id'],
 'provider_status':'ERROR','passed':False,'phase4_complete':False,
 'diagnosis':'Inherited v4 evaluator requires canary completion <=8 tokens; approved v12 canary allows 128 and used 29.',
 'target_constrained_canary_passed':True,'canary_audit':w['canary_audit'],
 'clients':len(w['clients']),'requests':len(w['requests']),'metrics':metrics,
 'client_errors':sum(c['error'] is not None for c in w['clients']),
 'request_errors':sum(r['error'] is not None for r in w['requests']),
 'action6_acknowledged':sum(e['kind']=='action' and e['status']=='acknowledged' and e['fields'].get('action_id')==6 for c in w['clients'] for e in c['client_journal']),
 'internal_elapsed_seconds':final['elapsed_seconds'],'original_evaluation':evaluation,
 'source_removed':final['source_removed'],'dependency_trees_removed':cost['dependency_trees_removed'],
 'cleanup':{k:outer[k] for k in ('cleanup_verified','gpu_cleanup_verified','independent_gpu_cleanup_verified','scratch_removed','gpu_samples')},
 'account_gpu_usage_delta_seconds':round(after['gpu_quota_seconds']['time_used']-before['gpu_quota_seconds']['time_used'],6),
 'account_delta_scope':'Aggregate account change, not exact per-attempt billing',
 'exact_provider_billed_seconds':None,'charged_or_reserved_seconds':28800,'released_seconds':0,
 'attempt_consumed':True,'retry_authorized':False,
 'evidence_limits':'Canary body not retained; passed audit comes from frozen strict validation. No retrospective change to original verdict. No claim of game competence or production certification.',
 'evidence_archive':archive.relative_to(ROOT).as_posix(),'evidence_archive_sha256':sha(archive),
 'evidence':{p.relative_to(run).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}}
report=ROOT/'reports/phase4_v12_pilot_evaluation.json'
with report.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
ledger_path=ROOT/'config/phase4_v12_pilot_compute_ledger.json'
ledger=read(ledger_path)
assert not any(e['kind'].startswith('attempt_completed') for e in ledger['events'])
ledger['events'].append({'kind':'attempt_completed_accounting_pending','attempt_id':launch['attempt_id'],
 'recorded_at':record['recorded_at'],'provider_status':'ERROR','passed':False,
 'result_reference':report.relative_to(ROOT).as_posix(),'result_sha256':sha(report),
 'charged_or_reserved_seconds':28800,'released_seconds':0,'exact_provider_billed_seconds':None,
 'account_gpu_usage_delta_seconds':record['account_gpu_usage_delta_seconds'],'attempt_consumed':True,'retry_authorized':False})
tmp=ledger_path.with_suffix('.writing')
with tmp.open('x',encoding='utf-8') as f:json.dump(ledger,f,indent=2)
tmp.replace(ledger_path)
print(json.dumps({k:v for k,v in record.items() if k!='evidence'},indent=2))
