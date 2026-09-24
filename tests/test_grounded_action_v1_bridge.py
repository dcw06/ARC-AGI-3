"""Bounded model-process bridge retention without model or GPU startup."""
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from certification.phase4_integrated_v2.bridge import BridgeServer, ModelProxy, request_hash
from certification.phase4_integrated_v2.response_evidence import ResponseValidationError, capture
from research.grounded_action_v1.bridge_service import BridgeService, ProxyService, canary_request
from research.grounded_action_v1.local import ScriptedAdapter, ScriptedService, run
from research.grounded_action_v1.replay import evaluate

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(hasattr(__import__('socket'), 'AF_UNIX'), 'Unix socket required')
class GroundedBridgeTests(unittest.TestCase):
    def test_readiness_requires_complete_exact_canary_and_artifact(self):
        request = canary_request()
        body = '{"action":{"action_id":6,"action_data":{"x":0,"y":0}}}'
        digest = request_hash(request)
        audit = {'request_sha256': digest, 'tokenizer_prompt_tokens': 10,
                 'server_prompt_tokens': 10, 'server_completion_tokens': 20,
                 'finish_reason': 'stop'}
        canary = {'status': 'passed', 'request': request, 'request_sha256': digest,
                  **capture(body, audit)}
        ready = {'artifact': {'sha256': 'fixture'}, 'startup_seconds': 899,
                 'canary_audit': canary}

        def check(value):
            proxy = SimpleNamespace(started=False, call=lambda _message: value)
            adapter = ProxyService(proxy)
            adapter.connect_ready(expected_artifact={'sha256': 'fixture'})
            return proxy

        self.assertTrue(check(ready).started)
        mutations = []
        for field in ('response_content', 'response_bytes', 'response_sha256', 'audit'):
            value = copy.deepcopy(ready)
            del value['canary_audit'][field]
            mutations.append((field, value))
        for field, bad in (('status', 'failed'), ('request_sha256', '0' * 64),
                           ('response_sha256', 'a' * 64), ('response_truncated', True)):
            value = copy.deepcopy(ready)
            value['canary_audit'][field] = bad
            mutations.append((field, value))
        value = copy.deepcopy(ready)
        value['canary_audit']['request']['messages'][0]['content'] = 'different'
        mutations.append(('request', value))
        value = copy.deepcopy(ready)
        value['canary_audit']['request']['seed'] = False  # False == 0 under dict equality.
        mutations.append(('request_type', value))
        for field, bad in (('request_sha256', 'b' * 64), ('server_prompt_tokens', 11),
                           ('tokenizer_prompt_tokens', None), ('server_completion_tokens', 129),
                           ('finish_reason', 'length')):
            value = copy.deepcopy(ready)
            value['canary_audit']['audit'][field] = bad
            mutations.append(('audit_' + field, value))
        value = copy.deepcopy(ready)
        wrong = '{"action":{"action_id":6,"action_data":{"x":64,"y":0}}}'
        value['canary_audit'].update(response_content=wrong, response_bytes=len(wrong.encode()),
                                     response_sha256=hashlib.sha256(wrong.encode()).hexdigest())
        mutations.append(('illegal_action', value))
        for field, bad in (('startup_seconds', 901), ('artifact', {'sha256': 'other'})):
            value = copy.deepcopy(ready)
            value[field] = bad
            mutations.append((field, value))
        for name, value in mutations:
            with self.subTest(name=name):
                proxy = SimpleNamespace(started=False, call=lambda _message, v=value: v)
                with self.assertRaises(ValueError):
                    ProxyService(proxy).connect_ready(expected_artifact={'sha256': 'fixture'})
                self.assertFalse(proxy.started)

    def exercise(self, server_prompt_tokens, *, finish='stop', client_deadline=3):
        class Tokens:
            def apply_chat_template(self, *_args, **_kwargs):
                return [1] * 10

        calls = []

        def transport(request):
            calls.append(request)
            return SimpleNamespace(content='{"action":{"action_id":6,"action_data":{"x":0,"y":0}}}',
                                   prompt_tokens=10 if len(calls) == 1 else server_prompt_tokens,
                                   completion_tokens=22,
                                   finish_reason=finish)

        with tempfile.TemporaryDirectory() as folder, \
                patch('research.grounded_action_v1.model_service.verify'), \
                patch('research.grounded_action_v1.model_service.importlib.metadata.version',
                      side_effect=lambda name: {'transformers': '4.57.6', 'tokenizers': '0.22.2',
                                                'jinja2': '3.1.6'}[name]):
            scratch = Path(folder)
            service = BridgeService('unused', transport, tokenizer=Tokens())
            service.startup_canary()
            service.artifact = {'sha256': 'fixture'}
            service.startup_seconds = .1
            server = BridgeServer(scratch / 'model.sock', service, time.monotonic() + 5, scratch / 'cancel')
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
            thread.start()
            proxy = ModelProxy(scratch, 'unused', time.monotonic() + client_deadline, scratch / 'cancel')
            request = {'model': service.guard.protocol['model_id'], 'messages': [
                {'role': 'system', 'content': 'Return only JSON'}, {'role': 'user', 'content': '{}'}],
                'temperature': 0, 'seed': 0, 'max_tokens': 128,
                'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_object'}}
            try:
                self.assertFalse(proxy.started)
                ProxyService(proxy).connect_ready(expected_artifact={'sha256': 'fixture'})
                return proxy.complete(request), calls
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_valid_completion_crosses_bridge_once(self):
        result, calls = self.exercise(10)
        self.assertEqual(result.content[:9], '{"action"')
        self.assertEqual(len(calls), 2)

    def test_token_mismatch_retains_body_and_counts_across_bridge(self):
        with self.assertRaises(ResponseValidationError) as raised:
            self.exercise(11)
        evidence = raised.exception.response_evidence
        self.assertIn('"action"', evidence['response_content'])
        self.assertEqual(evidence['audit']['tokenizer_prompt_tokens'], 10)
        self.assertEqual(evidence['audit']['server_prompt_tokens'], 11)
        self.assertEqual(evidence['audit']['finish_reason'], 'stop')
        self.assertEqual(len(evidence['response_sha256']), 64)

    def test_canary_mismatch_retained_before_study_admission(self):
        class Tokens:
            def apply_chat_template(self, *_args, **_kwargs):
                return [1] * 10

        def bad_transport(_request):
            return SimpleNamespace(content='{"action":{"action_id":6,"action_data":{"x":0,"y":0}}}',
                                   prompt_tokens=11, completion_tokens=22, finish_reason='stop')

        with patch('research.grounded_action_v1.model_service.verify'), \
                patch('research.grounded_action_v1.model_service.importlib.metadata.version',
                      side_effect=lambda name: {'transformers': '4.57.6', 'tokenizers': '0.22.2',
                                                'jinja2': '3.1.6'}[name]):
            retained = []
            service = BridgeService('unused', bad_transport, tokenizer=Tokens(),
                                    retain_canary=lambda record: retained.append(json.loads(json.dumps(record))))
            with self.assertRaises(ResponseValidationError):
                service.startup_canary()
            self.assertEqual([record['status'] for record in retained],
                             ['attempted', 'received', 'failed'])
            self.assertIn('"action"', retained[1]['response_content'])
            self.assertEqual(retained[1]['audit']['server_prompt_tokens'], 11)
            self.assertEqual(service.canary_audit['status'], 'failed')
            self.assertIn('"action"', service.canary_audit['response_content'])
            self.assertEqual(service.canary_audit['audit']['server_prompt_tokens'], 11)
            self.assertEqual(service.calls, 0)
            with self.assertRaisesRegex(RuntimeError, 'already attempted'):
                service.startup_canary()

    def test_full_local_runner_uses_bridge_and_replays(self):
        class Tokens:
            def apply_chat_template(self, *_args, **_kwargs):
                return [1] * 10

        fixture = ScriptedService()

        def transport(request):
            raw = fixture.complete(request)
            return SimpleNamespace(content=raw['content'], prompt_tokens=10,
                                   completion_tokens=16, finish_reason=raw['finish_reason'])

        with tempfile.TemporaryDirectory() as folder, \
                patch('research.grounded_action_v1.model_service.verify'), \
                patch('research.grounded_action_v1.model_service.importlib.metadata.version',
                      side_effect=lambda name: {'transformers': '4.57.6', 'tokenizers': '0.22.2',
                                                'jinja2': '3.1.6'}[name]):
            scratch = Path(folder)
            service = BridgeService('unused', transport, tokenizer=Tokens())
            # The startup canary uses the same ACTION6 schema as the fixture.
            service.startup_canary()
            service.artifact = {'sha256': 'fixture'}
            service.startup_seconds = .1
            server = BridgeServer(scratch / 'model.sock', service, time.monotonic() + 45, scratch / 'cancel')
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
            thread.start()
            proxy = ModelProxy(scratch, 'unused', time.monotonic() + 45, scratch / 'cancel')
            try:
                ProxyService(proxy).connect_ready(expected_artifact={'sha256': 'fixture'})
                result = run(scratch / 'run.json', ProxyService(proxy),
                             lambda arm: ScriptedAdapter(arm), deadline_seconds=30)
                self.assertEqual(result['status'], 'complete', result['error'])
                self.assertEqual((evaluate(result)['calls'], service.calls), (12, 12))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
