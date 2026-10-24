"""Credential-free tests. All external transports and game operations are fake."""
from dataclasses import replace
import copy
import json
import multiprocessing
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from arcengine import GameState
from agent.e1_policy import CompletionResult
from agent.framework_adapter import OutcomeUnknown
from agent.state import Observation
from research.claude_arc_v1 import audit, config, policy, run, transport
from research.claude_arc_v1.arc import BoundedSession
from research.claude_arc_v1.backends import APIBackend, Budget, BudgetExceeded
from research.claude_arc_v1.cli import main, validate_live


def observation(game='ls20-test', level=0, state=GameState.NOT_FINISHED, frames=None, legal=(1, 6)):
    return Observation(game, tuple(np.asarray(f, dtype=np.uint8) for f in (frames or [[[0, 1], [0, 0]]])),
                       state, level, 3, 'guid-' + game, legal)


def settings(**kw):
    return replace(config.Config(), live_enabled=True, spend_limit_usd=10, max_actions_per_game=2, **kw)


class FakeTransport:
    def __init__(self, *, stop='end_turn', count=10, output=10, fail=False, model='claude-opus-5'):
        self.calls, self.stop, self.count, self.output, self.fail, self.model = [], stop, count, output, fail, model

    def __call__(self, url, method, headers, body, timeout):
        self.calls.append((url, headers, json.loads(body)))
        if self.fail:
            raise transport.TransportFailure('synthetic uncertain transport')
        if url.endswith('count_tokens'):
            value = {'input_tokens': self.count}
        else:
            value = {'model': self.model, 'id': 'synthetic', 'stop_reason': self.stop,
                'content': [{'type': 'thinking', 'thinking': 'synthetic'},
                            {'type': 'text', 'text': '{"action":{"action_id":1,"action_data":{}}}'}],
                'usage': {'input_tokens': 10, 'output_tokens': self.output}}
        return {'status': 200, 'body': json.dumps(value), 'headers': []}


class FakeBackend:
    def __init__(self, c, output=None):
        self.config, self.budget, self.requests, self.last_record = c, Budget(c), [], None
        self.output = output

    def complete(self, request):
        reserved = self.budget.reserve()
        self.requests.append(request)
        answer = {'action': {'action_id': 1, 'action_data': {}}}
        rank = config.STAGES.index(self.config.stage)
        if rank >= 2:
            answer['hypotheses'] = []
        if rank >= 3:
            answer['experiment'] = 'test an available control'
        if rank >= 4:
            answer['prediction'] = dict.fromkeys(policy.PREDICATES, None)
        if rank >= 5:
            answer['plan'] = []
        self.budget.settle(reserved, 10, 10)
        self.last_record = {'outcome': 'response_received', 'scripted': True}
        return CompletionResult(self.output if self.output is not None else json.dumps(answer), 10, 10, 0)


class FakeArc:
    def __init__(self, games=('ls20-test',), fail=None):
        self.games, self.fail, self.opened, self.closed = games, fail, 0, 0
        self.made, self.actions = [], []

    def list_game_ids(self):
        return self.games

    def open_scorecard(self, tags):
        self.opened += 1
        return 'synthetic-card'

    def bootstrap(self, game):
        if game in self.made:
            raise AssertionError('duplicate make')
        self.made.append(game)
        return SimpleNamespace(observation=observation(game), game_id=game)

    def dispatch(self, client, decision):
        self.actions.append(decision)
        if self.fail:
            raise self.fail('synthetic')
        client.observation = observation(client.game_id, 1, GameState.WIN)
        return client.observation

    def finalize_client(self, client):
        pass

    def close_scorecard(self):
        self.closed += 1
        return {'score': 1, 'card_id': 'synthetic-card'}


def completed_worker(url, method, headers, body, timeout, destination):
    Path(destination).write_text(json.dumps({'status': 200, 'headers': [], 'body': '{}'}))


def stalled_worker(url, method, headers, body, timeout, destination):
    Path(destination + '.partial').write_text('{')
    time.sleep(60)


