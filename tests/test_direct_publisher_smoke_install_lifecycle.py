"""Real Linux descendants through the installation and smoke-result cleanup paths.

The two timeout reproductions also run unchanged against 500caa6. Fixtures
explicitly kill/reap their children even when the vulnerable baseline leaks them.
No wheels, model, provider access or GPU activity are involved.
"""
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1 import install as I, run as R, server as S
from certification.direct_publisher_smoke_v1.binding import ROOT, load_protocol


WRAPPER = '''import json, os, pathlib, signal, sys, time
args = sys.argv[1:]
phase = ("venv creation" if args[:2] == ["-m", "venv"] else
         "offline install" if args[:3] == ["-m", "pip", "install"] else
         "pip check" if args[:3] == ["-m", "pip", "check"] else "package checks")
base = pathlib.Path(os.environ["FIXTURE_BASE"])
if phase == os.environ["FIXTURE_PHASE"]:
    if os.fork() == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (base / "child.pid").write_text(str(os.getpid()))
        time.sleep(60)
        os._exit(0)
    while not (base / "child.pid").exists():
        time.sleep(.005)
    (base / "parent.pid").write_text(str(os.getpid()))
    if os.environ.get("FIXTURE_BEHAVIOUR") != "orphan":
        time.sleep(60)
if phase == "venv creation":
    target = pathlib.Path(args[2]) / "bin" / "python"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pathlib.Path(__file__).read_bytes())
    target.chmod(0o755)
if phase == "package checks":
    print(json.dumps({"versions": {}, "imports": {}}), flush=True)
'''


