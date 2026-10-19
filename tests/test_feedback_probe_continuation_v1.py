"""Fault and delayed-effect checks for injectable checkpoint continuations.

All engines and completion callbacks are local fakes. No actual game, model,
provider, or dispatch beyond these fake objects is used.
"""
from copy import deepcopy
import json
import unittest

from research.feedback_probe_v1.checkpoints import select_checkpoints
from research.feedback_probe_v1.continuation import continuation
from research.feedback_probe_v1.interface import VARIANTS
from tests.test_feedback_probe_checkpoints_v1 import MODEL, fixture


def selected():
    case, events = fixture()
    return select_checkpoints(case, events, model=MODEL)[0]


def response(action_id=1, action_data=None):
    return json.dumps({'action_id': action_id, 'action_data': action_data or {},
                       'predicted_visible_change': 'unknown'})


class Clock:
    def __init__(self):
        self.value = 0

    def __call__(self):
        return self.value


class FakeEngine:
    """Restore recorded prefix exactly, then return independently chosen states."""
    def __init__(self, checkpoint, *, initial_mutation=None, restore_mutation=None, followup=None):
        self.checkpoint = deepcopy(checkpoint)
        self.initial_mutation = initial_mutation
        self.restore_mutation = restore_mutation
        self.followup = followup
        self.actions, self.bootstrap_calls, self.close_calls = [], 0, 0

    def bootstrap(self):
        self.bootstrap_calls += 1
        observation = deepcopy(self.checkpoint['initial'])
        if self.initial_mutation:
            self.initial_mutation(observation)
        return observation

    def dispatch(self, action):
        index = len(self.actions)
        self.actions.append(deepcopy(action))
        prefix = self.checkpoint['prefix']
        if index < len(prefix):
            if action != prefix[index]['action']:
                raise AssertionError('the exact prefix action was not restored')
            observation = deepcopy(prefix[index]['after'])
            if self.restore_mutation:
                self.restore_mutation(index, observation)
            return observation
        observation = deepcopy(self.checkpoint['current'])
        if self.followup:
            self.followup(index - len(prefix), action, observation)
        return observation

    def close(self):
        self.close_calls += 1
        return {'closed': True, 'fake_engine_only': True}


