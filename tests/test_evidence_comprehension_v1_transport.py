"""Evidence comprehension v1: absolute-deadline transport and metrics, server-side cancellation, cache verdicts (CPU fake)."""
import json
import time
import unittest

from research.evidence_comprehension_v1 import transport as T
from research.evidence_comprehension_v1.fake_server import HANG_AT, FakeVLLM
from research.evidence_comprehension_v1.probes import build_request, load_frozen

FROZEN, _ = load_frozen()
CONTEXTS = {c['context_id']: c for c in FROZEN['contexts']}
REQUESTS = [build_request(CONTEXTS[p['context_id']], p) for p in FROZEN['probes'][:HANG_AT + 2]]


def serve(fault, latency=0.0):
    return FakeVLLM(fault=fault, latency_seconds=latency).start()


def run_to_hang(server, timeout=1.0):
    call = T.CancellableTransport(server.base_url, timeout)
    for request in REQUESTS[:HANG_AT - 1]:
        call(request)
    with unittest.TestCase().assertRaises(T.CallTimedOut):
        call(REQUESTS[HANG_AT - 1])
    return call


class Transport(unittest.TestCase):
    def test_answers_and_positive_prefix_cache_evidence(self):
        server = serve('none')
        try:
            result = T.CancellableTransport(server.base_url, 5)(REQUESTS[0])
            self.assertEqual(result.finish_reason, 'stop')
            evidence = T.prefix_caching_evidence(T.read_metrics(server.base_url, time.monotonic() + 5))
            self.assertTrue(evidence['prefix_caching_disabled_verified'])
        finally:
            server.close()

    def test_enabled_prefix_cache_is_detected(self):
        server = serve('prefix_cache_enabled')
        try:
            T.CancellableTransport(server.base_url, 5)(REQUESTS[0])
            evidence = T.prefix_caching_evidence(T.read_metrics(server.base_url, time.monotonic() + 5))
            self.assertFalse(evidence['prefix_caching_disabled_verified'])
        finally:
            server.close()

    def test_no_prompt_yet_is_not_verification(self):
        server = serve('none')
        try:
            values = T.read_metrics(server.base_url, time.monotonic() + 5)
            self.assertFalse(T.prefix_caching_evidence(values)['prefix_caching_disabled_verified'])
        finally:
            server.close()

    def test_timeout_closes_the_connection_and_the_server_aborts(self):
        server = serve('hang_once')
        try:
            started = time.monotonic()
            call = run_to_hang(server)
            self.assertLess(time.monotonic() - started, 4)
            evidence = T.verify_idle(server.base_url, time.monotonic() + 5)
            self.assertTrue(evidence['idle'], evidence)
            self.assertEqual(evidence['aborted_total'], 1)
            self.assertIn(('aborted', HANG_AT), server.log)
            call(REQUESTS[HANG_AT])  # the server keeps serving after the abort
        finally:
            server.close()

    def test_caller_deadline_overrides_the_timeout(self):
        server = serve('hang_once')
        try:
            call = T.CancellableTransport(server.base_url, 30)
            for request in REQUESTS[:HANG_AT - 1]:
                call(request)
            started = time.monotonic()
            with self.assertRaises(T.CallTimedOut):
                call(REQUESTS[HANG_AT - 1], deadline=started + 0.8)
            self.assertLess(time.monotonic() - started, 0.8 + T.TEARDOWN_SECONDS + 0.3)
        finally:
            server.close()

    def test_slow_abort_within_the_window_is_verified(self):
        server = serve('slow_abort')
        try:
            run_to_hang(server)
            evidence = T.verify_idle(server.base_url, time.monotonic() + 3)
            self.assertTrue(evidence['idle'], evidence)
            self.assertGreaterEqual(evidence['waited_seconds'], 0.5)
        finally:
            server.close()

    def test_late_abort_fails_by_the_deadline(self):
        server = serve('late_abort')
        try:
            run_to_hang(server)
            started = time.monotonic()
            evidence = T.verify_idle(server.base_url, started + 2)
            self.assertFalse(evidence['idle'])
            self.assertLess(time.monotonic() - started, 2 + 0.5)
        finally:
            server.close()

    def test_ignored_disconnect_fails_idle_verification(self):
        server = serve('no_abort')
        try:
            run_to_hang(server)
            evidence = T.verify_idle(server.base_url, time.monotonic() + 2)
            self.assertFalse(evidence['idle'])
            self.assertEqual(evidence['running'], 1)
        finally:
            server.close()

    def test_trickling_metrics_are_cut_off_at_the_deadline(self):
        server = serve('trickle_metrics')
        try:
            run_to_hang(server)
            started = time.monotonic()
            with self.assertRaises(T.MetricsTimedOut):
                T.read_metrics(server.base_url, started + 1.0)
            self.assertLess(time.monotonic() - started, 1.0 + T.TEARDOWN_SECONDS + 0.3)
            started = time.monotonic()
            evidence = T.verify_idle(server.base_url, started + 1.5)
            self.assertFalse(evidence['idle'])
            self.assertLess(time.monotonic() - started, 1.5 + T.TEARDOWN_SECONDS + 0.5)
        finally:
            server.close()

    def test_idle_observed_after_the_deadline_is_rejected(self):
        # Review of r1: a 15 s check returned success after 20 s. Scaled: each read takes 0.6 s; idle on the
        # second read, which completes after the 1.0 s deadline.
        reads = []

        def slow_reader(url, deadline, clock=time.monotonic):
            time.sleep(0.6)
            reads.append(clock())
            running = 1 if len(reads) == 1 else 0
            return {'vllm:num_requests_running': running, 'vllm:num_requests_waiting': 0}
        started = time.monotonic()
        evidence = T.verify_idle('http://127.0.0.1:1', started + 1.0, reader=slow_reader)
        self.assertFalse(evidence['idle'], evidence)
        self.assertEqual(evidence['error'], 'observation completed after the deadline')
        self.assertLess(time.monotonic() - started, 1.5)

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
        for bad in (float('nan'), float('inf'), None, True):
            with self.assertRaises((ValueError, TypeError)):
                T.read_metrics('http://127.0.0.1:8000', bad)


