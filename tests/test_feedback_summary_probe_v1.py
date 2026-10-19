"""No inference: request identity, independent arithmetic and continuation faults."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from research.feedback_probe_v1.interface import recognition_request as old_recognition
from research.feedback_summary_probe_v1.audit import audit_continuation, audit_recognition_request
from research.feedback_summary_probe_v1.continuation import continuation
from research.feedback_summary_probe_v1.interface import VARIANTS, policy_request, recognition_request
from research.initial_geometry_assistance_v1.geometry import digest
from research.recent_feedback_v1.interface import request_for_variant
from tests.test_feedback_probe_continuation_v1 import selected, response, Clock, FakeEngine
from tests.test_feedback_probe_checkpoints_v1 import MODEL
from tests.test_feedback_probe_interface_v1 import request, transition, observation


class Engine(FakeEngine):
    def close(self):
        self.close_calls += 1
        return {'closed': True, 'local_scorecard_opened': True, 'local_scorecard_closed': True, 'online_calls': 0}


def run(checkpoint=None, variant='recent_summary', followup=None, complete=None):
    checkpoint = checkpoint or selected()
    engine, events = Engine(checkpoint, followup=followup), []
    result = continuation(checkpoint, variant, engine, complete or (lambda _: response()), events.append,
                          model=MODEL, deadline=10, now=lambda: 0)
    return checkpoint, engine, events, result


class Interfaces(unittest.TestCase):
    def test_raw_conditions_reproduce_old_baselines_exactly(self):
        base = request()
        self.assertEqual(policy_request(base, 'recent_raw'), base)
        self.assertEqual(recognition_request(base, 'recent_raw'), old_recognition(base))

    def test_summary_is_exactly_prior_tested_interface_not_a_new_prompt(self):
        base = request()
        before = deepcopy(base)
        for variant in VARIANTS:
            self.assertEqual(policy_request(base, variant), request_for_variant(base, variant))
        self.assertEqual(base, before)
        self.assertEqual(recognition_request(base, 'recent_summary')['messages'][1]['content'][-2],
                         policy_request(base, 'recent_summary')['messages'][1]['content'][-1])

    def test_factual_arms_share_question_contract_and_all_original_images(self):
        base = request()
        raw, summarized = (recognition_request(base, v) for v in VARIANTS)
        summarized['messages'][1]['content'].pop(-2)
        self.assertEqual(raw, summarized)
        for v in VARIANTS:
            audit_recognition_request({'base_request': base}, v, recognition_request(base, v))

    def test_independent_recognition_refuses_forged_summary_even_after_rehash(self):
        base = request([transition(changed=True)])
        for field, value in (('changed_cell_count', 0), ('changed_bbox_xyxy_inclusive', [0, 0, 63, 63])):
            with self.subTest(field=field):
                body = recognition_request(base, 'recent_summary')
                part = body['messages'][1]['content'][-2]
                summary = json.loads(part['text'])
                summary['transitions'][-1][field] = value
                part['text'] = json.dumps(summary, sort_keys=True, separators=(',', ':'))
                with self.assertRaisesRegex(ValueError, 'summary differs'):
                    audit_recognition_request({'base_request': base}, 'recent_summary', body)

    def test_recognition_contract_mutations_and_assistant_carryover_are_refused(self):
        base = request()
        for mutate in (lambda b: b.update(model='other'), lambda b: b.update(seed=True),
                       lambda b: b['messages'][0].update(content='new instructions'),
                       lambda b: b['messages'].append({'role': 'assistant', 'content': 'answer'})):
            for variant in VARIANTS:
                body = recognition_request(base, variant)
                mutate(body)
                with self.assertRaises((ValueError, KeyError)):
                    audit_recognition_request({'base_request': base}, variant, body)

    def test_small_boundary_change_and_unchanged_grid_are_counted(self):
        entry = transition()
        entry['after']['grid'][63][0] = 4
        body = policy_request(request([entry], entry['after']), 'recent_summary')
        summary = json.loads(body['messages'][1]['content'][-1]['text'])['transitions'][-1]
        self.assertEqual(summary['changed_cell_count'], 1)
        self.assertEqual(summary['changed_bbox_xyxy_inclusive'], [0, 63, 0, 63])
        self.assertFalse(summary['before_grid_equals_current'])
        summary = json.loads(policy_request(request(), 'recent_summary')['messages'][1]['content'][-1]['text'])['transitions'][-1]
        self.assertEqual(summary['changed_cell_count'], 0)
        self.assertIsNone(summary['changed_bbox_xyxy_inclusive'])

    def test_unknown_variant_refused_and_no_future_function_annotations_copied(self):
        old = transition()
        old['private_future_outcome'] = 'DO_NOT_COPY'
        base = request([old])
        self.assertNotIn('DO_NOT_COPY', json.dumps(policy_request(base, 'recent_summary')))
        for fn in (policy_request, recognition_request):
            with self.assertRaises(ValueError):
                fn(base, 'invented')


class Continuations(unittest.TestCase):
    def test_exact_request_journal_matches_callback_and_independent_engine_replay(self):
        for variant in VARIANTS:
            calls = []
            checkpoint, engine, events, result = run(variant=variant,
                complete=lambda b: calls.append(deepcopy(b)) or response())
            self.assertEqual(calls, [e['body'] for e in events if e['kind'] == 'request'])
            self.assertEqual(result['variant'], variant)
            self.assertEqual(engine.actions[:2], [r['action'] for r in checkpoint['prefix']])
            self.assertEqual(result['continuation_dispatches'], 4)
            replay = Engine(checkpoint)
            audited = audit_continuation(checkpoint, variant, events, model=MODEL, replay_engine=replay)
            self.assertTrue(audited['engine_replayed'])
            self.assertEqual(audited['variant'], variant)
            self.assertEqual(engine.actions, replay.actions)
            self.assertEqual(engine.close_calls, 1)
            self.assertFalse(audited['lifecycle_certified'])

    def test_summary_refreshes_after_actual_new_transition(self):
        def change(index, action, obs):
            obs['grid'][63][0] = 2 if index % 2 == 0 else 0
        calls = []
        checkpoint, _, events, _ = run(followup=change,
            complete=lambda b: calls.append(deepcopy(b)) or response())
        summaries = [json.loads(b['messages'][1]['content'][-1]['text']) for b in calls]
        self.assertEqual([s['decision_step'] for s in summaries], [2, 3, 4, 5])
        self.assertEqual(summaries[0]['transitions'][-1]['changed_cell_count'], 0)
        self.assertEqual(summaries[1]['transitions'][-1]['changed_cell_count'], 1)
        self.assertEqual(summaries[1]['transitions'][-1]['changed_bbox_xyxy_inclusive'], [0, 63, 0, 63])
        self.assertEqual(summaries[2]['transitions'][-1]['changed_cell_count'], 1)
        audit_continuation(checkpoint, 'recent_summary', events, model=MODEL, replay_engine=Engine(checkpoint, followup=change))

    def test_updated_hash_cannot_hide_forged_summary_or_model(self):
        checkpoint, _, events, _ = run()
        for what in ('count', 'model', 'role', 'tokens'):
            mutated = deepcopy(events)
            e = next(e for e in mutated if e['kind'] == 'request')
            if what == 'count':
                part = e['body']['messages'][1]['content'][-1]
                value = json.loads(part['text'])
                value['transitions'][-1]['changed_cell_count'] = 5
                part['text'] = json.dumps(value, sort_keys=True, separators=(',', ':'))
            elif what == 'model': e['body']['model'] = 'another-model'
            elif what == 'role': e['body']['messages'][1]['role'] = 'assistant'
            else: e['body']['max_tokens'] = 4096
            e['request_sha256'] = digest(e['body'])
            with self.subTest(what=what), self.assertRaises(ValueError):
                audit_continuation(checkpoint, 'recent_summary', mutated, model=MODEL)

    def test_unconfirmed_or_mismatched_dispatch_is_not_a_complete_condition(self):
        checkpoint, _, events, _ = run()
        changed = deepcopy(events)
        next(e for e in changed if e['kind'] == 'transition')['action']['action_id'] = 6
        with self.assertRaises(ValueError):
            audit_continuation(checkpoint, 'recent_summary', changed, model=MODEL)
        changed = deepcopy(events)
        changed[-1]['reason'] = 'first_level_complete'
        with self.assertRaises(ValueError):
            audit_continuation(checkpoint, 'recent_summary', changed, model=MODEL)

    def test_repetition_remains_legal_when_hidden_delayed_effect_requires_it(self):
        def delayed(index, action, obs):
            if index == 1:
                obs['levels_completed'] = 1
        for variant in VARIANTS:
            checkpoint, engine, events, result = run(variant=variant, followup=delayed)
            self.assertEqual(result['reason'], 'first_level_complete')
            self.assertEqual(result['continuation_dispatches'], 2)
            audit_continuation(checkpoint, variant, events, model=MODEL, replay_engine=Engine(checkpoint, followup=delayed))

    def test_invalid_reply_is_preserved_without_retry_or_execution(self):
        checkpoint, engine, events, result = run(complete=lambda _: 'not json')
        self.assertEqual(result['reason'], 'invalid_answer')
        self.assertEqual(result['policy_calls'], 1)
        self.assertEqual(result['continuation_dispatches'], 0)
        self.assertEqual(len(engine.actions), len(checkpoint['prefix']))
        audit_continuation(checkpoint, 'recent_summary', events, model=MODEL)

    def test_late_request_journal_cannot_reopen_admission(self):
        checkpoint, clock = selected(), Clock()
        engine, calls, events = Engine(checkpoint), [], []
        def sink(event):
            events.append(event)
            if event['kind'] == 'request': clock.value = 10
        with self.assertRaises(TimeoutError):
            continuation(checkpoint, 'recent_summary', engine, lambda b: calls.append(b), sink,
                         model=MODEL, deadline=10, now=clock)
        self.assertEqual(calls, [])
        self.assertEqual(len(engine.actions), len(checkpoint['prefix']))
        self.assertEqual(engine.close_calls, 1)

    def test_wrong_restoration_and_variant_identity_refuse(self):
        checkpoint = selected()
        engine = Engine(checkpoint, initial_mutation=lambda o: o.update(legal_actions=[6]))
        calls = []
        with self.assertRaises(ValueError):
            continuation(checkpoint, 'recent_summary', engine, lambda b: calls.append(b), lambda _: None,
                         model=MODEL, deadline=10, now=lambda: 0)
        self.assertEqual(calls, [])
        self.assertEqual(engine.close_calls, 1)
        checkpoint, _, events, _ = run()
        events[-1]['variant'] = 'recent_raw'
        with self.assertRaises(ValueError):
            audit_continuation(checkpoint, 'recent_summary', events, model=MODEL)

    def test_slow_summary_transformation_cannot_issue_a_late_request(self):
        checkpoint, clock = selected(), Clock()
        engine, calls = Engine(checkpoint), []
        transforms = []
        def transform(body, variant):
            transforms.append(variant)
            value = policy_request(body, variant)
            if len(transforms) == 2:
                clock.value = 10
            return value
        with patch('research.feedback_summary_probe_v1.continuation.policy_request', side_effect=transform):
            with self.assertRaises(TimeoutError):
                continuation(checkpoint, 'recent_summary', engine, lambda b: calls.append(b), lambda _: None,
                             model=MODEL, deadline=10, now=clock)
        self.assertEqual(calls, [])
        self.assertEqual(len(engine.actions), len(checkpoint['prefix']))
        self.assertEqual(engine.close_calls, 1)

    def test_unknown_variant_closes_an_already_created_engine(self):
        checkpoint = selected()
        engine = Engine(checkpoint)
        with self.assertRaises(ValueError):
            continuation(checkpoint, 'unknown', engine, lambda _: self.fail('unexpected call'), lambda _: None,
                         model=MODEL, deadline=10, now=lambda: 0)
        self.assertEqual(engine.close_calls, 1)
        self.assertEqual(engine.actions, [])

    def test_rejected_summary_closes_already_created_replay_engine(self):
        checkpoint, _, events, _ = run()
        event = next(e for e in events if e['kind'] == 'request')
        event['request_sha256'] = '0'*64
        replay = Engine(checkpoint)
        with self.assertRaises(ValueError):
            audit_continuation(checkpoint, 'recent_summary', events, model=MODEL, replay_engine=replay)
        self.assertEqual(replay.close_calls, 1)
        self.assertEqual(replay.actions, [])


if __name__ == '__main__':
    unittest.main()
