"""The successor study service: the reviewed per-call contract over the verified counted client (scripted client and
clock; no server, model or GPU)."""
import json
import os
from pathlib import Path
import unittest

from certification.direct_publisher_smoke_v1.client import RequestFailed
from research.evidence_memory_v1.successor import plan as PL
from research.evidence_memory_v1.successor.service import StudyCallError, StudyService

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = PL.SESSIONS['A']['package']
POSIX = os.name == 'posix'


def metrics(prompt, queries=0, running=0, waiting=0, aborted=0):
    return (f'vllm:num_requests_running{{model_name="m"}} {running}\nvllm:num_requests_waiting{{model_name="m"}} {waiting}\n'
            f'vllm:prompt_tokens_total{{model_name="m"}} {prompt}\nvllm:prefix_cache_queries_total{{model_name="m"}} {queries}\n'
            f'vllm:request_success_total{{finished_reason="abort",model_name="m"}} {aborted}\n').encode()


def completion(content, prompt, tokens=5, finish='stop'):
    return json.dumps({'model': 'm', 'choices': [{'index': 0, 'message': {'content': content}, 'finish_reason': finish}],
                       'usage': {'prompt_tokens': prompt, 'completion_tokens': tokens}}).encode()


class Client:
    host, port, ledger, clock, served = '127.0.0.1', 1, None, None, 'm'


class Scripted:
    """call_by(request_id, body, deadline) answered by the next scripted handler; records ids and deadlines."""

    def __init__(self, now):
        self.now, self.handlers, self.calls = now, [], []

    def call_by(self, request_id, body, deadline):
        self.calls.append((request_id, round(deadline, 6)))
        return self.handlers.pop(0)(request_id, deadline)


class StudyServiceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen, cls.digest = PL.load_frozen(ROOT, PACKAGE)
        audit = json.loads((ROOT / PACKAGE / 'token-audit.json').read_bytes())
        cls.counts = PL.validate_audit(audit, cls.frozen, cls.digest)
        cls.requests = [request for _, _, _, request in PL.scheduled_requests(cls.frozen)[:4]]

    def service(self, mode='live'):
        self.t = [100.0]
        self.retained = {'server': [], 'cancellations': []}
        service = StudyService(Client(), self.frozen, self.digest, self.counts, mode=mode, launch={'argv': ['x']},
                               retain_server=self.retained['server'].append,
                               retain_cancellation=self.retained['cancellations'].append,
                               clock=lambda: self.t[0], sleep=lambda s: self.t.__setitem__(0, self.t[0] + s))
        service.client = Scripted(lambda: self.t[0])
        return service

    def step(self, seconds, status, raw):
        def handler(request_id, deadline):
            self.t[0] += seconds
            return status, raw
        return handler

    def started(self, total=500, queries=0):
        service = self.service()
        service.client.handlers.append(self.step(0.01, 200, metrics(total, queries)))
        if queries:
            with self.assertRaises(Exception):
                service.startup_check()
        else:
            service.startup_check()
        return service

    def prompt(self, request):
        return self.counts[PL.request_sha256(request)]

    def test_no_study_call_before_the_counters_show_prefix_caching_disabled(self):
        service = self.service()
        with self.assertRaisesRegex(StudyCallError, '^RuntimeError: startup canary'):
            service.complete(self.requests[0])
        broken = self.started(queries=7)
        self.assertIn('violation', self.retained['server'][-1])
        with self.assertRaisesRegex(StudyCallError, 'startup canary'):
            broken.complete(self.requests[0])

    def test_an_answer_carries_audited_tokens_counters_and_host_timing(self):
        service = self.started()
        request = self.requests[0]
        n = self.prompt(request)
        service.client.handlers += [self.step(0.5, 200, completion('{"values":["no_evidence"]}', n)),
                                    self.step(0.01, 200, metrics(500 + n))]
        result = service.complete(request, deadline=self.t[0] + 80)
        self.assertEqual((result['tokenizer_prompt_tokens'], result['server_prompt_tokens']), (n, n))
        self.assertTrue(result['cache_check']['prefix_caching_disabled_verified'])
        self.assertEqual(result['cache_check']['deadline_after_seconds'], 76)
        self.assertEqual(result['host_timing']['answered_after_seconds'], 0.5)
        ids = [c[0] for c in service.client.calls]
        self.assertEqual(ids, ['K0000', 'Q00000', 'M00000'])
        self.assertEqual(service.client.calls[1][1], round(100.01 + 60, 6))  # inference deadline: +60 s

    @unittest.skipUnless(POSIX, 'the reviewed runner imports POSIX-only run evidence (fcntl)')
    def test_rejections_and_parity_are_reported_as_the_reviewed_bridge_did(self):
        from research.evidence_memory_v1.successor.runner import classify
        service = self.started()
        unlisted = dict(self.requests[0], max_tokens=63)
        with self.assertRaises(StudyCallError) as caught:
            service.complete(unlisted)
        self.assertEqual(classify(caught.exception), 'rejected')
        request = self.requests[1]
        n = self.prompt(request)
        service.client.handlers += [self.step(0.2, 200, completion('{"values":["no_evidence"]}', n + 1)),
                                    self.step(0.01, 200, metrics(600 + n))]
        with self.assertRaisesRegex(StudyCallError, '^TokenParityViolation: token audit mismatch') as caught:
            service.complete(request)
        self.assertEqual(classify(caught.exception), 'transport_failure')
        service.calls = service.max_calls
        with self.assertRaises(StudyCallError) as caught:
            service.complete(self.requests[2])
        self.assertEqual(classify(caught.exception), 'rejected')

    @unittest.skipUnless(POSIX, 'the reviewed runner imports POSIX-only run evidence (fcntl)')
    def test_a_timeout_is_cancelled_and_verified_idle_by_counted_reads(self):
        from research.evidence_memory_v1.successor.runner import classify
        service = self.started()

        def hang(request_id, deadline):
            self.t[0] = deadline + 0.01
            raise RequestFailed(f'{request_id}: deadline exceeded')
        service.client.handlers += [hang, self.step(0.05, 200, metrics(500, running=1)),
                                    self.step(0.05, 200, metrics(500, aborted=1))]
        with self.assertRaises(StudyCallError) as caught:
            service.complete(self.requests[0])
        self.assertEqual(classify(caught.exception), 'timed_out')
        record = self.retained['cancellations'][-1][-1]
        self.assertTrue(record['idle'])
        self.assertEqual(record['timing']['inference_deadline_after_seconds'], 60)
        self.assertEqual(record['idle_verification']['aborted_total'], 1)
        self.assertEqual([c[0] for c in service.client.calls[1:]], ['Q00000', 'V00000', 'V00000'])
        self.assertTrue(all(deadline <= 100.01 + 76 for _, deadline in service.client.calls[2:]))

    def test_a_server_that_never_goes_idle_stops_the_service(self):
        service = self.started()

        def hang(request_id, deadline):
            self.t[0] = deadline + 0.01
            raise RequestFailed('deadline exceeded')
        service.client.handlers += [hang] + [self.step(0.01, 200, metrics(500, running=1))] * 200
        with self.assertRaisesRegex(StudyCallError, '^ServerNotIdle'):
            service.complete(self.requests[0])
        self.assertFalse(self.retained['cancellations'][-1][-1]['idle'])
        reads = [c for c in service.client.calls if c[0] == 'V00000']
        self.assertLessEqual(len(reads), PL.idle_reads())
        with self.assertRaisesRegex(StudyCallError, '^ServerNotIdle: service stopped'):
            service.complete(self.requests[1])

    @unittest.skipUnless(POSIX, 'the reviewed runner imports POSIX-only run evidence (fcntl)')
    def test_a_failure_before_the_deadline_is_a_transport_failure_without_idle_reads(self):
        from research.evidence_memory_v1.successor.runner import classify
        service = self.started()

        def refused(request_id, deadline):
            self.t[0] += 0.1
            raise RequestFailed('connection refused')
        service.client.handlers.append(refused)
        with self.assertRaises(StudyCallError) as caught:
            service.complete(self.requests[0])
        self.assertEqual(classify(caught.exception), 'transport_failure')
        self.assertEqual([c[0] for c in service.client.calls], ['K0000', 'Q00000'])

    def test_a_reply_after_the_call_bound_is_rejected(self):
        service = self.started()
        request = self.requests[0]
        n = self.prompt(request)
        service.client.handlers += [self.step(59, 200, completion('{"values":["no_evidence"]}', n)),
                                    self.step(4, 200, metrics(500 + n))]
        with self.assertRaisesRegex(StudyCallError, '^TimeoutError: reply expired'):
            service.complete(request, deadline=self.t[0] + 60)

    def test_counters_that_stop_showing_caching_disabled_stop_the_service(self):
        service = self.started()
        request = self.requests[0]
        n = self.prompt(request)
        service.client.handlers += [self.step(0.2, 200, completion('{"values":["no_evidence"]}', n)),
                                    self.step(0.01, 200, metrics(500 + n, queries=n))]
        with self.assertRaisesRegex(StudyCallError, '^ServerConfigViolation'):
            service.complete(request)
        self.assertIsNotNone(service.broken)

    def test_rehearsal_timing_is_the_reviewed_rehearsal_timing(self):
        self.assertEqual(PL.timing('rehearsal'), {'timeout': 2.0, 'teardown': 1, 'verify': 3.0, 'bound': 10.0})
        self.assertEqual(PL.timing('live'), {'timeout': 60, 'teardown': 1, 'verify': 15, 'bound': 80})


if __name__ == '__main__':
    unittest.main()
