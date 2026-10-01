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


class CommittedStateRecovery(unittest.TestCase):
    """Fresh-checkout review of r2: a SIGTERM during an atomic write must not discard the committed partial run."""

    def setUp(self):
        import tempfile
        from research.ws3_questionnaire_v1 import evidence as E
        self.E = E
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name) / 'run'
        self.writer = E.RunEvidence(self.folder, 1 << 20)
        self.writer(self.folder / 'run.json', {'calls_recorded': 0, 'status': 'running', 'stop_reason': None})
        for i in range(3):
            self.writer(self.folder / f'calls/{i:05d}.json', {'index': i, 'status': 'answered'})
            self.writer(self.folder / 'run.json', {'calls_recorded': i + 1, 'status': 'running', 'stop_reason': None})

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_clean_run_uses_the_strict_path(self):
        run = self.E.load_verified(self.folder)
        self.assertNotIn('evidence_recovery', run)
        self.assertEqual(len(run['calls']), 3)

    def test_interrupted_writes_recover_the_committed_state(self):
        cases = {
            'half-written manifest': lambda f: (f / 'manifest.json.tmp').write_bytes(b'{"version": "evid'),
            'half-written index': lambda f: (f / 'run.json.tmp').write_bytes(b'{"calls_rec'),
            'appended but uncommitted log line': lambda f: open(f / 'calls.jsonl', 'ab').write(b'{"index": 3, "sta'),
        }
        for label, damage in cases.items():
            with self.subTest(label):
                self.setUp()
                damage(self.folder)
                run = self.E.load_verified(self.folder)
                self.assertEqual((run['status'], run['stop_reason'], run['calls_recorded']),
                                 ('incomplete', 'interrupted_evidence', 3))
                self.assertIn('evidence_recovery', run)
                self.tearDown()

    def test_the_fresh_checkout_state_index_one_call_behind(self):
        """The call was logged and committed; the kill came while the index was being replaced."""
        self.writer(self.folder / 'calls/00003.json', {'index': 3, 'status': 'answered'})
        (self.folder / 'manifest.json.tmp').write_bytes(b'{"partial')
        run = self.E.load_verified(self.folder)
        self.assertEqual((run['calls_recorded'], run['evidence_recovery']['index_calls_recorded']), (4, 3))
        self.assertEqual([c['index'] for c in run['calls']], [0, 1, 2, 3])

    def test_an_index_one_step_ahead_of_its_manifest_is_used_for_metadata_only(self):
        """The retained fresh-clone failure: run.json replaced, then the kill during manifest.json.tmp."""
        from research.evidence_comprehension_v2.evidence import atomic_write, encode
        atomic_write(self.folder / 'run.json', encode({'calls_recorded': 3, 'status': 'running', 'stop_reason': None,
                                                       'phase_reached': 'withheld_pass_1'}))
        (self.folder / 'manifest.json.tmp').write_bytes(b'{"partial')
        run = self.E.load_verified(self.folder)
        self.assertFalse(run['evidence_recovery']['index_committed'])
        self.assertEqual((run['status'], run['calls_recorded'], len(run['calls'])), ('incomplete', 3, 3))

    def test_an_interrupted_first_append_recovers_an_empty_committed_log(self):
        """Review of 95aef4f: the kill lands after calls.jsonl is created but before the manifest records any call."""
        from research.evidence_comprehension_v2.evidence import encode
        line = encode({'index': 0, 'status': 'answered'}) + b'\n'
        for label, written in (('partial first line', line[:7]), ('whole first line', line)):
            with self.subTest(label):
                self.tearDown()
                self.tmp = __import__('tempfile').TemporaryDirectory()
                self.folder = Path(self.tmp.name) / 'run'
                writer = self.E.RunEvidence(self.folder, 1 << 20)
                writer(self.folder / 'run.json', {'calls_recorded': 0, 'status': 'running', 'stop_reason': None})
                (self.folder / 'calls.jsonl').write_bytes(written)
                (self.folder / 'manifest.json.tmp').write_bytes(b'{"partial')
                run = self.E.load_verified(self.folder)
                self.assertEqual((run['status'], run['stop_reason'], run['calls_recorded'], run['calls']),
                                 ('incomplete', 'interrupted_evidence', 0, []))
                self.assertEqual(run['evidence_recovery']['ignored_uncommitted_log_bytes'], len(written))
                self.assertTrue(run['evidence_recovery']['index_committed'])

    def test_tampering_or_unexpected_files_are_still_refused(self):
        raw = (self.folder / 'calls.jsonl').read_bytes()
        (self.folder / 'calls.jsonl').write_bytes(raw.replace(b'answered', b'timed_out', 1))
        with self.assertRaises(self.E.EvidenceError):
            self.E.load_verified(self.folder)
        self.tearDown()
        self.setUp()
        (self.folder / 'extra.json').write_bytes(b'{}')
        with self.assertRaises(self.E.EvidenceError):
            self.E.load_verified(self.folder)


if __name__ == '__main__':
    unittest.main()
