"""Session B launches only after session A is technically complete (protocol v2 frozen, section 12; owner decision of
October 9, 2026), enforced in session B's launch tooling (research/evidence_memory_v1/successor/session_order.py).

Every record, approval, reservation and claim here is a fabricated fixture in a temporary directory; nothing is real,
submitted or retained. CPU only; no GPU, provider call or network.
"""
import contextlib
import copy
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from research.evidence_memory_v1.successor import plan as PL, session_order as SO
from tests.test_evidence_memory_v1_successor import (ROOT, SESSIONS, NOTEBOOKS, fabricated_session_a_evaluation,
                                                     gated_fixture, put_session_a_record)

LAUNCH = {label: importlib.import_module(spec['module'] + '.launch') for label, spec in PL.SESSIONS.items()}
VALID = fabricated_session_a_evaluation()


def fixture_root(folder, record=VALID, named=None):
    """A minimal B checkout: session A's protocol, the retained record (unless None) and B's compute authorization
    naming `named` (default: the record's SHA-256)."""
    root = Path(folder)
    protocol = PL.SESSIONS['A']['package'] + '/protocol.json'
    (root / protocol).parent.mkdir(parents=True, exist_ok=True)
    (root / protocol).write_bytes((ROOT / protocol).read_bytes())
    digest = put_session_a_record(root, record) if record is not None else None
    compute = SESSIONS['B'].COMPUTE
    (root / compute).parent.mkdir(parents=True, exist_ok=True)
    (root / compute).write_text(json.dumps({SO.FIELD: digest if named is None else named}), encoding='utf-8')
    return root


def changed(**edits):
    """VALID with dotted-path edits applied ('analysis.invalid_by_pass.pass_2.rule_met': False)."""
    record = copy.deepcopy(VALID)
    for path, value in edits.items():
        *parents, last = path.split('.')
        node = record
        for key in parents:
            node = node[key]
        node[last] = value
    return record


