"""Consolidate retained attempt outcomes without inventing billing or releasing credit."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
entries=[]
for path in sorted((ROOT/'config').glob('phase4*compute_ledger.json')):
    ledger=read(path);events=ledger['events']
    reserve=next(e for e in events if e['kind']=='reserve')
    attempt=ledger.get('attempt_id') or reserve['attempt_id']
    completed=[e for e in events if e['kind'].startswith('attempt_completed')]
    launch=[e for e in events if e['kind']=='launch_receipt']
    receipt=read(ROOT/launch[-1]['reference']) if launch else {}
    end=completed[-1] if completed else {}
    status=end.get('provider_status')
    if status: classification='terminal_'+status.lower()+'_exact_billing_unresolved'
    elif receipt.get('http_status')==400 or '400 Client Error' in receipt.get('error',''):
        classification='upload_rejected_http_400_no_successful_launch_receipt'
    else: classification='upload_outcome_unresolved_no_retry'
    entry={'attempt_id':attempt,'ledger':path.relative_to(ROOT).as_posix(),'ledger_sha256':sha(path),
      'disposition':classification,'provider_status':status,'launch_receipt':launch[-1]['reference'] if launch else None,
      'result_reference':end.get('result_reference'),'account_gpu_usage_delta_seconds':end.get('account_gpu_usage_delta_seconds'),
      'exact_provider_billed_seconds':end.get('exact_provider_billed_seconds'),
      'reservation_seconds':reserve.get('seconds',reserve.get('charged_or_reserved_seconds')),
      'released_seconds':0,'attempt_reusable':False}
    for key in ('launch_receipt','result_reference'):
        if entry[key]:entry[key+'_sha256']=sha(ROOT/entry[key])
    entries.append(entry)
observations=ROOT/'reports/runs/phase4-v13-pilot-20260918/provider-observations.jsonl'
latest=json.loads(observations.read_text().splitlines()[-1])
record={'recorded_at':datetime.now(timezone.utc).isoformat(),'scope':'consolidated_phase4_attempt_accounting_disposition',
 'attempts':entries,'latest_account_observation':latest,
 'reconciliation_status':'Outcomes and aggregate deltas reconciled to retained receipts; exact per-attempt billing and ambiguous v10 upload remain unresolved.',
 'billing_evidence_required':'Provider per-session usage/invoice or authoritative allocation history identifying each attempt, including rejected/ambiguous submissions.',
 'no_double_counting':'Reservation events are ceilings, not costs. Account deltas are not summed across attempts or quota-reset periods.',
 'release_policy':'No local reservation released or transferred on aggregate quota evidence alone; zero provider reservation is reported separately.',
 'new_spending_authorized':False}
with (ROOT/'reports/phase4_attempt_accounting_reconciliation.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps({'attempts':len(entries),'dispositions':[(e['attempt_id'],e['disposition']) for e in entries]}))
