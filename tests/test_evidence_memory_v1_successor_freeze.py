"""The owner-gated frozen-set path, exercised only with non-withheld test seeds (no withheld seed is drawn, generated,
printed or committed here). Needs the pinned tokenizer files."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from research.evidence_memory_v1 import fidelity as F, stage1 as ST, tokens as TK
from research.evidence_memory_v1.successor import freeze as FZ, plan as PL

ROOT = Path(__file__).resolve().parents[1]
FOUND = TK.locate()
TEST_PREFIX = 'evidence-memory-v1-stage1-freeze-test/'  # deliberately not the withheld prefix
TEST_NONCE = '0123456789abcdef' * 2
TEST_SEED = TEST_PREFIX + TEST_NONCE
TEXT_MARKERS = ('Question', 'Evidence:', 'step 0', 'ACTION', 'Candidates', 'values', 'choice')


@unittest.skipUnless(FOUND, 'the pinned tokenizer files are not available offline')
class OwnerGatedPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = TK.Tokenizer(FOUND)

    def test_a_non_withheld_test_seed_builds_checks_and_reports_counts_only(self):
        raw, summary = FZ.build_checked('A', TEST_SEED, 'withheld', 'withheld', self.tokenizer)
        frozen = json.loads(raw)
        self.assertTrue(summary['passed'])
        self.assertEqual(summary['exclusions'], {k: 0 for k in summary['exclusions']})
        self.assertEqual((summary['trajectories'], summary['scheduled_calls']), (168, len(PL.call_order(frozen))))
        self.assertEqual(frozen['seed_sha256'], hashlib.sha256(TEST_SEED.encode()).hexdigest())
        self.assertEqual((frozen['case_source'], frozen['session']), ('withheld', 'A'))
        self.assertNotEqual(raw, (ROOT / PL.SESSIONS['A']['package'] / 'probes.json').read_bytes())
        text = json.dumps(summary)
        self.assertFalse([m for m in TEXT_MARKERS if m in text])
        self.assertNotIn(TEST_NONCE, text)

    def test_the_owner_command_end_to_end_reaches_the_live_frozen_set_condition(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            commitment = folder / 'seed-commitment.json'
            commitment.write_text(json.dumps({'withheld_seed_sha256': hashlib.sha256(TEST_SEED.encode()).hexdigest()}))
            nonce = folder / 'outside-repository' / 'nonce.txt'
            nonce.parent.mkdir()
            nonce.write_text(TEST_NONCE + '\n')
            out = folder / 'private-checkout'
            stdout = io.StringIO()
            argv = ['freeze', 'withheld', '--session', 'B', '--nonce-file', str(nonce), '--out-root', str(out)]
            with patch.object(FZ, 'SEED_PREFIX', TEST_PREFIX), patch.object(FZ, 'COMMITMENT', commitment), \
                    patch.object(sys, 'argv', argv), contextlib.redirect_stdout(stdout):
                FZ.main()
            printed = stdout.getvalue()
            self.assertNotIn(TEST_NONCE, printed)
            self.assertFalse([m for m in TEXT_MARKERS if m in printed])
            package = PL.SESSIONS['B']['package']
            raw = (out / package / 'probes.json').read_bytes()
            self.assertEqual(json.loads(printed)['frozen_set_sha256'], hashlib.sha256(raw).hexdigest())
            frozen = json.loads(raw)
            # The audit step needs transformers (scripts/audit_evidence_memory_v1_tokens.py); this test stands in for it
            # with pure-Python counts (equal on every Stage 1 request, see the token cross-check) to finish the path.
            rows = [dict(r, prompt_tokens=self.tokenizer.chat_prompt_tokens(req['messages']),
                         pure_python_prompt_tokens=self.tokenizer.chat_prompt_tokens(req['messages']))
                    for r, (_, _, _, req) in zip(PL.audit_rows(frozen), PL.scheduled_requests(frozen))]
            audit = {'schema': PL.AUDIT_SCHEMA, 'session': 'B', 'frozen_set_sha256': hashlib.sha256(raw).hexdigest(),
                     'tokenizer': PL.PINNED_TOKENIZER, 'passed': True, 'requests': rows}
            audit_raw = (json.dumps(audit) + '\n').encode()
            (out / package / 'token-audit.json').write_bytes(audit_raw)
            experiment = PL.experiment_section(frozen, hashlib.sha256(raw).hexdigest(), hashlib.sha256(audit_raw).hexdigest(),
                                               package, frozen['seed_sha256'])
            protocol = {'experiment': experiment}
            self.assertEqual(PL.live_frozen_set_reasons(out, protocol, package), [])
            PL.validate_audit(audit, frozen, hashlib.sha256(raw).hexdigest())
            self.assertEqual(experiment['case_source'], 'withheld')

    def test_no_build_without_a_commitment_or_with_a_different_nonce(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            nonce = folder / 'nonce.txt'
            nonce.write_text(TEST_NONCE)
            argv = ['freeze', 'withheld', '--session', 'A', '--nonce-file', str(nonce), '--out-root', str(folder)]
            with patch.object(sys, 'argv', argv), patch.object(FZ, 'build_checked') as build:
                placeholder = folder / 'placeholder.json'
                placeholder.write_text(json.dumps({'withheld_seed_sha256': PL.SEED_PLACEHOLDER}))
                with patch.object(FZ, 'COMMITMENT', placeholder), self.assertRaises(PermissionError):
                    FZ.main()  # a placeholder commitment: no seed has been drawn
                if json.loads(FZ.COMMITMENT.read_bytes())['withheld_seed_sha256'] == PL.SEED_PLACEHOLDER:
                    with self.assertRaises(PermissionError):
                        FZ.main()  # the repository awaits the fresh draw: nothing builds
                else:
                    with self.assertRaisesRegex(SystemExit, 'does not match'):
                        FZ.main()  # the owner's committed hash (gate 1): any other nonce builds nothing
                retired = folder / 'retired.json'
                matching = hashlib.sha256((FZ.SEED_PREFIX + TEST_NONCE).encode()).hexdigest()
                retired.write_text(json.dumps({'withheld_seed_sha256': matching,
                                               'retired': [{'withheld_seed_sha256': matching}]}))
                with patch.object(FZ, 'COMMITMENT', retired), self.assertRaisesRegex(PermissionError, 'retired'):
                    FZ.main()  # even the matching nonce of a retired draw builds nothing
                other = folder / 'commitment.json'
                other.write_text(json.dumps({'withheld_seed_sha256': 'a' * 64}))
                with patch.object(FZ, 'COMMITMENT', other), self.assertRaisesRegex(SystemExit, 'does not match'):
                    FZ.main()
            build.assert_not_called()
            self.assertFalse((folder / PL.SESSIONS['A']['package']).exists())
            for bad in ('', 'xyz', TEST_NONCE + '0', TEST_NONCE.upper()):
                nonce.write_text(bad)
                with self.assertRaises(ValueError):
                    FZ.seed_from_nonce_file(nonce)

    def test_an_exclusion_condition_refuses_to_write(self):
        real = F.evaluate
        seen = []

        def one_unfaithful(records, memory, expected):
            report = real(records, memory, expected)
            if not seen:
                seen.append(1)
                report = dict(report, faithful=False)
            return report
        with patch.object(F, 'evaluate', one_unfaithful):
            with self.assertRaises(ValueError) as caught:
                FZ.build_checked('A', TEST_SEED, 'withheld', 'withheld', self.tokenizer)
        message = str(caught.exception)
        self.assertIn('"faithful_memory_not_faithful": 1', message)
        self.assertFalse([m for m in TEXT_MARKERS if m in message])

    def test_the_committed_commitment_is_the_owners_recorded_hash(self):
        # Only sha256(seed) is in the repository, matching the custody record. The first draw (October 10, 2026)
        # was retired before execution because the decoding design changed after it (frozen protocol section 5):
        # its record is kept, and it can never be built from again.
        record = json.loads(FZ.COMMITMENT.read_bytes())
        value = record['withheld_seed_sha256']
        custody = json.loads((Path(__file__).resolve().parents[1]
                              / 'reports/evidence_memory_v1_successor/nonce_custody.json').read_bytes())
        first = '7f11432aed195bbd18732abd6cb513024b48e401de17c5fd27e11b17dadfb04b'
        self.assertEqual([(r['draw'], r['withheld_seed_sha256'], r['status'], r['automated_check_failure'], r['executed'])
                          for r in record['retired']], [(1, first, 'retired_before_execution', False, False)])
        (draw1,) = custody['retired_draws']
        self.assertEqual((draw1['withheld_seed_sha256'], draw1['status']), (first, 'retired_before_execution'))
        self.assertEqual({c['printed'] for c in draw1['copy_checks']}, {first})
        self.assertEqual(custody['withheld_seed_sha256'], value)
        self.assertNotEqual(value, first)
        if record['status'] == 'awaiting_fresh_draw':
            self.assertEqual(value, PL.SEED_PLACEHOLDER)
            self.assertEqual((custody['status'], custody['copies_confirmed'], custody['copy_checks']),
                             ('awaiting_fresh_draw', 0, []))
            with self.assertRaises(PermissionError):
                FZ.committed_seed_sha256()
        else:
            self.assertEqual(record['status'], 'committed')
            self.assertTrue(len(value) == 64 and all(c in '0123456789abcdef' for c in value))
            self.assertEqual(FZ.committed_seed_sha256(), value)
            self.assertEqual(custody['status'], 'two_copies_confirmed')
            self.assertEqual({c['printed'] for c in custody['copy_checks']}, {value})
            self.assertEqual(len({c['copy_id'] for c in custody['copy_checks']}), 2)
        self.assertEqual(ST.CASE_SOURCES, ('development_stand_in', 'withheld'))

    def test_the_frozen_text_is_not_edited_after_the_final_design_freeze(self):
        # Frozen protocol section 5: the complete final design was frozen in review snapshots r7, before the fresh
        # draw, and the frozen text is not edited for that draw. Every later review lock binds the same bytes.
        current = hashlib.sha256((ROOT / 'reports/evidence_memory_v1_protocol_v2_frozen.md').read_bytes()).hexdigest()
        for scope in ('evidence-memory-v1-session-a', 'evidence-memory-v1-session-b'):
            for frozen in sorted((ROOT / 'notebooks').glob(scope + '-review-r*')):
                if int(frozen.name.rsplit('-r', 1)[1]) >= 7:
                    lock = json.loads((frozen / 'review-source-lock.json').read_bytes())
                    self.assertEqual(lock['review_documents']['reports/evidence_memory_v1_protocol_v2_frozen.md'],
                                     current, frozen.name)


if __name__ == '__main__':
    unittest.main()
