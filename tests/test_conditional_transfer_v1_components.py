import copy
import unittest
from research.conditional_transfer_v1 import fixtures as FX, writer as W, schema as S, score as SC, attribution as A, render as R


class Components(unittest.TestCase):
    def setUp(self):
        self.case = FX.build('contradiction', 1, 24)
        self.store = W.write(self.case)

    def test_faithful_writer_preserves_all_qualifications_and_counters(self):
        self.assertEqual(W.flatten(self.store), W.source_facts(self.case))
        self.assertFalse(W.audit(self.case, self.store)['faults'])
        rule = [r for r in self.store if r['action']['action_id'] == 6][0]
        self.assertEqual(len(rule['supporting_record_ids']), 2)
        self.assertEqual(len(rule['contradictory_record_ids']), 1)
        self.assertEqual(rule['applicability_status'], 'contradicted')
        self.assertEqual(rule['epistemic_status'], 'hypothesis')
        self.assertEqual(rule['revision_history'][-1]['status'], 'contradicted')
        self.assertEqual(set(rule['supporting_record_ids'] + rule['contradictory_record_ids']),
                         {o['id'] for o in rule['observations']})

    def test_hypothesis_never_automatically_becomes_observation(self):
        for r in self.store:
            self.assertEqual(r['epistemic_status'], 'hypothesis')
        r = copy.deepcopy([r for r in self.store if len(r['observations']) > 1][0])
        r['epistemic_status'] = 'observation'
        with self.assertRaises(ValueError):
            S.validate_rule(r)

    def test_wrong_coords_and_unresolved_claims_rejected(self):
        rule = copy.deepcopy(self.store[0])
        rule['action']['action_data']['x'] = -1
        with self.assertRaises(ValueError):
            S.validate_rule(rule)
        rule = copy.deepcopy(self.store[0])
        rule['supporting_record_ids'].append('forged')
        with self.assertRaises(ValueError):
            S.validate_rule(rule)

    def test_omitted_correction_and_broadened_scope_writer_faults(self):
        bad = copy.deepcopy(self.store)
        bad[0]['contradictory_record_ids'] = []
        bad[0]['scope']['level'] = 20
        self.assertTrue(W.audit(self.case, bad)['faults'])

    def test_reader_parses_rendered_request_only(self):
        req = R.request(self.case, 'transfer', R.raw_items(self.case))
        output = SC.scripted_reader(req)
        p, visible = SC.parse_request(req)
        key = SC.judge(visible, p['rule'], p['target'], p['task'])
        self.assertTrue(SC.score(output, 'transfer', key, R.allowed_ids(req))['correct'])
        p['evidence']['records'] = []
        req['messages'][1]['content'] = S.compact(p)
        output_empty = SC.scripted_reader(req)
        self.assertNotEqual(output, output_empty)
        self.assertEqual(S.validate_response(output_empty, 'transfer', R.allowed_ids(req))['answer'], 'unestablished')

    def test_invalid_responses_not_repaired(self):
        samples = ['not JSON', '```json\n{}\n```', '{"answer":"unknown","evidence_ids":[]}',
                   '{"answer":"retain","answer":"retire","evidence_ids":[]}',
                   '{"answer":"retain","evidence_ids":["x","x"]}',
                   '{"answer":"retain","evidence_ids":["not-visible"]}',
                   '{"answer":"retain","evidence_ids":[],"extra":true}',
                   '{"answer":"retain","evidence_ids":[NaN]}',
                   '{"answer":"retain","evidence_ids":[1]}',
                   '{"answer":"retain","evidence_ids":[]} trailing']
        key = {'answer': 'retain', 'required_groups': [], 'eligible_ids': []}
        for out in samples:
            with self.subTest(output=out):
                self.assertFalse(SC.score(out, 'update', key, {'x'})['valid'])

    def test_precision_and_coverage_distinct(self):
        key = {'answer': 'records', 'required_groups': [['a'], ['b']], 'eligible_ids': ['a', 'b']}
        one = SC.score(S.compact({'answer': 'records', 'evidence_ids': ['a']}), 'evidence', key, {'a', 'b', 'c'})
        self.assertEqual(one['reference_precision'], 1)
        self.assertEqual(one['reference_coverage'], 0.5)
        extra = SC.score(S.compact({'answer': 'records', 'evidence_ids': ['a', 'b', 'c']}), 'evidence', key, {'a', 'b', 'c'})
        self.assertEqual(extra['reference_precision'], 2/3)
        self.assertEqual(extra['reference_coverage'], 1)

    def test_simultaneous_writer_selector_reader_faults(self):
        def key(answer, ref):
            return {'answer': answer, 'required_groups': [[ref]], 'eligible_ids': [ref]}
        truth, store, selected = key('supported_local', 'a'), key('unestablished', 'b'), key('contradicted', 'c')
        out = S.compact({'answer': 'supported_local', 'evidence_ids': ['a']})
        result = A.evaluate(truth, store, selected, out, 'transfer', {'a', 'b', 'c'}, True)
        for flag in ('writer_store_loss_or_distortion', 'selection_loss_or_distortion', 'reader_error', 'writer_integrity_fault_present'):
            self.assertTrue(result[flag])
        out = S.compact({'answer': 'contradicted', 'evidence_ids': ['c']})
        result = A.evaluate(truth, store, selected, out, 'transfer', {'a', 'b', 'c'}, True)
        self.assertTrue(result['writer_store_loss_or_distortion'])
        self.assertTrue(result['selection_loss_or_distortion'])
        self.assertFalse(result['reader_error'])
        self.assertFalse(result['correct_truth'])

    def test_real_lossy_store_selector_and_reader_faults_coexist(self):
        rule, target = self.case['proposed_rule'], self.case['target']
        truth = SC.judge(W.source_facts(self.case), rule, target, 'transfer')
        lossy = copy.deepcopy(self.store)
        for r in lossy:
            if r['action'] == rule['action']:
                r['observations'] = [o for o in r['observations'] if o['visual'] == rule['effect']]
        self.assertTrue(W.audit(self.case, lossy)['faults'])
        full_store = SC.judge(W.flatten(lossy), rule, target, 'transfer')
        selected_facts = [f for f in W.flatten(lossy) if f['action'] != rule['action']]
        selected = SC.judge(selected_facts, rule, target, 'transfer')
        allowed = {f['id'] for f in selected_facts} | {target['observation_id']}
        output = S.compact({'answer': 'contradicted', 'evidence_ids': [target['observation_id']]})
        result = A.evaluate(truth, full_store, selected, output, 'transfer', allowed, True)
        self.assertTrue(result['writer_category_loss_or_distortion'])
        self.assertTrue(result['selection_category_loss_or_distortion'])
        self.assertTrue(result['reader_error'])


if __name__ == '__main__':
    unittest.main()
