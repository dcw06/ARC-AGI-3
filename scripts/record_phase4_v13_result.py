"""Verify completed target evidence, replay acceptance, and reconcile aggregate usage."""
from datetime import datetime, timezone
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_v13.evaluate import evaluate,monitor_fields
from certification.phase4_v13.telemetry import read_telemetry
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=ROOT/'reports/runs/phase4-v13-pilot-20260918'
out=run/'download/phase4-development-v13'
launch=read(ROOT/'reports/phase4_v13_pilot_launch.json')
before=read(ROOT/'reports/phase4_v13_pilot_prelaunch.json')
after=json.loads((run/'provider-observations.jsonl').read_text().splitlines()[-1])
assert after['status'].endswith('.COMPLETE') and after['provider_version']==launch['provider_version']==1
folder=ROOT/'notebooks/phase4-lifecycle-v13-review-r1'
lock=read(folder/'review-source-lock.json')
for base,key in ((ROOT,'bindings'),(folder,'artifacts')):
    for name,digest in lock[key].items():assert sha(base/name)==digest,name
package=ROOT/'notebooks/phase4-v13-pilot-launch-ready-r1'
for name,digest in read(package/'launch-package-lock.json')['artifacts'].items():assert sha(package/name)==digest
final=read(out/'evaluation/notebook-result.json')
assert final['passed'] and final['completed'] and final['source_removed'] and final['error'] is None
assert final['evaluation_sha256']==sha(out/'evaluation/result.json')
assert final['cleanup_sha256']==sha(out/'control/notebook-cost.json')
cost=read(out/'control/notebook-cost.json')
assert cost['dependency_trees_removed'] and cost['error'] is None
report=read(out/'control/outer.json')
w=read(out/'worker/state.json');report['worker']=w
telemetry=read_telemetry(out/'monitor')
report.update(monitor_fields(read(out/'monitor/monitor-result.json'),telemetry,first_cell_monotonic=report['first_cell_monotonic']))
verdict=evaluate(report,read(ROOT/'certification/phase4_v1/workload.json'))
assert verdict['passed'],verdict['errors']
assert report['independent_gpu_cleanup_verified'] and read(out/'control/gpu-cleanup.json')['gpu_cleanup_verified']
assert final['elapsed_seconds']<27540
metrics={key:sum(c['result'][key] for c in w['clients']) for key in
 ('policy_failures','parser_repairs','inference_queue_failures','inference_transport_failures','acknowledged_actions','levels_completed')}
samples=telemetry['samples']
files=sorted(p for p in run.rglob('*') if p.is_file())
archive=ROOT/'evidence/phase4-v13-pilot-passed-v1.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(run).as_posix())
record={'recorded_at':datetime.now(timezone.utc).isoformat(),'attempt_id':launch['attempt_id'],
 'provider_status':'COMPLETE','provider_version':1,'passed':True,'phase4_complete':False,
 'scope':'development_model_lifecycle_not_production_certification','independent_local_replay_passed':True,
 'clients':len(w['clients']),'requests':len(w['requests']),'metrics':metrics,'canary_audit':w['canary_audit'],
 'action6_acknowledged':sum(e['kind']=='action' and e['status']=='acknowledged' and e['fields'].get('action_id')==6 for c in w['clients'] for e in c['client_journal']),
 'internal_elapsed_seconds':final['elapsed_seconds'],'source_removed':final['source_removed'],
 'dependency_trees_removed':cost['dependency_trees_removed'],
 'cleanup':{k:report[k] for k in ('cleanup_verified','gpu_cleanup_verified','independent_gpu_cleanup_verified','scratch_removed')},
 'gpu_samples':len(samples),'max_sampling_gap_seconds':max(b['elapsed_seconds']-a['elapsed_seconds'] for a,b in zip(samples,samples[1:])),
 'evaluation':verdict,'final_receipt':final,
 'account_gpu_usage_delta_seconds':round(after['gpu_quota_seconds']['time_used']-before['gpu_quota_seconds']['time_used'],6),
 'account_delta_scope':'Aggregate account change, not exact per-attempt billing','exact_provider_billed_seconds':None,
 'provider_reserved_seconds_observed':after['gpu_quota_seconds']['time_reserved'],
 'charged_or_reserved_seconds':28800,'released_seconds':0,'attempt_consumed':True,'retry_authorized':False,
 'evidence_archive':archive.relative_to(ROOT).as_posix(),'evidence_archive_sha256':sha(archive),
 'evidence':{p.relative_to(run).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}}
path=ROOT/'reports/phase4_v13_pilot_evaluation.json'
with path.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
ledger_path=ROOT/'config/phase4_v13_pilot_compute_ledger.json';ledger=read(ledger_path)
assert not any(e['kind'].startswith('attempt_completed') for e in ledger['events'])
ledger['events'].append({'kind':'attempt_completed_accounting_pending','attempt_id':launch['attempt_id'],
 'recorded_at':record['recorded_at'],'provider_status':'COMPLETE','passed':True,
 'result_reference':path.relative_to(ROOT).as_posix(),'result_sha256':sha(path),
 'charged_or_reserved_seconds':28800,'released_seconds':0,'exact_provider_billed_seconds':None,
 'account_gpu_usage_delta_seconds':record['account_gpu_usage_delta_seconds'],'attempt_consumed':True,'retry_authorized':False})
tmp=ledger_path.with_suffix('.writing')
with tmp.open('x',encoding='utf-8') as f:json.dump(ledger,f,indent=2)
tmp.replace(ledger_path)
print(json.dumps({k:v for k,v in record.items() if k not in ('evidence','evaluation')},indent=2))
