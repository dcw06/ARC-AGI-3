"""Evidence comprehension v2 after the run: the approved package is unchanged and post-run tooling is derived."""
import hashlib
import json
from pathlib import Path
import unittest

from scripts import derive_evidence_comprehension_v2 as D
from scripts import derive_evidence_comprehension_v2_postrun as POST

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'notebooks/evidence-comprehension-v2-review-r1/review-source-lock.json'


class ApprovedPackage(unittest.TestCase):
    def test_every_binding_and_review_document_matches_the_approved_lock(self):
        lock = json.loads(LOCK.read_bytes())
        for key in ('bindings', 'review_documents'):
            for name, digest in lock[key].items():
                with self.subTest(name=name):
                    self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_approved_derivation_still_reproduces_its_files(self):
        self.assertEqual(D.stale(), [])


class PostRun(unittest.TestCase):
    def test_post_run_files_match_their_derivation(self):
        self.assertEqual(POST.stale(), [])

    def test_post_run_derivation_does_not_overlap_the_approved_one(self):
        self.assertFalse(set(POST.DERIVED) & set(D.DERIVED))


if __name__ == '__main__':
    unittest.main()
