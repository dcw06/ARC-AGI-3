"""Prepare then submit exactly one approved R6 session using the canonical existing ledger."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from scripts import prepare_stagnation_supervision_v1_authorization_r6 as P
from scripts.review_stagnation_supervision_v1_authorization_r6 import verify,extract
from scripts.submit_stagnation_supervision_v1_r6_once import LEDGER, durable_new, submit_once
from scripts.kaggle_stagnation_supervision_v1_r6_no_retry import request_body, credential_session, KaggleNoRetry

SOURCE_SHA='365572597cc972268dc0cb7b52d5b10ea2b5f4f31ea22bbbaf77285d2272bd03'
PACKAGE_SHA='297f8aecd484464ffa9cdd309a2eb1dc0b31b2ec5ebd3edd63a1c8cedf8f221a'
PACKAGE=P.ROOT/'notebooks/stagnation-supervision-v1-r6-session1-launch'
FILES=('scripts/kaggle_stagnation_supervision_v1_r6_no_retry.py','tests/test_ssv_kaggle_no_retry.py',
       'scripts/launch_stagnation_supervision_v1_r6_session1.py')
USER_INSTRUCTION=('Next: implement and review the explicitly no-retry Kaggle adapter, record your R6 source and '
 'launch approvals, then verify the final package before submitting session 1 once. Do not create another '
 'reservation or submit the superseded R5 notebook. The submission guard is local, not distributed: use one '
 'canonical ledger and one designated operator. Real GPU timing remains unmeasured, and this run still '
 'cannot certify the false-interruption gate or complete Phase 4.')


def files():return {n:P.sha((P.ROOT/n).read_bytes()) for n in FILES}


def prepare():
    lock,notebook,payload,source=verify(P.OUT)
    if lock['source_review_sha256']!=SOURCE_SHA or P.sha((P.OUT/'review-source-lock.json').read_bytes())!=PACKAGE_SHA:
        raise ValueError('approved R6 identity differs')
    if PACKAGE.exists() or (LEDGER/'r6-prelaunch.json').exists() or (LEDGER/'submission-claim.json').exists():
        raise FileExistsError('existing package/prelaunch/submission; inspect, do not repeat')
    # Credentials must be locally present before recording approvals or attempting a submission.
    session=credential_session();session.close()
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);extract(root,payload,source);gate=P.authority(root)
        records={n:(LEDGER/n).read_bytes() for n in gate.RESERVED_HASHES}
        for n,b in records.items():
            path=root/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
        execution=gate.validate_reservation(root)
        common={'status':'approved','scope':gate.SCOPE,'review_lock_sha256':SOURCE_SHA,
                'package_lock_sha256':PACKAGE_SHA,'user_response':USER_INSTRUCTION,
                'recorded_at_utc':datetime.now(timezone.utc).isoformat()}
        records[gate.SUCCESSOR_SOURCE]=P.raw({**common,'approval_kind':'source'})
        records[gate.LAUNCH]=P.raw({**common,'approval_kind':'launch',
          'authorization_scope':'submit_and_execute_one_attempt','submission_authorized':True,
          'source_approval_sha256':P.sha(records[gate.SUCCESSOR_SOURCE]),
          'reservation_sha256':gate.RESERVED_HASHES[gate.RESERVATION],
          'compute_authorization_sha256':gate.RESERVED_HASHES[gate.COMPUTE],
          'execution_sha256':gate.RESERVED_HASHES[gate.EXECUTION],
          'attempt_id':execution['attempt_id'],'session':'1','maximum_submissions':1,'automatic_retries':0,
          'designated_operator':'Codex primary agent in this session','canonical_ledger':str(LEDGER.resolve()),
          'adapter_source_bindings':files()})
        for n in (gate.SUCCESSOR_SOURCE,gate.LAUNCH):
            p=LEDGER/n;p.parent.mkdir(parents=True,exist_ok=True)
            durable_new(p,json.loads(records[n]))
        P.assemble_approved(P.OUT,records,'1',PACKAGE)
        body=request_body(PACKAGE)
        # Inspect the exact wire body, including serialized notebook, before approval to send.
        wire=json.loads(body)
        # Field names come from the installed, inspected SDK's request serializer.
        assert wire['sessionTimeoutSeconds']==5400 and wire['machineShape']=='NvidiaRtxPro6000'
        assert wire['isPrivate'] is True and wire['enableGpu'] is True and wire['enableInternet'] is False
        assert json.loads(wire['text'])==json.loads((PACKAGE/'profile.ipynb').read_bytes())
        final_nb=json.loads((PACKAGE/'profile.ipynb').read_bytes())
        code=final_nb['cells'][1]['source']
        call=('    from scripts.stagnation_supervision_v1_launch import notebook_entry\n'
              '    notebook_entry(source,started,MODE,SESSION)\n')
        gate_only=("    from research.stagnation_supervision_v1.closed_loop.authority import require\n"
                   "    assert require(source)['session']=='1'\n")
        if code.count(call)!=1:raise ValueError('entrypoint')
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'verify.py';p.write_text(code.replace(call,gate_only))
            result=subprocess.run([sys.executable,str(p)],cwd=directory,capture_output=True,text=True,timeout=120,
                env=dict(os.environ,CUDA_VISIBLE_DEVICES='',TMPDIR=directory,TMP=directory,TEMP=directory))
            if result.returncode:raise RuntimeError('final extracted approval check failed')
            if {p.name for p in Path(directory).iterdir()}!={'verify.py'}:raise ValueError('source removal')
        receipt={'status':'verified_for_single_submission','source_review_sha256':SOURCE_SHA,
          'package_lock_sha256':PACKAGE_SHA,'request_body_sha256':P.sha(body),'request_bytes':len(body),
          'package_binding_sha256':P.sha((PACKAGE/'package-binding.json').read_bytes()),
          'adapter_source_bindings':files(),'adapter_tests_passed':2,
          'adapter_test_cases':['success','redirect','429','503','disconnect','duplicate_send','missing_claim','request_drift'],
          'http_retries':0,'follow_redirects':False,'canonical_ledger':str(LEDGER.resolve()),
          'operator':'Codex primary agent in this session','live_entrypoint_executed':False,
          'reservation_reused':execution['attempt_id'],'new_reservations':0,
          'sdk_versions':{n:importlib.metadata.version(n) for n in ('kaggle','kagglesdk','requests','urllib3')}}
        durable_new(LEDGER/'r6-prelaunch.json',receipt)
        print(json.dumps(receipt,indent=2))


def submit():
    receipt=json.loads((LEDGER/'r6-prelaunch.json').read_bytes())
    if receipt['adapter_source_bindings']!=files() or receipt['canonical_ledger']!=str(LEDGER.resolve()):
        raise ValueError('adapter or canonical ledger changed')
    if (LEDGER/'submission-claim.json').exists():raise PermissionError('submission already claimed; no retry')
    if receipt['package_binding_sha256']!=P.sha((PACKAGE/'package-binding.json').read_bytes()):
        raise ValueError('final package binding differs')
    transport=KaggleNoRetry(credential_session(),LEDGER,receipt['request_body_sha256'])
    result=submit_once(PACKAGE,transport,ledger=LEDGER)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['submit']:submit()
    else:raise SystemExit('choose prepare or submit explicitly; no implicit submission')
