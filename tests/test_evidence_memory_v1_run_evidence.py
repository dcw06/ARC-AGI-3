"""Stage 1 run evidence: a verified but never-finalized run index is recovered, never accepted as is.

The runner commits its index after each call (status 'running') and finalizes it only after its loop; a lost-monitor
teardown can terminate the worker between those writes (found by Track 4, b859a8a; WS3's recovery runs only when
strict verification fails). These tests force that window deterministically, with no timing: the termination is
raised exactly after a call and its per-call index have been committed. POSIX-only: the reviewed evidence writer
imports fcntl.
"""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

if os.name == 'posix':  # the reviewed evidence writer imports fcntl
    from research.evidence_comprehension_v2 import evidence as E2
    from research.evidence_memory_v1.run import evidence as E, runner

ANSWER = {'content': '{"values":["no_evidence"]}', 'tokenizer_prompt_tokens': 10, 'server_prompt_tokens': 10,
          'server_completion_tokens': 3, 'finish_reason': 'stop', 'cache_check': None, 'host_timing': None}


class Terminated(BaseException):
    """Stands in for the SIGTERM that ends the worker: not an Exception, so the runner cannot finalize its index."""


def service(cancel):
    """Answers calls 1-5; on call 6 the supervisor's cancel file appears and the call fails (recorded 'canceled')."""
    class Service:
        calls = 0

        def complete(self, request, deadline=None):
            Service.calls += 1
            if Service.calls == 6:
                cancel.write_text('{}')
                raise RuntimeError('TimeoutError: bridge admission closed')
            return dict(ANSWER)
    return Service()


def run_until_terminated(folder, kill_after_status):
    """Terminate right after the runner commits the first call with this status and its per-call index."""
    cancel = Path(folder) / 'cancel.json'

    class KilledAfterCommit(runner.Admission):
        def record(self, status):
            if status == kill_after_status:
                raise Terminated()
            return super().record(status)

    with mock.patch.object(runner, 'Admission', KilledAfterCommit):
        try:
            runner.run(Path(folder) / 'run', service(cancel), started=time.monotonic(), kind='test',
                       cutoff_seconds=3000, bound_seconds=10, cancel=cancel)
        except Terminated:
            return
    raise AssertionError('the run was not terminated')


@unittest.skipUnless(os.name == 'posix', 'the reviewed run evidence writer is POSIX-only (fcntl)')
class NeverFinalizedIndex(unittest.TestCase):
    def test_the_strict_loader_alone_accepts_a_running_index(self):
        """The defect, kept visible: v2's strict loader verifies the evidence and returns status 'running'."""
        with tempfile.TemporaryDirectory() as folder:
            run_until_terminated(folder, 'canceled')
            strict = E2.load_verified(Path(folder) / 'run')
        self.assertEqual((strict['status'], strict['stop_reason'], len(strict['calls'])), ('running', None, 6))

    def test_a_running_index_after_a_canceled_call_is_recovered_as_interrupted(self):
        with tempfile.TemporaryDirectory() as folder:
            run_until_terminated(folder, 'canceled')
            run = E.load_verified(Path(folder) / 'run')
        self.assertEqual((run['status'], run['stop_reason']), ('incomplete', 'interrupted_evidence'))
        self.assertEqual([c['status'] for c in run['calls']], ['answered'] * 5 + ['canceled'])
        self.assertEqual(run['calls_recorded'], 6)
        recovery = run['evidence_recovery']
        self.assertEqual((recovery['index_finalized'], recovery['index_status'], recovery['committed_calls']),
                         (False, 'running', 6))

    def test_a_running_index_after_an_answered_first_call_is_recovered_too(self):
        with tempfile.TemporaryDirectory() as folder:
            run_until_terminated(folder, 'answered')  # killed after the first call's commit
            run = E.load_verified(Path(folder) / 'run')
        self.assertEqual((run['status'], run['stop_reason'], run['calls_recorded']),
                         ('incomplete', 'interrupted_evidence', 1))
        self.assertEqual([c['status'] for c in run['calls']], ['answered'])
        self.assertFalse(run['evidence_recovery']['index_finalized'])

    def test_a_finalized_run_is_returned_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            cancel = Path(folder) / 'cancel.json'  # the same service, without termination
            index = runner.run(Path(folder) / 'run', service(cancel), started=time.monotonic(), kind='test',
                               cutoff_seconds=3000, bound_seconds=10, cancel=cancel)
            run = E.load_verified(Path(folder) / 'run')
            strict = E2.load_verified(Path(folder) / 'run')
        self.assertEqual((index['status'], index['stop_reason']), ('incomplete', 'canceled'))
        self.assertEqual((run['status'], run['stop_reason']), ('incomplete', 'canceled'))
        self.assertNotIn('evidence_recovery', run)
        self.assertEqual(run, strict)

    def test_the_evaluator_never_grants_completion_to_a_recovered_run(self):
        source = Path(runner.__file__).with_name('evaluate.py').read_text(encoding='utf-8')
        self.assertIn("recovered = run.get('evidence_recovery')", source)
        self.assertIn('not calls_errors and not recovered', source)
        self.assertIn('from research.evidence_memory_v1.run.evidence import load_verified', source)


class WrapperDecision(unittest.TestCase):
    """The wrapper's decision on any platform: WS3's loader is stubbed (and, off POSIX, fcntl with it, only for the
    duration of the import), so no evidence writer runs."""

    def decide(self, ws3_result):
        import sys
        import types
        stub = {} if os.name == 'posix' else {'fcntl': types.ModuleType('fcntl')}
        with mock.patch.dict(sys.modules, stub):
            from research.evidence_memory_v1.run import evidence as wrapper
            with mock.patch.object(wrapper._ws3, 'load_verified', return_value=dict(ws3_result)):
                return wrapper.load_verified('unused')

    def test_running_index_is_recovered(self):
        run = self.decide({'status': 'running', 'stop_reason': None, 'calls_recorded': 2, 'calls': [{}, {}]})
        self.assertEqual((run['status'], run['stop_reason'], run['calls_recorded']),
                         ('incomplete', 'interrupted_evidence', 2))
        self.assertEqual(run['evidence_recovery']['index_status'], 'running')
        self.assertFalse(run['evidence_recovery']['index_finalized'])

    def test_running_index_keeps_a_recorded_stop_reason(self):
        run = self.decide({'status': 'running', 'stop_reason': 'canceled', 'calls_recorded': 1, 'calls': [{}]})
        self.assertEqual((run['status'], run['stop_reason']), ('incomplete', 'canceled'))

    def test_finalized_and_already_recovered_runs_are_unchanged(self):
        for value in ({'status': 'complete', 'stop_reason': None, 'calls': [{}]},
                      {'status': 'incomplete', 'stop_reason': 'admission_cutoff', 'calls': []},
                      {'status': 'incomplete', 'stop_reason': 'interrupted_evidence', 'calls': [],
                       'evidence_recovery': {'index_committed': False}}):
            self.assertEqual(self.decide(value), value)


if __name__ == '__main__':
    unittest.main()
