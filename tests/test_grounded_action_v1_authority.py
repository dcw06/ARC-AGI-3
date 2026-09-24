"""Stage B authorization is independent of prior GPU experiments."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.grounded_action_v1 import authority
from research.grounded_action_v1.target_host import main as host_main
from research.grounded_action_v1.target_monitor import main as monitor_main
from research.grounded_action_v1.target_worker import main as worker_main
from research.grounded_action_v1.target_worker import expected_artifact


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approvals(root):
    bindings = {}
    for name in authority.REQUIRED_SOURCE:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('review fixture\n')
        bindings[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    lock = write(root, authority.REVIEW, {'status': 'reviewed_launch_source',
                                          'scope': authority.SCOPE, 'bindings': bindings})
    source = write(root, authority.SOURCE, {'status': 'approved', 'scope': authority.SCOPE,
        'approval_kind': 'source', 'review_lock_sha256': lock, 'user_response': 'approved fixture'})
    compute = write(root, authority.COMPUTE, {'status': 'approved', 'scope': authority.SCOPE,
        'approval_kind': 'compute', 'review_lock_sha256': lock, 'user_response': 'approved fixture',
        'source_approval_sha256': source, **authority.LIMITS})
    execution = write(root, authority.EXECUTION, {'scope': authority.SCOPE,
        'attempt_id': 'gab1-fixture-001', 'review_lock_sha256': lock,
        'source_approval_sha256': source, 'compute_authorization_sha256': compute})
    write(root, authority.RESERVATION, {'status': 'reserved', 'attempt_id': 'gab1-fixture-001',
        'seconds': 3600, 'execution_sha256': execution, 'events': ['reserve']})


class AuthorityTests(unittest.TestCase):
    def test_worker_artifact_identity_is_bound_to_frozen_profile(self):
        artifact = expected_artifact()
        self.assertEqual(artifact['file_count'], 81)
        self.assertEqual(len(artifact['tree_sha256']), 64)

    def test_current_review_cannot_authorize_live_launch(self):
        with self.assertRaises(PermissionError):
            authority.require()
        for entrypoint in (host_main, monitor_main, worker_main):
            with self.subTest(entrypoint=entrypoint.__module__), self.assertRaises(PermissionError):
                entrypoint()

    def test_exact_one_attempt_and_all_separate_bindings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            approvals(root)
            self.assertEqual(authority.require(root)['attempt_id'], 'gab1-fixture-001')
            claim = authority.consume_runtime(root, root)
            self.assertTrue(claim.exists())
            with self.assertRaises(FileExistsError):
                authority.consume_runtime(root, root)

    def test_missing_mismatched_or_consumed_authority_cannot_claim(self):
        for label, name, mutation in (
            ('missing-source', authority.SOURCE, lambda path: path.unlink()),
            ('source-drift', authority.SOURCE, lambda path: path.write_text('{}')),
            ('compute-limit', authority.COMPUTE,
             lambda path: write(path.parents[1], authority.COMPUTE,
                                {**json.loads(path.read_text()), 'maximum_study_calls': 13})),
            ('consumed', authority.RESERVATION,
             lambda path: write(path.parents[2], authority.RESERVATION,
                                {**json.loads(path.read_text()), 'events': ['reserve', 'consume']})),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                approvals(root)
                mutation(root / name)
                with self.assertRaises(PermissionError):
                    authority.consume_runtime(root, root)
                self.assertFalse((root / '.gab1-fixture-001.runtime-consumed.json').exists())


if __name__ == '__main__':
    unittest.main()
