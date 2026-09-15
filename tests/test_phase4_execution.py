import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from dataclasses import replace
from agent.e1_policy import CompletionResult
from agent.production_policy import load_operational_primary

from evaluation.phase4 import ROOT
from evaluation.phase4_execution import LOCK, LEDGER, authority, reserve, verify_lock
from evaluation.phase4_target import capacity, bind_gpu, worker, run_target
from scripts.build_phase4_target_notebook import build


class Phase4ExecutionTests(unittest.TestCase):
    def test_review_notebook_compiles_is_private_and_offline(self):
        notebook, metadata = build()
        self.assertTrue(metadata["is_private"])
        self.assertFalse(metadata["enable_internet"])
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile(cell["source"], "notebook", "exec")
        self.assertIn("REVIEW ONLY", notebook["cells"][0]["source"])
        with self.assertRaises(PermissionError):
            build(reserved=True)

    def test_reservation_requires_approval_binds_lock_and_is_single_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = verify_lock()
            for name in [*lock["sources"], LOCK, LEDGER]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, path)
            with self.assertRaises(PermissionError):
                reserve(root, "test-attempt")
            ledger = {"schema_version": 1, "authorized_seconds": 28800,
                      "approval_reference": "TEST_ONLY", "events": []}
            (root / LEDGER).write_text(json.dumps(ledger))
            self.assertEqual(reserve(root, "test-attempt")["seconds"], 28800)
            self.assertEqual(authority(root)["attempt_id"], "test-attempt")
            with self.assertRaises(PermissionError):
                reserve(root, "repeat")
            (root / "evaluation/phase4_target.py").write_text("# drift")
            with self.assertRaises(ValueError):
                authority(root)

    def test_capacity_fixed_window_rule_and_invalid_input(self):
        windows = [{"index": i, "completed": 1100, "seconds": 1100} for i in range(8)]
        result = capacity(windows)
        self.assertEqual(result["C_nominal"], 19800)
        self.assertEqual(result["C_admit"], 12672)
        self.assertTrue(result["capacity_passed"])
        for bad in ([], windows[:-1], [{**w, "seconds": float("nan")} for w in windows],
                    [{**w, "completed": 1099} for w in windows]):
            with self.assertRaises(ValueError):
                capacity(bad)

    def test_gpu_startup_binding_requires_idle_device(self):
        with patch("evaluation.phase4_target.subprocess.run") as run, \
             patch("evaluation.phase4_target.gpu_pids", return_value=[123]):
            run.return_value.stdout = "GPU-example\n"
            with self.assertRaises(ValueError):
                bind_gpu(86 * 1024**3)

    def test_target_worker_exact_windows_with_mocked_model(self):
        backend = Mock()
        backend.primary = load_operational_primary(ROOT)
        backend.audit = {"test_only": True}
        backend.complete.return_value = CompletionResult("fixture", prompt_tokens=100, completion_tokens=5)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "gpu_binding.json").write_text('{}')
            with patch("evaluation.phase4_target.authority"), \
                 patch("evaluation.phase4_target.TargetServiceBackend", return_value=backend), \
                 patch("evaluation.phase4_target.time.sleep", side_effect=RuntimeError("test stops cancellation probe")):
                import time
                with self.assertRaisesRegex(RuntimeError, "test stops"):
                    worker(root, root, time.monotonic())
            state = json.loads((root / "state.json").read_text())
            self.assertEqual(state["completed_requests"], 8800)
            self.assertEqual([w["completed"] for w in state["windows"]], [1100] * 8)
            self.assertEqual(backend.complete.call_count, 8801)
            backend.close.assert_called_once()

    def test_target_supervisor_requires_verified_cleanup(self):
        import time
        windows = [{"index": i, "completed": 1100, "seconds": 1100} for i in range(8)]
        with tempfile.TemporaryDirectory() as directory:
            def launch(argv, **kwargs):
                scratch = Path(argv[argv.index("--scratch") + 1])
                (scratch / "state.json").write_text(json.dumps({"audit": {},
                    "windows": windows, "cancel_probe_ready": True}))
                process = Mock()
                process.pid = 123456
                process.poll.return_value = None
                return process
            with patch("evaluation.phase4_target.authority", return_value={"attempt_id": "TEST"}), \
                 patch("evaluation.phase4_target.bind_gpu", return_value={"gpu_uuid": "GPU-TEST"}), \
                 patch("evaluation.phase4_target.subprocess.Popen", side_effect=launch), \
                 patch("evaluation.phase4_target.group_rss_bytes", return_value=1), \
                 patch("evaluation.phase4_target.sample_gpu", return_value={"used_bytes": 1}), \
                 patch("evaluation.phase4_target.terminate_group") as terminate, \
                 patch("evaluation.phase4_target.group_exists", return_value=False), \
                 patch("evaluation.phase4_target.gpu_pids", return_value=[]):
                result = run_target(Path(directory), time.monotonic())
            terminate.assert_called_once()
            self.assertTrue(result["cleanup_verified"])
            self.assertEqual(result["status"], "passed_fixture_prescreen_only")
            self.assertFalse(result["phase4_complete"])


if __name__ == "__main__":
    unittest.main()
