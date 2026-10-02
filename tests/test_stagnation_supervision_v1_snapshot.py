"""Track 3 source snapshot and synthetic authority rejection tests; never launches processes or GPUs."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest import mock

from research.stagnation_supervision_v1.closed_loop import authority as A


class Authority(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write(A.REVIEW, {'status': 'reviewed_launch_source', 'scope': A.SCOPE,
                              'bindings': {n: self.source(n) for n in A.REQUIRED_SOURCE}})
        self.write(A.SOURCE, {'status': 'approved', 'scope': A.SCOPE, 'approval_kind': 'source',
                              'user_response': 'synthetic test only', 'review_lock_sha256': self.sha(A.REVIEW)})
        self.write(A.COMPUTE, {'status': 'approved', 'scope': A.SCOPE, 'approval_kind': 'compute',
                               'user_response': 'synthetic test only', 'review_lock_sha256': self.sha(A.REVIEW),
                               'source_approval_sha256': self.sha(A.SOURCE),
                               'sessions': {'1': copy.deepcopy(A.SESSION_LIMITS['1'])}})
        self.write(A.EXECUTION, {'scope': A.SCOPE, 'review_lock_sha256': self.sha(A.REVIEW),
                                 'source_approval_sha256': self.sha(A.SOURCE),
                                 'compute_authorization_sha256': self.sha(A.COMPUTE),
                                 'session': '1', 'attempt_id': 'ssv1-test-0001'})
        self.write(A.RESERVATION, {'status': 'reserved', 'attempt_id': 'ssv1-test-0001', 'seconds': 5400,
                                   'events': ['reserve'], 'execution_sha256': self.sha(A.EXECUTION)})

    def source(self, name):
        raw = (A.ROOT / name).read_bytes()
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True), encoding='utf-8')

    def sha(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def test_gpu_disabled_gate_rejects_even_complete_synthetic_authority(self):
        self.assertTrue(A.LIVE_DISABLED)
        with self.assertRaisesRegex(PermissionError, 'disabled'):
            A.require(self.root)

    def test_underlying_gate_accepts_only_complete_bound_test_records(self):
        with mock.patch.object(A, 'LIVE_DISABLED', False):
            self.assertEqual(A.require(self.root)['session'], '1')

    def test_missing_authority_and_source_rejected(self):
        for name in (A.REVIEW, A.SOURCE, A.COMPUTE, A.EXECUTION, A.RESERVATION,
                     sorted(A.REQUIRED_SOURCE)[0]):
            with self.subTest(name=name):
                path = self.root / name
                raw = path.read_bytes()
                path.unlink()
                try:
                    with mock.patch.object(A, 'LIVE_DISABLED', False), self.assertRaises(PermissionError):
                        A.require(self.root)
                finally:
                    path.write_bytes(raw)

    def test_mismatched_and_consumed_records_rejected(self):
        mutations = ((A.SOURCE, 'review_lock_sha256', '0' * 64),
                     (A.COMPUTE, 'source_approval_sha256', '0' * 64),
                     (A.EXECUTION, 'compute_authorization_sha256', '0' * 64),
                     (A.EXECUTION, 'session', '3'),
                     (A.RESERVATION, 'seconds', 4800),
                     (A.RESERVATION, 'status', 'consumed'),
                     (A.RESERVATION, 'events', ['reserve', 'launch']))
        for name, key, value in mutations:
            with self.subTest(name=name, key=key):
                original = json.loads((self.root / name).read_bytes())
                self.write(name, {**original, key: value})
                try:
                    with mock.patch.object(A, 'LIVE_DISABLED', False), self.assertRaises(PermissionError):
                        A.require(self.root)
                finally:
                    self.write(name, original)

    def test_runtime_consumption_is_exclusive(self):
        with mock.patch.object(A, 'LIVE_DISABLED', False):
            A.consume_runtime(self.root, self.root)
            A.verify_runtime_claim(self.root, self.root)
            with self.assertRaises(FileExistsError):
                A.consume_runtime(self.root, self.root)

    def test_actual_model_host_import_excludes_game_dependencies(self):
        code = '''import importlib.abc, sys
class BlockGame(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('arcengine', 'arc_agi'):
            raise ModuleNotFoundError('game dependency prohibited: ' + fullname)
sys.meta_path.insert(0, BlockGame())
import research.stagnation_supervision_v1.closed_loop.host
assert not any(n.split('.')[0] in ('arcengine', 'arc_agi') for n in sys.modules)
'''
        value = subprocess.run([sys.executable, '-c', code], cwd=A.ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(value.returncode, 0, value.stderr)


if __name__ == '__main__':
    unittest.main()
