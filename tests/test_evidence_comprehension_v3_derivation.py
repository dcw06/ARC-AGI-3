"""Evidence comprehension v3 runtime: derivation from v2's reviewed stack, notebook inventory, allow-list."""
import hashlib
import json
from pathlib import Path
import unittest

from research.evidence_comprehension_v3 import schedule as S
from scripts import derive_evidence_comprehension_v3 as D

ROOT = Path(__file__).resolve().parents[1]
V1_LOCK = ROOT / 'notebooks/evidence-comprehension-v1-review-r3/review-source-lock.json'
V2_LOCK = ROOT / 'notebooks/evidence-comprehension-v2-review-r1/review-source-lock.json'


def bound(path):
    lock = json.loads(path.read_bytes())
    return {**lock['bindings'], **lock['review_documents']}


class Derivation(unittest.TestCase):
    def test_derived_files_match_the_derivation(self):
        self.assertEqual(D.stale(), [])

    def test_v2_sources_are_the_ones_v2s_launch_bound(self):
        v2 = bound(V2_LOCK)
        for target in D.DERIVED:
            with self.subTest(target=target):
                source = D.src(target)
                self.assertIn(source, v2)
                self.assertEqual(hashlib.sha256((ROOT / source).read_bytes()).hexdigest(), v2[source])

    def test_reexported_modules_are_the_reviewed_objects(self):
        from research.evidence_comprehension_v1 import service as SV1
        from research.evidence_comprehension_v2 import evidence as E2, schedule as S2
        from research.evidence_comprehension_v3 import evidence as E3, service as SV3
        self.assertIs(S.call_order, S2.call_order)
        self.assertIs(S.Admission, S2.Admission)
        self.assertIs(E3.RunEvidence, E2.RunEvidence)
        self.assertIs(E3.load_verified, E2.load_verified)
        self.assertTrue(issubclass(SV3.QuestionnaireService, SV1.QuestionnaireService))
        self.assertIs(SV3.validate_server_config, SV1.validate_server_config)


class AllowList(unittest.TestCase):
    def test_host_serves_exactly_the_v3_requests_and_schedule_length(self):
        from research.action_effect_history_v1.service import request_hash
        from research.evidence_comprehension_v3 import authority, probes as P, service
        frozen, digest = P.load_frozen()
        allowed, served, ceiling = service.frozen_requests()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.assertEqual(set(allowed), {request_hash(P.build_request(contexts[p['context_id']], p))
                                        for p in frozen['probes']})
        self.assertEqual(served, digest)
        self.assertEqual(ceiling, len(S.call_order(frozen)))
        self.assertEqual(ceiling, 6054)
        self.assertEqual(authority.LIMITS['maximum_questionnaire_calls'], ceiling)


class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import build_evidence_comprehension_v3_review as R
        cls.R, cls.names = R, R.inventory()

    def test_shared_files_are_byte_identical_to_what_v1_and_v2_ran_live(self):
        for lock in (V1_LOCK, V2_LOCK):
            bindings = json.loads(lock.read_bytes())['bindings']
            for name in (n for n in self.names if n in bindings):
                with self.subTest(lock=lock.parent.name, name=name):
                    self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), bindings[name])

    def test_closure_is_closed_and_carries_every_required_source(self):
        from research.evidence_comprehension_v3 import authority
        self.assertLessEqual(authority.REQUIRED_SOURCE, set(self.names))
        names = set(self.names)
        for name in self.names:
            if name.endswith('.py'):
                self.assertLessEqual(self.R._dependencies(name), names, name)

    def test_v2_question_set_is_not_needed_or_carried(self):
        self.assertNotIn('research/evidence_comprehension_v2/probes.json', self.names)
        self.assertIn('research/evidence_comprehension_v3/probes.json', self.names)


if __name__ == '__main__':
    unittest.main()