@unittest.skipUnless(sys.platform == 'linux', 'Linux process groups and subreaper required')
class InstallationDescendants(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='install-descendants-')
        self.base = Path(self.temp.name)
        self.libc = ctypes.CDLL(None, use_errno=True)
        setting = ctypes.c_int()
        self.assertEqual(self.libc.prctl(37, ctypes.byref(setting), 0, 0, 0), 0)
        self.previous = setting.value
        # Also adopt the vulnerable baseline's orphans so reproductions cannot
        # leave zombies behind in an environment whose PID 1 does not reap them.
        self.assertEqual(self.libc.prctl(36, 1, 0, 0, 0), 0)
        self.wrapper = self.base / 'python'
        self.wrapper.write_text(f'#!{sys.executable}\n' + WRAPPER)
        self.wrapper.chmod(0o755)
        self.extra_processes = []
        self.attempts = 0

    def tearDown(self):
        pids = [int(path.read_text()) for path in self.base.glob('*.pid')]
        pids += [process.pid for process in self.extra_processes]
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for process in self.extra_processes:
            process.wait(timeout=3)
        for pid in pids:
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        self.libc.prctl(36, self.previous, 0, 0, 0)
        self.temp.cleanup()

    def execute(self, phase, behaviour='hang', interruption=False):
        self.attempts += 1
        output = self.base / f'evidence-{self.attempts}'
        protocol = load_protocol(ROOT)
        protocol['runtime'].update(packages={}, imports=[])
        protocol['runtime'].pop('torch_cuda_build', None)
        protocol['limits'].update(installation_seconds=3, internal_seconds=15,
                                  admission_cutoff_seconds=12, cleanup_reserve_seconds=3)
        protocol['server'].update(terminate_grace_seconds=.05, kill_grace_seconds=.5)
        original_wait = subprocess.Popen.wait
        interrupted = False

        def wait(process, *args, **kwargs):
            nonlocal interrupted
            selected = ((phase == 'offline install' and process.args[1:4] == ['-m', 'pip', 'install'])
                        or (phase == 'package checks' and process.args[1] == '-I'))
            if interruption and selected and not interrupted:
                until = time.monotonic() + 3
                while not (self.base / 'parent.pid').exists() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue((self.base / 'parent.pid').exists())
                interrupted = True
                raise KeyboardInterrupt('fixture import/installation interrupt')
            return original_wait(process, *args, **kwargs)

        with patch.dict(os.environ, FIXTURE_BASE=str(self.base), FIXTURE_PHASE=phase,
                        FIXTURE_BEHAVIOUR=behaviour), \
             patch.object(R.host, 'host_facts', return_value={}), \
             patch.object(R, 'verify_bundle', return_value={}), \
             patch.object(subprocess.Popen, 'wait', wait):
            options = dict(bundle=self.base / 'bundle', workdir=self.base / 'work', python=str(self.wrapper))
            if interruption:
                with self.assertRaises(KeyboardInterrupt):
                    R.run('rehearsal', protocol, output, time.monotonic(), **options)
            else:
                R.run('rehearsal', protocol, output, time.monotonic(), **options)
        return json.loads((output / 'result.json').read_bytes())

    def assert_reaped(self, result):
        self.assertTrue((self.base / 'child.pid').exists(), result)
        child = int((self.base / 'child.pid').read_text())
        parent = int((self.base / 'parent.pid').read_text())
        for pid in (parent, child):
            self.assertFalse(Path(f'/proc/{pid}').exists(), f'installation descendant {pid} remains')
        self.assertTrue(result['cleanup_verified'], result['cleanup'])
        self.assertTrue(result['cleanup']['groups_absent'])
        groups = result['cleanup']['installation']['groups']
        self.assertTrue(all(group['groups_absent'] for group in groups))
        self.assertTrue(any(child in group['reaped_descendants'] for group in groups))
        self.assertTrue(any(group['sigkill_sent'] for group in groups))

    def test_installation_timeout_descendant_is_reaped_before_cleanup_verified(self):
        result = self.execute('offline install')
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_stage'], 'installation')
        self.assert_reaped(result)

    def test_import_timeout_descendant_is_reaped_before_cleanup_verified(self):
        result = self.execute('package checks')
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_stage'], 'installation')
        self.assert_reaped(result)

    def test_venv_and_pip_check_timeouts_reap_descendants(self):
        for phase in ('venv creation', 'pip check'):
            with self.subTest(phase=phase):
                result = self.execute(phase)
                self.assertFalse(result['passed'])
                self.assert_reaped(result)
                for path in self.base.glob('*.pid'):
                    path.unlink()

    def test_installation_and_import_interruptions_reap_descendants(self):
        for phase in ('offline install', 'package checks'):
            with self.subTest(phase=phase):
                result = self.execute(phase, interruption=True)
                self.assertFalse(result['passed'])
                self.assertIn('KeyboardInterrupt', result['error'])
                self.assert_reaped(result)
                for path in self.base.glob('*.pid'):
                    path.unlink()

    def test_parent_exit_does_not_hide_living_child(self):
        # Parent exits successfully; its TERM-resistant child keeps the log fd.
        processes = I.InstallationProcesses(terminate_grace=.05, kill_grace=.5)
        with patch.dict(os.environ, FIXTURE_BASE=str(self.base), FIXTURE_PHASE='package checks',
                        FIXTURE_BEHAVIOUR='orphan'):
            try:
                checked = I._run([str(self.wrapper), '-I'], self.base / 'install.log',
                                 time.monotonic() + 3, os.environ.copy(), 'package checks', processes)
                self.assertEqual(json.loads(checked.stdout)['versions'], {})
            finally:
                cleanup = processes.stop(time.monotonic() + 1)
        self.assert_reaped({'cleanup_verified': cleanup['groups_absent'],
                            'cleanup': {'groups_absent': cleanup['groups_absent'], 'installation': cleanup}})

    def test_commands_enable_adoption_and_restore_previous_setting(self):
        self.assertEqual(self.libc.prctl(36, 0, 0, 0, 0), 0)
        self.test_parent_exit_does_not_hide_living_child()
        setting = ctypes.c_int()
        self.assertEqual(self.libc.prctl(37, ctypes.byref(setting), 0, 0, 0), 0)
        self.assertEqual(setting.value, 0)

    def test_final_cleanup_does_not_signal_retired_numeric_group_ids(self):
        processes = I.InstallationProcesses(.05, .5)
        I._run([sys.executable, '-c', 'pass'], self.base / 'install.log', time.monotonic() + 3,
               os.environ.copy(), 'pip check', processes)
        with patch.object(S.os, 'killpg', side_effect=AssertionError('retired group must not be signalled')):
            self.assertTrue(processes.stop(time.monotonic() + 1)['groups_absent'])

    def test_command_cleanup_overrun_fails_installation_deadline(self):
        processes = I.InstallationProcesses(terminate_grace=3, kill_grace=1)
        with patch.dict(os.environ, FIXTURE_BASE=str(self.base), FIXTURE_PHASE='package checks',
                        FIXTURE_BEHAVIOUR='orphan'):
            try:
                with self.assertRaisesRegex(I.InstallFailed, 'deadline reached during process cleanup'):
                    I._run([str(self.wrapper), '-I'], self.base / 'install.log',
                           time.monotonic() + 2, os.environ.copy(), 'package checks', processes)
            finally:
                cleanup = processes.stop(time.monotonic() + 1)
        self.assertTrue(cleanup['groups_absent'])
        self.assertFalse(Path('/proc/' + (self.base / 'child.pid').read_text()).exists())

    def test_startup_interruptions_preserve_installation_ownership(self):
        original_popen, original_getpgid = S.subprocess.Popen, S.os.getpgid
        previous_handler = signal.getsignal(signal.SIGALRM)
        def cutoff(*args):
            raise TimeoutError('fixture startup interrupt')
        signal.signal(signal.SIGALRM, cutoff)
        try:
            for boundary in ('assignment', 'group registration'):
                with self.subTest(boundary=boundary):
                    processes = I.InstallationProcesses(.05, .5)
                    def popen(*args, **kwargs):
                        process = original_popen(*args, **kwargs)
                        self.extra_processes.append(process)
                        if boundary == 'assignment':
                            os.kill(os.getpid(), signal.SIGALRM)
                        return process
                    def getpgid(pid):
                        os.kill(os.getpid(), signal.SIGALRM)
                        return original_getpgid(pid)
                    with patch.object(S.subprocess, 'Popen', side_effect=popen), \
                         patch.object(S.os, 'getpgid', side_effect=getpgid if boundary == 'group registration'
                                      else original_getpgid):
                        try:
                            with self.assertRaises(TimeoutError):
                                I._run([sys.executable, '-c', 'import time; time.sleep(60)'],
                                       self.base / 'install.log', time.monotonic() + 3,
                                       os.environ.copy(), 'offline install', processes)
                        finally:
                            cleanup = processes.stop(time.monotonic() + 1)
                    self.assertTrue(cleanup['groups_absent'])
                    self.assertEqual(cleanup['groups'][0]['ownership'], 'registered')
        finally:
            signal.signal(signal.SIGALRM, previous_handler)

    def test_uncertain_installation_startup_never_verifies_cleanup(self):
        original_popen = S.subprocess.Popen
        def popen(*args, **kwargs):
            self.extra_processes.append(original_popen(*args, **kwargs))
            raise TimeoutError('exception before process assignment')
        with patch.object(S.subprocess, 'Popen', side_effect=popen):
            result = self.execute('offline install')
        self.assertFalse(result['passed'])
        self.assertFalse(result['cleanup_verified'])
        self.assertFalse(result['cleanup']['groups_absent'])
        self.assertEqual(result['cleanup']['installation']['groups'][0]['ownership'], 'uncertain')

    def test_gpu_receipt_cannot_override_unverified_installation_groups(self):
        from tests.test_direct_publisher_smoke_lifecycle import LifecycleDeadline
        receipt = {'groups': [], 'groups_absent': False, 'interrupted': [], 'error': None}
        with patch.object(I.InstallationProcesses, 'stop', return_value=receipt):
            result, _ = LifecycleDeadline().exercise(gpu_delay=True)
        self.assertTrue(result['cleanup']['gpu']['gpu_cleanup_verified'])
        self.assertFalse(result['cleanup_verified'])
        self.assertFalse(result['cleanup']['groups_absent'])
        self.assertFalse(result['passed'])

    def test_installation_cleanup_overrun_cannot_pass(self):
        from tests.test_direct_publisher_smoke_lifecycle import LifecycleDeadline
        original_stop = I.InstallationProcesses.stop
        def slow_stop(processes, deadline):
            time.sleep(.2)
            return original_stop(processes, deadline)
        with patch.object(I.InstallationProcesses, 'stop', slow_stop):
            result, _ = LifecycleDeadline().exercise()
        self.assertTrue(result['cleanup_verified'])
        self.assertFalse(result['passed'])
        self.assertFalse(result['lifecycle_deadline']['met'])


if __name__ == '__main__':
    unittest.main()
