"""Gateway-startup regressions; safe GET polling never repeats mutable work."""
import unittest

import requests

from research.cpu_competition_v1 import runtime
from tests.test_cpu_competition_v1 import Adapter, Clock, program


class ReadinessAdapter(Adapter):
    def __init__(self, outcomes, clock):
        super().__init__()
        self.outcomes, self.clock, self.bounds = list(outcomes), clock, []

    def begin_readiness(self, bound):
        self.bounds.append(('begin', bound))

    def end_readiness(self):
        self.bounds.append(('end',))

    def list_game_ids(self):
        self.calls.append(('inventory',))
        value = self.outcomes.pop(0) if self.outcomes else requests.ConnectionError('still starting')
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            return value()
        return value


def http_error(status):
    response = requests.Response()
    response.status_code, response._content = status, b'not ready'
    response._content_consumed = True
    return requests.HTTPError(response=response)


class GatewayReadiness(unittest.TestCase):
    def fixture(self, outcomes, deadline=10.0):
        clock = Clock()
        adapter = ReadinessAdapter(outcomes, clock)
        slept, events = [], []
        def sleep(seconds):
            slept.append(seconds)
            clock.value += seconds
        return adapter, clock, sleep, slept, events

    def test_connection_refusal_then_ready_does_not_consume_a_mutable_attempt(self):
        adapter, clock, sleep, slept, events = self.fixture([
            requests.ConnectionError('synthetic not listening'), ('zz99-12345678',)])
        result = runtime.run(adapter, program(), work_deadline=10, now=clock,
                             sleep=sleep, log=events.append, max_actions=1)
        self.assertEqual(adapter.calls.count(('inventory',)), 2)
        self.assertEqual(adapter.calls.count(('open',)), 1)
        self.assertEqual(adapter.calls.count(('close',)), 1)
        self.assertEqual(result['actions_acknowledged'], 1)
        self.assertTrue(result['closed_verified'])
        self.assertEqual(slept, [1.0])
        self.assertEqual(adapter.bounds, [('begin', 10), ('end',)])
        self.assertEqual(events[-1], dict(phase='gateway_ready', GET_attempts=2))

    def test_immediate_readiness_uses_one_GET_and_no_sleep(self):
        adapter, clock, sleep, slept, _ = self.fixture([('zz99-12345678',)])
        runtime.run(adapter, program(), work_deadline=10, now=clock, sleep=sleep, max_actions=1)
        self.assertEqual(adapter.calls.count(('inventory',)), 1)
        self.assertEqual(slept, [])

    def test_only_transient_GET_failures_are_retried(self):
        errors = [requests.ConnectionError(), requests.Timeout(), TimeoutError()]
        errors += [http_error(code) for code in (429, 500, 502, 503, 504)]
        for error in errors:
            with self.subTest(error_type=type(error).__name__):
                adapter, clock, sleep, _, _ = self.fixture([error, ('zz99-12345678',)])
                result = runtime.run(adapter, program(), work_deadline=10,
                                     now=clock, sleep=sleep, max_actions=1)
                self.assertTrue(result['closed_verified'])
                self.assertEqual(adapter.calls.count(('open',)), 1)

    def test_permanent_statuses_and_malformed_JSON_fail_without_POST_or_retry(self):
        errors = [http_error(code) for code in (301, 400, 401, 403, 404, 409, 501)]
        errors += [ValueError('malformed JSON'), requests.exceptions.JSONDecodeError('bad', 'x', 0)]
        for error in errors:
            with self.subTest(error_type=type(error).__name__):
                adapter, clock, sleep, slept, _ = self.fixture([error])
                with self.assertRaises(type(error)):
                    runtime.run(adapter, program(), work_deadline=10, now=clock, sleep=sleep)
                self.assertEqual(adapter.calls, [('inventory',)])
                self.assertEqual(adapter.bounds[-1], ('end',))
                self.assertEqual(slept, [])

    def test_work_deadline_bounds_sleep_and_prevents_another_GET(self):
        adapter, clock, sleep, slept, _ = self.fixture([requests.ConnectionError()])
        with self.assertRaises(TimeoutError):
            runtime.run(adapter, program(), work_deadline=0.25, now=clock, sleep=sleep)
        self.assertEqual(clock.value, 0.25)
        self.assertEqual(slept, [0.25])
        self.assertEqual(adapter.calls, [('inventory',)])
        self.assertEqual(adapter.bounds, [('begin', 0.25), ('end',)])

    def test_readiness_is_limited_to_600_seconds_even_with_larger_work_budget(self):
        adapter, clock, sleep, slept, _ = self.fixture([])
        with self.assertRaises(TimeoutError):
            runtime.run(adapter, program(), work_deadline=3000, now=clock, sleep=sleep)
        self.assertEqual(clock.value, 600.0)
        self.assertEqual(sum(slept), 600.0)
        self.assertEqual(len(adapter.calls), 600)
        self.assertEqual(adapter.bounds, [('begin', 600.0), ('end',)])

    def test_inventory_that_arrives_after_deadline_cannot_open_scorecard(self):
        adapter, clock, sleep, _, _ = self.fixture([])
        def late():
            clock.value = 10.1
            return ('zz99-12345678',)
        adapter.outcomes = [late]
        with self.assertRaises(TimeoutError):
            runtime.run(adapter, program(), work_deadline=10, now=clock, sleep=sleep)
        self.assertEqual(adapter.calls, [('inventory',)])

    def test_bootstrap_timeout_is_not_retried_after_readiness_succeeds(self):
        adapter, clock, sleep, _, _ = self.fixture([('zz99-12345678',)])
        adapter.bootstrap_errors['zz99-12345678'] = requests.Timeout('synthetic lost reply')
        result = runtime.run(adapter, program(), work_deadline=10, now=clock, sleep=sleep)
        self.assertEqual(adapter.calls.count(('bootstrap', 'zz99-12345678')), 1)
        self.assertEqual(result['bootstrap_failures'], 1)
        self.assertEqual(adapter.decisions, [])


if __name__ == '__main__':
    unittest.main()
