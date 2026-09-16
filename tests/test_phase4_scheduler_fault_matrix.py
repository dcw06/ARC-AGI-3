"""Local baseline scheduler/fault coverage; no GPU or batching performance claim."""
from concurrent.futures import ThreadPoolExecutor
import errno
import threading
import unittest
from unittest.mock import patch

from agent.e1_policy import CompletionResult
from agent.scheduler import FairInferenceQueue, QueuedInferenceExecutor
from certification.phase4_v1.local_probe import probe, ScriptedCompletion
from certification.phase4_v1.lifecycle import evaluate_local_record
from agent.framework_adapter import LocalFrameworkAdapter


class SchedulerFaultMatrixTests(unittest.TestCase):
    def test_priority_unit_is_sequence_not_identity_payload_or_generation(self):
        q = FairInferenceQueue()
        seen = []
        for index, (identity, generation, state) in enumerate(
                [('z', 999, 'large'), ('a', 0, ''), ('m', 42, 'small')]):
            q.submit(identity, generation, state, lambda i=index: seen.append(i))
        while q.size:
            q.service_one()
        self.assertEqual(seen, [0, 1, 2])

    def test_new_arrivals_cannot_overtake_waiting_requests(self):
        q = FairInferenceQueue()
        seen = []
        for i in range(110):
            q.submit(str(i), 0, 's', lambda i=i: seen.append(i))
        for i in range(110):
            q.service_one()
            q.submit('new-' + str(i), 0, 's', lambda: seen.append('new'))
        self.assertEqual(seen, list(range(110)))

    def test_age_boundary_and_expired_head_does_not_block_next(self):
        for age, expected in [(299.999, True), (300, True), (300.001, False)]:
            with self.subTest(age=age):
                q = FairInferenceQueue(max_age_seconds=300)
                seen = []
                old = q.submit('old', 0, 's', lambda: seen.append('old'))
                new = q.submit('new', 0, 's', lambda: seen.append('new'))
                old.submitted_monotonic = 1000 - age
                new.submitted_monotonic = 1000
                with patch('agent.scheduler.time.monotonic', return_value=1000):
                    q.service_one(); q.service_one()
                self.assertEqual(seen, ['old', 'new'] if expected else ['new'])
                self.assertEqual(old.canceled.is_set(), not expected)

    def test_cancel_and_supersession_are_client_isolated(self):
        for cancel in (False, True):
            q = FairInferenceQueue()
            seen = []
            stale = q.submit('a', 0, 'old', lambda: self.fail('stale callback'))
            if cancel:
                q.cancel_client('a')
            q.submit('a', 1, 'new', lambda: seen.append('a'))
            q.submit('b', 0, 'other', lambda: seen.append('b'))
            while q.size:
                q.service_one()
            self.assertTrue(stale.canceled.is_set())
            self.assertEqual(seen, ['a', 'b'])

    def test_worker_topologies_bound_concurrency_and_preserve_110_results(self):
        # Occupy every worker before release; assert overlap without timing guesses.
        # These are admission waves, not vLLM GPU batch measurements.
        for workers in (1, 2, 8):
            with self.subTest(workers=workers):
                gate, ready = threading.Event(), threading.Event()
                lock = threading.Lock()
                active = peak = entered = 0
                def callback(i):
                    nonlocal active, peak, entered
                    with lock:
                        active += 1; entered += 1; peak = max(peak, active)
                        if active == workers:
                            ready.set()
                    try:
                        if not gate.wait(5):
                            raise TimeoutError('test release missing')
                        return (i, 'x' * (1 + i % 9))
                    finally:
                        with lock:
                            active -= 1
                executor = QueuedInferenceExecutor(worker_count=workers)
                try:
                    with ThreadPoolExecutor(max_workers=16) as callers:
                        futures = [callers.submit(executor.execute, client_id=str(i),
                            generation=0, state_hash=str(i), callback=lambda i=i: callback(i),
                            timeout_seconds=10) for i in range(110)]
                        try:
                            self.assertTrue(ready.wait(5), 'workers did not overlap')
                        finally:
                            gate.set()
                        self.assertEqual([f.result(10) for f in futures],
                                         [(i, 'x' * (1 + i % 9)) for i in range(110)])
                    self.assertEqual(entered, 110)
                    self.assertEqual(peak, workers)
                finally:
                    gate.set(); executor.close()
                self.assertTrue(all(not w.is_alive() for w in executor._workers))

    def test_model_and_storage_errors_do_not_poison_worker_or_retry(self):
        with QueuedInferenceExecutor(worker_count=8) as executor:
            for error in (TimeoutError('model timeout'), ConnectionError('model disconnected'),
                          OSError(errno.ENOSPC, 'disk full'), PermissionError('read only')):
                with self.subTest(error=type(error).__name__):
                    calls = []
                    def fail():
                        calls.append(1)
                        raise error
                    with self.assertRaises(type(error)):
                        executor.execute(client_id='a', generation=0, state_hash='s', callback=fail)
                    self.assertEqual(calls, [1])
                    self.assertEqual(executor.execute(client_id='b', generation=0,
                        state_hash='s', callback=lambda: 'healthy'), 'healthy')

    def test_model_failures_degrade_to_legal_actual_environment_actions(self):
        for error in (TimeoutError('timeout'), ConnectionError('disconnect')):
            with self.subTest(error=type(error).__name__):
                with patch.object(ScriptedCompletion, 'complete', side_effect=error) as call:
                    record = probe()['record']
                self.assertTrue(evaluate_local_record(record, expected_fault='policy_error')['passed'])
                self.assertEqual(call.call_count, 2)
                self.assertEqual(record['result']['acknowledged_actions'], 2)

    def test_forbidden_workspace_request_falls_back_without_tool_execution(self):
        with patch('agent.e1_policy.SafeOperationWorkspace') as workspace, \
             patch.object(ScriptedCompletion, 'complete', return_value=CompletionResult(
                '{"operation":"read_file","arguments":{"path":"/not-authorized"}}')):
            record = probe()['record']
        workspace.assert_not_called()
        self.assertTrue(evaluate_local_record(record, expected_fault='policy_error')['passed'])
        self.assertEqual(record['result']['policy_failures'], 2)

    def test_storage_failure_at_finalization_never_claims_success_or_retries(self):
        for error in (OSError(errno.ENOSPC, 'disk full'), PermissionError('read only')):
            with patch.object(LocalFrameworkAdapter, 'close_scorecard', side_effect=error) as close:
                value = probe()
            self.assertEqual(close.call_count, 1)
            self.assertFalse(value['evaluation']['passed'])
            self.assertEqual(value['record']['finalization_status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
