import copy
import unittest
from research.conditional_transfer_v1 import fixtures as FX, writer as W, schema as S, render as R, selection as SE, score as SC, shortcuts as SH
from research.evidence_memory_v1.tokens import Tokenizer


class Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = Tokenizer()

    def test_final_rendered_token_caps_and_completion(self):
        for f in FX.FAMILIES:
            for g in (0, 1, 2, 3, 4, 5):
                c = FX.build(f, g, 24)
                store = W.write(c)
                for cap in S.CEILINGS:
                    for arm in S.ARMS:
                        selected = SE.select(c, store, arm, cap, self.tokenizer)
                        for task in S.TASKS:
                            req = R.request(c, task, selected['items'], selected['memory'])
                            self.assertLessEqual(self.tokenizer.chat_prompt_tokens(req['messages']), cap)
                            out = SC.scripted_reader(req)
                            self.assertLessEqual(len(self.tokenizer.encode(out)), S.OUTPUT_CAP)
                            p, fs = SC.parse_request(req)
                            self.assertTrue(SC.score(out, task, SC.judge(fs, p['rule'], p['target'], task), R.allowed_ids(req))['correct'])

    def test_atomic_correction_survives_when_group_fits(self):
        c = FX.build('contradiction', 1, 24)
        store = W.write(c)
        selected = SE.select(c, store, 'conditional_memory', 1536, self.tokenizer)
        rule = [r for r in selected['items'] if r['action']['action_id'] == 6][0]
        self.assertTrue(rule['supporting_record_ids'])
        self.assertTrue(rule['contradictory_record_ids'])
        req = R.request(c, 'transfer', selected['items'], True)
        self.assertEqual(S.validate_response(SC.scripted_reader(req), 'transfer', R.allowed_ids(req))['answer'], 'contradicted')

    def test_hidden_labels_cannot_change_selection(self):
        c = FX.build('appearance_match', 2, 8)
        altered = copy.deepcopy(c)
        altered.update(family='secret-family', group='secret-group', split='secret-split', evaluator_only={'keys': 'do not retrieve'})
        for arm in S.ARMS:
            self.assertEqual(SE.select(c, W.write(c), arm, 1536, self.tokenizer),
                             SE.select(altered, W.write(c), arm, 1536, self.tokenizer))

    def test_oversized_recent_record_stops_prefix(self):
        c = FX.build('distractor_history', 3, 24)
        for arm in ('recent_history', 'retrieved_evidence'):
            selected = SE.select(c, W.write(c), arm, 1536, self.tokenizer)
            self.assertEqual(selected['items'], [])
        memory = SE.select(c, W.write(c), 'conditional_memory', 1536, self.tokenizer)
        self.assertTrue(memory['items'])

    def test_latest_and_unknown_shortcuts_fail_positive_controls(self):
        c = FX.build('appearance_match', 0)
        req = R.request(c, 'transfer', R.raw_items(c))
        p, fs = SC.parse_request(req)
        key = SC.judge(fs, p['rule'], p['target'], 'transfer')
        self.assertEqual(key['answer'], 'supported_local')
        for name in ('latest_entry', 'always_unknown'):
            self.assertFalse(SC.score(SH.read(req, name), 'transfer', key, R.allowed_ids(req))['category_correct'])


if __name__ == '__main__':
    unittest.main()
