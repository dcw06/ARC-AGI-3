"""Evidence-linked memory v1 (Track 2): the Stage 1 frozen question set, requests and request enumeration."""
import collections
import json
import unittest

from research.evidence_memory_v1 import protocol as P, readers as RD, stage1 as ST, tokens as TK, trajectories as TR

FOUND = TK.locate()


class RepeatSelection(unittest.TestCase):
    def test_whole_groups_ten_percent_every_family_deterministic(self):
        chosen = ST.repeat_groups(TR.SEED)
        self.assertEqual(chosen, ST.repeat_groups(TR.SEED))
        self.assertEqual(len(chosen), ST.REPEAT_GROUPS)
        self.assertEqual(len(set(chosen)), ST.REPEAT_GROUPS)
        self.assertEqual({f for f, _ in chosen}, set(TR.FAMILIES))
        self.assertGreaterEqual(ST.REPEAT_GROUPS, 0.1 * ST.GROUPS_PER_FAMILY * len(TR.FAMILIES))
        self.assertNotEqual(chosen, ST.repeat_groups('another seed'))

    def test_request_schema_and_key_answers_validate(self):
        q = {'kind': 'recall', 'level': 0, 'state': 'a' * 64, 'action': TR.act(1), 'control': 'family'}
        probe = {'kind': 'recall', 'question': q}
        request = ST.build_request({'evidence': 'step 0 | x'}, probe)
        self.assertEqual((request['temperature'], request['max_tokens'], request['model']), (0, P.MAX_TOKENS, ST.MODEL))
        self.assertEqual(request['messages'], P.reader_messages('step 0 | x', q))
        self.assertTrue(request['response_format']['json_schema']['strict'])
        key = json.dumps(ST.key_answer('recall', ['final_frame_differs']))
        self.assertEqual(RD.score(key, q, ['final_frame_differs']), {'valid': True, 'correct': True})


class DecodingSchemaWithoutUniqueItems(unittest.TestCase):
    """Protocol v2 frozen, section 2: `uniqueItems` is dropped from the recall DECODING schema only (vLLM 0.19's
    structured-output backends refuse it); scoring is unchanged and still rejects duplicates."""

    def test_no_request_schema_carries_unique_items(self):
        recall = ST.response_schema('recall')
        self.assertEqual(recall, {'type': 'object', 'additionalProperties': False, 'required': ['values'],
                                  'properties': {'values': {'type': 'array', 'minItems': 1, 'items': {
                                      'type': 'string', 'enum': list(ST.RECALL_VALUES)}}}})
        for kind in ('recall', 'decision'):
            q = {'kind': kind, 'level': 0, 'state': 'a' * 64, 'action': TR.act(1), 'control': 'family',
                 'goal': 'reach the goal', 'candidates': [TR.act(1), TR.act(2)]}
            request = ST.build_request({'evidence': 'step 0 | x'}, {'kind': kind, 'question': q})
            self.assertNotIn('uniqueItems', json.dumps(request))
            self.assertEqual(request['response_format']['json_schema']['schema'], ST.response_schema(kind))
            self.assertTrue(request['response_format']['json_schema']['strict'])

    def test_answers_the_decoder_now_admits_are_still_scored_invalid(self):
        from research.evidence_memory_v1.run import score as SC
        q = {'kind': 'recall', 'level': 0, 'state': 'a' * 64, 'action': TR.act(1), 'control': 'family'}
        value = ST.RECALL_VALUES[0]
        for values in ([value, value], ['final_frame_differs', 'final_frame_differs', 'no_observed_change'],
                       ['no_evidence', 'no_evidence'], ['no_evidence', value]):
            output = json.dumps({'values': values})
            gold = sorted(set(values))
            with self.assertRaises(RD.ResponseError):
                RD.validate_response(output, q)
            self.assertEqual(RD.score(output, q, gold)['valid'], False)
            self.assertEqual(RD.score(output, q, gold)['correct'], False)
            flags = P.score(output, q, gold, gold)
            self.assertEqual({k: flags[k] for k in ('valid', 'correct_truth', 'correct_package', 'unsupported',
                                                     'abstained')},
                             {'valid': False, 'correct_truth': False, 'correct_package': False, 'unsupported': False,
                              'abstained': False})
            probe = {'probe_id': 'p', 'question': q, 'truth': gold, 'package': gold}
            self.assertEqual((SC.score(probe, output)['valid'], SC.score(probe, output)['correct']), (False, False))
        self.assertTrue(RD.score(json.dumps({'values': [value]}), q, [value])['valid'])


