"""Mutations and delayed-effect guards for independent continuation replay."""
from copy import deepcopy
import json
import unittest

from research.feedback_probe_v1.audit import audit_continuation
from research.feedback_probe_v1.checkpoints import select_checkpoints
from research.feedback_probe_v1.continuation import continuation
from research.initial_geometry_assistance_v1.geometry import digest
from tests.test_feedback_probe_checkpoints_v1 import fixture, MODEL


def checkpoint():
    case, events = fixture()
    return select_checkpoints(case, events, model=MODEL)[0]


class ScriptEngine:
    def __init__(self, value, mode='unchanged', fail_prefix=None, mismatch_at=None):
        self.value, self.mode = value, mode
        self.fail_prefix, self.mismatch_at = fail_prefix, mismatch_at
        self.actions = []
        self.opened = self.closed = False
        self.close_calls = 0
        self.current = deepcopy(value['initial'])

    def bootstrap(self):
        self.opened = True
        return deepcopy(self.current)

    def dispatch(self, action):
        index = len(self.actions)
        self.actions.append(deepcopy(action))
        prefix = self.value['prefix']
        if index == self.fail_prefix:
            raise RuntimeError('injected prefix failure')
        if index < len(prefix):
            if action != prefix[index]['action']:
                raise ValueError('synthetic engine action differs from replay prefix')
            self.current = deepcopy(prefix[index]['after'])
        else:
            local = index-len(prefix)
            if self.mode in ('changed', 'delayed') and (self.mode == 'changed' or local >= 1):
                self.current['grid'][5][7] = local+1
            if self.mode == 'delayed' and local == 1:
                self.current['levels_completed'] = 1
            if self.mode == 'game_over':
                self.current['state'] = 'GAME_OVER'
        result = deepcopy(self.current)
        if index == self.mismatch_at:
            result['grid'][63][63] = 9
        return result

    def close(self):
        self.close_calls += 1
        if self.closed:
            raise ValueError('duplicate synthetic close')
        self.closed = True
        return {'closed': True, 'local_scorecard_opened': self.opened,
                'local_scorecard_closed': self.opened, 'online_calls': 0}


def answer(action=None, prediction='unknown'):
    return json.dumps(dict(action or {'action_id': 1, 'action_data': {}},
                           predicted_visible_change=prediction))


def retained(mode='unchanged', variant='baseline', text=None):
    value = checkpoint()
    engine, events = ScriptEngine(value, mode), []
    continuation(value, variant, engine, lambda body: answer() if text is None else text,
                 events.append, model=MODEL, deadline=100, now=lambda: 0)
    return value, events


