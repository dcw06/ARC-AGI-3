import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from certification.phase4_v6.outer import run_local, group_present


class OuterTests(unittest.TestCase):
    def run_probe(self, worker, monitor=None, *, announce=True, **limits):
        # Monitor observes a PID supplied by outer; never spawns the worker.
        monitor = monitor or '''import os,sys,time
pid=int(sys.argv[1])
while True:
    try: os.kill(pid,0)
    except ProcessLookupError: break
    time.sleep(.01)
'''
        if announce:
            monitor = ('from certification.phase4_v6.handshake import publish_local_ready; '
                       'publish_local_ready()\n') + monitor
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            result = run_local([sys.executable, '-c', worker],
                lambda pid, out: [sys.executable, '-c', monitor, str(pid)], output,
                seconds=4, reserve=2, grace=.05, verification_seconds=1, **limits)
            self.assertEqual(json.loads((output / 'outer.json').read_text()), result)
            self.assertTrue(result['cleanup_verified'], result)
            self.assertTrue(all(not group_present(pid) for pid in result['owned_groups']))
            return result

    def test_complete_worker_and_monitor_are_not_certification(self):
        result = self.run_probe('import time; time.sleep(.1)')
        self.assertEqual(result['status'], 'local_commands_completed_pending_evidence_review', result)
        self.assertFalse(result['target_gpu_certified'])

    def test_injected_resource_monitor_integrates_with_outer_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            result = run_local([sys.executable, '-c', 'import time; time.sleep(.15)'],
                lambda pid, out: [sys.executable, '-m', 'certification.phase4_v6.monitor',
                    '--injected', str(pid), str(out / 'resource-monitor')], output,
                seconds=5, reserve=2, grace=.05, verification_seconds=1,
                readiness_seconds=2)
            self.assertEqual(result['status'], 'local_commands_completed_pending_evidence_review', result)
            self.assertTrue(result['worker_released'])
            receipt = json.loads((output / 'resource-monitor/monitor-result.json').read_text())
            self.assertEqual(receipt['status'], 'injected_monitor_completed')
            self.assertFalse(receipt['target_gpu_certified'])

    def test_monitor_hang_is_externally_terminated(self):
        result = self.run_probe('import time; time.sleep(.1)', 'import time; time.sleep(30)')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('outer deadline', result['error'])
        self.assertTrue(result['admission_canceled'])

    def test_monitor_crash_cleans_worker(self):
        result = self.run_probe('import time; time.sleep(30)', 'raise RuntimeError("monitor fault")')
        self.assertEqual(result['status'], 'failed')

    def test_worker_crash_cleans_monitor(self):
        result = self.run_probe('raise RuntimeError("worker fault")', 'import time; time.sleep(30)')
        self.assertEqual(result['status'], 'failed')

    def test_clean_monitor_exit_cannot_abandon_live_worker(self):
        result = self.run_probe('import time; time.sleep(30)', 'pass')
        self.assertEqual(result['status'], 'failed')
        self.assertIsNotNone(result['error'])

    def test_descendant_survives_leader_exit_but_not_outer_cleanup(self):
        worker = '''import subprocess,sys,time
subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)'])
time.sleep(.15)
'''
        result = self.run_probe(worker)
        self.assertTrue(result['cleanup_verified'])

    def test_failed_monitor_launch_never_releases_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            sentinel = path / 'should-not-exist'
            result = run_local([sys.executable, '-c',
                'import pathlib,sys; pathlib.Path(sys.argv[1]).touch()', str(sentinel)],
                lambda pid, out: ['/nonexistent-phase4-monitor'], path / 'output',
                seconds=4, reserve=2, grace=.05, verification_seconds=1)
            self.assertFalse(sentinel.exists())
            self.assertFalse(result['worker_released'])
            self.assertTrue(result['cleanup_verified'], result)

    def test_exhausted_first_cell_denies_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_local([], lambda *_: [], Path(directory) / 'output',
                          started=time.monotonic()-100)

    def test_missing_ready_never_releases_worker(self):
        result = self.run_probe('pass', 'import time; time.sleep(30)',
                                announce=False, readiness_seconds=.1)
        self.assertFalse(result['worker_released'])
        self.assertIn('readiness deadline', result['error'])

    def test_malformed_ready_never_releases_worker(self):
        code = '''import os,pathlib,time
pathlib.Path(os.environ['P4_READY_PATH']).write_text('{"kind":"passed"}')
time.sleep(30)
'''
        result = self.run_probe('pass', code, announce=False)
        self.assertFalse(result['worker_released'])
        self.assertIn('mismatch', result['error'])

    def test_late_ready_never_releases_worker(self):
        code = '''import time
time.sleep(.3)
from certification.phase4_v6.handshake import publish_local_ready
publish_local_ready()
time.sleep(30)
'''
        result = self.run_probe('pass', code, announce=False, readiness_seconds=.1)
        self.assertFalse(result['worker_released'])
        self.assertIn('readiness deadline', result['error'])