class Configuration(unittest.TestCase):
    def test_default_plan_never_imports_arc_client_or_creates_transport(self):
        with patch('builtins.print'), patch.object(APIBackend, '__init__', side_effect=AssertionError('no client')):
            self.assertEqual(main(['--config', 'config/claude_arc_v1.example.json']), 0)

    def test_live_requires_separate_consent_and_keys(self):
        c = settings()
        args = dict(execute=True, confirm_paid=True, confirm_online=True, confirm_competition=False,
                    environ={'ARC_API_KEY': 'test-arc', 'ANTHROPIC_API_KEY': 'test-anthropic'})
        validate_live(c, **args)
        for key, value in (('confirm_paid', False), ('confirm_online', False), ('environ', {})):
            with self.subTest(key=key), self.assertRaises(PermissionError):
                validate_live(c, **{**args, key: value})
        with self.assertRaises(PermissionError):
            validate_live(config.Config(), **args)
        with self.assertRaises(PermissionError):
            validate_live(settings(mode='competition', games=()), **args)

    def test_invalid_caps_urls_and_nonfinite_json_refuse(self):
        for kw in ({'spend_limit_usd': float('nan')}, {'max_actions_per_game': True},
                   {'request_timeout_seconds': 0}, {'arc_base_url': 'https://evil.example'},
                   {'local_model_url': 'http://remote.example'}, {'mode': 'competition'}, {'games': ()}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                config.Config(**kw)
        for text in ('{"x":NaN}', '{"x":1e999}', '{"x":1,"x":2}'):
            with self.assertRaises(ValueError):
                config.strict_json(text)


class Backends(unittest.TestCase):
    def test_anthropic_translation_usage_and_reasoning_separation(self):
        c, fake = settings(), FakeTransport()
        b = APIBackend(c, Budget(c), transport=fake, key='test-key')
        result = b.complete(policy.Policy(c).request(observation()))
        self.assertEqual(len(fake.calls), 2)
        body = fake.calls[1][2]
        self.assertEqual(body['thinking'], {'type': 'adaptive'})
        self.assertEqual(body['output_config'], {'effort': 'medium'})
        self.assertNotIn('temperature', body)
        self.assertNotIn('seed', body)
        self.assertNotIn('synthetic', result.content)
        self.assertEqual((result.prompt_tokens, result.completion_tokens), (10, 10))
        self.assertEqual(b.budget.reserved_unknown, 0)

    def test_disabled_or_exhausted_budget_never_calls_network(self):
        for c in (config.Config(), replace(settings(), spend_limit_usd=0)):
            fake = FakeTransport()
            b = APIBackend(c, Budget(c), transport=fake, key='test-key')
            with self.assertRaises((BudgetExceeded, PermissionError)):
                b.complete(policy.Policy(c).request(observation()))
            self.assertEqual(fake.calls, [])

    def test_timeout_spends_attempt_and_preserves_unknown_reservation(self):
        c, fake = settings(max_model_calls=1), FakeTransport(fail=True)
        b = APIBackend(c, Budget(c), transport=fake, key='test-key')
        req = policy.Policy(c).request(observation())
        with self.assertRaises(transport.TransportFailure):
            b.complete(req)
        self.assertGreater(b.budget.reserved_unknown, 0)
        with self.assertRaises(BudgetExceeded):
            b.complete(req)
        self.assertEqual(len(fake.calls), 1)

    def test_bad_count_prevents_generation(self):
        c, fake = settings(), FakeTransport(count=9999999)
        b = APIBackend(c, Budget(c), transport=fake, key='test-key')
        with self.assertRaises(BudgetExceeded):
            b.complete(policy.Policy(c).request(observation()))
        self.assertEqual(len(fake.calls), 1)

    def test_truncation_and_wrong_model_do_not_return_actions(self):
        for kw in ({'stop': 'max_tokens'}, {'model': 'another-model'}, {'output': 999999}):
            c, fake = settings(), FakeTransport(**kw)
            b = APIBackend(c, Budget(c), transport=fake, key='test-key')
            with self.assertRaises(ValueError):
                b.complete(policy.Policy(c).request(observation()))
            self.assertIsNotNone(b.last_record.get('provider_response'))

    def test_local_backend_same_request_without_anthropic_key(self):
        c = settings(backend='local_openai', model='local-qwen', input_usd_per_million=0, output_usd_per_million=0)
        calls = []
        def fake(url, method, headers, body, timeout):
            calls.append((url, headers, json.loads(body)))
            if url.endswith('/tokenize'):
                return {'status': 200, 'headers': [], 'body': '{"count":10}'}
            return {'status': 200, 'headers': [], 'body': json.dumps({'model': 'local-qwen',
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10},
                'choices': [{'finish_reason': 'stop', 'message': {'content': '{"action":{"action_id":1,"action_data":{}}}'}}]})}
        b = APIBackend(c, Budget(c), transport=fake, key='')
        b.complete(policy.Policy(c).request(observation()))
        self.assertNotIn('x-api-key', calls[0][1])
        self.assertEqual(calls[0][0], 'http://127.0.0.1:8000/tokenize')
        self.assertEqual(calls[1][0], 'http://127.0.0.1:8000/v1/chat/completions')


