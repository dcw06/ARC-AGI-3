"""Feedback-action v1 token audit: every request form is enumerated from the real offline engine; exact counting is
refused outside the pinned tokenizer stack (TODO for the main session's pinned environment)."""
import json
import unittest

from research.feedback_action_v1 import adapter as AD, token_audit as TA
from research.feedback_action_v1.live.policy import validate_policy_request


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
            for name in TA.WORST_TEXT:
                self.assertIn((f'steady_worst_carried_{name}', game, 'candidate'), labels)
        self.assertEqual(len(labels), 1 + 3 * 2 * 2 + 3 * len(TA.WORST_TEXT))
        for label, game, arm, request in self.rows[1:]:
            self.assertEqual(validate_policy_request(request), arm, (label, game))

    def test_worst_carried_statement_is_at_the_caps(self):
        for label, game, arm, request in self.rows:
            if label.startswith('steady_worst_carried'):
                carried = json.loads(request['messages'][1]['content'])[AD.PREVIOUS_FIELD]
                self.assertEqual((len(carried['hypothesis']), len(carried['if_different'])),
                                 (AD.TEXT_LIMIT, AD.TEXT_LIMIT))

    def test_described_rows(self):
        rows = TA.describe(self.rows)
        self.assertTrue(all(len(r['request_sha256']) == 64 and r['request_bytes'] > 0 for r in rows))
        self.assertEqual({r['max_tokens'] for r in rows if r['arm'] == 'candidate'}, {AD.CANDIDATE_MAX_TOKENS})


class Completions(unittest.TestCase):
    def test_longest_completions_are_schema_valid(self):
        texts = TA.longest_completions()
        for arm, rows in texts.items():
            for text in rows:
                decision = AD.parse({'content': text, 'finish_reason': 'stop'}, [6], arm)
                self.assertIsNotNone(decision['action'], (arm, text[:60]))
                if arm == 'candidate':
                    self.assertIsNotNone(decision['procedure'], decision['procedure_error'])


class PinnedOnly(unittest.TestCase):
    def test_counting_refuses_outside_the_pinned_stack(self):
        if TA.pinned_versions() == TA.PINNED:
            self.skipTest('pinned stack present: the audit can run here')
        with self.assertRaises(SystemExit) as caught:
            TA.tokenize(TA.ROOT / '.cache/phase4-tokenizer')
        self.assertIn('TODO(pinned tokenizer)', str(caught.exception))
        self.assertFalse(TA.OUTPUT.exists())  # no counts were written


if __name__ == '__main__':
    unittest.main()
