"""CPU deployment lifecycle contracts using fake installs and a fake watchdog.

No package installs, model inference, game dispatches or network requests occur.
The only real timer test interrupts a mocked requests method sleeping locally.
"""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import signal
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests

from research.cpu_competition_v1 import supervisor
from research.cpu_competition_v1.runtime import DeadlineSession
from research.initial_geometry_assistance_v1 import live_resources


class LifecycleFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / 'source'
        contracts = self.root / 'research/cpu_competition_v1'
        contracts.mkdir(parents=True)
        (contracts / 'wheels.json').write_text(json.dumps({}), encoding='utf-8')
        self.wheels = self.base / 'wheels'
        self.wheels.mkdir()
        self.runtime_temp = self.base / 'runtime-temporary'
        self.runtime_temp.mkdir()
        self.clock = 100.0
        self.commands = []
        self.transitions = []
        self.watch = None
        self.fail_command = None
        self.worker_finish = None

    def invoke(self, callback, *, scored=True, diagnostics=None):
        fixture = self

        class Watchdog:
            def __init__(self, deadline):
                self.deadline = deadline
                self.active = False
                fixture.watch = self

            def start(self):
                self.active = True
                fixture.transitions.append('watch-start')

            def close(self):
                fixture.assertTrue(self.active)
                self.active = False
                fixture.transitions.append('watch-close')

        class Processes:
            def __init__(self, watcher):
                fixture.assertIs(watcher, fixture.watch)

            def command(self, argv, log, deadline, env, label):
                fixture.assertTrue(fixture.watch.active)
                with Path(log).open('ab') as stream:
                    stream.write(b'synthetic retained diagnostic\n')
                index = len(fixture.commands)
                fixture.commands.append(dict(argv=argv, deadline=deadline, label=label))
                if fixture.fail_command == index:
                    raise RuntimeError('synthetic installation failure')
                if label == 'Single-scorecard CPU competition agent' and fixture.worker_finish is not None:
                    fixture.clock = fixture.worker_finish
                return SimpleNamespace(stdout='synthetic worker output')

            def stop(self, deadline):
                fixture.assertTrue(fixture.watch.active)
                fixture.assertEqual(deadline, fixture.watch.deadline)
                fixture.transitions.append('process-stop')
                return dict(groups_absent=True, error=None, interrupted=False)

        with ExitStack() as stack:
            # Mock-clock lifecycle receipts are test internals, not run telemetry.
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(patch.object(live_resources, 'HardDeadline', Watchdog))
            stack.enter_context(patch.object(live_resources, 'Processes', Processes))
            stack.enter_context(patch.object(live_resources, 'environment', return_value={}))
            stack.enter_context(patch.object(supervisor.sys, 'version_info', (3, 12, 0)))
            stack.enter_context(patch.object(supervisor.time, 'monotonic', lambda: self.clock))
            stack.enter_context(patch.object(supervisor.tempfile, 'mkdtemp', return_value=str(self.runtime_temp)))
            supervisor.entry(self.root, self.wheels, scored=scored, finalize=callback,
                             diagnostics=diagnostics)

    def test_worker_keeps_cleanup_reserve_and_callback_runs_inside_watchdog(self):
        def callback(completed):
            self.assertTrue(completed)
            self.assertTrue(self.watch.active)
            self.assertFalse(self.runtime_temp.exists())
            self.assertEqual(self.transitions[-1], 'process-stop')
            self.transitions.append('artifact-finalize')

        self.invoke(callback)
        worker = self.commands[-1]
        work_arg = worker['argv'].index('--work-seconds') + 1
        final_arg = worker['argv'].index('--final-seconds') + 1
        admission_budget = int(worker['argv'][work_arg])
        worker_final_budget = int(worker['argv'][final_arg])
        # Admission must close while the worker can still close its scorecard.
        self.assertGreater(worker_final_budget, admission_budget)
        self.assertGreater(worker['deadline'], 100.0 + admission_budget)
        self.assertLess(worker['deadline'], self.watch.deadline)
        self.assertEqual(self.transitions,
                         ['watch-start', 'process-stop', 'artifact-finalize', 'watch-close'])
        self.assertFalse(self.watch.active)

    def test_work_returning_after_admission_can_still_finalize_in_reserve(self):
        self.worker_finish = 3130.0  # Admission closed at 3100; hard deadline is 3400.
        calls = []

        def callback(completed):
            calls.append(completed)
            self.assertTrue(self.watch.active)
            self.assertFalse(self.runtime_temp.exists())
            self.assertLess(self.clock, self.watch.deadline)

        self.invoke(callback)
        self.assertEqual(self.clock, self.worker_finish)
        self.assertEqual(calls, [True])
        self.assertFalse(self.watch.active)

    def test_late_artifact_finalization_fails_with_emergency_watchdog_active(self):
        def callback(completed):
            self.assertTrue(completed)
            self.assertTrue(self.watch.active)
            self.clock = self.watch.deadline + 0.1

        with self.assertRaisesRegex(TimeoutError, 'finalization deadline'):
            self.invoke(callback)
        # A failed overrun must not disarm the emergency deadline.
        self.assertTrue(self.watch.active)
        self.assertNotIn('watch-close', self.transitions)

    def test_callback_failure_propagates_and_closes_watchdog_before_deadline(self):
        class ArtifactFailure(Exception):
            pass

        def callback(completed):
            self.assertTrue(completed)
            self.assertTrue(self.watch.active)
            self.assertFalse(self.runtime_temp.exists())
            raise ArtifactFailure('synthetic artifact failure')

        with self.assertRaises(ArtifactFailure):
            self.invoke(callback)
        self.assertFalse(self.watch.active)
        self.assertEqual(self.transitions[-1], 'watch-close')

    def test_install_failure_never_finalizes_artifacts_as_success(self):
        self.fail_command = 0
        completed_values = []

        def callback(completed):
            completed_values.append(completed)
            self.assertTrue(self.watch.active)
            self.assertFalse(self.runtime_temp.exists())

        with self.assertRaisesRegex(RuntimeError, 'installation failure'):
            self.invoke(callback)
        self.assertEqual(completed_values, [False])
        self.assertEqual(len(self.commands), 1)
        self.assertFalse(self.watch.active)
        self.assertEqual(self.transitions, ['watch-start', 'process-stop', 'watch-close'])

    def test_failure_retains_bounded_log_before_removing_temporary_runtime(self):
        self.fail_command = 0
        diagnostics = self.base / 'diagnostics'
        with self.assertRaisesRegex(RuntimeError, 'installation failure'):
            self.invoke(lambda completed: self.assertFalse(completed), diagnostics=diagnostics)
        self.assertFalse(self.runtime_temp.exists())
        self.assertIn('synthetic retained diagnostic', (diagnostics / 'worker.log').read_text())
        record = json.loads((diagnostics / 'worker-cleanup.json').read_bytes())
        self.assertFalse(record['worker_completed'])
        self.assertEqual(record['failure_type'], 'RuntimeError')
        self.assertEqual(record['phase'], 'environment_creation')
        self.assertTrue(record['cleanup']['groups_absent'])
        self.assertEqual(record['final_lifecycle_verdict'], 'not_certified_by_this_diagnostic')

    def test_prior_diagnostics_are_never_overwritten(self):
        diagnostics = self.base / 'diagnostics'
        diagnostics.mkdir()
        (diagnostics / 'worker.log').write_text('previous attempt')
        with self.assertRaises(FileExistsError):
            self.invoke(lambda completed: None, diagnostics=diagnostics)
        self.assertEqual((diagnostics / 'worker.log').read_text(), 'previous attempt')
        self.assertEqual(self.commands, [])


@unittest.skipUnless(hasattr(signal, 'setitimer'), 'requires POSIX interval timers')
class AbsoluteResponseDeadline(unittest.TestCase):
    def test_mocked_stalled_response_is_interrupted_and_signal_state_restored(self):
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        previous = signal.getsignal(signal.SIGALRM)

        def stalled_request(_session, _method, _url, **kwargs):
            self.assertFalse(kwargs['allow_redirects'])
            self.assertFalse(kwargs['stream'])
            self.assertGreater(kwargs['timeout'], 0)
            time.sleep(0.15)
            self.fail('absolute alarm did not interrupt the mocked response')

        started = time.monotonic()
        session = DeadlineSession(started + 0.03)
        self.addCleanup(session.close)
        with patch.object(requests.Session, 'request', stalled_request):
            with self.assertRaisesRegex(TimeoutError, 'absolute HTTP response deadline'):
                session.request('GET', 'https://unused.invalid/no-network')
        self.assertLess(time.monotonic() - started, 0.12)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertIs(signal.getsignal(signal.SIGALRM), previous)


if __name__ == '__main__':
    unittest.main()
