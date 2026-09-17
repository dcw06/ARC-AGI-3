"""Record the consumed attempt's evidence without treating quota delta as billing."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
run = ROOT/'reports/runs/phase4-v6-install-20260917'
result_path = run/'output/phase4-v6-install-check/result.json'
log_path = run/'output/phase4-v6-install-check/install.log'
result = json.loads(result_path.read_text())
observations = [json.loads(line) for line in (run/'provider-observations.jsonl').read_text().splitlines()]
numeric = [row for row in observations if 'gpu_quota_seconds' in row]
before = next(row for row in numeric if row['status'].endswith('.QUEUED'))
after = numeric[-1]
if after['status'] != 'KernelWorkerStatus.ERROR' or result['passed'] is not False:
    raise ValueError('unexpected attempt disposition; requires review')
if 'ensurepip' not in log_path.read_text():
    raise ValueError('expected bootstrap failure not found')
inventory = {path.relative_to(ROOT).as_posix(): {
    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
    for path in (run/'output').rglob('*') if path.is_file()}
record = {
    'schema_version': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(),
    'attempt_id': 'p4-v6-install-20260917T084416Z', 'provider_version': 1,
    'provider_status': after['status'], 'passed': False,
    'failure_stage': 'fresh_venv_ensurepip_bootstrap',
    'underlying_ensurepip_failure_reason': 'not exposed by retained venv stderr',
    'verified_model_wheelhouse_payloads': result['wheelhouses']['model_payloads'],
    'verified_environment_wheels': result['wheelhouses']['environment_wheels'],
    'dependency_installation_reached': False, 'cuda_check_reached': False,
    'model_loaded': False, 'pilot_launched': False,
    'internal_elapsed_seconds': result['elapsed_seconds'],
    'account_gpu_seconds_before': before['gpu_quota_seconds']['time_used'],
    'account_gpu_seconds_after': after['gpu_quota_seconds']['time_used'],
    'account_gpu_usage_delta_seconds': round(after['gpu_quota_seconds']['time_used']-
                                            before['gpu_quota_seconds']['time_used'], 6),
    'account_delta_scope': 'aggregate quota change, not verified per-attempt billing or complete session inventory',
    'exact_provider_billed_seconds': None, 'charged_or_reserved_seconds': 1800,
    'released_seconds': 0, 'attempt_consumed': True, 'retry_authorized': False,
    'phase4_complete': False, 'evidence': inventory,
}
output = ROOT/'reports/phase4_v6_install_evaluation.json'
with output.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
ledger_path = ROOT/'config/phase4_v6_install_compute_ledger.json'
ledger = json.loads(ledger_path.read_text())
if any(event['kind'] == 'attempt_completed_accounting_pending' for event in ledger['events']):
    raise ValueError('completion already recorded')
ledger['events'].append({
    'kind': 'attempt_completed_accounting_pending', 'attempt_id': record['attempt_id'],
    'recorded_at': record['recorded_at'], 'provider_version': 1, 'provider_status': 'ERROR',
    'result_reference': output.relative_to(ROOT).as_posix(),
    'result_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'charged_or_reserved_seconds': 1800, 'released_seconds': 0,
    'exact_provider_billed_seconds': None, 'account_gpu_usage_delta_seconds': record['account_gpu_usage_delta_seconds'],
    'attempt_consumed': True, 'retry_authorized': False,
})
temporary = ledger_path.with_suffix('.writing')
with temporary.open('x', encoding='utf-8') as stream:
    json.dump(ledger, stream, indent=2)
temporary.replace(ledger_path)
print(json.dumps({key: value for key, value in record.items() if key != 'evidence'}, indent=2))
