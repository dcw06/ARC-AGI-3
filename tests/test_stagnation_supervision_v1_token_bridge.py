"""CPU-only checks of exact reflection counting across the isolated model socket."""
import copy
import hashlib
from pathlib import Path
import tempfile
import threading
import time
import unittest

from certification.phase4_integrated_v2.bridge import ModelProxy, request_hash
from research.action_effect_history_v1.rehearsal import FixtureTokenizer
from research.stagnation_supervision_v1 import intervention as I
from research.stagnation_supervision_v1.closed_loop import bridge as B, model_service as MS, token_bridge as TB


def request():
    return B.reflection_request(I.PROMPT + '\n\nEvidence:\n{}')


class TokenBridgeTests(unittest.TestCase):
    def service(self):
        service = MS.SupervisionModelService('rehearsal', lambda _request: None,
                                             tokenizer=FixtureTokenizer(), check_versions=False)
        service.canary_audit = {'status': 'passed'}
        return service

    def test_exact_count_is_hash_bound_and_does_not_charge_inference(self):
        service = self.service()
        req = request()
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            cancel = scratch / 'cancel'
            deadline = time.monotonic() + 5
            with TB.TokenBridgeServer(scratch / 'model.sock', service, deadline, cancel) as server:
                proxy = ModelProxy(scratch, 'unused', deadline, cancel)
                proxy.started = True  # an already verified ready handshake in the worker
                thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
                thread.start()
                try:
                    count = TB.worker_count(proxy, req)
                    self.assertEqual(count, service._admit(req))
                    self.assertEqual(B.worker_token_counter('rehearsal', proxy)(req['messages'][1]['content']), count)
                    self.assertEqual(B.worker_token_counter('live', proxy)(req['messages'][1]['content']), count)
                    self.assertEqual(service.token_count_calls, 3)
                    self.assertEqual((service.calls, service.reflection_calls), (0, 0))
                    self.assertEqual(proxy.audit_records, [])
                    with self.assertRaisesRegex(RuntimeError, 'request hash'):
                        proxy.call({'op': TB.COUNT_OP, 'request': req, 'request_sha256': '0' * 64})
                    self.assertEqual((service.calls, service.reflection_calls), (0, 0))
                finally:
                    server.shutdown()
                    thread.join(timeout=2)

    def test_count_requires_ready_and_exact_reflection_contract(self):
        service = self.service()
        req = request()
        with self.assertRaisesRegex(RuntimeError, 'not ready'):
            TB.worker_count(type('Proxy', (), {'started': False})(), req)
        service.canary_audit = None
        with self.assertRaisesRegex(RuntimeError, 'not ready'):
            TB.count_reflection(service, req, request_hash(req))
        service.canary_audit = {'status': 'passed'}
        bad = copy.deepcopy(req)
        bad['max_tokens'] += 1
        with self.assertRaisesRegex(ValueError, 'frozen model settings'):
            TB.count_reflection(service, bad, request_hash(bad))
        self.assertEqual((service.calls, service.reflection_calls), (0, 0))

    def test_reply_binding_and_count_ceiling(self):
        req = request()
        digest = request_hash(req)

        class Proxy:
            started = True
            def call(self, _message):
                return {'request_sha256': '0' * 64, 'prompt_tokens': 1}

        with self.assertRaisesRegex(ValueError, 'bridge reply'):
            TB.worker_count(Proxy(), req)
        service = self.service()
        service.token_count_calls = TB.MAX_COUNT_CALLS
        with self.assertRaisesRegex(ValueError, 'count ceiling'):
            TB.count_reflection(service, req, digest)
        self.assertEqual((service.calls, service.reflection_calls), (0, 0))

    def test_canary_mutations_are_rejected_before_bridge_ready(self):
        service = self.service()
        canary = MS.canary_request()
        body = '{"action":{"action_id":6,"action_data":{"x":1,"y":1}}}'
        raw = body.encode()
        prompt = service._admit(canary)
        ready = {'artifact': {'rehearsal': 'scripted_model_not_target_evidence'}, 'startup_seconds': 1,
                 'canary_audit': {'status': 'passed', 'request': canary,
                                  'request_sha256': MS.request_hash(canary), 'response_content': body,
                                  'response_bytes': len(raw), 'response_sha256': hashlib.sha256(raw).hexdigest(),
                                  'response_truncated': False,
                                  'audit': {'request_sha256': MS.request_hash(canary),
                                            'tokenizer_prompt_tokens': prompt, 'server_prompt_tokens': prompt,
                                            'server_completion_tokens': 12, 'finish_reason': 'stop'}}}
        MS.validate_ready(ready, ready['artifact'])
        for field, bad in [('tokenizer_prompt_tokens', True), ('tokenizer_prompt_tokens', 0),
                           ('server_prompt_tokens', -1), ('server_completion_tokens', True),
                           ('server_completion_tokens', 0), ('server_completion_tokens', 129)]:
            with self.subTest(field=field, bad=bad):
                changed = copy.deepcopy(ready)
                changed['canary_audit']['audit'][field] = bad
                with self.assertRaisesRegex(ValueError, 'canary evidence'):
                    MS.validate_ready(changed, ready['artifact'])


if __name__ == '__main__':
    unittest.main()
