"""The real target entrypoints are inert without new Stage B authority."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

from research.grounded_action_v1.target_supervisor import run_live
from scripts.phase4_grounded_action_v1_launch import run as run_first_cell


class TargetLiveGateTests(unittest.TestCase):
    def test_no_approval_precedes_output_subprocess_and_gpu_query(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('subprocess.Popen') as launch, patch('subprocess.run') as query:
                with self.assertRaises(PermissionError):
                    run_live(root / 'supervisor', root, '/not/a/game/python',
                             '/not/a/model/python', root / 'games', started=time.monotonic())
                with self.assertRaises(PermissionError):
                    run_first_cell(root / 'first-cell', root, started=time.monotonic())
                launch.assert_not_called()
                query.assert_not_called()
            self.assertFalse((root / 'supervisor').exists())
            self.assertFalse((root / 'first-cell').exists())

    @unittest.skipUnless(os.name == 'posix', 'requires POSIX process groups')
    def test_monitor_exit_before_readiness_reaps_worker_and_retains_cleanup(self):
        from certification.phase4_integrated_v2.monitor import VRAM
        from scripts.run_grounded_action_v1_engine_local import group_exited

        gpu = {'uuid': 'GPU-TEST', 'name': 'RTX PRO 6000',
               'total_bytes': 96 * 1024**3, 'used_bytes': 1}

        class Probes:
            def __init__(self, *_):
                pass

            def bind(self):
                return {'gpu_uuid': gpu['uuid'], 'initial_telemetry': gpu,
                        'max_used_vram_bytes': VRAM}

            def sample(self, _):
                return gpu

            def gpu_pids(self):
                return []

        launched = []

        def spawn(_argv, **kwargs):
            code = 'import time; time.sleep(30)' if not launched else 'raise SystemExit(1)'
            process = subprocess.Popen([sys.executable, '-c', code], **kwargs)
            launched.append(process)
            return process

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'output'
            other_python = Path('/usr/bin/python3')
            self.assertTrue(other_python.is_file())
            with (patch('research.grounded_action_v1.authority.require', return_value={}),
                  patch('research.grounded_action_v1.target_supervisor.consume_runtime'),
                  patch('research.grounded_action_v1.target_supervisor.LiveProbes', Probes)):
                report = run_live(output, root, sys.executable, other_python, root / 'games',
                                  started=time.monotonic(), spawn=spawn)
            self.assertEqual(report['status'], 'failed')
            self.assertFalse(report['worker_released'])
            self.assertTrue(report['process_groups_exited'])
            self.assertTrue(report['independent_gpu_cleanup_verified'])
            self.assertTrue(report['scratch_removed'])
            self.assertEqual(len(launched), 2)
            self.assertTrue(all(group_exited(p.pid) for p in launched))
            self.assertTrue((output / 'control/outer.json').is_file())
            self.assertTrue((output / 'control/gpu-cleanup.json').is_file())

    @unittest.skipUnless(os.name == 'posix', 'requires POSIX process groups')
    def test_connected_supervisor_success_and_failure_censoring(self):
        from certification.phase4_integrated_v2.monitor import VRAM
        from scripts.run_grounded_action_v1_engine_local import group_exited

        root_repo = Path(__file__).resolve().parents[1]
        with zipfile.ZipFile(root_repo / 'evidence/perception-stage-b-v1-local-engine.zip') as bundle:
            trajectory = bundle.read('run.json')
        gpu = {'uuid': 'GPU-TEST', 'name': 'RTX PRO 6000',
               'total_bytes': 96 * 1024**3, 'used_bytes': 1}

        class Probes:
            def __init__(self, *_):
                pass

            def bind(self):
                return {'gpu_uuid': gpu['uuid'], 'initial_telemetry': gpu,
                        'max_used_vram_bytes': VRAM}

            def sample(self, _):
                return gpu

            def gpu_pids(self):
                return []

        worker_code = '''
import os,sys,time
from pathlib import Path
from certification.phase4_integrated_v2.evidence import EvidenceStore
gate, output, record, mode = int(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
assert os.read(gate, 1) == b'G'
if mode == 'startup': raise SystemExit(1)
if mode == 'deadline': time.sleep(1)
if mode == 'cancel':
    while not (output / 'control/cancel.json').exists(): time.sleep(.01)
    raise SystemExit(1)
store = EvidenceStore(output, 'worker')
store.save('model-ready.json', {'fixture': True})
store.write('trajectory.json', record.read_bytes())
'''
        monitor_code = '''
import os,sys,time
from pathlib import Path
from certification.phase4_integrated_v2.evidence import EvidenceStore
output, nonce, worker = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
store = EvidenceStore(output, 'monitor')
gpu = {'uuid':'GPU-TEST','name':'RTX PRO 6000','total_bytes':96*1024**3,'used_bytes':1}
binding = {'gpu_uuid':gpu['uuid'],'initial_telemetry':gpu,'max_used_vram_bytes':86*1024**3}
sample = {'uuid':gpu['uuid'],'used_bytes':1,'rss_bytes':1,'scratch_bytes':1,
          'elapsed_seconds':.01,'monotonic_seconds':time.monotonic()}
store.save('telemetry.json', {'samples':[sample]})
store.save('ready.json', {'scope':'stage_b_live_resource_monitor','nonce':nonce,
    'worker_pid':worker,'monitor_pid':os.getpid(),'gpu_binding':binding,'sample':sample})
while not (output / 'control/stop-monitor.json').exists(): time.sleep(.01)
'''

        for mode in ('success', 'startup', 'cancel', 'deadline', 'evidence', 'cleanup'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                output = root / 'output'
                record = root / 'record.json'
                record.write_bytes(trajectory)
                processes = []
                timer = None

                def spawn(argv, **kwargs):
                    nonlocal timer
                    if not processes:
                        command = [sys.executable, '-c', worker_code, str(argv[2]),
                                   str(output), str(record), mode]
                    else:
                        nonce = argv[argv.index('--nonce') + 1]
                        command = [sys.executable, '-c', monitor_code,
                                   str(output), nonce, str(processes[0].pid)]
                    process = subprocess.Popen(command, **kwargs)
                    processes.append(process)
                    if len(processes) == 2 and mode == 'cancel':
                        def cancel_after_ready():
                            until = time.monotonic() + 3
                            while not (output / 'control/monitor-ready-ack.json').exists() and time.monotonic() < until:
                                time.sleep(.01)
                            if (output / 'control/monitor-ready-ack.json').exists():
                                from certification.phase4_integrated_v2.evidence import EvidenceStore
                                EvidenceStore(output, 'control').save('cancel.json', {'fixture': True})
                        timer = threading.Thread(target=cancel_after_ready)
                        timer.start()
                    return process

                started = time.monotonic() - (2999.3 if mode == 'deadline' else 0)
                patches = [patch('research.grounded_action_v1.authority.require', return_value={}),
                           patch('research.grounded_action_v1.target_supervisor.consume_runtime'),
                           patch('research.grounded_action_v1.target_supervisor.LiveProbes', Probes)]
                if mode == 'cleanup':
                    patches.append(patch('research.grounded_action_v1.target_supervisor.independent_cleanup',
                        return_value={'gpu_cleanup_verified': False, 'error': 'fixture surviving GPU process'}))
                if mode == 'evidence':
                    from certification.phase4_integrated_v2.evidence import EvidenceStore
                    original_save = EvidenceStore.save
                    def save(store, name, value, **kwargs):
                        if name == 'monitor-ready-ack.json':
                            raise ValueError('fixture evidence budget exhausted')
                        return original_save(store, name, value, **kwargs)
                    patches.append(patch.object(EvidenceStore, 'save', save))
                try:
                    for item in patches:
                        item.start()
                    report = run_live(output, root, sys.executable, Path('/usr/bin/python3'),
                                      root / 'games', started=started, spawn=spawn)
                finally:
                    for item in reversed(patches):
                        item.stop()
                    if timer is not None:
                        timer.join(timeout=3)
                self.assertEqual(len(processes), 2)
                self.assertTrue(all(group_exited(p.pid) for p in processes), report)
                self.assertTrue(report['process_groups_exited'], report)
                self.assertTrue(report['scratch_removed'], report)
                self.assertTrue((output / 'control/outer.json').is_file(), report)
                self.assertTrue((output / 'control/gpu-cleanup.json').is_file(), report)
                if mode == 'success':
                    self.assertEqual(report['status'],
                                     'development_study_complete_pending_archive_review', report)
                    self.assertEqual(report['replay']['status'], 'valid_offline_development_pair')
                else:
                    self.assertEqual(report['status'], 'failed', report)
                    if mode in ('startup', 'cancel', 'deadline', 'cleanup'):
                        self.assertTrue(report['worker_released'], report)
                    if mode == 'evidence':
                        self.assertFalse(report['worker_released'], report)
                    if mode == 'cleanup':
                        self.assertFalse(report['independent_gpu_cleanup_verified'])
                    if mode == 'evidence':
                        self.assertIn('evidence budget exhausted', report['error'])


if __name__ == '__main__':
    unittest.main()