class SessionOrderRecord(unittest.TestCase):
    def reasons(self, record=VALID, named=None):
        with tempfile.TemporaryDirectory() as folder:
            return SO.reasons(fixture_root(folder, record, named), SESSIONS['B'].COMPUTE)

    def test_a_technically_complete_live_valid_record_bound_by_hash_passes(self):
        self.assertEqual(VALID['analysis']['technical_status'], 'session_technically_valid')
        self.assertEqual(set(VALID['analysis']['invalid_by_pass']), {'pass_1', 'pass_2'})
        self.assertEqual(self.reasons(), [])

    def test_an_absent_record_refuses(self):
        found = self.reasons(record=None, named='0' * 64)
        self.assertEqual(len(found), 1)
        self.assertIn('session A technical evaluation absent', found[0])
        self.assertIn(SO.RECORD, found[0])

    def test_a_hash_mismatch_or_an_unnamed_hash_refuses(self):
        found = self.reasons(named='0' * 64)
        self.assertEqual(len(found), 1)
        self.assertIn('does not match', found[0])
        for named in ('', 'not-a-sha', 'A' * 64, 64):
            with tempfile.TemporaryDirectory() as folder:
                root = fixture_root(folder)
                (root / SESSIONS['B'].COMPUTE).write_text(json.dumps({SO.FIELD: named}), encoding='utf-8')
                found = SO.reasons(root, SESSIONS['B'].COMPUTE)
                self.assertEqual(len(found), 1, named)
                self.assertIn(f'does not name {SO.FIELD}', found[0])
        with tempfile.TemporaryDirectory() as folder:  # a record changed after it was named
            root = fixture_root(folder)
            path = root / SO.RECORD
            path.write_bytes(path.read_bytes() + b' ')
            self.assertIn('does not match', ' '.join(SO.reasons(root, SESSIONS['B'].COMPUTE)))
        with tempfile.TemporaryDirectory() as folder:  # no compute authorization at all
            root = fixture_root(folder)
            (root / SESSIONS['B'].COMPUTE).unlink()
            self.assertIn('compute authorization unreadable', ' '.join(SO.reasons(root, SESSIONS['B'].COMPUTE)))

    def test_a_session_that_is_not_technically_complete_refuses(self):
        cases = {
            'not complete': {'technically_complete': False},
            'lifecycle failed': {'lifecycle_passed': False, 'lifecycle_errors': ['lifecycle: study: transport']},
            'call errors': {'call_errors': ['call 7: request hash differs']},
            'evidence not verified': {'run_evidence': {'verified': False, 'error': 'ValueError: manifest'}},
            'recovered evidence': {'run_evidence': {'verified': True, 'recovered': True}},
            'incomplete run': {'run.status': 'incomplete', 'run.stop_reason': 'admission_cutoff'},
            'incomplete gate': {'gate_status': 'incomplete'},
        }
        for name, edits in cases.items():
            found = self.reasons(changed(**edits))
            self.assertIn('session A is not technically complete', found, name)

    def test_a_session_invalid_in_any_pass_refuses(self):
        pass_2 = VALID['analysis']['invalid_by_pass']['pass_2']
        arm = sorted(pass_2['by_arm'])[0]
        scheduled = VALID['analysis']['answers']['pass_2']['scheduled']
        cases = {
            'repeat pass over the 2% rule': {'analysis.invalid_by_pass.pass_2.rule_met': False,
                                             f'analysis.invalid_by_pass.pass_2.by_arm.{arm}.rule_met': False,
                                             'analysis.invalid_rule_met': False,
                                             'analysis.technical_status': 'session_technically_invalid_outputs'},
            'one arm over the rule only': {f'analysis.invalid_by_pass.pass_1.by_arm.{arm}.rule_met': False},
            'status not valid': {'analysis.technical_status': 'session_technically_invalid_outputs'},
            'a repeat call unanswered': {'analysis.answers.pass_2.answered': scheduled - 1},
            'the repeat pass missing': {'analysis.invalid_by_pass': {
                'pass_1': VALID['analysis']['invalid_by_pass']['pass_1']}},
            'incomplete': {'analysis.completeness': {'withheld': 'incomplete'}},
            'another session': {'analysis.session': 'B'},
            'no technical report': {'analysis': None},
        }
        for name, edits in cases.items():
            found = self.reasons(changed(**edits))
            self.assertIn('session A is not technically valid in every pass', found, name)

    def test_only_session_as_live_withheld_evaluation_of_its_registered_set_counts(self):
        cases = {
            'rehearsal mode': ({'mode': 'rehearsal'}, 'not live'),
            'development stand-in': ({'case_source': 'development_stand_in'}, 'not withheld'),
            'another session': ({'session': 'B', 'package': PL.SESSIONS['B']['package']}, "not session A's"),
            'another frozen set': ({'frozen_set_sha256': '0' * 64}, 'registered frozen set'),
        }
        for name, (edits, expected) in cases.items():
            found = self.reasons(changed(**edits))
            self.assertTrue(any(expected in r for r in found), (name, found))
        for raw in (b'not json', b'[]'):
            with tempfile.TemporaryDirectory() as folder:
                root = fixture_root(folder, record=raw)
                self.assertIn('unreadable', ' '.join(SO.record_reasons(root)))

    def test_the_record_check_reads_no_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = fixture_root(folder)
            (root / SESSIONS['B'].COMPUTE).unlink()
            self.assertEqual(SO.record_reasons(root), [])


