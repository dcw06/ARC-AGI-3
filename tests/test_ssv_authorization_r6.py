"""Actual historical reservation records plus temporary synthetic successor approvals."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from scripts import prepare_stagnation_supervision_v1_authorization_r6 as P
from scripts.review_stagnation_supervision_v1_authorization_r6 import verify, extract
from scripts.submit_stagnation_supervision_v1_r6_once import submit_once, durable_new, LEDGER


class Authorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.root = Path(cls.tmp.name)
        cls.lock, cls.notebook, cls.payload, cls.source = verify(P.OUT)
        extract(cls.root, cls.payload, cls.source); cls.gate = P.authority(cls.root)
        cls.historical = {n: (LEDGER / n).read_bytes() for n in cls.gate.RESERVED_HASHES}
        for n, value in cls.historical.items():
            path=cls.root/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def setUp(self):
        for name in (self.gate.SUCCESSOR_SOURCE, self.gate.LAUNCH):
            (self.root/name).unlink(missing_ok=True)

    def put(self, name, value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(P.raw(value))

    def approve(self):
        a=self.gate
        common={'scope':a.SCOPE,'status':'approved','review_lock_sha256':P.sha(P.raw(self.source)),
                'user_response':'SYNTHETIC TEST ONLY'}
        self.put(a.SUCCESSOR_SOURCE,{**common,'approval_kind':'source'})
        self.put(a.LAUNCH,{**common,'approval_kind':'launch','authorization_scope':'submit_and_execute_one_attempt',
            'submission_authorized':True,'source_approval_sha256':P.sha((self.root/a.SUCCESSOR_SOURCE).read_bytes()),
            'reservation_sha256':a.RESERVED_HASHES[a.RESERVATION],
            'compute_authorization_sha256':a.RESERVED_HASHES[a.COMPUTE],
            'execution_sha256':a.RESERVED_HASHES[a.EXECUTION],
            'session':'1','attempt_id':'ssv1-r5-session1-reservation-001','maximum_submissions':1,'automatic_retries':0})

    def test_actual_reservation_valid_but_not_execution_authority(self):
        self.assertEqual(self.gate.validate_reservation(self.root)['session'],'1')
        with self.assertRaises(PermissionError):self.gate.require(self.root)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'denied'
            with self.assertRaises(ValueError):P.assemble_approved(P.OUT,self.historical,'1',out)
            self.assertFalse(out.exists())

    def test_source_approval_alone_and_reservation_only_launch_flags_rejected(self):
        self.approve();path=self.root/self.gate.LAUNCH;raw=path.read_bytes();path.unlink()
        with self.assertRaises(PermissionError):self.gate.require(self.root)
        value=json.loads(raw);value.update(authorization_scope='reserve_one_attempt_only',submission_authorized=False)
        self.put(self.gate.LAUNCH,value)
        with self.assertRaises(PermissionError):self.gate.require(self.root)

    def test_exact_launch_binding_and_mutations(self):
        self.approve();self.assertEqual(self.gate.require(self.root)['session'],'1')
        path=self.root/self.gate.LAUNCH;raw=path.read_bytes()
        for field,value in [('submission_authorized',False),('authorization_scope','reserve_one_attempt_only'),
            ('review_lock_sha256','0'*64),('source_approval_sha256','0'*64),('reservation_sha256','0'*64),
            ('compute_authorization_sha256','0'*64),('execution_sha256','0'*64),('session','2'),
            ('attempt_id','different'),('maximum_submissions',2),('automatic_retries',1),('user_response','')]:
            with self.subTest(field=field):
                mutated=json.loads(raw);mutated[field]=value;self.put(self.gate.LAUNCH,mutated)
                with self.assertRaises(PermissionError):self.gate.require(self.root)
        path.write_bytes(raw)

    def test_consumed_reservation_and_source_drift_rejected(self):
        self.approve()
        for name in (self.gate.RESERVATION,P.AUTH):
            path=self.root/name;raw=path.read_bytes();path.write_bytes(raw+b'\n')
            try:
                with self.assertRaises(PermissionError):self.gate.require(self.root)
            finally:path.write_bytes(raw)

    def test_runtime_claim_is_single_use(self):
        self.approve();marker=self.gate.consume_runtime(self.root,self.root)
        try:
            with self.assertRaises(FileExistsError):self.gate.consume_runtime(self.root,self.root)
        finally:marker.unlink()

    def test_submission_rejection_success_failure_and_claim_survival(self):
        self.approve();a=self.gate
        sidecars={n:(self.root/n).read_bytes() for n in (*a.RESERVED_HASHES,a.SUCCESSOR_SOURCE,a.LAUNCH)}
        with tempfile.TemporaryDirectory() as tmp:
            package=Path(tmp)/'package';P.assemble_approved(P.OUT,sidecars,'1',package)
            # Reuse verified reconstruction to avoid redoing compression for every fault;
            # actual assembler and exact artifacts above were checked unmocked.
            def assemble(folder, records, session, dest):
                for n,value in records.items():
                    path=self.root/n;path.write_bytes(value)
                a.require(self.root)
                shutil.copytree(package,dest)
            for outcome in ('success','timeout','preexisting_claim','reservation_only'):
                with self.subTest(outcome=outcome):
                    ledger=Path(tmp)/outcome;ledger.mkdir()
                    (ledger/'compute-ledger.json').write_bytes((LEDGER/'compute-ledger.json').read_bytes())
                    for n,value in sidecars.items():
                        path=ledger/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
                    calls=[]
                    def send(path):
                        self.assertTrue((ledger/'submission-claim.json').is_file());calls.append(path)
                        if outcome=='timeout':raise TimeoutError('synthetic unknown provider outcome')
                    if outcome=='preexisting_claim':durable_new(ledger/'submission-claim.json',{'crash':'before result'})
                    if outcome=='reservation_only':(ledger/a.LAUNCH).unlink()
                    with patch('scripts.review_stagnation_supervision_v1_authorization_r6.verify',return_value=(self.lock,self.notebook,self.payload,self.source)),patch.object(P,'assemble_approved',side_effect=assemble):
                        if outcome=='success':self.assertTrue(submit_once(package,send,ledger=ledger)['consumed'])
                        else:
                            with self.assertRaises((FileNotFoundError,FileExistsError,TimeoutError)):
                                submit_once(package,send,ledger=ledger)
                        with self.assertRaises((FileExistsError,FileNotFoundError)):
                            submit_once(package,send,ledger=ledger)
                    self.assertEqual(len(calls),1 if outcome in ('success','timeout') else 0)
                    if outcome=='timeout':
                        self.assertEqual(json.loads((ledger/'submission-result.json').read_bytes())['status'],
                                         'submission_outcome_unknown_no_retry')

    def test_actual_reservation_only_notebook_refuses_before_live_entry(self):
        import os, subprocess, sys
        code=self.notebook['cells'][1]['source']
        insertion=''.join(f'    p=source/{n!r};p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes({v!r})\n'
                          for n,v in sorted(self.historical.items()))
        code=code.replace(P.MARKER,insertion)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cell.py';path.write_text(code)
            result=subprocess.run([sys.executable,str(path)],cwd=tmp,capture_output=True,text=True,timeout=120,
                                  env=dict(os.environ,CUDA_VISIBLE_DEVICES='',TMPDIR=tmp,TMP=tmp,TEMP=tmp))
            self.assertNotEqual(result.returncode,0)
            self.assertIn('explicit hash-bound launch approval required',result.stderr)
            self.assertEqual({p.name for p in Path(tmp).iterdir()},{'cell.py'})