class ContinuationAuditChecks(unittest.TestCase):
    def test_both_variants_exactly_reconstruct_and_replay_prefix_plus_four_actions(self):
        for variant in ('baseline', 'probe_instruction'):
            value, events = retained(variant=variant)
            before = deepcopy(events)
            engine = ScriptEngine(value)
            result = audit_continuation(value, variant, events, model=MODEL, replay_engine=engine)
            self.assertEqual(events, before)
            self.assertTrue(result['content_replay_passed'])
            self.assertTrue(result['engine_replayed'])
            self.assertEqual(result['prefix_dispatches'], 2)
            self.assertEqual(result['policy_calls'], 4)
            self.assertEqual(result['continuation_dispatches'], 4)
            self.assertEqual(result['reason'], 'action_cap')
            self.assertFalse(result['first_level_complete'])
            self.assertFalse(result['lifecycle_certified'])
            self.assertFalse(result['outcome_claim_permitted'])
            self.assertEqual(len(engine.actions), 6)
            self.assertEqual(engine.close_calls, 1)
            self.assertEqual(result['diagnostics']['executed_decisions_after_full_unchanged'], 4)
            self.assertEqual(result['diagnostics']['repeated_previous_action_after_full_unchanged'], 4)

    def test_repetition_after_unchanged_can_be_required_for_delayed_success(self):
        value, events = retained(mode='delayed', variant='probe_instruction')
        engine = ScriptEngine(value, 'delayed')
        result = audit_continuation(value, 'probe_instruction', events, model=MODEL, replay_engine=engine)
        self.assertTrue(result['first_level_complete'])
        self.assertEqual(result['continuation_dispatches'], 2)
        self.assertEqual(result['diagnostics']['distinct_executed_full_actions'], 1)
        self.assertEqual(result['diagnostics']['visibly_changed_transitions'], 1)
        self.assertEqual(result['diagnostics']['repeated_previous_action_after_full_unchanged'], 2)

    def test_game_over_is_derived_from_observed_state(self):
        value, events = retained(mode='game_over')
        result = audit_continuation(value, 'baseline', events, model=MODEL)
        self.assertEqual(result['reason'], 'game_over')
        self.assertEqual(result['continuation_dispatches'], 1)
        self.assertFalse(result['first_level_complete'])

    def test_changed_pixels_and_prediction_accuracy_have_separate_denominators(self):
        value, events = retained(mode='changed', text=answer(prediction='yes'))
        result = audit_continuation(value, 'baseline', events, model=MODEL)
        self.assertEqual(result['diagnostics']['visibly_changed_transitions'], 4)
        self.assertEqual(result['diagnostics']['known_visible_change_predictions'], 4)
        self.assertEqual(result['diagnostics']['correct_known_visible_change_predictions'], 4)
        self.assertEqual(result['diagnostics']['unknown_visible_change_predictions'], 0)
        self.assertFalse(result['first_level_complete'])

    def test_all_request_fields_are_rebuilt_even_after_attacker_updates_body_hash(self):
        value, original = retained(variant='probe_instruction')
        for mutation in ('model', 'system', 'role', 'image', 'schema', 'tokens', 'seed', 'probe', 'geometry'):
            events = deepcopy(original)
            row = next(event for event in events if event['kind'] == 'request')
            body = row['body']
            if mutation == 'model': body['model'] = 'different-model'
            elif mutation == 'system': body['messages'][0]['content'] += ' changed'
            elif mutation == 'role': body['messages'][1]['role'] = 'assistant'
            elif mutation == 'image':
                part = next(p for p in body['messages'][1]['content'] if p['type'] == 'image_url')
                part['image_url']['url'] += 'changed'
            elif mutation == 'schema': body['response_format'] = {'type': 'text'}
            elif mutation == 'tokens': body['max_tokens'] = 257
            elif mutation == 'seed': body['seed'] = False
            elif mutation == 'probe': body['messages'][1]['content'][-1]['text'] = 'Repeat every action.'
            elif mutation == 'geometry':
                part = body['messages'][1]['content'][0]
                meta = json.loads(part['text']); meta['initial_objects'] = [{'invented': True}]
                part['text'] = json.dumps(meta)
            row['request_sha256'] = digest(body)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                audit_continuation(value, 'probe_instruction', events, model=MODEL)

    def test_stale_request_hash_and_wrong_condition_refuse(self):
        value, events = retained(variant='probe_instruction')
        next(event for event in events if event['kind'] == 'request')['request_sha256'] = '0'*64
        with self.assertRaises(ValueError): audit_continuation(value, 'probe_instruction', events, model=MODEL)
        _, events = retained(variant='probe_instruction')
        with self.assertRaises(ValueError): audit_continuation(value, 'baseline', events, model=MODEL)

    def test_summary_counters_labels_and_final_states_cannot_override_events(self):
        value, original = retained()
        for key, replacement in [('policy_calls', 0), ('prefix_dispatches', 0), ('continuation_dispatches', 0),
                                 ('reason', 'first_level_complete'), ('policy_calls', True),
                                 ('lifecycle_certified', True), ('variant', 'probe_instruction'),
                                 ('checkpoint_id', 'other')]:
            events = deepcopy(original)
            events[-1][key] = replacement
            with self.subTest(key=key, value=replacement), self.assertRaises(ValueError):
                audit_continuation(value, 'baseline', events, model=MODEL)
        events = deepcopy(original)
        events[-1]['final_observation']['levels_completed'] = 1
        with self.assertRaises(ValueError): audit_continuation(value, 'baseline', events, model=MODEL)

    def test_missing_prefix_wrong_prefix_and_observation_drift_refuse(self):
        value, original = retained()
        for kind in ('bootstrap_intent', 'initial', 'prefix_dispatch_intent', 'prefix_transition', 'checkpoint_ready'):
            events = deepcopy(original)
            index = next(i for i, event in enumerate(events) if event['kind'] == kind)
            del events[index]
            with self.subTest(missing=kind), self.assertRaises(ValueError):
                audit_continuation(value, 'baseline', events, model=MODEL)
        for kind in ('prefix_transition', 'checkpoint_ready', 'transition'):
            events = deepcopy(original)
            row = next(event for event in events if event['kind'] == kind)
            observation = row['after'] if kind == 'transition' else row['observation']
            if kind == 'transition':
                # This observation may only be checked against the next request
                # or an actual engine, so mutate its *before* chain instead.
                observation = row['before']
            observation['grid'][1][2] = 8
            with self.subTest(observation=kind), self.assertRaises(ValueError):
                audit_continuation(value, 'baseline', events, model=MODEL)

    def test_response_action_and_dispatch_intent_must_agree(self):
        value, events = retained()
        row = next(event for event in events if event['kind'] == 'response')
        row['text'] = answer({'action_id': 6, 'action_data': {'x': 3, 'y': 4}})
        with self.assertRaises(ValueError): audit_continuation(value, 'baseline', events, model=MODEL)
        _, events = retained()
        next(event for event in events if event['kind'] == 'dispatch_intent')['before_sha256'] = '0'*64
        with self.assertRaises(ValueError): audit_continuation(value, 'baseline', events, model=MODEL)

    def test_invalid_answer_is_retained_without_an_action_or_completion_credit(self):
        for text in ('not JSON', answer({'action_id': 7, 'action_data': {}})):
            value, events = retained(text=text)
            result = audit_continuation(value, 'baseline', events, model=MODEL)
            self.assertEqual(result['reason'], 'invalid_answer')
            self.assertEqual(result['policy_calls'], 1)
            self.assertEqual(result['continuation_dispatches'], 0)
            self.assertFalse(result['first_level_complete'])
            events[-1]['reason'] = 'first_level_complete'
            events[-1]['error'] = None
            with self.assertRaises(ValueError): audit_continuation(value, 'baseline', events, model=MODEL)

    def test_partial_restoration_and_pending_model_call_fail_closed(self):
        value = checkpoint()
        engine, events = ScriptEngine(value, fail_prefix=1), []
        with self.assertRaises(RuntimeError):
            continuation(value, 'baseline', engine, lambda body: answer(), events.append,
                         model=MODEL, deadline=100, now=lambda: 0)
        result = audit_continuation(value, 'baseline', events, model=MODEL)
        self.assertEqual(result['reason'], 'exception')
        self.assertEqual(result['prefix_dispatches'], 1)
        self.assertFalse(result['restoration_complete'])
        self.assertTrue(result['unconfirmed_dispatch'])
        self.assertFalse(result['first_level_complete'])
        engine, events = ScriptEngine(value), []
        def timeout(body): raise TimeoutError('injected model timeout')
        with self.assertRaises(TimeoutError):
            continuation(value, 'baseline', engine, timeout, events.append,
                         model=MODEL, deadline=100, now=lambda: 0)
        result = audit_continuation(value, 'baseline', events, model=MODEL)
        self.assertEqual(result['reason'], 'deadline')
        self.assertTrue(result['restoration_complete'])
        self.assertTrue(result['unconfirmed_model_call'])
        self.assertEqual(result['policy_calls'], 0)
        self.assertFalse(result['first_level_complete'])

    def test_post_response_deadline_cannot_credit_a_dispatch(self):
        value, events, clock = checkpoint(), [], [0]
        def complete(body):
            clock[0] = 101
            return answer()
        with self.assertRaises(TimeoutError):
            continuation(value, 'baseline', ScriptEngine(value), complete, events.append,
                         model=MODEL, deadline=100, now=lambda: clock[0])
        result = audit_continuation(value, 'baseline', events, model=MODEL)
        self.assertEqual(result['policy_calls'], 1)
        self.assertEqual(result['continuation_dispatches'], 0)
        self.assertFalse(result['first_level_complete'])

    def test_no_request_after_terminal_or_four_action_cap(self):
        for mode in ('delayed', 'unchanged'):
            value, events = retained(mode=mode)
            request = deepcopy(next(event for event in events if event['kind'] == 'request'))
            events.insert(-2, request)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                audit_continuation(value, 'baseline', events, model=MODEL)

    def test_actual_engine_drift_and_any_audit_failure_still_close_replay_engine(self):
        value, events = retained()
        for index in (0, 2):
            engine = ScriptEngine(value, mismatch_at=index)
            with self.subTest(index=index), self.assertRaises(ValueError):
                audit_continuation(value, 'baseline', events, model=MODEL, replay_engine=engine)
            self.assertEqual(engine.close_calls, 1)
        engine = ScriptEngine(value)
        altered = deepcopy(value)
        altered['decision_step'] = 3
        with self.assertRaises(ValueError):
            audit_continuation(altered, 'baseline', events, model=MODEL, replay_engine=engine)
        self.assertEqual(engine.close_calls, 1)

    def test_close_receipt_and_trailing_events_are_mandatory(self):
        value, original = retained()
        for mutation in ('missing', 'open', 'trailing', 'summary_extra', 'intent_extra'):
            events = deepcopy(original)
            if mutation == 'missing': del events[-2]
            elif mutation == 'open': events[-2]['receipt']['local_scorecard_closed'] = False
            elif mutation == 'trailing': events.append({'kind': 'extra'})
            elif mutation == 'summary_extra': events[-1]['completion_claim'] = True
            elif mutation == 'intent_extra': events[0]['extra'] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                audit_continuation(value, 'baseline', events, model=MODEL)


if __name__ == '__main__':
    unittest.main()