class PolicyTests(unittest.TestCase):
    def test_exact_one_legal_action_and_strict_coordinates(self):
        p = policy.Policy(settings())
        for action in ({'action_id': True, 'action_data': {}}, {'action_id': 2, 'action_data': {}},
                       {'action_id': 0, 'action_data': {}}, {'action_id': 6, 'action_data': {'x': 2.5, 'y': 3}},
                       {'action_id': 6, 'action_data': {'x': 64, 'y': 3}},
                       {'action_id': 1, 'action_data': {'x': 2, 'y': 3}}):
            with self.subTest(action=action), self.assertRaises(ValueError):
                p.parse(json.dumps({'action': action}), observation())
        self.assertEqual(p.parse('{"action":{"action_id":6,"action_data":{"x":1,"y":1}}}', observation())[0].action_id, 6)

    def test_stages_are_cumulative_and_baseline_has_no_ledger(self):
        baseline = policy.Policy(settings()).request(observation())
        self.assertNotIn('history', json.loads(baseline['messages'][1]['content'])['evidence'])
        for stage in config.STAGES:
            p = policy.Policy(settings(stage=stage))
            raw = FakeBackend(p.config).complete(p.request(observation())).content
            p.parse(raw, observation())

    def test_transient_effect_and_prospective_prediction(self):
        c = settings(stage='world_model')
        p = policy.Policy(c)
        before = observation()
        answer = json.loads(FakeBackend(c).complete(p.request(before)).content)
        answer['prediction'] = {'any_frame_changed': True, 'final_frame_changed': False, 'level_increased': False}
        decision, answer = p.parse(json.dumps(answer), before)
        after = observation(frames=[[[1, 1], [0, 0]], [[0, 1], [0, 0]]])
        result = p.observe(before, decision, after, answer)
        self.assertTrue(all(x['correct'] for x in result['prediction_checks'].values()))

    def test_missing_reference_and_stale_level_claim_refuse_or_clear(self):
        c = settings(stage='hypotheses')
        p = policy.Policy(c)
        raw = {'action': {'action_id': 1, 'action_data': {}}, 'hypotheses': [
            {'id': 'h', 'statement': 'claim', 'status': 'supported_locally', 'evidence_ids': ['missing']}]}
        with self.assertRaises(ValueError):
            p.parse(json.dumps(raw), observation())
        raw['hypotheses'][0].update(status='tentative', evidence_ids=[])
        d, answer = p.parse(json.dumps(raw), observation())
        p.observe(observation(), d, observation(level=1), answer)
        self.assertEqual(p.hypotheses, [])


