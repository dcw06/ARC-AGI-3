"""Subprocess-level probes; never start a GPU model or environment."""
import unittest
from unittest.mock import patch

from evaluation.phase4_runner import supervise, TargetServiceBackend


class Phase4RunnerTests(unittest.TestCase):
    def test_complete_fixed_windows_and_cleanup(self):
        result = supervise()
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(result["worker"]["completed_requests"], 8800)
        self.assertEqual([w["completed"] for w in result["worker"]["windows"]], [1100] * 8)
        self.assertTrue(result["within_deadline"])
        self.assertTrue(result["scratch_removed"])
        self.assertFalse(result["target_gpu_certified"])

    def test_faults_fail_without_false_success(self):
        for fault in ("startup", "inference", "timeout", "storage", "finalization"):
            with self.subTest(fault=fault):
                result = supervise(fault=fault)
                self.assertEqual(result["status"], "failed")
                self.assertTrue(result["scratch_removed"])
                self.assertTrue(result["within_deadline"])
                self.assertFalse(result["target_gpu_certified"])
                if fault == "finalization":
                    self.assertEqual(result["finalization_status"], "unknown")

    def test_uncooperative_backend_and_finalization_terminated(self):
        for fault in ("hang", "finalization_hang"):
            with self.subTest(fault=fault):
                result = supervise(fault=fault, timeout_seconds=3, reserve_seconds=1)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["stop_reason"], "admission_deadline")
                self.assertEqual(result["finalization_status"], "unknown")
                self.assertTrue(result["within_deadline"])
                self.assertTrue(result["scratch_removed"])

    def test_resource_limits_and_probe_fail_closed(self):
        with patch("evaluation.phase4_runner.group_rss_bytes", return_value=100):
            result = supervise(fault="hang", memory_limit_bytes=1)
        self.assertEqual(result["stop_reason"], "host_memory_limit")
        with patch("evaluation.phase4_runner.tree_bytes", return_value=100):
            result = supervise(fault="hang", disk_limit_bytes=1)
        self.assertEqual(result["stop_reason"], "scratch_limit")
        with patch("evaluation.phase4_runner.group_rss_bytes", side_effect=OSError):
            result = supervise(fault="hang")
        self.assertEqual(result["stop_reason"], "resource_monitor_failure")

    def test_target_gate_precedes_process_launch(self):
        with patch("evaluation.phase4_runner.subprocess.Popen") as launch:
            with self.assertRaises(PermissionError):
                supervise(backend="target")
            launch.assert_not_called()
        with patch("agent.production_policy.ModelService.start") as start:
            with self.assertRaises(PermissionError):
                TargetServiceBackend().start()
            start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