class SessionBLaunchTooling(unittest.TestCase):
    """The condition lives in session B's launch tooling only: the launch package (launch-build, write_package,
    submit) and the claim. The per-scope live gate (binding.require_live) and session A's tooling are unchanged.
    Each case is a fresh fabricated checkout, because the fabricated approvals bind the compute authorization."""

    @contextlib.contextmanager
    def enabled(self, label='B', **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            put, patches = gated_fixture(root, label, **kwargs)
            for p in patches:
                p.start()
            try:
                yield root
            finally:
                for p in reversed(patches):
                    p.stop()

    REFUSED = {
        'absent record': {'session_a_record': False, 'named': '0' * 64},
        'record not named': {'session_a_record': False},
        'hash mismatch': {'named': '0' * 64},
        'not technically complete': {'session_a_record': changed(technically_complete=False)},
        'incomplete run': {'session_a_record': changed(**{'run.status': 'incomplete'})},
        'invalid repeat pass': {'session_a_record': changed(**{'analysis.invalid_by_pass.pass_2.rule_met': False})},
        'rehearsal evaluation': {'session_a_record': changed(mode='rehearsal')},
    }

    def test_the_launch_package_is_built_only_after_session_a_is_technically_complete(self):
        B, N, L = SESSIONS['B'], NOTEBOOKS['B'], LAUNCH['B']
        with self.enabled() as root:  # complete, live, valid in every pass and bound by hash: built
            self.assertIn('kernel-metadata.json', N.launch_artifacts(root))
            lock = L.write_package(root, root / 'package')
            self.assertTrue(lock['attempt_id'].startswith('em1b-'))
        for name, kwargs in self.REFUSED.items():
            with self.enabled(**kwargs) as root:
                with self.assertRaises(B.LiveRefused, msg=name) as caught:
                    N.launch_artifacts(root)
                self.assertTrue(caught.exception.reasons, name)
                self.assertNotIn('authorization:', ' '.join(caught.exception.reasons), name)  # not the live gate
                with self.assertRaises(B.LiveRefused, msg=name):
                    L.write_package(root, root / 'package')
                self.assertFalse((root / 'package').exists(), name)
                protocol, execution = B.require_live(root)  # the per-scope live gate does not look at session A
                self.assertTrue(execution['attempt_id'].startswith('em1b-'), name)
        with self.enabled(session_a_record=False, named='0' * 64) as root:
            with self.assertRaises(B.LiveRefused) as caught:
                N.launch_artifacts(root)
            self.assertIn('session A technical evaluation absent', ' '.join(caught.exception.reasons))

    def test_submission_and_claim_refuse_and_spend_nothing(self):
        B, L = SESSIONS['B'], LAUNCH['B']

        class Backend:
            pushed = 0

            def push(self, folder):
                Backend.pushed += 1
                return {'ref': 'fixture/em1', 'versionNumber': 1}

        for name, kwargs in self.REFUSED.items():
            with self.enabled(**kwargs) as root:
                folder = root / 'package'
                folder.mkdir()
                with self.assertRaises(L.LaunchRefused, msg=name):
                    L.submit(root, folder, Backend())
                self.assertEqual(Backend.pushed, 0, name)
                self.assertFalse((root / B.RECEIPT).exists(), name)  # the attempt is not spent
                (root / B.CLAIM).unlink()
                with self.assertRaises(L.LaunchRefused, msg=name):
                    L.claim(root)
                self.assertFalse((root / B.CLAIM).exists(), name)  # never claimed
        with self.enabled() as root:
            (root / B.CLAIM).unlink()
            self.assertTrue(L.claim(root).startswith('em1b-'))  # complete and bound: the fixture claim is made
            self.assertTrue((root / B.CLAIM).exists())

    def test_session_a_tooling_never_reads_the_condition(self):
        B, N, L = SESSIONS['A'], NOTEBOOKS['A'], LAUNCH['A']
        with self.enabled('A') as root:
            self.assertFalse((root / SO.RECORD).exists())
            self.assertIn('kernel-metadata.json', N.launch_artifacts(root))
            (root / B.CLAIM).unlink()
            self.assertTrue(L.claim(root).startswith('em1a-'))
        for name in ('notebook.py', 'launch.py', 'binding.py'):
            self.assertNotIn('session_order', (ROOT / PL.SESSIONS['A']['package'] / name).read_text(encoding='utf-8'))
        self.assertNotIn('session_order', (ROOT / 'scripts/evidence_memory_v1_session_a_package.py').read_text(
            encoding='utf-8'))
        self.assertNotIn('session_order', (ROOT / PL.SESSIONS['B']['package'] / 'binding.py').read_text(
            encoding='utf-8'))  # B's per-scope live gate is unchanged too

    def test_session_order_source_is_bound_by_session_bs_review_lock(self):
        self.assertIn(SO.__name__.replace('.', '/') + '.py', NOTEBOOKS['B'].source_names(ROOT))
        self.assertNotIn(SO.__name__.replace('.', '/') + '.py', NOTEBOOKS['A'].source_names(ROOT))
        lock = json.loads((ROOT / SESSIONS['B'].review_lock(ROOT)).read_bytes())
        source = 'research/evidence_memory_v1/successor/session_order.py'
        self.assertEqual(lock['bindings'][source], hashlib.sha256((ROOT / source).read_bytes()).hexdigest())

    def test_launch_build_in_this_checkout_names_the_missing_session_a_record(self):
        self.assertFalse((ROOT / SO.RECORD).exists())  # no session-A record exists in the public checkout
        script = importlib.import_module('scripts.evidence_memory_v1_session_b_package')
        out = io.StringIO()
        with patch.object(sys, 'argv', ['package', 'launch-build']), contextlib.redirect_stdout(out):
            self.assertEqual(script.main(), 1)
        text = out.getvalue()
        self.assertIn('LIVE_ENABLED is False', text)
        self.assertIn('session A technical evaluation absent', text)
        script_a = importlib.import_module('scripts.evidence_memory_v1_session_a_package')
        out = io.StringIO()
        with patch.object(sys, 'argv', ['package', 'launch-build']), contextlib.redirect_stdout(out):
            self.assertEqual(script_a.main(), 1)
        self.assertNotIn('session A technical evaluation', out.getvalue())


if __name__ == '__main__':
    unittest.main()
