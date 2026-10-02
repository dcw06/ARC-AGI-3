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
        old = {arm: P.metrics(r)['old_evidence_accuracy'][0] for arm, r in rows.items()}
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


def row(arm, family, group, delay, evidence, correct, question=0, kind='recall', control='family', truth=None,
        package=None, unsupported=False, answer=None):
    truth = truth or ['final_frame_differs']
    return {'arm': arm, 'family': family, 'group': group, 'delay': delay, 'evidence': evidence, 'kind': kind,
            'control': control, 'trajectory': f'{family}-{group}-d{delay}', 'question': question, 'truth': truth,
            'package': package or truth, 'correct_truth': correct, 'correct_package': True, 'valid': True,
            'unsupported': unsupported, 'abstained': False, 'answer': answer or str(correct)}


def arms(spec):
    """{arm: rows} from {arm: (recent accuracy, old accuracy)} over 4 families x 6 groups."""
    out = {}
    for arm, (recent, old) in spec.items():
        rows = []
        for f in range(4):
            for g in range(6):
                rows.append(row(arm, f'f{f}', g, 0, 'recent', g < recent * 6))
                rows.append(row(arm, f'f{f}', g, 8, 'old', g < old * 6))
        out[arm] = rows
    return out


class PrimaryEndpointAndContrasts(unittest.TestCase):
    def test_bootstrap_is_seeded_stratified_and_brackets_the_estimate(self):
        values = {'a': [0.0, 1.0, 0.5, 1.0], 'b': [1.0], 'c': [0.2, 0.4]}
        ci = P.bootstrap_ci(values, resamples=2000)
        self.assertEqual(ci, P.bootstrap_ci(values, resamples=2000))
        self.assertLessEqual(ci[0], P._macro(values))
        self.assertGreaterEqual(ci[1], P._macro(values))
        self.assertEqual(P.bootstrap_ci({'a': [0.3, 0.3], 'b': [0.7]}, resamples=500), [0.5, 0.5])

    def test_old_evidence_accuracy_is_primary_and_a_smaller_forgetting_gap_is_not_rewarded(self):
        # Memory loses recent information (recent 0.5) while matching recent_raw on old evidence (0.5): its
        # recent-minus-old gap is smaller, yet it gains no access. The primary contrast must say so.
        rows = arms({'recent_raw': (1.0, 0.5), 'state_keyed_raw': (1.0, 0.5), 'memory': (0.5, 0.5),
                     P.REFERENCE: (1.0, 1.0)})
        gap = {arm: P.forgetting_effect(rows[arm])[0] for arm in ('recent_raw', 'memory')}
        self.assertLess(gap['memory'], gap['recent_raw'])
        result = P.analyze_rows(rows, resamples=500)
        self.assertEqual(result['contrasts']['memory_vs_recent_raw']['estimate'], 0.0)
        self.assertEqual(result['conclusions']['access_vs_recent_history'], 'no_difference_detected')
        self.assertEqual(result['conclusions']['verdict'], 'access_preservation_not_shown')
        self.assertEqual(result['primary_endpoint']['memory']['estimate'], 0.5)

    def test_the_two_contrasts_support_different_conclusions(self):
        rows = arms({'recent_raw': (1.0, 0.0), 'state_keyed_raw': (1.0, 1.0), 'memory': (1.0, 1.0),
                     P.REFERENCE: (1.0, 1.0)})
        c = P.analyze_rows(rows, resamples=500)['conclusions']
        self.assertEqual(c['access_vs_recent_history'], 'memory_preserves_access')
        self.assertEqual(c['improvement_over_retrieval'], 'no_difference_detected')
        self.assertEqual(c['verdict'], 'memory_preserves_access_not_shown_over_retrieval')
        rows = arms({'recent_raw': (1.0, 0.0), 'state_keyed_raw': (1.0, 0.0), 'memory': (1.0, 1.0),
                     P.REFERENCE: (1.0, 1.0)})
        self.assertEqual(P.analyze_rows(rows, resamples=500)['conclusions']['verdict'],
                         'memory_preserves_access_and_improves_over_retrieval')

    def test_representation_contrast_is_restricted_to_evidence_available_in_both(self):
        rows = arms({'recent_raw': (1.0, 0.0), 'state_keyed_raw': (1.0, 0.0), 'memory': (1.0, 1.0),
                     P.REFERENCE: (1.0, 1.0)})
        for r in rows['state_keyed_raw']:
            if r['evidence'] == 'old' and r['group'] < 3:
                r['package'] = ['no_evidence']  # the retrieval package lacks the evidence for half the groups
        c = P.analyze_rows(rows, resamples=500)['contrasts']['memory_vs_state_keyed_raw_evidence_in_both']
        self.assertEqual((c['eligible_questions'], c['excluded_questions']), (12, 12))
        self.assertEqual(c['groups'], 12)

    def test_comprehension_floor_and_unsupported_margin(self):
        rows = arms({'recent_raw': (0.5, 0.0), 'state_keyed_raw': (1.0, 1.0), 'memory': (1.0, 1.0),
                     P.REFERENCE: (1.0, 1.0)})
        c = P.analyze_rows(rows, resamples=500)['conclusions']
        self.assertFalse(c['interpretable'])
        self.assertEqual(c['verdict'], 'not_interpretable_cannot_isolate_retention_from_comprehension')
        rows = arms({'recent_raw': (1.0, 0.0), 'state_keyed_raw': (1.0, 0.0), 'memory': (1.0, 1.0),
                     P.REFERENCE: (1.0, 1.0)})
        for r in rows['memory']:
            r['unsupported'] = r['group'] == 0  # one group in six asserts unsupported values
        c = P.analyze_rows(rows, resamples=500)['conclusions']
        self.assertEqual(c['unsupported_claims'], 'outside_margin')
        self.assertEqual(c['verdict'], 'memory_preserves_access_unsupported_claims_outside_margin')

    def test_stability_counts_identical_repeated_answers(self):
        first = [row('memory', 'f0', 0, 8, 'old', True, question=q, answer=str(q)) for q in range(4)]
        second = [dict(r, answer=r['answer'] if r['question'] else 'changed') for r in first]
        s = P.stability(first, second)
        self.assertEqual((s['repeated_questions'], s['identical']), (4, 3))


if __name__ == '__main__':
    unittest.main()