class Controller(unittest.TestCase):
    def execute(self, c, arc=None, backend=None):
        folder = Path(self.temp.name) / ('run-' + str(len(list(Path(self.temp.name).iterdir()))))
        evidence = run.Evidence(folder)
        arc, backend = arc or FakeArc(), backend or FakeBackend(c)
        result = run.evaluate(c, backend, arc, evidence)
        return result, folder, arc, backend

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp.cleanup()

    def test_normal_run_closes_one_card_and_independent_audit_matches(self):
        result, folder, arc, _ = self.execute(settings())
        self.assertTrue(result['full_lifecycle_complete'])
        self.assertEqual((arc.opened, arc.closed), (1, 1))
        checked = audit.audit(folder)
        self.assertEqual((checked['levels_recorded'], checked['actions_acknowledged']), (1, 1))
        self.assertFalse(checked['engine_replay_verified'])

    def test_invalid_response_closes_without_action_or_retry(self):
        c = settings()
        result, _, arc, backend = self.execute(c, backend=FakeBackend(c, 'bad json'))
        self.assertFalse(result['full_lifecycle_complete'])
        self.assertEqual((len(arc.actions), arc.closed, len(backend.requests)), (0, 1, 1))

    def test_unknown_dispatch_stops_and_closes(self):
        result, folder, arc, _ = self.execute(settings(), arc=FakeArc(fail=OutcomeUnknown))
        self.assertFalse(result['full_lifecycle_complete'])
        self.assertEqual(result['games'][0]['actions_uncertain'], 1)
        self.assertEqual((len(arc.actions), arc.closed), (1, 1))
        audit.audit(folder)

    def test_all_competition_inventory_once_and_fresh_game_memory(self):
        c = settings(mode='competition', games=(), stage='history')
        result, folder, arc, backend = self.execute(c, arc=FakeArc(('ls20-test', 'ar25-test')))
        self.assertEqual(arc.made, ['ls20-test', 'ar25-test'])
        self.assertEqual(result['games_not_started'], [])
        for request in backend.requests:
            self.assertEqual(json.loads(request['messages'][1]['content'])['evidence']['history'], [])
        audit.audit(folder)

    def test_changed_log_or_forged_level_summary_refuses(self):
        result, folder, _, _ = self.execute(settings())
        path = folder / 'summary.json'
        summary = json.loads(path.read_bytes())
        summary['games'][0]['levels_completed'] = 3
        path.write_text(json.dumps(summary))
        with self.assertRaises(ValueError):
            audit.audit(folder)
        summary['games'][0]['levels_completed'] = 1
        path.write_text(json.dumps(summary))
        log = folder / 'events.jsonl'
        log.write_text(log.read_text().replace('ls20-test', 'fake-game', 1))
        with self.assertRaisesRegex(ValueError, 'corruption'):
            audit.audit(folder)

    def test_logging_failure_cannot_skip_scorecard_close(self):
        c, arc = settings(), FakeArc()
        evidence = run.Evidence(Path(self.temp.name) / 'broken-log')
        original = evidence.write
        def failing(kind, **kw):
            if kind == 'scorecard_close_entered':
                raise OSError('synthetic log error')
            return original(kind, **kw)
        evidence.write = failing
        result = run.evaluate(c, FakeBackend(c), arc, evidence)
        self.assertEqual(arc.closed, 1)
        self.assertFalse(result['full_lifecycle_complete'])

    def test_budget_exhaustion_does_not_initialize_another_game(self):
        c = settings(games=('ls20', 'ar25'), max_model_calls=1)
        result, folder, arc, _ = self.execute(c, arc=FakeArc(('ls20-test', 'ar25-test')))
        self.assertEqual(arc.made, ['ls20-test'])
        self.assertEqual(arc.closed, 1)
        self.assertEqual(result['games_not_started'], ['ar25-test'])
        audit.audit(folder)

    def test_interrupt_still_closes_card(self):
        c, arc = settings(), FakeArc()
        backend = FakeBackend(c)
        backend.complete = lambda request: (_ for _ in ()).throw(KeyboardInterrupt())
        result, _, _, _ = self.execute(c, arc=arc, backend=backend)
        self.assertFalse(result['full_lifecycle_complete'])
        self.assertEqual(arc.closed, 1)

    def test_late_log_finalization_cannot_leave_a_passing_receipt(self):
        c, arc, clock = settings(), FakeArc(), [0.0]
        evidence = run.Evidence(Path(self.temp.name) / 'late-finalization')
        close = evidence.close
        def late_close():
            close()
            clock[0] = c.run_seconds + 1
        evidence.close = late_close
        result = run.evaluate(c, FakeBackend(c), arc, evidence, now=lambda: clock[0])
        self.assertFalse(result['full_lifecycle_complete'])
        self.assertFalse((evidence.folder / 'summary.json').exists())
        self.assertTrue((evidence.folder / 'failed-finalization.json').exists())

    def test_late_summary_rename_also_invalidates_receipt(self):
        import os
        c, arc, clock = settings(), FakeArc(), [0.0]
        evidence = run.Evidence(Path(self.temp.name) / 'late-rename')
        original = os.replace
        def late_replace(source, destination):
            original(source, destination)
            clock[0] = c.run_seconds + 1
        with patch('research.claude_arc_v1.run.os.replace', side_effect=late_replace):
            result = run.evaluate(c, FakeBackend(c), arc, evidence, now=lambda: clock[0])
        self.assertFalse(result['full_lifecycle_complete'])
        self.assertFalse((evidence.folder / 'summary.json').exists())

    def test_audit_rejects_forged_success_on_a_failed_run(self):
        c = settings()
        _, folder, _, _ = self.execute(c, backend=FakeBackend(c, 'not JSON'))
        path = folder / 'summary.json'
        value = json.loads(path.read_bytes())
        value.update(problems=[], full_lifecycle_complete=True)
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            audit.audit(folder)


class Transport(unittest.TestCase):
    def test_http_error_or_redirect_is_not_retried(self):
        for status in (302, 429, 500):
            calls = []
            def fake(*args):
                calls.append(args)
                return {'status': status, 'headers': [], 'body': 'not retained'}
            with self.assertRaises(Exception):
                BoundedSession('https://three.arcprize.org', lambda: 1, transport=fake).get('https://three.arcprize.org/api/games')
            self.assertEqual(len(calls), 1)

    def test_worker_result_is_complete_and_reaped(self):
        before = {p.pid for p in multiprocessing.active_children()}
        result = transport.request_once('https://unused.invalid', 'POST', {}, b'{}', 10, worker=completed_worker)
        self.assertEqual(result['status'], 200)
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)

    def test_partial_stalled_worker_hits_absolute_deadline_and_is_reaped(self):
        before = {p.pid for p in multiprocessing.active_children()}
        begin = time.monotonic()
        with self.assertRaises(transport.TransportFailure):
            transport.request_once('https://unused.invalid', 'POST', {}, b'{}', 2, worker=stalled_worker)
        self.assertLess(time.monotonic() - begin, 8)
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)


if __name__ == '__main__':
    unittest.main()
