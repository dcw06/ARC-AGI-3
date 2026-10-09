"""The questionnaire stage on the verified runtime: frozen order, the unchanged admission and stop rules, retained
evidence, and no scoring in the runner (CPU only; an in-memory client, no HTTP)."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger, RequestRefused
from certification.direct_publisher_smoke_v1.client import RequestFailed
from research.progress_subgoal_v1 import schedule as S
from research.progress_subgoal_v1_runtime2 import questionnaire as QN
from research.progress_subgoal_v1_runtime2.evidence import Evidence
from tests import psv1r2_fixtures as FX

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = []


def tearDownModule():
    for folder in FOLDERS:
        shutil.rmtree(folder, ignore_errors=True)


class FakeTime:
    def __init__(self, start=100.0):
        self.t = start

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class FakeClient:
    """Answers questionnaire requests with the scripted rule; faults by questionnaire call number."""

    def __init__(self, protocol, clock, time, *, hang=(), http_error=(), refuse=(), busy_after_hang=False,
                 call_seconds=0.01):
        self.ledger = Ledger(protocol['requests'], protocol['limits']['maximum_model_requests'], clock)
        self.time, self.hang, self.http_error, self.refuse = time, set(hang), set(http_error), set(refuse)
        self.busy_after_hang, self.busy, self.call_seconds = busy_after_hang, False, call_seconds
        self.timeout = protocol['experiment']['call_timing']['timeout_seconds']
        self.contents = FX.scripted_contents('scripted')
        self.audit = QN.token_audit(ROOT)
        self.sent = []

    def call(self, request_id, body=None):
        if request_id in self.refuse:
            raise RequestRefused(f'{request_id}: scripted refusal')
        self.ledger.admit(request_id)
        if request_id == QN.IDLE_REQUEST:
            self.time.sleep(0.01)
            running = 1 if self.busy else 0
            return 200, (f'vllm:num_requests_running{{model_name="m"}} {running}.0\n'
                         'vllm:num_requests_waiting{model_name="m"} 0.0\n').encode()
        n = int(request_id[1:])
        self.sent.append((request_id, body))
        if n in self.hang:
            self.time.sleep(self.timeout + 0.05)
            self.busy = self.busy_after_hang
            raise RequestFailed(f'{request_id}: deadline exceeded')
        self.time.sleep(self.call_seconds)
        if n in self.http_error:
            return 500, b'{"error":"scripted"}'
        content, finish = self.contents[n]
        return 200, FX.reply(content, finish, self.audit['prompt_tokens'][n]).encode()


def stage(protocol, client_kwargs=None, *, mode='rehearsal', start=0.0, cutoff=None):
    time = FakeTime(1000.0)
    limits = dict(protocol['limits'])
    if cutoff is not None:
        limits['admission_cutoff_seconds'] = cutoff
    clock = Clock(limits, time.now() - start, now=time.now)
    client = FakeClient(protocol, clock, time, **(client_kwargs or {}))
    folder = Path(tempfile.mkdtemp(prefix='psv1r2-stage-'))
    FOLDERS.append(folder)
    evidence = Evidence(folder / 'evidence', mode)
    return client, clock, evidence, time


def run(protocol, client_kwargs=None, **kwargs):
    client, clock, evidence, time = stage(protocol, client_kwargs, **kwargs)
    try:
        summary = QN.run_questionnaire(ROOT, client, evidence, clock, protocol, now=time.now, sleep=time.sleep)
        error = None
    except Exception as exc:  # the stage's own stop
        summary, error = None, exc
    index = json.loads((evidence.folder / 'questionnaire/run.json').read_bytes())
    calls = sorted((evidence.folder / 'questionnaire/calls').iterdir()) if (evidence.folder / 'questionnaire/calls').exists() else []
    return summary, error, index, [json.loads(p.read_bytes()) for p in calls], client


class Stage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = FX.declared_protocol()

    def test_complete_run_sends_the_frozen_requests_in_order_and_never_scores(self):
        summary, error, index, calls, client = run(self.protocol)
        self.assertIsNone(error)
        self.assertEqual((summary['status'], summary['calls_recorded'], summary['counts']),
                         ('complete', 5852, {'answered': 5852}))
        _, _, rows, hashes, _ = FX.schedule()
        self.assertEqual([body for _, body in client.sent], [r[4] for r in rows])
        self.assertEqual([c['request_sha256'] for c in calls], hashes)
        for record in calls[:50]:
            self.assertFalse({'score', 'valid', 'correct', 'answer'} & set(record))
        self.assertEqual(index['status'], 'complete')

    def test_one_timeout_with_the_server_idle_is_missing_not_failed(self):
        summary, error, index, calls, _ = run(self.protocol, {'hang': {7}})
        self.assertIsNone(error)
        self.assertEqual(summary['counts'], {'answered': 5851, 'timed_out': 1})
        timed = calls[7]
        self.assertEqual(timed['status'], 'timed_out')
        self.assertTrue(timed['idle_verification']['idle'])
        self.assertNotIn('response', timed)

    def test_two_consecutive_timeouts_stop_the_run(self):
        summary, error, index, calls, _ = run(self.protocol, {'hang': {7, 8}})
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual((index['status'], index['stop_reason'], len(calls)), ('incomplete', 'consecutive_timeouts', 9))

    def test_server_not_idle_after_a_timeout_stops_as_transport_failure(self):
        summary, error, index, calls, _ = run(self.protocol, {'hang': {7}, 'busy_after_hang': True})
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual((index['stop_reason'], calls[-1]['status']), ('transport_failure', 'transport_failure'))
        self.assertFalse(calls[-1]['idle_verification']['idle'])

    def test_http_error_and_refusal_stop_the_run(self):
        for kwargs, status in (({'http_error': {3}}, 'transport_failure'), ({'refuse': {'Q00003'}}, 'rejected')):
            summary, error, index, calls, _ = run(self.protocol, kwargs)
            self.assertIsInstance(error, RuntimeError)
            self.assertEqual((index['stop_reason'], len(calls), calls[-1]['status']), (status, 4, status))

    def test_admission_cutoff_is_a_reported_stop_not_a_failure(self):
        # Calls take 0.2 s; admission closes once elapsed + bound (10 s) exceeds a 30 s cutoff.
        summary, error, index, calls, _ = run(self.protocol, {'call_seconds': 0.2}, cutoff=30)
        self.assertIsNone(error)
        self.assertEqual((summary['status'], summary['stop_reason']), ('incomplete', 'admission_cutoff'))
        bound = QN.bound(self.protocol['experiment']['call_timing'])
        self.assertTrue(all(c['started_at'] + bound <= 30 + 0.5 for c in calls))
        self.assertLess(len(calls), 5852)

    def test_intent_is_retained_before_the_request_is_sent(self):
        protocol = self.protocol
        client, clock, evidence, time = stage(protocol)
        seen = []
        original = client.call

        def call(request_id, body=None):
            if request_id.startswith('Q0'):
                record = json.loads((evidence.folder / f'questionnaire/calls/{int(request_id[1:]):05d}.json').read_bytes())
                seen.append(record['status'])
                if len(seen) == 3:
                    raise KeyboardInterrupt('simulated kill during a call')
            return original(request_id, body)
        client.call = call
        with self.assertRaises(KeyboardInterrupt):
            QN.run_questionnaire(ROOT, client, evidence, clock, protocol, now=time.now, sleep=time.sleep)
        self.assertEqual(seen, ['intent'] * 3)
        index = json.loads((evidence.folder / 'questionnaire/run.json').read_bytes())
        self.assertEqual(index['status'], 'running')  # never finalized: the evaluator treats it as incomplete

    def test_live_mode_uses_only_the_frozen_cutoff_and_timing(self):
        frozen = FX.frozen_protocol()
        with self.assertRaises(PermissionError):
            QN.call_timing(self.protocol, 'live')
        client, clock, evidence, time = stage(frozen, mode='live', cutoff=1200)
        with self.assertRaises(PermissionError):
            QN.run_questionnaire(ROOT, client, evidence, clock, frozen, now=time.now, sleep=time.sleep)
        self.assertEqual(clock.limits['admission_cutoff_seconds'], 1200)
        self.assertEqual(S.ADMISSION_CUTOFF_SECONDS, 3000)

    def test_request_plan_timeouts_must_match_the_call_timing(self):
        protocol = copy.deepcopy(self.protocol)
        protocol['requests'][7]['timeout_seconds'] = 60
        client, clock, evidence, time = stage(protocol)
        with self.assertRaisesRegex(ValueError, 'request plan timeouts'):
            QN.run_questionnaire(ROOT, client, evidence, clock, protocol, now=time.now, sleep=time.sleep)

    def test_idle_reads_stay_inside_the_window_and_the_cap(self):
        time = FakeTime(0.0)

        class Busy:
            reads = 0

            def call(self, request_id, body=None):
                self.reads += 1
                time.sleep(0.2)
                return 200, b'vllm:num_requests_running 1.0\nvllm:num_requests_waiting 0.0\n'
        client = Busy()
        result = QN.verify_idle(client, deadline=15.0, now=time.now, sleep=time.sleep)
        self.assertFalse(result['idle'])
        self.assertLessEqual(client.reads, QN.IDLE_READS_PER_TIMEOUT)
        self.assertLessEqual(time.now(), 15.0 + 1e-9)
        self.assertEqual(QN.IDLE_READS_PER_TIMEOUT * QN.MAX_TIMED_OUT_CALLS, 750)
        self.assertLessEqual(S.ADMISSION_CUTOFF_SECONDS // S.PER_CALL_TIMEOUT_SECONDS, QN.MAX_TIMED_OUT_CALLS)


if __name__ == '__main__':
    unittest.main()
