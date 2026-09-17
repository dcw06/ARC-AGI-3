from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from agent.scheduler import QueuedInferenceExecutor, InferenceQueueError
from certification.phase4_v6.measurement import (
    RequestTimeline, MeasuredInference, validate_telemetry, save_bounded)
from certification.phase4_v6.evaluate import capacity_from_worker


class MeasurementTests(unittest.TestCase):
    def test_checkpoint_write_does_not_block_inference_completions(self):
        from certification.phase4_v1.lifecycle import validate_freeze
        from certification.phase4_v6 import worker
        from types import SimpleNamespace
        _, rows = validate_freeze()
        release = threading.Event()
        completed = threading.Event()
        checkpoints = []

        def client(row, adapter, factory, watchdog):
            if row != rows[0] and not release.wait(5):
                raise TimeoutError('checkpoint did not release clients')
            policy = factory(None)
            policy.inference.execute(client_id='test', generation=0, state_hash='s',
                callback=lambda: policy.client.complete({'client': row['client_id']}))
            if row != rows[0]:
                completed.set()
            return {'client_id': row['client_id']}

        class Store:
            def save(self, name, value):
                checkpoints.append(value)
                if len(checkpoints) == 2:
                    release.set()
                    if not completed.wait(5):
                        raise TimeoutError('checkpoint blocked inference completion')

        with tempfile.TemporaryDirectory() as directory, patch.object(worker, 'run_client', client):
            root = Path(directory)
            state = worker.run_workload(rows, lambda row: object(),
                lambda row, watchdog: SimpleNamespace(complete=lambda request: 'ok'),
                root/'state.json', root/'cancel', evidence_store=Store())
        self.assertEqual(state['status'], 'complete', state['error'])
        self.assertIsNone(state['error'])
        self.assertEqual(len(state['clients']), 110)
        self.assertEqual(checkpoints[0]['clients'], [])
        self.assertEqual(len(checkpoints[1]['clients']), 1)
        self.assertEqual(len(checkpoints[-1]['request_timeline']), 110)

    def test_timeline_snapshot_is_detached_from_later_updates(self):
        timeline = RequestTimeline(time.monotonic())
        timeline.events.append({'request_id': 'request-0', 'outcome': 'pending'})
        snapshot = timeline.snapshot()
        timeline.events[0]['outcome'] = 'completed'
        timeline.events.append({'request_id': 'request-1'})
        self.assertEqual(snapshot, [{'request_id': 'request-0', 'outcome': 'pending'}])
        snapshot[0]['outcome'] = 'changed'
        self.assertEqual(timeline.events[0]['outcome'], 'completed')

    def test_110_worker_instrumentation_does_not_change_requests(self):
        from certification.phase4_v1.lifecycle import validate_freeze
        from certification.phase4_v4 import worker as old
        from certification.phase4_v6 import worker as new
        from agent.e1_policy import CompletionResult
        _, rows = validate_freeze()
        class Completion:
            def complete(self, request):
                return CompletionResult('unchanged')
        def client(row, adapter, factory, watchdog):
            policy = factory(None)
            request = {'model': 'local-test-only', 'messages': [{'content': row['client_id']}]}
            value = policy.inference.execute(client_id='same-policy-key', generation=0,
                state_hash='s', callback=lambda: policy.client.complete(request))
            return {'client_id': row['client_id'], 'test_result': value.content}
        states = []
        for module in (old, new):
            with tempfile.TemporaryDirectory() as directory, patch.object(module, 'run_client', side_effect=client):
                root = Path(directory)
                states.append(module.run_workload(rows, lambda row: object(),
                    lambda row, watchdog: Completion(), root / 'state.json', root / 'cancel'))
        self.assertEqual(states[1]['status'], 'complete', states[1].get('error'))
        self.assertEqual(sorted((r['client_id'], r['request_sha256']) for r in states[0]['requests']),
                         sorted((r['client_id'], r['request_sha256']) for r in states[1]['requests']))
        self.assertEqual(len(states[1]['request_timeline']), 110)
        candidate = capacity_from_worker(states[1])
        self.assertIsNone(candidate['C_admit'])
        states[1]['requests'][0]['request_id'] = 'not-in-timeline'
        with self.assertRaises(ValueError):
            capacity_from_worker(states[1])

    def test_observation_preserves_110_callback_results_and_unique_ids(self):
        timeline = RequestTimeline(time.monotonic())
        with QueuedInferenceExecutor(worker_count=8) as executor:
            def call(i):
                inference = MeasuredInference(executor, str(i), timeline)
                return inference.execute(client_id='policy-visible', generation=0,
                    state_hash='s', callback=lambda: (i, timeline.current_id()))
            with ThreadPoolExecutor(max_workers=16) as pool:
                values = list(pool.map(call, range(110)))
        events = timeline.snapshot()
        self.assertEqual([v[0] for v in values], list(range(110)))
        self.assertEqual(len({v[1] for v in values}), 110)
        self.assertEqual({e['request_id'] for e in events}, {v[1] for v in values})
        for event in events:
            self.assertLessEqual(event['submitted_seconds'], event['service_started_seconds'])
            self.assertLessEqual(event['service_started_seconds'], event['completed_seconds'])
            self.assertLessEqual(event['completed_seconds'], event['returned_seconds'])
            self.assertEqual(event['outcome'], 'completed')

    def test_failure_kept_and_callback_not_retried(self):
        timeline = RequestTimeline(time.monotonic())
        with QueuedInferenceExecutor(worker_count=1) as executor:
            inference = MeasuredInference(executor, 'a', timeline)
            with self.assertRaises(TimeoutError):
                inference.execute(client_id='a', generation=0, state_hash='s',
                                  callback=lambda: (_ for _ in ()).throw(TimeoutError()))
        self.assertEqual(len(timeline.snapshot()), 1)
        self.assertEqual(timeline.snapshot()[0]['error'], 'TimeoutError')

    def test_late_completion_does_not_turn_timeout_into_success(self):
        timeline = RequestTimeline(time.monotonic())
        release = threading.Event()
        executor = QueuedInferenceExecutor(worker_count=1)
        try:
            inference = MeasuredInference(executor, 'a', timeline)
            with self.assertRaises(InferenceQueueError):
                inference.execute(client_id='a', generation=0, state_hash='s',
                                  callback=lambda: release.wait(2), timeout_seconds=.03)
        finally:
            release.set(); executor.close()
        event = timeline.snapshot()[0]
        self.assertEqual(event['outcome'], 'failed')
        self.assertIsNotNone(event['completed_seconds'])

    def test_evidence_capacity_denies_callback(self):
        timeline = RequestTimeline(time.monotonic(), maximum=0)
        with QueuedInferenceExecutor(worker_count=1) as executor:
            with self.assertRaises(ValueError):
                MeasuredInference(executor, 'a', timeline).execute(client_id='a',
                    generation=0, state_hash='s', callback=lambda: self.fail('must not execute'))

    def test_telemetry_gaps_order_identity_and_nonfinite_fail(self):
        samples = [{'uuid': 'GPU-test', 'used_bytes': 1, 'elapsed_seconds': t}
                   for t in (0, .5, 1, 1.5, 2)]
        validate_telemetry(samples, 0, 2, 'GPU-test')
        for bad in ([], samples[:1], samples[-1:], list(reversed(samples)),
                    [{**samples[0], 'elapsed_seconds': float('nan')}],
                    [{**s, 'uuid': 'wrong'} for s in samples]):
            with self.assertRaises(ValueError):
                validate_telemetry(bad, 0, 2, 'GPU-test')

    def test_total_evidence_and_atomic_peak_accounted_without_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            save_bounded(path, {'x': 'old'}, byte_limit=100)
            original = path.read_bytes()
            save_bounded(path.parent / 'other.json', {'y': 'other'}, byte_limit=100)
            with self.assertRaises(ValueError):
                save_bounded(path, {'x': 'n' * 100}, byte_limit=100)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ValueError):
                save_bounded(path, {'x': float('nan')}, byte_limit=100)
            self.assertEqual(json.loads(path.read_text()), {'x': 'old'})
