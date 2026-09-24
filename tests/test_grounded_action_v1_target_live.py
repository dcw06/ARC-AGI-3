"""The real target entrypoints are inert without new Stage B authority."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main()