@unittest.skipUnless(FOUND, 'the pinned tokenizer files are not available offline')
class FrozenSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = TK.Tokenizer(FOUND)
        cls.frozen = json.loads(ST.RUN_PROBES.read_bytes())

    def test_committed_stand_in_equals_a_fresh_build(self):
        self.assertEqual(ST.encode(ST.build('A', tokenizer=self.tokenizer)), ST.RUN_PROBES.read_bytes())
        self.assertEqual(self.frozen['case_source'], 'development_stand_in')
        with self.assertRaises(ValueError):
            ST.build('C', tokenizer=self.tokenizer)
        with self.assertRaises(ValueError):
            ST.build('A', case_source='live', tokenizer=self.tokenizer)

    def test_schedule_is_group_interleaved_and_the_repeat_is_whole_groups(self):
        probes = {p['probe_id']: p for p in self.frozen['probes']}
        first = self.frozen['schedule'][0]['probe_ids']
        self.assertEqual(sorted(first), sorted(probes))
        blocks = [(probes[i]['group'], probes[i]['family']) for i in first]
        runs = [b for n, b in enumerate(blocks) if n == 0 or blocks[n - 1] != b]
        self.assertEqual(len(runs), len(set(runs)))  # every group's calls are contiguous
        self.assertEqual([g for g, _ in runs], sorted(g for g, _ in runs))  # group index outer, families inner
        repeat = {tuple(fg) for fg in self.frozen['repeat_groups']}
        second = self.frozen['schedule'][1]['probe_ids']
        self.assertEqual(second, [i for i in first if (probes[i]['family'], probes[i]['group']) in repeat])
        per_group = collections.Counter((probes[i]['family'], probes[i]['group']) for i in first)
        self.assertEqual(len(second), sum(per_group[fg] for fg in repeat))

    def test_every_arm_question_and_budget(self):
        contexts = {c['context_id']: c for c in self.frozen['contexts']}
        by_trajectory = collections.defaultdict(lambda: collections.defaultdict(list))
        for p in self.frozen['probes']:
            by_trajectory[p['trajectory']][p['arm']].append(p)
            self.assertNotIn('expected_answer', p['question'])
            self.assertEqual(RD.score(json.dumps(p['key']), p['question'], p['truth'])['correct'], True)
        for arms in by_trajectory.values():
            self.assertEqual(set(arms), set(ST.ARM_ORDER))
            counts = {len(v) for v in arms.values()}
            self.assertEqual(len(counts), 1)
            controls = {p['control'] for p in arms['memory']}
            self.assertIn('recent', controls)
            budget = len(self.tokenizer.encode(contexts[arms['recent_raw'][0]['context_id']]['evidence']))
            for arm in ('state_keyed_raw', 'memory'):
                self.assertLessEqual(len(self.tokenizer.encode(contexts[arms[arm][0]['context_id']]['evidence'])), budget)

    def test_enumeration_covers_every_scheduled_call_of_both_sessions(self):
        rows = list(ST.enumerate_requests(tokenizer=self.tokenizer))
        frozen_b = ST.build('B', tokenizer=self.tokenizer)
        expected = sum(len(b['probe_ids']) for f in (self.frozen, frozen_b) for b in f['schedule'])
        self.assertEqual(len(rows), expected)
        self.assertEqual({r['arm'] for r in rows}, set(ST.ARM_ORDER))
        self.assertEqual({r['pass_id'] for r in rows}, {'pass_1', 'pass_2'})
        self.assertEqual({r['session'] for r in rows}, {'A', 'B'})
        repeated = [r for r in rows if r['pass_id'] == 'pass_2']
        self.assertEqual({r['probe_id'].split('/')[0].split('-d')[0][4:] for r in repeated}, set(TR.FAMILIES))
        for r in rows[:50] + repeated[:20]:
            self.assertEqual(r['pure_python_prompt_tokens'], self.tokenizer.chat_prompt_tokens(r['request']['messages']))
        self.assertTrue(any('Question:' in r['request']['messages'][1]['content'] for r in rows))


if __name__ == '__main__':
    unittest.main()
