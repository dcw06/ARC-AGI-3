"""Evidence comprehension v1: total-deadline transport, server-side cancellation and cache metrics (CPU fake)."""
import json
import time
import unittest

from research.evidence_comprehension_v1 import transport as T
from research.evidence_comprehension_v1.fake_server import HANG_AT, FakeVLLM
from research.evidence_comprehension_v1.probes import build_request
from scripts.build_evidence_comprehension_v1 import OUTPUT

FROZEN = json.loads(OUTPUT.read_bytes())
CONTEXTS = {c['context_id']: c for c in FROZEN['contexts']}
REQUESTS = [build_request(CONTEXTS[p['context_id']], p) for p in FROZEN['probes'][:HANG_AT + 2]]


def serve(fault, latency=0.0):
    return FakeVLLM(fault=fault, latency_seconds=latency).start()


class Transport(unittest.TestCase):
    def test_answers_and_positive_prefix_cache_evidence(self):
        server = serve('none')
        try:
            call = T.CancellableTransport(server.base_url, 5)
            result = call(REQUESTS[0])
            self.assertEqual(result.finish_reason, 'stop')
            self.assertIn('answer', json.loads(result.content) if result.content != 'not json' else {'answer': 1})
            evidence = T.prefix_caching_evidence(T.read_metrics(server.base_url))
            self.assertTrue(evidence['prefix_caching_disabled_verified'])
        finally:
            server.close()

    def test_enabled_prefix_cache_is_detected(self):
        server = serve('prefix_cache_enabled')
        try:
            T.CancellableTransport(server.base_url, 5)(REQUESTS[0])
            evidence = T.prefix_caching_evidence(T.read_metrics(server.base_url))
            self.assertFalse(evidence['prefix_caching_disabled_verified'])
            self.assertGreater(evidence['prefix_cache_queries_total'], 0)
        finally:
            server.close()

    def test_no_prompt_yet_is_not_verification(self):
        server = serve('none')
        try:
            self.assertFalse(T.prefix_caching_evidence(T.read_metrics(server.base_url))['prefix_caching_disabled_verified'])
        finally:
            server.close()

    def test_timeout_closes_the_connection_and_the_server_aborts(self):
        server = serve('hang_once')
        try:
            call = T.CancellableTransport(server.base_url, 1.0)
            for request in REQUESTS[:HANG_AT - 1]:
                call(request)
            started = time.monotonic()
            with self.assertRaises(T.CallTimedOut):
                call(REQUESTS[HANG_AT - 1])
            self.assertLess(time.monotonic() - started, 3)  # total deadline, not a per-read timeout
            evidence = T.verify_idle(server.base_url, 5)
            self.assertTrue(evidence['idle'], evidence)
            self.assertEqual(evidence['aborted_total'], 1)
            self.assertIn(('aborted', HANG_AT), server.log)
            call(REQUESTS[HANG_AT])  # the server keeps serving after the abort
        finally:
            server.close()

    def test_ignored_disconnect_fails_idle_verification(self):
        server = serve('no_abort')
        try:
            call = T.CancellableTransport(server.base_url, 1.0)
            for request in REQUESTS[:HANG_AT - 1]:
                call(request)
            with self.assertRaises(T.CallTimedOut):
                call(REQUESTS[HANG_AT - 1])
            evidence = T.verify_idle(server.base_url, 2)
            self.assertFalse(evidence['idle'])
            self.assertEqual(evidence['running'], 1)
        finally:
            server.close()

    def test_http_error_and_invalid_settings(self):
        server = serve('http_error')
        try:
            call = T.CancellableTransport(server.base_url, 5)
            for request in REQUESTS[:HANG_AT - 1]:
                call(request)
            with self.assertRaises(ConnectionError):
                call(REQUESTS[HANG_AT - 1])
        finally:
            server.close()
        for bad in (0, -1, float('inf'), float('nan'), True):
            with self.assertRaises(ValueError):
                T.CancellableTransport('http://127.0.0.1:8000', bad)
        with self.assertRaises(ValueError):
            T.CancellableTransport('http://example.com:8000', 5)

    def test_metric_parsing(self):
        values = T.parse_metrics('# HELP x\nvllm:num_requests_running{a="1"} 2\nvllm:num_requests_running{a="2"} 1\n'
                                 'vllm:request_success_total{finished_reason="abort",m="x"} 3\nbad line\nx NaN\n')
        self.assertEqual(T.metric_total(values, 'vllm:num_requests_running'), 3)
        self.assertIsNone(T.metric_total(values, 'vllm:num_requests_waiting'))
        self.assertEqual(T.server_load(values)['aborted_total'], 3)
        self.assertFalse(T.verify_idle('http://127.0.0.1:1', 0.3)['idle'])  # unreachable: never "idle"


if __name__ == '__main__':
    unittest.main()
