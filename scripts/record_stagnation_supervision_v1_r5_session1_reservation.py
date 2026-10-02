"""Record the explicit R5/session-1 reservation approval; no provider submission."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from scripts import prepare_stagnation_supervision_v1_authorization_r5 as P
from scripts.review_stagnation_supervision_v1_authorization_r5 import verify, extract

SOURCE_SHA = 'a6091bc20401cc280c818b932ac9a351fd7e4998c337525f611c76f2c3756571'
PACKAGE_SHA = '6cb4b854d94197fb4a1a138fbe2756f9a5a8d0e8fac8707c07b333858f37ee00'
RECORDS = P.ROOT / 'reports/stagnation_supervision_v1_r5_session1_authority'
PACKAGE = P.ROOT / 'notebooks/stagnation-supervision-v1-r5-session1-reserved'


def main():
    if RECORDS.exists() or PACKAGE.exists():
        raise FileExistsError('one reservation only; inspect existing records, never automatically retry')
    lock, notebook, payload, source = verify(P.OUT)
    if (lock['source_review_sha256'] != SOURCE_SHA or
            P.sha((P.OUT / 'review-source-lock.json').read_bytes()) != PACKAGE_SHA):
        raise ValueError('user-approved source/package differs')
    receipt = json.loads((P.ROOT / 'reports/stagnation_supervision_v1_authorization_checks_r5.json').read_bytes())
    if (receipt['source_review_sha256'] != SOURCE_SHA or receipt['package_lock_sha256'] != PACKAGE_SHA
            or receipt['status'] != 'locally_reviewed_pending_explicit_approvals'
            or not receipt['packaged_cpu_replay_and_lifecycle_passed']):
        raise ValueError('review receipt binding')
    now = datetime.now(timezone.utc).isoformat()
    attempt = 'ssv1-r5-session1-reservation-001'
    with tempfile.TemporaryDirectory() as tmp:
        extract(Path(tmp), payload, source)
        gate = P.authority(tmp)
        common = {'status': 'approved', 'scope': gate.SCOPE, 'review_lock_sha256': SOURCE_SHA,
                  'package_lock_sha256': PACKAGE_SHA, 'recorded_at_utc': now}
        records = {}
        records[gate.SOURCE] = P.raw({**common, 'approval_kind': 'source', 'user_response': 'Approve R5 source'})
        records[gate.COMPUTE] = P.raw({**common, 'approval_kind': 'compute',
            'user_response': 'Authorize session 1 reservation',
            'source_approval_sha256': P.sha(records[gate.SOURCE]), 'sessions': {'1': gate.SESSION_LIMITS['1']},
            'authorization_scope': 'reserve_one_attempt_only', 'submission_authorized': False})
        records[gate.EXECUTION] = P.raw({'scope': gate.SCOPE, 'session': '1', 'attempt_id': attempt,
            'review_lock_sha256': SOURCE_SHA, 'source_approval_sha256': P.sha(records[gate.SOURCE]),
            'compute_authorization_sha256': P.sha(records[gate.COMPUTE])})
        records[gate.RESERVATION] = P.raw({'status': 'reserved', 'attempt_id': attempt,
            'seconds': 5400, 'events': ['reserve'], 'execution_sha256': P.sha(records[gate.EXECUTION]),
            'reserved_at_utc': now, 'provider_submission_started': False,
            'reservation_type': 'local_authorized_compute_budget_not_provider_capacity_booking'})
        for name, raw in records.items():
            path = Path(tmp) / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        if gate.require(tmp)['session'] != '1':
            raise ValueError('reservation gate')
    # Durable exclusive records precede packaging; failure never creates a second reservation.
    RECORDS.mkdir()
    for name, raw in records.items():
        path = RECORDS / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(raw)
    ledger = {'attempt_id': attempt, 'session': '1', 'authorized_seconds': 5400,
              'internal_seconds': 5100, 'maximum_attempts': 1, 'automatic_retries': 0,
              'source_review_sha256': SOURCE_SHA, 'submission_authorized': False,
              'provider_submission_started': False, 'consumed': False,
              'events': [{'kind': 'reserve', 'seconds': 5400, 'recorded_at_utc': now}],
              'authority_sidecars': {n: P.sha(v) for n, v in records.items()},
              'session2_authorized': False}
    (RECORDS / 'compute-ledger.json').write_bytes(P.raw(ledger))
    P.assemble_approved(P.OUT, records, '1', PACKAGE)
    # Check every emitted artifact and exercise extraction/authority only, never the live entrypoint.
    binding = json.loads((PACKAGE / 'package-binding.json').read_bytes())
    for name, digest in binding['artifacts'].items():
        if P.sha((PACKAGE / name).read_bytes()) != digest: raise ValueError('package hash')
    if binding['sidecars'] != ledger['authority_sidecars'] or binding['submitted'] is not False:
        raise ValueError('package authority binding')
    nb = json.loads((PACKAGE / 'profile.ipynb').read_bytes())
    code = nb['cells'][1]['source']
    original = ('    from scripts.stagnation_supervision_v1_launch import notebook_entry\n'
                '    notebook_entry(source,started,MODE,SESSION)\n')
    replacement = ("    from research.stagnation_supervision_v1.closed_loop.authority import require\n"
                   "    assert require(source)['session']=='1'\n")
    if code.count(original) != 1: raise ValueError('entrypoint changed')
    with tempfile.TemporaryDirectory() as tmp:
        import os
        path = Path(tmp) / 'verify.py'; path.write_text(code.replace(original, replacement))
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', TMPDIR=tmp, TMP=tmp, TEMP=tmp)
        result = subprocess.run([sys.executable, str(path)], cwd=tmp, env=env,
                                capture_output=True, text=True, timeout=120)
        if result.returncode: raise ValueError('extracted gate: ' + result.stderr[-1000:])
        if {p.name for p in Path(tmp).iterdir()} != {'verify.py'}: raise ValueError('source cleanup')
    verification = {'status': 'reserved_and_locally_verified_not_submitted', 'attempt_id': attempt,
        'source_review_sha256': SOURCE_SHA, 'package_lock_sha256': PACKAGE_SHA,
        'launch_package_binding_sha256': P.sha((PACKAGE / 'package-binding.json').read_bytes()),
        'authority_records_sha256': ledger['authority_sidecars'],
        'extracted_authority_gate_verified': True, 'live_entrypoint_executed': False,
        'runtime_claim_consumed': False, 'submitted': False, 'session2_authorized': False,
        'submission_requires_new_user_instruction': True}
    (RECORDS / 'verification.json').write_bytes(P.raw(verification))
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
