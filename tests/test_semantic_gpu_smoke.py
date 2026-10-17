"""CPU fault checks only: never loads a model or queries/allocates a GPU."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch
from research.object_discovery_boundaries_v1 import semantic_smoke as S


class Scope(unittest.TestCase):
    def test_missing_authority_refuses_before_gpu_or_process_creation(self):
        with patch.object(S,'Commands',side_effect=AssertionError('process owner created')):
            with self.assertRaises(PermissionError): S.run(dict(scope=S.SCOPE),None)

    def test_gpu_scope_has_no_implicit_six_board_or_generation_budget(self):
        self.assertEqual(S.SCOPE['modes'],['seeded','automatic'])
        self.assertEqual(S.SCOPE['granularity'],1)
        self.assertEqual(S.SCOPE['smoke_case'],'board-06')
        self.assertEqual(S.SCOPE['model_http_requests'],0)
        self.assertEqual(S.SCOPE['new_molmopoint_generations'],0)

    def test_subprocess_environment_drops_credentials_and_relative_library_paths(self):
        with patch.dict(os.environ,dict(KAGGLE_API_TOKEN='synthetic-secret',LD_LIBRARY_PATH='/driver:relative:/driver')):
            env = S.environment(Path('/tmp/synthetic'),'GPU-synthetic')
        self.assertNotIn('KAGGLE_API_TOKEN',env)
        self.assertEqual(env['LD_LIBRARY_PATH'],'/driver')
        self.assertEqual(env['MPLBACKEND'],'Agg')
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'],'GPU-synthetic')

    def test_extractor_refuses_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root/'unsafe.tar'
            with tarfile.open(archive,'w') as output:
                info = tarfile.TarInfo('../outside'); info.size = 0; output.addfile(info)
            with self.assertRaises(tarfile.FilterError):
                S.extract_tar(archive,root/'new',time.monotonic()+2)
            self.assertFalse((root/'outside').exists())


@unittest.skipUnless(sys.platform=='linux','Linux process groups and subreaper')
class Ownership(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.owner = S.Commands()
        self.addCleanup(self.emergency)

    def emergency(self):
        self.owner.emergency()
        for entry in self.owner.entries:
            process = entry['group'].process
            if process is not None:
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired: pass
            if hasattr(entry['group'],'_log'): entry['group']._log.close()
        self.owner.libc.prctl(36,self.owner.previous,0,0,0)

    def command(self,code,seconds=2):
        return self.owner.command([sys.executable,'-c',code],self.root/'process.log',
                                  time.monotonic()+seconds,dict(PATH=os.defpath))

    def test_normal_exit_reaps_and_records_registered_absence(self):
        self.assertIn('ok',self.command("print('ok')"))
        receipt = self.owner.stop(time.monotonic()+1)
        self.assertTrue(receipt['groups_absent'])
        self.assertEqual(receipt['groups'][0]['ownership'],'registered')

    def test_child_descendant_is_killed_and_reaped(self):
        self.command("import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])")
        receipt = self.owner.stop(time.monotonic()+1)
        self.assertTrue(receipt['groups_absent'])
        self.assertEqual(self.owner.members(receipt['groups'][0]['pgid'],time.monotonic()+1),[])

    def test_command_timeout_keeps_ownership_for_reserved_cleanup(self):
        with self.assertRaises(TimeoutError): self.command('import time;time.sleep(60)',.08)
        self.assertTrue(self.owner.stop(time.monotonic()+1)['groups_absent'])

    def test_startup_signal_cannot_skip_registration_or_owned_cleanup(self):
        old = signal.signal(signal.SIGTERM,lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()))
        self.addCleanup(signal.signal,signal.SIGTERM,old)
        original = os.getpgid
        def interrupted(pid):
            signal.raise_signal(signal.SIGTERM)
            return original(pid)
        with patch.object(os,'getpgid',side_effect=interrupted),self.assertRaises(KeyboardInterrupt):
            self.command('import time;time.sleep(60)')
        self.assertEqual(self.owner.entries[0]['group'].ownership,'registered')
        self.assertTrue(self.owner.stop(time.monotonic()+1)['groups_absent'])

    def test_uncertain_spawn_never_claims_group_absence(self):
        original = subprocess.Popen
        captured = []
        def interrupted(*args,**kwargs):
            process = original(*args,**kwargs); captured.append(process)
            raise KeyboardInterrupt()
        try:
            with patch.object(subprocess,'Popen',side_effect=interrupted),self.assertRaises(KeyboardInterrupt):
                self.command('import time;time.sleep(60)')
            with self.assertRaisesRegex(RuntimeError,'uncertain'):
                self.owner.stop(time.monotonic()+1)
        finally:
            for process in captured:
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait(timeout=2)

    def test_work_alarm_leaves_time_to_stop_real_child(self):
        started = time.monotonic()
        with S.alarm(started+.3,started+.08) as final_phase:
            with self.assertRaises(TimeoutError):
                self.command('import time;time.sleep(60)',seconds=2)
            final_phase()
            receipt = self.owner.stop(started+.3)
        self.assertTrue(receipt['groups_absent'])
        self.assertLess(time.monotonic()-started,.3)

    def test_emergency_kill_does_not_census_or_block_on_wait(self):
        with self.assertRaises(TimeoutError): self.command('import time;time.sleep(60)',.08)
        with patch.object(self.owner,'members',side_effect=AssertionError('census before kill')):
            self.owner.emergency()
        self.assertTrue(self.owner.stop(time.monotonic()+1)['groups_absent'])

    def test_final_alarm_escapes_stalled_census(self):
        self.command("print('ok')")
        entry = self.owner.entries[0]; entry['retired'] = False
        started = time.monotonic()
        with self.assertRaises(S.LifecycleDeadline),S.alarm(started+.08,started+.08):
            with patch.object(self.owner,'members',side_effect=lambda *args:time.sleep(.5)):
                self.owner.stop(started+1)
        self.assertLess(time.monotonic()-started,.3)


if __name__=='__main__': unittest.main()
