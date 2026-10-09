"""Feedback-action v1 token audit: every request form is enumerated from the real offline engine (both sessions) and
the committed exact audit (pinned tokenizer, research/feedback_action_v1/token_audit.json) is bound to those forms."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.feedback_action_v1 import adapter as AD, token_audit as TA
from research.feedback_action_v1.live.policy import validate_policy_request

LABELS_PER_CANDIDATE = len(TA.WORST_TEXT) + len(TA.PROBE_TEXT)


class Forms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = TA.forms()

    def test_every_form_is_enumerated_and_valid(self):
        labels = [(label, game, arm) for label, game, arm, _ in self.rows]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels[0], ('canary', None, None))
        games = {'s5i5-18d95033', 'ls20-9607627b', 'sk48-d8078629'}
        for game in games:
            for arm in AD.ARMS:
                self.assertIn(('first', game, arm), labels)
                self.assertIn(('steady_largest', game, arm), labels)
            for name in list(TA.WORST_TEXT) + list(TA.PROBE_TEXT):
                self.assertIn((f'steady_worst_carried_{name}', game, 'candidate'), labels)
        self.assertEqual(len(labels), 1 + 3 * 2 * 2 + 3 * LABELS_PER_CANDIDATE)
        for label, game, arm, request in self.rows[1:]:
            self.assertEqual(validate_policy_request(request), arm, (label, game))

    def test_worst_carried_statement_is_at_the_caps(self):
        for label, game, arm, request in self.rows:
            if label.startswith('steady_worst_carried'):
                carried = json.loads(request['messages'][1]['content'])[AD.PREVIOUS_FIELD]
                self.assertEqual((len(carried['hypothesis']), len(carried['if_different'])),
                                 (AD.TEXT_LIMIT, AD.TEXT_LIMIT))

    def test_committed_exact_audit_is_bound_to_these_forms(self):
        if not TA.OUTPUT.exists():
            self.skipTest('exact audit not produced yet (pinned stack)')
        audit = json.loads(TA.OUTPUT.read_bytes())
        self.assertEqual(audit['versions'], TA.PINNED)
        described = TA.describe(self.rows)
        self.assertEqual([(r['label'], r['game_id'], r['arm'], r['request_sha256']) for r in audit['forms']],
                         [(r['label'], r['game_id'], r['arm'], r['request_sha256']) for r in described])
        self.assertTrue(audit['all_forms_within_limits'])
        self.assertTrue(all(type(r['prompt_tokens']) is int and 0 < r['prompt_tokens'] <= TA.PROMPT_CEILING
                            for r in audit['forms']))
        manifest = json.loads(Path(TA.ROOT / 'certification/phase4_integrated_v2/tokenizer_manifest.json').read_bytes())
        self.assertEqual(audit['tokenizer_files'], manifest['files'])


class Completions(unittest.TestCase):
    def test_longest_responses_are_schema_valid_for_both_options(self):
        from research.feedback_action_v1.live import owner_gates as G
        gates = json.loads(G.GATES.read_bytes())
        gates['free_text_format']['decision'] = 'ascii_only'
        for option, text in TA.WORST_TEXT.items():
            value = TA.candidate_response(text, 'changed_then_returned', 'different_state_from_now', 'retained', False)
            for name, options in TA.FORMATS.items():
                serialized = json.dumps(value, ensure_ascii=False, **options)
                decision = AD.parse({'content': serialized, 'finish_reason': 'stop'}, [6], 'candidate')
                self.assertIsNotNone(decision['action'], (option, name))
                self.assertIsNotNone(decision['procedure'], decision['procedure_error'])
                problem = G.free_text_problem(decision['procedure'], gates)
                self.assertEqual(problem is None, option == 'ascii_only', (option, problem))


class PinnedOnly(unittest.TestCase):
    def test_counting_refuses_outside_the_pinned_stack(self):
        if TA.pinned_versions() == TA.PINNED:
            self.skipTest('pinned stack present: the audit can run here')
        with tempfile.TemporaryDirectory() as tmp:
            forms = Path(tmp) / 'forms.json'
            forms.write_text('[]')
            out = Path(tmp) / 'audit.json'
            with self.assertRaises(SystemExit) as caught:
                TA.tokenize(forms, TA.ROOT / '.cache/phase4-tokenizer', out)
            self.assertIn('TODO(pinned tokenizer)', str(caught.exception))
            self.assertFalse(out.exists())  # no counts were written


if __name__ == '__main__':
    unittest.main()
