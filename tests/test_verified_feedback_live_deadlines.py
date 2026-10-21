"""Admission cutoffs preserve exact prefixes without certifying hard overruns."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.verified_feedback_v1.flow import run_case
from research.verified_feedback_live_v1.audit import audit_case
from research.verified_feedback_live_v1.live_evaluation import audit_study
from research.verified_feedback_live_v1.live_worker import study, MODEL, canary
from certification.direct_publisher_smoke_v1.accounting import Clock as BudgetClock
from tests.test_verified_feedback_v1 import selected, answer, candidates, FakeEngine, Clock
from tests.verified_feedback_live_fixture import create, protocol_patches
from tests.feedback_probe_live_fixture import EffectEngine
from tests.test_feedback_probe_audit_v1 import ScriptEngine


class DeadlinePrefixes(unittest.TestCase):
    def run_prefix(self, boundary):
        cp = selected(); pair = candidates(cp, 0); clock = Clock(); events = []; replies = []
        engine = FakeEngine(cp)
        original_close = engine.close
        def close():
            result = original_close()
            if boundary == 'close': clock.value = 10
            return result
        engine.close = close
        def emit(event):
            events.append(deepcopy(event))
            if ((boundary == 'complete' and event['kind'] == 'transition' and event['decision'] == 1) or
                (boundary == 'partial' and event['kind'] == 'transition' and event['decision'] == 0) or
                (boundary == 'request' and event['kind'] == 'request' and event['decision'] == 1) or
                (boundary == 'response' and event['kind'] == 'response' and event['decision'] == 0) or
                (boundary == 'commit' and event['kind'] == 'forecast_commit') or
                (boundary == 'dispatch' and event['kind'] == 'dispatch_intent' and event['decision'] == 0) or
                (boundary == 'bootstrap' and event['kind'] == 'bootstrap_intent') or
                (boundary == 'restore' and event['kind'] == 'restore_dispatch_intent')):
                clock.value = 10
        def reply(_):
            text = answer(first=not replies, prediction='none'); replies.append(text); return text
        result = run_case(cp, pair, 'verified_feedback', engine, reply, emit, deadline=10, now=clock)
        self.assertEqual(engine.close_calls, 1)
        return cp, pair, result, events

    def test_cutoff_after_last_action_keeps_action_cap(self):
        cp, pair, result, events = self.run_prefix('complete')
        self.assertEqual((result['reason'], result['model_calls'], result['new_dispatches']), ('action_cap', 2, 2))
        self.assertIsNone(result['error'])
        self.assertEqual(audit_case(cp, pair, 'verified_feedback', events, FakeEngine(cp)), result)

    def test_cutoff_during_close_does_not_relabel_finished_science(self):
        _, _, result, _ = self.run_prefix('close')
        self.assertEqual(result['reason'], 'action_cap')
        self.assertIsNone(result['error'])

    def test_partial_answer_unissued_request_and_undispatched_commit_replay(self):
        for boundary, calls, dispatches in (('partial', 1, 1), ('request', 1, 1), ('commit', 1, 0),
                ('response', 1, 0), ('dispatch', 1, 0), ('bootstrap', 0, 0), ('restore', 0, 0)):
            with self.subTest(boundary=boundary):
                cp, pair, result, events = self.run_prefix(boundary)
                self.assertEqual((result['reason'], result['model_calls'], result['new_dispatches']),
                                 ('deadline', calls, dispatches))
                self.assertEqual(sum(e['kind'] == 'admission_stop' for e in events), 1)
                self.assertEqual(audit_case(cp, pair, 'verified_feedback', events, FakeEngine(cp)), result)

    def test_forged_stop_boundary_and_missing_stop_receipt_refuse(self):
        cp, pair, _, events = self.run_prefix('partial')
        for mode in ('boundary', 'missing', 'negative', 'late'):
            changed = deepcopy(events)
            stop = next(e for e in changed if e['kind'] == 'admission_stop')
            if mode == 'boundary': stop['check_index'] += 1
            elif mode == 'missing': changed.remove(stop)
            elif mode == 'negative': stop['overrun_seconds'] = -1
            else: stop['overrun_seconds'] = 300
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                audit_case(cp, pair, 'verified_feedback', changed, FakeEngine(cp))

    def test_unwitnessed_engine_timeout_is_not_a_graceful_admission_stop(self):
        cp = selected(); engine = FakeEngine(cp); events = []
        original = engine.dispatch
        def dispatch(action):
            if len(engine.actions) == len(cp['prefix']): raise TimeoutError('engine transport stalled')
            return original(action)
        engine.dispatch = dispatch
        with self.assertRaisesRegex(TimeoutError, 'transport stalled'):
            run_case(cp, candidates(cp, 0), 'verified_feedback', engine, lambda _: answer(),
                     events.append, deadline=10, now=lambda: 0)
        self.assertEqual(engine.close_calls, 1)
        self.assertFalse(any(e['kind'] == 'admission_stop' for e in events))


class UnstartedConditions(unittest.TestCase):
    def check_partial_lifecycle(self, inputs, output):
        # Reuse the established synthetic provider/lifecycle fixture. A valid
        # lifecycle must not promote missing study work to technical completion.
        from tests.test_verified_feedback_live_evaluation import ProbeLiveEvaluationChecks
        helper = ProbeLiveEvaluationChecks()
        helper.inputs = inputs
        review, lock, pin, provider = helper.lifecycle(output)
        evaluated = helper.live(output, review, lock, pin, provider)
        self.assertTrue(evaluated['lifecycle_certified'])
        self.assertFalse(evaluated['technically_complete'])
        self.assertFalse(evaluated['study_schedule_complete'])

    def test_one_partial_condition_and_all_remaining_slots_are_scored(self):
        with tempfile.TemporaryDirectory() as folder:
            seed = Path(folder)/'seed'; seed.mkdir()
            inputs, _, _ = create(seed)
            output = Path(folder)/'partial'; output.mkdir()
            clock = Clock(); clock.value = 100
            def call(client, identity, body):
                _, entry = client.ledger.admit(identity)
                text = 'ok' if body == canary() else answer(first=identity.endswith('/0'), choice='B', prediction='none')
                entry.update(outcome='http_200', seconds=0.01)
                return 200, json.dumps({'model': MODEL,
                    'choices': [{'message': {'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}}).encode()
            def bounded(cp, pair, variant, engine, reply, sink, *, deadline):
                def emit(event):
                    sink(event)
                    if event['kind'] == 'transition': clock.value = deadline
                return run_case(cp, pair, variant, engine, reply, emit, deadline=deadline, now=clock)
            with ExitStack() as stack:
                protocol_patches(stack)
                stack.enter_context(patch('research.verified_feedback_live_v1.live_worker.time.monotonic', side_effect=clock))
                stack.enter_context(patch('research.verified_feedback_live_v1.live_worker.Clock',
                    side_effect=lambda limits, started: BudgetClock(limits, started, now=clock)))
                stack.enter_context(patch('research.verified_feedback_live_v1.live_worker.Client.call', new=call))
                stack.enter_context(patch('research.verified_feedback_live_v1.live_worker.run_case', side_effect=bounded))
                completed = study({'inputs': str(inputs), 'input_manifest_sha256': 'synthetic', 'started': 100, 'port': 1},
                    output, token_audit=lambda _: 100, engine_factory=lambda cp, variant, effect: EffectEngine(cp, effect))
                self.assertEqual(completed[0]['reason'], 'deadline')
                self.assertEqual([r['reason'] for r in completed[1:]], ['not_admitted']*15)
                result = audit_study(output, inputs, token_audit=lambda _: 100,
                                     replay_factory=lambda cp, variant: ScriptEngine(cp))
            self.assertEqual(result['phase_coverage'], dict(scheduled=32, reached=1, valid=1))
            self.assertEqual(result['generations'], 2)
            self.assertEqual(result['continuation_dispatches'], 1)
            self.assertEqual(result['local_scorecards'], 1)
            self.assertFalse(result['study_schedule_complete'])
            self.check_partial_lifecycle(inputs, output)

    def test_headroom_stop_keeps_all_slots_without_opening_engines(self):
        with tempfile.TemporaryDirectory() as folder:
            seed = Path(folder)/'seed'; seed.mkdir()
            inputs, _, _ = create(seed)
            output = Path(folder)/'partial'; output.mkdir()
            def call(client, identity, body):
                self.assertEqual(body, canary())
                _, entry = client.ledger.admit(identity)
                entry.update(outcome='http_200', seconds=0.01)
                return 200, json.dumps({'model': MODEL,
                    'choices': [{'message': {'role': 'assistant', 'content': 'ok'}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 1, 'total_tokens': 101}}).encode()
            def engine(*args): raise AssertionError('unadmitted condition opened an engine')
            with ExitStack() as stack:
                protocol_patches(stack)
                stack.enter_context(patch('research.verified_feedback_live_v1.live_worker.time.monotonic', return_value=2881))
                stack.enter_context(patch('research.verified_feedback_live_v1.live_worker.Clock',
                    side_effect=lambda limits, started: BudgetClock(limits, started, now=lambda: 2881)))
                stack.enter_context(patch('research.verified_feedback_live_v1.live_worker.Client.call', new=call))
                completed = study({'inputs': str(inputs), 'input_manifest_sha256': 'synthetic', 'started': 0, 'port': 1},
                                  output, token_audit=lambda _: 100, engine_factory=engine)
                self.assertEqual(len(completed), 16)
                self.assertEqual({r['reason'] for r in completed}, {'not_admitted'})
                result = audit_study(output, inputs, token_audit=lambda _: 100, replay_factory=engine)
            self.assertEqual(result['phase_coverage'], dict(scheduled=32, reached=0, valid=0))
            self.assertEqual(result['generations'], 1)
            self.assertEqual(result['offline_actions_including_bootstraps'], 0)
            self.assertFalse(result['study_schedule_complete'])
            self.check_partial_lifecycle(inputs, output)


class CleanupReserve(unittest.TestCase):
    def test_close_uses_reserve_without_reopening_dispatch(self):
        from research.verified_feedback_live_v1.engine import FeedbackEngine
        engine = object.__new__(FeedbackEngine)
        engine.deadline, engine.cleanup_deadline, engine.closing = 3000, 3300, False
        def close(base):
            self.assertEqual(base.deadline, 3300)
            return {'closed': True}
        with patch('research.initial_geometry_assistance_v1.engine_bridge.BridgeEngine.close', new=close):
            self.assertEqual(engine.close(), {'closed': True})
        with self.assertRaisesRegex(RuntimeError, 'cleanup started'): engine.bootstrap()
        with self.assertRaisesRegex(RuntimeError, 'cleanup started'): engine.dispatch({'action_id': 1})

    def test_bad_cleanup_bounds_refuse_before_process_creation(self):
        from research.verified_feedback_live_v1.engine import FeedbackEngine
        with patch('research.initial_geometry_assistance_v1.engine_bridge.BridgeEngine.__init__') as constructor:
            for cleanup in (True, float('inf'), float('nan'), 3000, 3300.1):
                with self.subTest(cleanup=cleanup), self.assertRaises(ValueError):
                    FeedbackEngine(None, None, None, None, None, 3000,
                                   cleanup_deadline=cleanup, env={}, on_effect=lambda _: None)
            constructor.assert_not_called()


if __name__ == '__main__': unittest.main()
