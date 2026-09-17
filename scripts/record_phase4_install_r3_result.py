"""Preserve the repaired probe's terminal evidence and conservative accounting."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
run = ROOT/'reports/runs/phase4-v6-install-r3-20260917'
output = run/'output/phase4-v6-install-check'
result = json.loads((output/'result.json').read_text())
stages = json.loads((output/'bootstrap/stages.json').read_text())
log = (output/'bootstrap/stages.log').read_text()
observations = [json.loads(line) for line in (run/'provider-observations.jsonl').read_text().splitlines()]
after = observations[-1]
before = json.loads((ROOT/'reports/phase4_v6_install_r3_preflight.json').read_text())
assert after['status'].endswith('.ERROR') and not result['passed']
assert 'numba 0.61.2 has requirement numpy<2.3,>=1.24' in log
assert 'mistral-common 1.11.1 has requirement numpy<2.4,>=1.25' in log
assert all(row['passed'] for row in stages[:6])
assert stages[6]['stage'] == 'dependency_check' and not stages[6]['passed']
ledger_path = ROOT/'config/phase4_v6_install_r3_compute_ledger.json'
ledger = json.loads(ledger_path.read_text())
assert not any(e['kind'] == 'attempt_completed_accounting_pending' for e in ledger['events'])
archive = ROOT/'evidence/phase4-v6-install-r3-failed-v1.zip'
files = sorted(path for path in run.rglob('*') if path.is_file())
with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as bundle:
    for path in files:
        bundle.write(path, path.relative_to(run).as_posix())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
record = dict(
    recorded_at=datetime.now(timezone.utc).isoformat(),
    attempt_id='p4-v6-install-r3-20260917T112448Z', provider_version=1,
    provider_status='ERROR', passed=False, failure_stage='dependency_check',
    cause='Frozen numpy 2.4.4 conflicts with numba 0.61.2 (<2.3) and mistral-common 1.11.1 (<2.4 on Python 3.12).',
    model_service_install_command_passed=True, environment_install_command_passed=True,
    dependency_check_passed=False, torch_wheel_contract_verified=True,
    empty_venv_bootstrap_passed=True, host_pip_targeting_passed=True,
    host_python='3.12.13', host_pip='24.1.2',
    wheelhouses=result['wheelhouses'], internal_elapsed_seconds=result['elapsed_seconds'],
    cuda_check_reached=False, model_loaded=False, pilot_launched=False,
    gpu_cleanup_verified=False, scratch_cleanup_verified=False,
    cleanup_evidence_note='Failure result does not emit affirmative cleanup receipts.',
    account_gpu_seconds_before=before['gpu_quota_seconds']['time_used'],
    account_gpu_seconds_after=after['gpu_quota_seconds']['time_used'],
    account_gpu_usage_delta_seconds=round(after['gpu_quota_seconds']['time_used']-before['gpu_quota_seconds']['time_used'],6),
    account_delta_scope='Aggregate account change; not exact attempt billing.',
    exact_provider_billed_seconds=None, charged_or_reserved_seconds=1800,
    released_seconds=0, attempt_consumed=True, retry_authorized=False,
    evidence_archive=archive.relative_to(ROOT).as_posix(), evidence_archive_sha256=sha(archive),
    evidence={p.relative_to(run).as_posix(): {'sha256':sha(p),'bytes':p.stat().st_size} for p in files})
report = ROOT/'reports/phase4_v6_install_r3_evaluation.json'
with report.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
ledger['events'].append(dict(kind='attempt_completed_accounting_pending',
    attempt_id=record['attempt_id'], recorded_at=record['recorded_at'],
    provider_status='ERROR', provider_version=1,
    result_reference=report.relative_to(ROOT).as_posix(), result_sha256=sha(report),
    charged_or_reserved_seconds=1800, released_seconds=0, exact_provider_billed_seconds=None,
    account_gpu_usage_delta_seconds=record['account_gpu_usage_delta_seconds'],
    attempt_consumed=True, retry_authorized=False))
temporary = ledger_path.with_suffix('.writing')
with temporary.open('x', encoding='utf-8') as stream:
    json.dump(ledger, stream, indent=2)
temporary.replace(ledger_path)
print(json.dumps({k:v for k,v in record.items() if k != 'evidence'}, indent=2))
