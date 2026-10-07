"""Construction, component attribution, rendered-reader and request leakage checks."""
import copy
import json
import unittest

from research.evidence_memory_v1 import fidelity as F, protocol as P, render as R, schema as S
from research.evidence_memory_v1 import tokens as TK, writers as W
from research.evidence_memory_stress_v1 import fixtures as FX, diagnostics as D, build as B


class StressConstruction(unittest.TestCase):
    def test_keys_are_independent_and_all_families_are_covered(self):
        cases = FX.generate()
        self.assertEqual(len(cases), 48)
        self.assertEqual({c['family'] for c in cases}, set(FX.FAMILIES))
        for c in cases:
            for q, key in zip(c['evaluator_only']['expected']['questions'], c['evaluator_only']['keys']):
                truth = {'values': F.gold(c['records'], q)} if q['kind'] == 'recall' else D.hypothesis_gold(c['records'], q)
                self.assertEqual(key, truth, c['id'])

    def test_coordinate_answers_are_not_action_id_answers(self):
        c = FX.build('coordinates')
        qs = c['evaluator_only']['expected']['questions']
        self.assertEqual(qs[0]['action']['action_id'], qs[1]['action']['action_id'])
        self.assertNotEqual(qs[0]['action']['action_data'], qs[1]['action']['action_data'])
        self.assertNotEqual(F.gold(c['records'], qs[0]), F.gold(c['records'], qs[1]))

    def test_failed_and_unknown_do_not_establish_no_change(self):
        c = FX.build('unobserved_dispatch')
        self.assertEqual([r['dispatch']['status'] for r in c['records'][:2]], ['outcome_unknown', 'failed'])
        for q in c['evaluator_only']['expected']['questions'][:2]:
            self.assertEqual(F.gold(c['records'], q), ['no_evidence'])

    def test_transient_is_not_final_frame_only(self):
        c = FX.build('transient_return')
        raw = c['raws'][0]
        self.assertEqual(raw['before']['frames'][-1], raw['outcome']['after']['frames'][-1])
        self.assertNotEqual(raw['before']['frames'][-1], raw['outcome']['after']['frames'][0])
        self.assertEqual(F.gold(c['records'], c['evaluator_only']['expected']['questions'][0]), ['changed_then_returned'])

    def test_same_frame_at_a_new_level_does_not_inherit_old_evidence(self):
        c = FX.build('level_boundary')
        old, new = c['evaluator_only']['expected']['questions']
        self.assertEqual(old['state'], new['state'])
        self.assertNotEqual(old['level'], new['level'])
        self.assertEqual(F.gold(c['records'], old), ['changed_then_returned'])
        self.assertEqual(F.gold(c['records'], new), ['no_evidence'])

    def test_constructions_repeat_across_delays_and_are_reproducible(self):
        self.assertEqual(FX.generate(), FX.generate())
        for family in FX.FAMILIES:
            a, b = FX.build(family, delay=0), FX.build(family, delay=24)
            self.assertEqual(a['raws'][0]['before'], b['raws'][0]['before'])
            self.assertEqual(a['raws'][0]['proposal'], b['raws'][0]['proposal'])


