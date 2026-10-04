"""progress_subgoal_v1 packaging: derivation from WS3 v1's reviewed files, review inventory and review lock.

The inventory follows tracked files only (git ls-files), as WS3 r2 does, so run from a git checkout."""
import hashlib
import json
from pathlib import Path
import unittest

from research.progress_subgoal_v1 import authority
from scripts import derive_progress_subgoal_v1 as D

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / authority.REVIEW


class Derivation(unittest.TestCase):
    def test_packaging_and_runtime_files_match_their_derivations(self):
        self.assertEqual(D.stale(), [])

    def test_ws3_sources_are_unchanged_since_the_derivation(self):
        self.assertEqual(D.source_hashes(), D.SOURCE_SHA256)
        self.assertEqual(D.RUNTIME.source_hashes(), D.RUNTIME.SOURCE_SHA256)

    def test_no_existing_ws3_file_is_a_target(self):
        targets = set(D.TARGETS) | set(D.RUNTIME.DERIVED)
        self.assertFalse({t for t in targets if 'ws3' in t})


class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import build_progress_subgoal_v1_review as R
        cls.R, cls.names = R, R.inventory()

    def test_inventory_binds_the_runtime_and_the_frozen_question_set(self):
        self.assertTrue(authority.REQUIRED_SOURCE <= set(self.names), authority.REQUIRED_SOURCE - set(self.names))
        self.assertIn('research/progress_subgoal_v1/probes.json', self.names)

    def test_build_only_modules_and_other_question_sets_are_not_packaged(self):
        for name in ('rehearse.py', 'derive.py', 'token_audit.py', 'rules.py'):
            self.assertNotIn('research/progress_subgoal_v1/' + name, self.names)
        self.assertFalse([n for n in self.names if n.startswith('research/ws3_questionnaire_v1/')])
        self.assertNotIn('research/progress_subgoal_v1/rehearsal_results.json', self.names)

    def test_review_lock_matches_the_inventory_and_the_working_tree(self):
        lock = json.loads(LOCK.read_bytes())
        self.assertEqual(sorted(lock['bindings']), self.names)
        for name, digest in {**lock['bindings'], **lock['review_documents']}.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        for name, digest in lock['artifacts'].items():
            self.assertEqual(hashlib.sha256((LOCK.parent / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual((lock['scope'], lock['authorized_seconds'], lock['gpu_launch_authorized']),
                         ('progress-subgoal-v1', 0, False))
        self.assertLess((LOCK.parent / 'profile.ipynb').stat().st_size, 900000)
        metadata = json.loads((LOCK.parent / 'kernel-metadata.json').read_bytes())
        self.assertEqual((metadata['enable_gpu'], metadata['enable_internet'], metadata['is_private']),
                         (False, False, True))

    def test_committed_review_and_approval_records_never_enter_the_inventory(self):
        """Review of bc0c1b9 [P1]: committing the lock added it to its own inventory (277 instead of 276)."""
        from scripts import progress_subgoal_v1_package as package
        records = {authority.REVIEW, authority.SOURCE, authority.COMPUTE, authority.EXECUTION, authority.RESERVATION,
                   package.CLAIM, package.RECEIPT, package.PRELAUNCH, 'reports/progress_subgoal_v1_package_review.json',
                   'notebooks/progress-subgoal-v1-review-r1/review-source-lock.json'}
        for name in records:
            self.assertTrue(self.R._sidecar(name), name)
        tracked = self.R._tracked()
        saved = list(self.R._TRACKED)
        try:  # as if every record (approvals, reservation, receipts, every lock revision) were committed
            self.R._TRACKED[:] = [frozenset(tracked | records)]
            again = self.R.inventory()
        finally:
            self.R._TRACKED[:] = saved
        self.assertEqual(again, self.names)
        self.assertFalse([n for n in again if n in records or n.startswith('notebooks/progress-subgoal-v1-')])

    def test_frozen_rules_and_decisions_are_bound_as_review_documents(self):
        documents = json.loads(LOCK.read_bytes())['review_documents']
        for name in ('research/progress_subgoal_v1/decision_rules.json',
                     'research/progress_subgoal_v1/third_arm_decision.json',
                     'research/progress_subgoal_v1/evaluation_seed.json'):
            self.assertIn(name, documents)


if __name__ == '__main__':
    unittest.main()
