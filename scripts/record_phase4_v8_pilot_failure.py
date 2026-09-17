"""Preserve the failed v8 attempt and reconcile aggregate quota conservatively."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
run = ROOT/'reports/runs/phase4-v8-pilot-20260917'
output = run/'output/phase4-development-v8'
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
launch = read(ROOT/'reports/phase4_v8_pilot_launch.json')
before = read(ROOT/'reports/phase4_v8_pilot_prelaunch.json')
after = json.loads((run/'provider-observations.jsonl').read_text().splitlines()[-1])
installation = read(output/'control/installation.json')
final = read(output/'evaluation/notebook-result.json')
outer = read(output/'control/outer.json')
from certification.phase4_v8.telemetry import read_telemetry
monitor = read_telemetry(output/'monitor')
cost = read(output/'control/notebook-cost.json')
failure = read(output/'monitor/failure.json')
assets = read(output/'control/game-assets.json')
assert after['status'].endswith('.ERROR') and launch['provider_version'] == 1
assert installation['passed'] and not final['passed']
assert assets['passed']
assert failure['error'] == 'ValueError: monitor resource or sampling-gap limit'
ledger_path = ROOT/'config/phase4_v8_pilot_compute_ledger.json'
ledger = read(ledger_path)
assert not any(e['kind'].startswith('attempt_completed') for e in ledger['events'])
files = sorted(p for p in run.rglob('*') if p.is_file())
archive = ROOT/'evidence/phase4-v8-pilot-failed-v1.zip'
with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as bundle:
    for path in files:
        bundle.write(path, path.relative_to(run).as_posix())
record = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'attempt_id': launch['attempt_id'], 'provider_version': 1,
    'provider_status': 'ERROR', 'passed': False, 'phase4_complete': False,
    'installation_passed': True, 'game_staging_passed': True, 'monitor_error': failure['error'],
    'model_start_reached': True, 'model_readiness_verified': False,
    'triggering_measurement_retained': False,
    'retained_samples': len(monitor['samples']),
    'max_retained_gap_seconds': max(b['elapsed_seconds']-a['elapsed_seconds'] for a,b in zip(monitor['samples'],monitor['samples'][1:])),
    'max_retained_rss_bytes': max(s['rss_bytes'] for s in monitor['samples']),
    'max_retained_scratch_bytes': max(s['scratch_bytes'] for s in monitor['samples']),
    'max_retained_vram_bytes': max(s['used_bytes'] for s in monitor['samples']),
    'internal_elapsed_seconds': final['elapsed_seconds'],
    'source_removed': final['source_removed'],
    'dependency_trees_removed': cost['dependency_trees_removed'],
    'scratch_removed': outer['scratch_removed'],
    'process_cleanup_verified': outer['cleanup_verified'],
    'gpu_cleanup_verified': None,
    'evidence_limitations': 'Staging and installation passed; source/dependency/scratch/process cleanup receipts passed. GPU cleanup is unverified because the monitor failed before cleanup. No completed model workload or capacity evidence.',
    'account_gpu_seconds_before': before['gpu_quota_seconds']['time_used'],
    'account_gpu_seconds_after': after['gpu_quota_seconds']['time_used'],
    'account_gpu_usage_delta_seconds': round(after['gpu_quota_seconds']['time_used']-before['gpu_quota_seconds']['time_used'], 6),
    'account_delta_scope': 'Aggregate account change, not exact per-attempt billing',
    'exact_provider_billed_seconds': None, 'charged_or_reserved_seconds': 28800,
    'released_seconds': 0, 'attempt_consumed': True, 'retry_authorized': False,
    'evidence_archive': archive.relative_to(ROOT).as_posix(),
    'evidence_archive_sha256': sha(archive),
    'evidence': {p.relative_to(run).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in files}}
report = ROOT/'reports/phase4_v8_pilot_evaluation.json'
with report.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
ledger['events'].append({
    'kind': 'attempt_completed_accounting_pending', 'attempt_id': launch['attempt_id'],
    'recorded_at': record['recorded_at'], 'provider_status': 'ERROR', 'provider_version': 1,
    'passed': False, 'result_reference': report.relative_to(ROOT).as_posix(),
    'result_sha256': sha(report), 'charged_or_reserved_seconds': 28800,
    'released_seconds': 0, 'exact_provider_billed_seconds': None,
    'account_gpu_usage_delta_seconds': record['account_gpu_usage_delta_seconds'],
    'attempt_consumed': True, 'retry_authorized': False})
temporary = ledger_path.with_suffix('.writing')
with temporary.open('x', encoding='utf-8') as stream:
    json.dump(ledger, stream, indent=2)
temporary.replace(ledger_path)
print(json.dumps({k: v for k, v in record.items() if k != 'evidence'}, indent=2))
