"""progress_subgoal_v1 run evidence: a verified but never-finalized run index is recovered, never accepted as is.

Review of fb0a85f (r3 check, fault monitor_exit): the evaluator received status 'running' and stop_reason None. The
runner commits its index after each call (status 'running') and finalizes it only after its loop; the lost-monitor
teardown killed the worker between those writes. These tests force that window deterministically (no timing): the
termination is raised exactly after a call and its per-call index have been committed."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from research.evidence_comprehension_v2 import evidence as E2
from research.progress_subgoal_v1 import evidence as E, runner

ANSWER = {'content': '{"answer":"unknown"}', 'tokenizer_prompt_tokens': 10, 'server_prompt_tokens': 10,
          'server_completion_tokens': 3, 'finish_reason': 'stop', 'cache_check': None, 'host_timing': None}


class Terminated(BaseException):
    """Stands in for the SIGTERM that ends the worker: not an Exception, so the runner cannot finalize its index."""


def run_until_terminated(folder, kill_after_status):
    """Answer calls 1-5, cancel call 6 (the supervisor's cancel file appears mid-call), and terminate right after the
    runner commits that call and its per-call index: exactly where the lost-monitor teardown landed."""
    cancel = Path(folder) / 'cancel.json'

    class Service:
        calls = 0

        def complete(self, request, deadline=None):
            Service.calls += 1
            if Service.calls == 6:
                cancel.write_text('{}')
                raise RuntimeError('TimeoutError: bridge admission closed')
            return dict(ANSWER)

    class KilledAfterCommit(runner.Admission):
        def record(self, status):
            if status == kill_after_status:
                raise Terminated()
            return super().record(status)

    with mock.patch.object(runner, 'Admission', KilledAfterCommit):
        try:
            runner.run(Path(folder) / 'run', Service(), started=time.monotonic(), kind='test', cutoff_seconds=3000,
                       bound_seconds=10, cancel=cancel)
        except Terminated:
            return
    raise AssertionError('the run was not terminated')


class NeverFinalizedIndex(unittest.TestCase):
    def test_the_strict_loader_alone_accepts_a_running_index(self):
        """The defect, kept visible: v2's strict loader verifies the evidence and returns status 'running'."""
        with tempfile.TemporaryDirectory() as folder:
            run_until_terminated(folder, 'canceled')
            strict = E2.load_verified(Path(folder) / 'run')
        self.assertEqual((strict['status'], strict['stop_reason'], len(strict['calls'])), ('running', None, 6))

    def test_a_running_index_is_recovered_as_interrupted(self):
        with tempfile.TemporaryDirectory() as folder:
            run_until_terminated(folder, 'canceled')
            run = E.load_verified(Path(folder) / 'run')
        self.assertEqual((run['status'], run['stop_reason']), ('incomplete', 'interrupted_evidence'))
        self.assertEqual([c['status'] for c in run['calls']], ['answered'] * 5 + ['canceled'])
        self.assertEqual(run['calls_recorded'], 6)
        recovery = run['evidence_recovery']
        self.assertEqual((recovery['index_finalized'], recovery['index_status'], recovery['committed_calls']),
                         (False, 'running', 6))

    def test_terminated_after_an_answered_call_is_recovered_too(self):
        with tempfile.TemporaryDirectory() as folder:
            run_until_terminated(folder, 'answered')  # killed after the first call's commit
            run = E.load_verified(Path(folder) / 'run')
        self.assertEqual((run['status'], run['stop_reason'], run['calls_recorded']), ('incomplete', 'interrupted_evidence', 1))

    def test_a_finalized_run_is_returned_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            cancel = Path(folder) / 'cancel.json'  # the same service, without termination

            class Service:
                calls = 0

                def complete(self, request, deadline=None):
                    Service.calls += 1
                    if Service.calls == 6:
                        cancel.write_text('{}')
                        raise RuntimeError('TimeoutError: bridge admission closed')
                    return dict(ANSWER)
            index = runner.run(Path(folder) / 'run', Service(), started=time.monotonic(), kind='test',
                               cutoff_seconds=3000, bound_seconds=10, cancel=cancel)
            run = E.load_verified(Path(folder) / 'run')
        self.assertEqual((index['status'], index['stop_reason']), ('incomplete', 'canceled'))
        self.assertEqual((run['status'], run['stop_reason']), ('incomplete', 'canceled'))
        self.assertNotIn('evidence_recovery', run)

    def test_the_evaluator_never_grants_completion_to_a_recovered_run(self):
        """evaluate_run reads recovery from the loaded run: recovered evidence is never technically complete."""
        source = Path(runner.__file__).with_name('evaluate_run.py').read_text(encoding='utf-8')
        self.assertIn("recovered = run.get('evidence_recovery')", source)
        self.assertIn('not calls_errors and not recovered', source)


if __name__ == '__main__':
    unittest.main()
