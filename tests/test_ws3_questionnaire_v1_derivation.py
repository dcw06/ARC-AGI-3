"""WS3 questionnaire runtime: derivation from v3's reviewed stack, notebook inventory, allow-list."""
import hashlib
import json
from pathlib import Path
import unittest

from research.ws3_questionnaire_v1 import schedule as S
from scripts import derive_ws3_questionnaire_v1 as D

ROOT = Path(__file__).resolve().parents[1]
LOCKS = {name: ROOT / f'notebooks/{name}/review-source-lock.json' for name in (
    'evidence-comprehension-v1-review-r3', 'evidence-comprehension-v2-review-r1', 'evidence-comprehension-v3-review-r1')}


def bound(path):
    lock = json.loads(path.read_bytes())
    return {**lock['bindings'], **lock['review_documents']}


class Derivation(unittest.TestCase):
    def test_derived_files_match_the_derivation(self):
        self.assertEqual(D.stale(), [])

    def test_v3_sources_are_the_ones_v3s_launch_bound(self):
        """Every v3 source is bound by v3's lock, except the two test-only diagnostics fixtures: v3's review-document
        list named the v2 fixture files instead (a v3 packaging slip, disclosed in the WS3 review guide). Those two
        are traced instead: they still reproduce from v3's derivation, whose own sources are bound by v2's lock."""
        from scripts import derive_evidence_comprehension_v3 as D3
        v2, v3 = bound(LOCKS['evidence-comprehension-v2-review-r1']), bound(LOCKS['evidence-comprehension-v3-review-r1'])
        unbound = []
        for target in D.DERIVED:
            with self.subTest(target=target):
                source = D.src(target)
                if source in v3:
                    self.assertEqual(hashlib.sha256((ROOT / source).read_bytes()).hexdigest(), v3[source])
                    continue
                unbound.append(source)
                self.assertIn(source, D3.DERIVED)
                self.assertNotIn(source, D3.stale())
                v2_source = D3.src(source)
                self.assertEqual(hashlib.sha256((ROOT / v2_source).read_bytes()).hexdigest(), v2[v2_source])
        self.assertEqual(sorted(unbound), ['tests/ecv3_diagnostics_fixtures.py', 'tests/ecv3_diagnostics_module_fixture.py'])

    def test_reexported_modules_are_the_reviewed_objects(self):
        from research.evidence_comprehension_v1 import service as SV1
        from research.evidence_comprehension_v2 import evidence as E2, schedule as S2
        from research.transition_evidence_v1 import score as TS
        from research.ws3_questionnaire_v1 import evidence as E, score as SC, service as SV
        self.assertIs(S.call_order, S2.call_order)
        self.assertIs(E.RunEvidence, E2.RunEvidence)
        self.assertIs(SC.analyze, TS.analyze)
        self.assertTrue(issubclass(SV.QuestionnaireService, SV1.QuestionnaireService))


class AllowList(unittest.TestCase):
    def test_host_serves_exactly_the_frozen_requests_and_schedule_length(self):
        from research.action_effect_history_v1.service import request_hash
        from research.ws3_questionnaire_v1 import authority, probes as P, service
        frozen, digest = P.load_frozen()
        allowed, served, ceiling = service.frozen_requests()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.assertEqual(set(allowed), {request_hash(P.build_request(contexts[p['context_id']], p))
                                        for p in frozen['probes']})
        self.assertEqual((served, ceiling), (digest, len(S.call_order(frozen))))
        self.assertEqual(ceiling, 5616)
        self.assertEqual(authority.LIMITS['maximum_questionnaire_calls'], ceiling)

    def test_frozen_file_matches_a_fresh_build(self):
        from scripts import build_ws3_questionnaire_v1 as B
        for path, raw in B.outputs(B.build()).items():
            self.assertEqual(raw, path.read_bytes(), path.name)


class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import build_ws3_questionnaire_v1_review as R
        cls.R, cls.names = R, R.inventory()

    def test_shared_files_are_byte_identical_to_what_earlier_launches_ran(self):
        for name, lock in LOCKS.items():
            bindings = json.loads(lock.read_bytes())['bindings']
            for path in (n for n in self.names if n in bindings):
                with self.subTest(lock=name, path=path):
                    self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), bindings[path])

    def test_closure_is_closed_and_carries_every_required_source(self):
        from research.ws3_questionnaire_v1 import authority
        names = set(self.names)
        self.assertLessEqual(authority.REQUIRED_SOURCE, names)
        for name in self.names:
            if name.endswith('.py'):
                self.assertLessEqual(self.R._dependencies(name), names, name)

    def test_every_packaged_file_is_tracked(self):
        self.assertFalse([n for n in self.names if n not in self.R._tracked()])

    def test_packaging_is_identical_with_and_without_incidental_ignored_files(self):
        """Review of 336348e: an extracted archive member present only on the author's machine entered r1's lock.
        The R8 trajectory path is written as a string in the replay script; it must never enter the package."""
        target = ROOT / 'reports/runs/phase4-grounded-action-v1-r8/download/phase4-grounded-action-v1/worker/trajectory.json'
        self.assertNotIn(target.relative_to(ROOT).as_posix(), self.R._tracked())
        existed = target.exists()
        backup = target.with_name(target.name + '.ws3-test-backup')
        try:
            if existed:
                target.rename(backup)
            without = self.R.inventory()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('{}', encoding='utf-8')
            with_file = self.R.inventory()
        finally:
            target.unlink(missing_ok=True)
            if existed:
                backup.rename(target)
        self.assertEqual(with_file, without)
        self.assertNotIn(target.relative_to(ROOT).as_posix(), with_file)

    def test_other_question_sets_are_not_carried(self):
        for name in ('research/evidence_comprehension_v2/probes.json', 'research/evidence_comprehension_v3/probes.json',
                     'research/transition_evidence_v1/fixtures.json'):
            self.assertNotIn(name, self.names)
        self.assertIn('research/ws3_questionnaire_v1/probes.json', self.names)


if __name__ == '__main__':
    unittest.main()