class FeedbackProbeContinuationChecks(unittest.TestCase):
    def run_continuation(self, checkpoint, engine, complete, events, *, variant='baseline', clock=None, sink=None):
        return continuation(checkpoint, variant, engine, complete, sink or events.append,
                            model=MODEL, deadline=10, now=clock or (lambda: 0))

    def test_exact_prefix_is_replayed_before_any_policy_call_and_journal_matches_callback(self):
        checkpoint = selected()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                engine, events, calls = FakeEngine(checkpoint), [], []

                def complete(body):
                    if not calls:
                        self.assertEqual(engine.bootstrap_calls, 1)
                        self.assertEqual(engine.actions, [old['action'] for old in checkpoint['prefix']])
                        self.assertEqual(events[-2]['kind'], 'checkpoint_ready')
                    # Keep a copy of the exact sent request, then mutate the callback's
                    # private object to prove it cannot rewrite the retained journal.
                    calls.append(deepcopy(body))
                    body['messages'][0]['content'] = 'callback-local mutation'
                    return response()

                result = self.run_continuation(checkpoint, engine, complete, events, variant=variant)
                self.assertEqual([e['body'] for e in events if e['kind'] == 'request'], calls)
                self.assertEqual([e['action'] for e in events if e['kind'] == 'prefix_dispatch_intent'],
                                 [old['action'] for old in checkpoint['prefix']])
                self.assertEqual(result['prefix_dispatches'], len(checkpoint['prefix']))
                self.assertEqual(result['policy_calls'], 4)
                self.assertEqual(result['continuation_dispatches'], 4)
                self.assertEqual(result['reason'], 'action_cap')
                self.assertFalse(result['lifecycle_certified'])
                self.assertEqual(engine.close_calls, 1)

    def test_hidden_counter_allows_unchanged_repeat_then_level_completion(self):
        checkpoint = selected()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                def delayed_effect(index, action, observation):
                    self.assertEqual(action, checkpoint['prefix'][-1]['action'])
                    if index == 1:
                        observation['grid'][4][5] = 3
                        observation['levels_completed'] = 1

                engine = FakeEngine(checkpoint, followup=delayed_effect)
                events, calls = [], []

                def complete(body):
                    calls.append(deepcopy(body))
                    return response()

                result = self.run_continuation(checkpoint, engine, complete, events, variant=variant)
                self.assertEqual(result['reason'], 'first_level_complete')
                self.assertEqual(result['policy_calls'], 2)
                self.assertEqual(result['continuation_dispatches'], 2)
                self.assertEqual(engine.actions, [checkpoint['prefix'][-1]['action']]*4)
                transitions = [e for e in events if e['kind'] == 'transition']
                self.assertEqual(transitions[0]['before'], transitions[0]['after'])
                self.assertNotEqual(transitions[1]['before']['grid'], transitions[1]['after']['grid'])
                self.assertEqual(result['final_observation']['levels_completed'], 1)
                self.assertEqual(engine.close_calls, 1)

    def test_four_no_effect_repeats_are_retained_without_a_repeat_ban(self):
        checkpoint = selected()
        engine, events = FakeEngine(checkpoint), []
        result = self.run_continuation(checkpoint, engine, lambda _: response(), events,
                                       variant='probe_instruction')
        transitions = [e for e in events if e['kind'] == 'transition']
        self.assertEqual(len(transitions), 4)
        self.assertTrue(all(e['before'] == e['after'] for e in transitions))
        self.assertEqual(result['reason'], 'action_cap')
        self.assertEqual(result['continuation_dispatches'], 4)
        self.assertEqual(engine.close_calls, 1)

    def test_terminal_or_mismatched_restored_observation_refuses_before_policy(self):
        checkpoint = selected()
        mutations = {
            'terminal_win': lambda obs: obs.update(state='WIN'),
            'terminal_game_over': lambda obs: obs.update(state='GAME_OVER'),
            'levels_completed': lambda obs: obs.update(levels_completed=1),
            'legal_controls': lambda obs: obs.update(legal_actions=[6]),
            'grid': lambda obs: obs['grid'][0].__setitem__(0, 5),
        }
        for where in ('initial', 'prefix'):
            for label, mutation in mutations.items():
                with self.subTest(where=where, mutation=label):
                    engine = FakeEngine(checkpoint,
                        initial_mutation=mutation if where == 'initial' else None,
                        restore_mutation=(lambda index, obs, mutate=mutation: mutate(obs))
                        if where == 'prefix' else None)
                    events, calls = [], []

                    def complete(body):
                        calls.append(deepcopy(body))
                        return response()

                    with self.assertRaisesRegex(ValueError, 'restored'):
                        self.run_continuation(checkpoint, engine, complete, events)
                    self.assertEqual(calls, [])
                    self.assertEqual(engine.close_calls, 1)
                    self.assertEqual(events[-1]['kind'], 'summary')
                    self.assertEqual(events[-1]['reason'], 'exception')
                    self.assertEqual(events[-1]['policy_calls'], 0)
                    self.assertEqual(events[-1]['continuation_dispatches'], 0)

    def test_invalid_answer_is_retained_without_continuation_dispatch_or_retry(self):
        checkpoint = selected()
        for bad in ('not json', response(6, {'x': True, 'y': 8}), response(2)):
            with self.subTest(answer=bad):
                engine, events, calls = FakeEngine(checkpoint), [], []

                def complete(body):
                    calls.append(deepcopy(body))
                    return bad

                result = self.run_continuation(checkpoint, engine, complete, events)
                self.assertEqual(result['reason'], 'invalid_answer')
                self.assertEqual(result['policy_calls'], 1)
                self.assertEqual(result['continuation_dispatches'], 0)
                self.assertEqual(len(calls), 1)
                self.assertEqual([e['text'] for e in events if e['kind'] == 'response'], [bad])
                self.assertFalse(any(e['kind'] == 'dispatch_intent' for e in events))
                self.assertEqual(len(engine.actions), len(checkpoint['prefix']))
                self.assertEqual(engine.close_calls, 1)

    def test_slow_dispatch_evidence_write_closes_deadline_before_action(self):
        checkpoint = selected()
        engine, clock, events, calls = FakeEngine(checkpoint), Clock(), [], []

        def sink(event):
            events.append(event)
            if event['kind'] == 'dispatch_intent':
                clock.value = 10.01

        def complete(body):
            calls.append(deepcopy(body))
            return response()

        with self.assertRaises(TimeoutError):
            self.run_continuation(checkpoint, engine, complete, events, clock=clock, sink=sink)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(engine.actions), len(checkpoint['prefix']))
        self.assertFalse(any(e['kind'] == 'transition' for e in events))
        self.assertEqual(events[-1]['reason'], 'deadline')
        self.assertEqual(events[-1]['continuation_dispatches'], 0)
        self.assertEqual(engine.close_calls, 1)

    def test_slow_request_evidence_write_closes_deadline_before_model_callback(self):
        checkpoint = selected()
        engine, clock, events, calls = FakeEngine(checkpoint), Clock(), [], []

        def sink(event):
            events.append(event)
            if event['kind'] == 'request':
                clock.value = 10

        def complete(body):
            calls.append(body)
            return response()

        with self.assertRaises(TimeoutError):
            self.run_continuation(checkpoint, engine, complete, events, clock=clock, sink=sink)
        self.assertEqual(calls, [])
        self.assertEqual(len(engine.actions), len(checkpoint['prefix']))
        self.assertEqual(events[-1]['reason'], 'deadline')
        self.assertEqual(engine.close_calls, 1)

    def test_completion_callback_interruption_keeps_failure_and_closes_engine(self):
        checkpoint = selected()
        engine, events = FakeEngine(checkpoint), []
        interrupted = KeyboardInterrupt('injected policy callback interruption')

        def complete(_):
            raise interrupted

        with self.assertRaises(KeyboardInterrupt) as raised:
            self.run_continuation(checkpoint, engine, complete, events)
        self.assertIs(raised.exception, interrupted)
        self.assertEqual(engine.close_calls, 1)
        self.assertEqual(len(engine.actions), len(checkpoint['prefix']))
        self.assertEqual(events[-2]['kind'], 'closed')
        self.assertEqual(events[-1]['kind'], 'summary')
        self.assertEqual(events[-1]['reason'], 'exception')
        self.assertIn('KeyboardInterrupt', events[-1]['error'])
        self.assertEqual(events[-1]['policy_calls'], 0)
        self.assertEqual(events[-1]['continuation_dispatches'], 0)


if __name__ == '__main__':
    unittest.main()
