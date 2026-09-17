"""Verify and preserve the successful r5 installation evidence and accounting."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
run=ROOT/'reports/runs/phase4-v6-install-r5-20260917'
output=run/'output/phase4-v6-install-check'
read=lambda path:json.loads(path.read_text(encoding='utf-8'))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
result=read(output/'result.json')
observations=[json.loads(line) for line in (run/'provider-observations.jsonl').read_text().splitlines()]
after=observations[-1]
before=read(ROOT/'reports/phase4_v6_install_r5_preflight.json')
assert after['status'].endswith('.COMPLETE')
assert result['passed'] and result['error'] is None
assert result['scratch_removed'] and result['gpu_cleanup_verified']
assert not result['model_loaded'] and not result['pilot_launched']
assert 0 < result['elapsed_seconds'] < 900
runtime={}
for role,final in [('model','model_cuda_and_isolation'),('game','game_runtime_and_isolation')]:
    stages=read(output/role/'stages.json')
    names=[row['stage'] for row in stages]
    assert len(names)==len(set(names))
    assert all(row['passed'] and row['error'] is None for row in stages)
    assert {'resolve_'+role,'install_'+role,'dependency_check','installed_inventory',final} <= set(names)
    rows=[]
    for line in (output/role/'stages.log').read_text(encoding='utf-8').splitlines():
        if line.startswith('{'):
            rows.append(json.loads(line))
    runtime[role]=rows[-1]
assert runtime['model']['cuda_tensor_operation_passed'] and runtime['model']['vllm_extension_import_passed']
assert runtime['model']['versions']=={'torch':'2.10.0','vllm':'0.19.0','transformers':'4.57.6','numpy':'2.2.6'}
assert runtime['model']['torch_runtime_version']=='2.10.0+cu128' and runtime['model']['cuda_build']=='12.8'
assert runtime['game']['isolated_game_imports_passed']
assert runtime['game']['versions']['numpy']=='2.4.4'
folder=ROOT/'notebooks/phase4-v6-install-check-proposal-r5'
review=read(folder/'review-source-lock.json')
for name,expected in review['bindings'].items(): assert sha(ROOT/name)==expected,name
for name,expected in review['artifacts'].items(): assert sha(folder/name)==expected,name
ledger_path=ROOT/'config/phase4_v6_install_r5_compute_ledger.json'
ledger=read(ledger_path)
assert not any(row['kind']=='attempt_completed_accounting_pending' for row in ledger['events'])
files=sorted(path for path in run.rglob('*') if path.is_file())
archive=ROOT/'evidence/phase4-v6-install-r5-passed-v1.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
    for path in files: bundle.write(path,path.relative_to(run).as_posix())
record={'recorded_at':datetime.now(timezone.utc).isoformat(),
    'attempt_id':'p4-v6-install-r5-20260917T121119Z','provider_version':1,
    'provider_status':'COMPLETE','passed':True,'scope':result['scope'],
    'runtime':runtime,'wheelhouses':result['wheelhouses'],
    'internal_elapsed_seconds':result['elapsed_seconds'],
    'scratch_removed':True,'gpu_cleanup_verified':True,
    'model_loaded':False,'pilot_launched':False,'phase4_complete':False,
    'account_gpu_seconds_before':before['gpu_quota_seconds']['time_used'],
    'account_gpu_seconds_after':after['gpu_quota_seconds']['time_used'],
    'account_gpu_usage_delta_seconds':round(after['gpu_quota_seconds']['time_used']-before['gpu_quota_seconds']['time_used'],6),
    'account_delta_scope':'Aggregate account change, not exact per-attempt billing',
    'exact_provider_billed_seconds':None,'charged_or_reserved_seconds':1800,
    'released_seconds':0,'attempt_consumed':True,'retry_authorized':False,
    'evidence_archive':archive.relative_to(ROOT).as_posix(),'evidence_archive_sha256':sha(archive),
    'evidence':{p.relative_to(run).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}}
report=ROOT/'reports/phase4_v6_install_r5_evaluation.json'
with report.open('x',encoding='utf-8') as stream: json.dump(record,stream,indent=2)
ledger['events'].append({'kind':'attempt_completed_accounting_pending',
    'attempt_id':record['attempt_id'],'recorded_at':record['recorded_at'],
    'provider_status':'COMPLETE','provider_version':1,'installation_check_passed':True,
    'result_reference':report.relative_to(ROOT).as_posix(),'result_sha256':sha(report),
    'charged_or_reserved_seconds':1800,'released_seconds':0,'exact_provider_billed_seconds':None,
    'account_gpu_usage_delta_seconds':record['account_gpu_usage_delta_seconds'],
    'attempt_consumed':True,'retry_authorized':False})
temporary=ledger_path.with_suffix('.writing')
with temporary.open('x',encoding='utf-8') as stream: json.dump(ledger,stream,indent=2)
temporary.replace(ledger_path)
print(json.dumps({k:v for k,v in record.items() if k!='evidence'},indent=2))
