"""Evidence comprehension v2 runtime: derivation from v1's reviewed stack, notebook inventory, allow-list, call log."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.evidence_comprehension_v2 import evidence as E
from research.evidence_comprehension_v2 import schedule as S
from scripts import derive_evidence_comprehension_v2 as D

ROOT = Path(__file__).resolve().parents[1]
V1_LOCK = ROOT / 'notebooks/evidence-comprehension-v1-review-r3/review-source-lock.json'


class Derivation(unittest.TestCase):
    def test_derived_files_match_the_derivation(self):
        self.assertEqual(D.stale(), [])

    def test_every_rule_matches_exactly_as_declared(self):
        for target in D.DERIVED:
            with self.subTest(target=target):
                D.derive_one(target)  # raises on any count mismatch or leftover v1 reference

    def test_v1_sources_are_the_ones_the_v1_launch_bound(self):
        bindings = json.loads(V1_LOCK.read_bytes())
        bound = {**bindings['bindings'], **bindings['review_documents']}
        for target, (source, _) in D.DERIVED.items():
            with self.subTest(source=source):
                self.assertIn(source, bound)
                self.assertEqual(hashlib.sha256((ROOT / source).read_bytes()).hexdigest(), bound[source])

    def test_reexported_modules_are_v1_objects(self):
        from research.evidence_comprehension_v1 import schedule as S1, service as SV1, transport as T1
        from research.evidence_comprehension_v2 import service as SV2, transport as T2
        self.assertIs(S.Admission, S1.Admission)
        self.assertIs(S.admit, S1.admit)
        self.assertEqual(S.PER_CALL_BOUND_SECONDS, S1.PER_CALL_BOUND_SECONDS)
        self.assertIs(T2.CancellableTransport, T1.CancellableTransport)
        self.assertIs(SV2.ProxyService, SV1.ProxyService)
        self.assertIs(SV2.validate_server_config, SV1.validate_server_config)
        self.assertTrue(issubclass(SV2.QuestionnaireService, SV1.QuestionnaireService))


class AllowList(unittest.TestCase):
    def test_host_serves_exactly_the_v2_requests_and_schedule_length(self):
        from research.action_effect_history_v1.service import request_hash
        from research.evidence_comprehension_v2 import authority, probes as P, service
        frozen, digest = P.load_frozen()
        allowed, served_digest, ceiling = service.frozen_requests()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.assertEqual(set(allowed), {request_hash(P.build_request(contexts[p['context_id']], p))
                                        for p in frozen['probes']})
        self.assertEqual(served_digest, digest)
        self.assertEqual(ceiling, len(S.call_order(frozen)))
        self.assertEqual(authority.LIMITS['maximum_questionnaire_calls'], ceiling)

    def test_call_order_is_the_frozen_schedule(self):
        from research.evidence_comprehension_v2 import probes as P
        frozen, _ = P.load_frozen()
        order = S.call_order(frozen)
        self.assertEqual([o[2] for o in order], [i for b in frozen['schedule'] for i in b['probe_ids']])
        self.assertEqual(list(dict.fromkeys(o[0] for o in order)), list(S.PHASES))
        broken = {**frozen, 'schedule': list(reversed(frozen['schedule']))}
        with self.assertRaises(ValueError):
            S.call_order(broken)


class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import build_evidence_comprehension_v2_review as R
        cls.names = R.inventory()

    def test_shared_files_are_byte_identical_to_the_files_v1_ran_live(self):
        bindings = json.loads(V1_LOCK.read_bytes())['bindings']
        shared = [n for n in self.names if n in bindings]
        self.assertGreater(len(shared), 200)
        for name in shared:
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), bindings[name], name)

    def test_closure_contains_the_v2_runtime_and_every_required_source(self):
        from research.evidence_comprehension_v2 import authority
        self.assertLessEqual(authority.REQUIRED_SOURCE, set(self.names))
        for module in ('supervisor', 'worker', 'host', 'monitor', 'runner', 'service', 'fake_server', 'evidence'):
            self.assertIn(f'research/evidence_comprehension_v2/{module}.py', self.names)
        self.assertIn('research/evidence_comprehension_v2/probes.json', self.names)

    def test_every_python_file_in_the_closure_resolves_its_repository_imports(self):
        from scripts import build_evidence_comprehension_v2_review as R
        names = set(self.names)
        for name in self.names:
            if name.endswith('.py'):
                self.assertLessEqual(R._dependencies(name), names, name)


class CallLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name) / 'run'
        self.writer = E.RunEvidence(self.folder, 4096)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, n):
        self.writer(self.folder / 'run.json', {'calls_recorded': 0})
        for i in range(n):
            self.writer(self.folder / f'calls/{i:05d}.json', {'index': i, 'status': 'answered'}, reserve_bytes=256)
            self.writer(self.folder / 'run.json', {'calls_recorded': i + 1})

    def test_round_trip(self):
        self.write(5)
        run = E.load_verified(self.folder)
        self.assertEqual([c['index'] for c in run['calls']], list(range(5)))
        self.assertEqual({p.name for p in self.folder.iterdir()}, {'run.json', 'calls.jsonl', 'manifest.json'})

    def test_out_of_order_or_reserved_writes_are_refused(self):
        self.write(1)
        for name in ('calls/00003.json', 'calls/00000.json', 'manifest.json', 'calls.jsonl'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.writer(self.folder / name, {'index': 3})

    def test_a_crash_between_log_and_manifest_is_detected(self):
        self.write(3)
        with (self.folder / 'calls.jsonl').open('ab') as stream:  # appended, manifest never updated
            stream.write(E.encode({'index': 3}) + b'\n')
        with self.assertRaises(E.EvidenceError):
            E.load_verified(self.folder)

    def test_torn_or_edited_lines_are_detected(self):
        self.write(3)
        raw = (self.folder / 'calls.jsonl').read_bytes()
        for label, data in (('torn', raw[:-5]), ('edited', raw.replace(b'answered', b'timed_out', 1))):
            with self.subTest(label):
                (self.folder / 'calls.jsonl').write_bytes(data)
                with self.assertRaises(E.EvidenceError):
                    E.load_verified(self.folder)

    def test_budget_keeps_room_for_the_final_index(self):
        with self.assertRaises(E.StorageExhausted):
            self.write(200)
        calls = E.load_unverified_calls(self.folder)
        self.assertTrue(0 < len(calls) < 200)
        self.writer(self.folder / 'run.json', {'calls_recorded': len(calls)})
        self.assertEqual(len(E.load_verified(self.folder)['calls']), len(calls))

    def test_consistent_forgeries_verify_but_change_content(self):
        self.write(3)
        E.forge(self.folder, 'calls/00001.json', lambda v: v.update(status='rejected'))
        self.assertEqual(E.load_verified(self.folder)['calls'][1]['status'], 'rejected')
        E.truncate(self.folder, 2)
        with self.assertRaises(E.EvidenceError):  # the index still counts three calls
            E.load_verified(self.folder)
        E.forge(self.folder, 'run.json', lambda v: v.update(calls_recorded=2))
        self.assertEqual(len(E.load_verified(self.folder)['calls']), 2)


if __name__ == '__main__':
    unittest.main()