class WriterAndAttribution(unittest.TestCase):
    def test_faithful_writer_preserves_facts_and_corrections(self):
        for c in FX.generate():
            run = W.run_writer(W.Faithful(), {'records': c['records']})
            report = F.evaluate(c['records'], run['memory'], c['evaluator_only']['expected'])
            self.assertEqual(run['log'], [], c['id'])
            self.assertTrue(report['faithful'], (c['id'], report))

    def test_supported_hypothesis_stays_hypothesis_then_is_contradicted(self):
        for family, status in [('hypothesis_pending', S.SUPPORTED), ('contradicted_hypothesis', S.CONTRADICTED)]:
            c = FX.build(family)
            memory = W.run_writer(W.Faithful(), c)['memory']
            entry = next(e for e in memory['entries'] if e['id'] == 'hyp-level-L0-a1')
            self.assertEqual(entry['kind'], S.HYPOTHESIS)
            self.assertEqual(entry['status'], status)
            q = c['evaluator_only']['expected']['questions'][-1]
            self.assertEqual(D.text_truth(R.memory_text(memory['entries']), q), c['evaluator_only']['keys'][-1])
            if status == S.CONTRADICTED:
                self.assertEqual([r['action_index'] for r in entry['counterevidence']], [2])

    def test_reset_retires_segment_conclusion_but_not_historical_fact(self):
        c = FX.build('reset_boundary')
        memory = W.run_writer(W.Faithful(), c)['memory']
        self.assertTrue(all(e['status'] == S.RETIRED for e in memory['entries'] if e['scope']['kind'] == S.SEGMENT))
        q = c['evaluator_only']['expected']['questions'][0]
        self.assertEqual(D.text_truth(R.memory_text(memory['entries']), q), {'values': ['no_observed_change']})

    def test_actual_lossy_writer_is_separate_from_a_reader_error(self):
        c = FX.build('transient_return', delay=24)
        q = c['evaluator_only']['expected']['questions'][0]
        memory = W.run_writer(W.Lossy(), c)['memory']
        store = D.text_truth(R.memory_text(memory['entries']), q)
        truth = {'values': F.gold(c['records'], q)}
        self.assertNotEqual(store, truth)
        result = D.attribution(truth, store, store, json.dumps(store), q)
        self.assertTrue(result['writer_store_loss_or_distortion'])
        self.assertFalse(result['selection_loss_or_distortion'])
        self.assertFalse(result['reader_error'])

    def test_selection_and_reader_errors_are_independently_detected(self):
        c = FX.build('transient_return')
        q = c['evaluator_only']['expected']['questions'][0]
        truth, absent = {'values': ['changed_then_returned']}, {'values': ['no_evidence']}
        selected = D.attribution(truth, truth, absent, json.dumps(absent), q)
        self.assertFalse(selected['writer_store_loss_or_distortion'])
        self.assertTrue(selected['selection_loss_or_distortion'])
        self.assertFalse(selected['reader_error'])
        reader = D.attribution(truth, truth, truth, json.dumps(absent), q)
        self.assertFalse(reader['selection_loss_or_distortion'])
        self.assertTrue(reader['reader_error'])
        both = D.attribution(truth, absent, absent, json.dumps(truth), q)
        self.assertTrue(both['writer_store_loss_or_distortion'])
        self.assertTrue(both['reader_error'])

    def test_fabricated_unknown_outcome_is_a_writer_fault(self):
        c = FX.build('unobserved_dispatch')
        memory = W.run_writer(W.Overclaiming(), c)['memory']
        self.assertTrue(F.faulty(F.evaluate(c['records'], memory, c['evaluator_only']['expected'])))

    def test_hypothesis_status_schema_rejects_overclaim_duplicates_and_invalid_json(self):
        q = {'kind': 'hypothesis_status'}
        key = {'status': 'hypothesis_only'}
        for raw in ('{"status":"established_fact"}', '{"status":"no_evidence","status":"hypothesis_only"}',
                    'NaN', '{"status":["contradicted"]}', '{"status":"hypothesis_only","confidence":1}'):
            self.assertFalse(D.score(raw, q, key, key)['valid'], raw)


