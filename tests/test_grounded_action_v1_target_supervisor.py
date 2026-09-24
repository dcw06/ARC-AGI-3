"""External CPU rehearsal, including target-host failure exits."""
import json
from pathlib import Path
import tempfile
import unittest

from research.grounded_action_v1.target_host import main as host_main
from research.grounded_action_v1.target_supervisor import main as supervisor_main
from research.grounded_action_v1.target_supervisor import run_review


class TargetSupervisorTests(unittest.TestCase):
    def test_review_entrypoints_reject_live_launch(self):
        for entrypoint in (host_main, supervisor_main):
            with self.assertRaises(PermissionError):
                entrypoint()

    def test_two_arm_rehearsal_uses_monitor_and_independent_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_review(Path(folder) / 'out', seconds=60)
            self.assertEqual(result['status'], 'review_cpu_fixture_verified', result['error'])
            self.assertEqual((result['calls'], result['dispatches']), (12, 4))
            self.assertTrue(result['cleanup_verified'])
            self.assertTrue(result['scratch_removed'])
            self.assertFalse(result['target_gpu_certified'])
            canary = json.loads((Path(result['data_root']) / 'host-evidence/worker/canary.json').read_bytes())
            self.assertEqual(canary['status'], 'passed')
            self.assertTrue((Path(folder) / 'out/monitor/telemetry.json').exists())

    def test_failures_cannot_admit_study_and_clean_owned_groups(self):
        with tempfile.TemporaryDirectory() as folder:
            for fault in ('startup', 'cancel', 'evidence'):
                with self.subTest(fault=fault):
                    result = run_review(Path(folder) / fault, seconds=40, fault=fault)
                    self.assertEqual(result['status'], 'failed')
                    self.assertTrue(result['cleanup_verified'])
                    self.assertTrue(result['scratch_removed'])
                    self.assertFalse(result['target_gpu_certified'])
                    self.assertFalse((Path(result['data_root']) / 'record.json').exists())
                    receipt = Path(result['data_root']) / 'host-evidence/worker/failure.json'
                    self.assertTrue(receipt.exists())


if __name__ == '__main__':
    unittest.main()
