"""Synthetic authority only; approvals below exist exclusively in temporary directories."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts import prepare_stagnation_supervision_v1_authorization_r5 as P
from scripts.review_stagnation_supervision_v1_authorization_r5 import verify, extract


class Authorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.lock, cls.notebook, cls.payload, cls.source = verify(P.OUT)
        extract(cls.root, cls.payload, cls.source)
        cls.gate = P.authority(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def put(self, name, data):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(P.raw(data))

    def digest(self, name):
        return P.sha((self.root / name).read_bytes())

    def records(self, session='1'):
        a = self.gate
        common = {'status': 'approved', 'scope': a.SCOPE, 'user_response': 'SYNTHETIC TEST ONLY',
                  'review_lock_sha256': self.digest(a.REVIEW)}
        self.put(a.SOURCE, {**common, 'approval_kind': 'source'})
        self.put(a.COMPUTE, {**common, 'approval_kind': 'compute',
                            'source_approval_sha256': self.digest(a.SOURCE),
                            'sessions': {session: a.SESSION_LIMITS[session]}})
        self.put(a.EXECUTION, {'scope': a.SCOPE, 'session': session, 'attempt_id': 'ssv1-r5-test-session-' + session,
            'review_lock_sha256': self.digest(a.REVIEW), 'source_approval_sha256': self.digest(a.SOURCE),
            'compute_authorization_sha256': self.digest(a.COMPUTE)})
        self.put(a.RESERVATION, {'status': 'reserved', 'attempt_id': 'ssv1-r5-test-session-' + session,
            'seconds': a.SESSION_LIMITS[session]['authorized_seconds'], 'events': ['reserve'],
            'execution_sha256': self.digest(a.EXECUTION)})

    def setUp(self):
        self.records()

    def test_only_declared_authority_delta_from_r4(self):
        import base64
        from scripts.review_action_effect_history_v1_notebook import verify_bindings
        _, _, parent = verify_bindings(P.PARENT)
        changed = {n for n, v in self.payload.items() if v != base64.b64decode(parent[n])}
        self.assertEqual(changed, {P.AUTH})
        self.assertFalse(self.gate.LIVE_DISABLED)
        self.assertEqual(self.gate.REVIEW, P.REVIEW)

    def test_each_session_accepts_only_its_own_exact_records(self):
        for session in ('1', '2'):
            self.records(session)
            self.assertEqual(self.gate.require(self.root)['session'], session)
        self.records()

    def test_missing_records_fail_closed(self):
        a = self.gate
        for name in (a.SOURCE, a.COMPUTE, a.EXECUTION, a.RESERVATION, a.REVIEW):
            path = self.root / name; original = path.read_bytes(); path.unlink()
            try:
                with self.assertRaises(PermissionError): a.require(self.root)
            finally:
                path.write_bytes(original)

    def test_mismatches_pending_consumed_and_cross_session_fail_closed(self):
        a = self.gate
        mutations = [(a.SOURCE, 'status', 'pending'), (a.SOURCE, 'user_response', ''),
            (a.SOURCE, 'review_lock_sha256', '0'*64), (a.COMPUTE, 'source_approval_sha256', '0'*64),
            (a.COMPUTE, 'sessions', {'1': a.SESSION_LIMITS['1'], '2': a.SESSION_LIMITS['2']}),
            (a.EXECUTION, 'session', '2'), (a.EXECUTION, 'compute_authorization_sha256', '0'*64),
            (a.RESERVATION, 'status', 'consumed'), (a.RESERVATION, 'events', ['reserve', 'launch']),
            (a.RESERVATION, 'seconds', 4800), (a.RESERVATION, 'attempt_id', 'ssv1-unrelated-test')]
        for name, key, value in mutations:
            with self.subTest(record=name, field=key):
                self.records(); original = (self.root / name).read_bytes()
                data = json.loads(original); data[key] = value; self.put(name, data)
                with self.assertRaises(PermissionError): a.require(self.root)
                (self.root / name).write_bytes(original)

    def test_source_drift_and_duplicate_runtime_claim_rejected(self):
        path = self.root / 'research/stagnation_supervision_v1/closed_loop/monitor.py'
        original = path.read_bytes(); path.write_bytes(original + b'\n# drift\n')
        try:
            with self.assertRaises(PermissionError): self.gate.require(self.root)
        finally: path.write_bytes(original)
        marker = self.gate.consume_runtime(self.root, self.root)
        try:
            self.gate.verify_runtime_claim(self.root, self.root)
            with self.assertRaises(FileExistsError): self.gate.consume_runtime(self.root, self.root)
        finally: marker.unlink()

    def test_local_assembler_cannot_omit_authority_or_switch_session(self):
        a = self.gate
        sidecars = {n: (self.root / n).read_bytes() for n in (a.SOURCE, a.COMPUTE, a.EXECUTION, a.RESERVATION)}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'package'
            with self.assertRaises(ValueError): P.assemble_approved(P.OUT, {}, '1', output)
            self.assertFalse(output.exists())
            with self.assertRaises(PermissionError): P.assemble_approved(P.OUT, sidecars, '2', output)
            self.assertFalse(output.exists())
            P.assemble_approved(P.OUT, sidecars, '1', output)
            receipt = json.loads((output / 'package-binding.json').read_bytes())
            self.assertFalse(receipt['submitted'])
            self.assertEqual(receipt['source_review_sha256'], self.lock['source_review_sha256'])
            meta = json.loads((output / 'kernel-metadata.json').read_bytes())
            self.assertTrue(meta['enable_gpu'] and meta['is_private'])
            self.assertFalse(meta['enable_internet'])
            with self.assertRaises(ValueError): P.assemble_approved(P.OUT, sidecars, '1', output)