@unittest.skipUnless(TK.locate(), 'hash-pinned tokenizer assets required for token and leakage checks')
class TokenAndLeakage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = TK.Tokenizer()
        cls.outputs = B.artifacts(cls.tokenizer)

    def test_same_token_ceiling_all_arms_and_no_scripted_reader_errors(self):
        results = json.loads(self.outputs['results.json'])
        for row in results['rows']:
            self.assertLessEqual(row['evidence_tokens'], row['budget_tokens'])
            self.assertFalse(row['reader_error'])
        self.assertTrue(any(r['selection_loss_or_distortion'] for r in results['rows']))
        for case in results['writer_audits']:
            self.assertEqual(case['arm_tokens']['recent_raw'], case['budget_tokens'])

    def test_poisoning_evaluator_metadata_cannot_change_any_arm_request(self):
        for family in FX.FAMILIES:
            c = FX.build(family)
            poison = copy.deepcopy(c)
            poison['family'] = 'DO_NOT_LEAK_FAMILY'
            poison['evaluator_only'] = {'answer': 'DO_NOT_LEAK_ANSWER', 'construction': 'DO_NOT_LEAK_CONSTRUCTION'}
            _, _, original, _ = B.contexts(c, self.tokenizer)
            _, _, altered, _ = B.contexts(poison, self.tokenizer)
            for arm in P.ARMS:
                self.assertEqual(original[arm][0], altered[arm][0])
                for q in c['evaluator_only']['expected']['questions']:
                    clean = {k: v for k, v in q.items() if k != 'expected_answer'}
                    self.assertEqual(D.request(original[arm][0], clean), D.request(altered[arm][0], clean))

    def test_requests_have_no_keys_or_family_labels_and_counts_are_real(self):
        requests = [json.loads(line) for line in self.outputs['requests.jsonl'].splitlines()]
        keys = json.loads(self.outputs['evaluator_keys.json'])['keys']
        self.assertEqual(len(requests), len(keys))
        self.assertEqual({r['request_id'] for r in requests}, {k['request_id'] for k in keys})
        for draft in requests:
            self.assertEqual(set(draft), {'request_id', 'request', 'prompt_tokens'})
            req = draft['request']
            self.assertEqual(draft['prompt_tokens'], self.tokenizer.chat_prompt_tokens(req['messages']))
            raw = json.dumps(req)
            self.assertNotIn('evaluator_only', raw)
            self.assertNotIn('expected_answer', raw)
            self.assertNotIn('development-', raw)
            self.assertEqual(req['max_tokens'], P.MAX_TOKENS)

    def test_manifest_binds_every_artifact_and_launch_is_disabled(self):
        import hashlib
        manifest = json.loads(self.outputs['manifest.json'])
        self.assertFalse(manifest['gpu_launch_authorized'])
        self.assertEqual(manifest['model_calls'], 0)
        for name, info in manifest['files'].items():
            self.assertEqual(info['sha256'], hashlib.sha256(self.outputs[name]).hexdigest())

    def test_later_correction_can_be_lost_after_a_faithful_writer(self):
        _, rows, _, _ = B.analyze(FX.build('contradicted_hypothesis', index=0, delay=8), self.tokenizer)
        for arm in ('memory', 'state_keyed_raw'):
            row = next(r for r in rows if r['arm'] == arm and r['kind'] == 'hypothesis_status')
            self.assertEqual(row['truth'], {'status': 'contradicted'})
            self.assertEqual(row['full_store_truth'], {'status': 'contradicted'})
            self.assertEqual(row['package_truth'], {'status': 'hypothesis_only'})
            self.assertEqual(row['missing_relevant_steps'], [1, 2])
            self.assertFalse(row['writer_store_loss_or_distortion'])
            self.assertTrue(row['selection_loss_or_distortion'])
            self.assertFalse(row['reader_error'])

    def test_every_key_obeys_the_actual_request_schema(self):
        import jsonschema
        requests = [json.loads(line) for line in self.outputs['requests.jsonl'].splitlines()]
        keys = json.loads(self.outputs['evaluator_keys.json'])['keys']
        for draft, key in zip(requests, keys):
            schema = draft['request']['response_format']['json_schema']['schema']
            jsonschema.validate(key['truth'], schema)
            jsonschema.validate(key['package_truth'], schema)


if __name__ == '__main__':
    unittest.main()