class Verdicts(unittest.TestCase):
    def test_cache_verdict_is_recomputed_from_counters(self):
        good = {'prompt_tokens_total': 120, 'prefix_cache_queries_total': 0, 'prefix_cache_hits_total': 0}
        self.assertTrue(T.cache_verdict(good))
        self.assertTrue(T.cache_verdict({**good, 'prefix_cache_hits_total': None}))
        for bad in ({**good, 'prefix_cache_queries_total': 999, 'prefix_cache_hits_total': 999,
                     'prefix_caching_disabled_verified': True},  # the review's forged record
                    {**good, 'prompt_tokens_total': 0}, {**good, 'prompt_tokens_total': -5},
                    {**good, 'prompt_tokens_total': float('nan')}, {**good, 'prefix_cache_queries_total': None},
                    {**good, 'prefix_cache_queries_total': True}, {**good, 'prefix_cache_hits_total': 3},
                    {'prefix_caching_disabled_verified': True}, None):
            with self.subTest(bad=bad):
                self.assertFalse(T.cache_verdict(bad) if bad is not None else T.cache_verdict({}))

    def test_idle_verdict_is_recomputed_from_measurements(self):
        good = {'idle': True, 'running': 0.0, 'waiting': 0.0, 'waited_seconds': 1.2}
        self.assertTrue(T.idle_verdict(good, 15))
        for bad in ({**good, 'running': 1.0}, {**good, 'waiting': None}, {**good, 'waited_seconds': 20.0},
                    {**good, 'waited_seconds': float('nan')}, {**good, 'waited_seconds': -1},
                    {**good, 'running': True}, {'idle': True}):
            with self.subTest(bad=bad):
                self.assertFalse(T.idle_verdict(bad, 15))

    def test_metric_parsing(self):
        values = T.parse_metrics('# HELP x\nvllm:num_requests_running{a="1"} 2\nvllm:num_requests_running{a="2"} 1\n'
                                 'vllm:request_success_total{finished_reason="abort",m="x"} 3\nbad line\nx NaN\n')
        self.assertEqual(T.metric_total(values, 'vllm:num_requests_running'), 3)
        self.assertIsNone(T.metric_total(values, 'vllm:num_requests_waiting'))
        self.assertEqual(T.server_load(values)['aborted_total'], 3)
        self.assertFalse(T.verify_idle('http://127.0.0.1:1', time.monotonic() + 0.3)['idle'])  # unreachable


if __name__ == '__main__':
    unittest.main()
