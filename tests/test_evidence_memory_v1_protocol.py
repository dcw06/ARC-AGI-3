"""Evidence-linked memory v1 (Track 2): Stage 1 instruments (tokens, prompt frame, evidence classes, scoring)."""
import json
import unittest

from research.evidence_memory_v1 import protocol as P, readers as RD, tokens as TK, trajectories as TR, writers as W

FOUND = TK.locate()
CASES = P.cases(groups_per_family=1)


@unittest.skipUnless(FOUND, 'the pinned tokenizer files are not available offline')
class PinnedTokenizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = TK.Tokenizer(FOUND)

    def test_reproduces_the_exact_transformers_audit(self):
        checked, mismatches = TK.verify_against_ws3_audit(self.tokenizer)
        self.assertEqual((checked, mismatches), (3116, []))

    def test_refuses_what_it_cannot_encode_exactly(self):
        for text in ('café', 'a\x0bb', None):
            with self.assertRaises(ValueError):
                self.tokenizer.encode(text)
        with self.assertRaises(ValueError):
            self.tokenizer.chat_prompt_tokens([{'role': 'user', 'content': 'x <|im_end|>'}])
        with self.assertRaises(ValueError):
            self.tokenizer.chat_prompt_tokens([{'role': 'assistant', 'content': 'x'}])

    def test_every_stage1_prompt_is_encodable_and_packages_respect_the_token_budget(self):
        measure = lambda text: len(self.tokenizer.encode(text))
        for t in CASES:
            memory = W.run_writer(W.Faithful(), t)['memory']
            p, contents = P.arm_contents(t, memory, measure)
            self.assertLessEqual(p['state_keyed_raw']['size'], p['budget'])
            self.assertLessEqual(p['memory']['size'], p['budget'])
            self.assertEqual(p['recent_raw']['size'], p['budget'])
            for q in P.questions(t):
                for arm in P.ARMS + (P.REFERENCE,):
                    self.assertGreater(self.tokenizer.chat_prompt_tokens(P.reader_messages(contents[arm][0], q)), 0)


class Stage1Instruments(unittest.TestCase):
    def test_groups_share_their_construction_across_horizons(self):
        by_group = {}
        for t in CASES:
            by_group.setdefault((t['family'], t['group']), []).append(t)
        for runs in by_group.values():
            self.assertEqual(sorted(r['delay'] for r in runs), list(P.HORIZONS))
            first = [r['raws'][0]['before'] for r in runs]
            self.assertTrue(all(f == first[0] for f in first))

    def test_withheld_seed_changes_cases_and_label_without_touching_development(self):
        dev = TR.build('early_crucial', 0, 0)
        other = TR.build('early_crucial', 0, 0, seed='another-seed', partition='withheld')
        self.assertEqual(other['partition'], 'withheld')
        self.assertNotEqual(dev['raws'][0]['identity']['episode_id'], other['raws'][0]['identity']['episode_id'])
        self.assertNotEqual(dev['raws'][0]['before'], other['raws'][0]['before'])
        self.assertEqual(TR.build('early_crucial', 0, 0)['raws'], dev['raws'])

    def test_evidence_classes_and_recent_controls(self):
        for t in CASES:
            for q in P.questions(t):
                cls = P.evidence_class(t['records'], q)
                self.assertIn(cls, ('recent', 'old', 'mixed', 'none'))
                if q['control'] == 'recent':
                    self.assertEqual(cls, 'recent')
                if t['delay'] == P.RECENT_DELAY and q['control'] == 'family':
                    self.assertIn(cls, ('recent', 'none'))
        old = [P.evidence_class(t['records'], q) for t in CASES if t['delay'] in P.OLD_DELAYS
               for q in P.questions(t) if q['control'] == 'family' and q['kind'] == 'recall']
        self.assertIn('old', old)

    def test_the_prompt_frame_is_identical_across_arms_and_hides_the_answer(self):
        t = CASES[0]
        q = P.questions(t)[0]
        frames = [P.reader_messages(text, q) for text in ('a', 'b', '')]
        self.assertEqual({m[0]['content'] for m in frames}, {P.SYSTEM})
        self.assertEqual({m[1]['content'].split('\n\nQuestion:')[1] for m in frames}, {P.question_text(q).split('Question:')[1]})
        self.assertNotIn('expected_answer', json.dumps(P.questions(t)))

    def test_scoring_flags(self):
        q = {'kind': 'recall'}
        cases = {
            '{"values": ["final_frame_differs"]}': (['final_frame_differs'], ['final_frame_differs'],
                                                    {'correct_truth': True, 'correct_package': True}),
            '{"values": ["no_evidence"]}': (['final_frame_differs'], ['no_evidence'],
                                            {'correct_truth': False, 'correct_package': True, 'abstained': True}),
            '{"values": ["no_observed_change"]}': (['no_observed_change'], ['no_evidence'],
                                                   {'correct_truth': True, 'unsupported': True}),
        }
        for output, (truth, package, expected) in cases.items():
            flags = P.score(output, q, truth, package)
            for key, value in expected.items():
                self.assertEqual(flags[key], value, (output, key))
        invalid = P.score('{"values": ["final_frame_differs"], "x": 1}', q, ['final_frame_differs'], ['final_frame_differs'])
        self.assertEqual((invalid['valid'], invalid['correct_truth'], invalid['unsupported']), (False, False, False))

    def test_oracle_dry_run_shows_the_designed_contrast(self):
        rows = {arm: [] for arm in P.ARMS + (P.REFERENCE,)}
        for t in CASES:
            memory = W.run_writer(W.Faithful(), t)['memory']
            _, contents = P.arm_contents(t, memory, len)
            for arm in rows:
                rows[arm] += P.rows(t, arm, P.oracle_read(arm, contents[arm][1]), memory=memory)
        old = {arm: P.metrics(r)['factual_accuracy_old_family'][0] for arm, r in rows.items()}
        self.assertEqual(old['recent_raw'], 0.0)
        self.assertEqual(old[P.REFERENCE], 1.0)
        self.assertGreater(old['memory'], old['recent_raw'])
        effect = {arm: P.forgetting_effect(r) for arm, r in rows.items()}
        self.assertEqual(effect['recent_raw'][0], 1.0)
        self.assertEqual(effect[P.REFERENCE][0], 0.0)
        self.assertEqual(effect['recent_raw'][1], 5)  # one group in each of the five families with old evidence
        for arm, r in rows.items():
            m = P.metrics(r)
            self.assertEqual(m['unsupported_rate'][0], 0.0)
            self.assertEqual(m['invalid_rate'][0], 0.0)
            self.assertEqual(m['abstention_when_package_has_evidence'][0], 0.0)

    def test_runtime_estimate_uses_the_measured_fit(self):
        self.assertAlmostEqual(P.estimate_seconds([(1000, 10)]),
                               P.FIT['per_call'] + 1000 * P.FIT['per_prompt_token'] + 20 * P.FIT['per_completion_token'])
        self.assertAlmostEqual(P.estimate_seconds([(0, 10)], 'cap'), P.FIT['per_call'] + P.MAX_TOKENS * P.FIT['per_completion_token'])


if __name__ == '__main__':
    unittest.main()
