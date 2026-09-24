"""CPU lifecycle tests for the GPU-disabled Stage B host."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from certification.phase4_integrated_v2.bridge import ModelProxy
from research.grounded_action_v1.bridge_service import BridgeService, ProxyService
from research.grounded_action_v1.target_host import serve_host


class Tokens:
    def apply_chat_template(self, *_args, **_kwargs):
        return [1] * 10


class Owner:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


@unittest.skipUnless(hasattr(__import__('socket'), 'AF_UNIX'), 'Unix socket required')
class HostTests(unittest.TestCase):
    def setUp(self):
        self.version = patch('research.grounded_action_v1.model_service.importlib.metadata.version',
                             side_effect=lambda name: {'transformers': '4.57.6', 'tokenizers': '0.22.2',
                                                       'jinja2': '3.1.6'}[name])
        self.binding = patch('research.grounded_action_v1.model_service.verify')
        self.version.start()
        self.binding.start()
        self.addCleanup(self.version.stop)
        self.addCleanup(self.binding.stop)

    def factory(self, retained, _deadline):
        owner = Owner()
        self.owner = owner
        service = BridgeService('unused', lambda _request: SimpleNamespace(
            content='{"action":{"action_id":6,"action_data":{"x":0,"y":0}}}',
            prompt_tokens=10, completion_tokens=20, finish_reason='stop'),
            tokenizer=Tokens(), retain_canary=retained)
        service.artifact = {'sha256': 'fixture'}
        return service, owner

    def test_ready_handshake_and_cancellation_close_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            cancel = scratch / 'cancel'
            result = []
            thread = threading.Thread(target=lambda: result.append(serve_host(
                scratch / 'model.sock', scratch / 'evidence', cancel,
                deadline=time.monotonic() + 10, service_factory=self.factory)))
            thread.start()
            try:
                limit = time.monotonic() + 3
                while not (scratch / 'model.sock').exists() and time.monotonic() < limit:
                    time.sleep(.02)
                self.assertTrue((scratch / 'model.sock').exists())
                proxy = ModelProxy(scratch, 'unused', time.monotonic() + 3, cancel)
                self.assertFalse(proxy.started)
                ready = ProxyService(proxy).connect_ready(expected_artifact={'sha256': 'fixture'})
                self.assertTrue(proxy.started)
                self.assertEqual(ready['canary_audit']['status'], 'passed')
                canary = json.loads((scratch / 'evidence/worker/canary.json').read_bytes())
                self.assertEqual(canary['status'], 'passed')
                self.assertEqual(len(canary['response_sha256']), 64)
            finally:
                cancel.touch()
                thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result[0]['status'], 'stopped')
            self.assertTrue(self.owner.closed)

    def test_startup_failure_retains_receipt_and_has_no_ready_socket(self):
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)

            def fail(_retain, _deadline):
                raise TimeoutError('fixture model startup')

            result = serve_host(scratch / 'model.sock', scratch / 'evidence', scratch / 'cancel',
                                deadline=time.monotonic() + 5, service_factory=fail)
            self.assertEqual(result['status'], 'failed')
            receipt = json.loads((scratch / 'evidence/worker/failure.json').read_bytes())
            self.assertIn('fixture model startup', receipt['error'])
            self.assertFalse((scratch / 'model.sock').exists())

    def test_preexisting_cancel_blocks_factory(self):
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            (scratch / 'cancel').touch()
            called = []
            result = serve_host(scratch / 'model.sock', scratch / 'evidence', scratch / 'cancel',
                                deadline=time.monotonic() + 5,
                                service_factory=lambda *_: called.append(True))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(called, [])
            self.assertIn('admission closed', result['error'])

    def test_evidence_exhaustion_rejects_readiness_and_closes_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            result = serve_host(scratch / 'model.sock', scratch / 'evidence', scratch / 'cancel',
                                deadline=time.monotonic() + 5, service_factory=self.factory,
                                evidence_limit=512)
            self.assertEqual(result['status'], 'failed')
            self.assertIn('evidence exhausted', result['error'])
            self.assertTrue(self.owner.closed)
            self.assertFalse((scratch / 'model.sock').exists())
            self.assertTrue((scratch / 'evidence/worker/failure.json').exists())


if __name__ == '__main__':
    unittest.main()
