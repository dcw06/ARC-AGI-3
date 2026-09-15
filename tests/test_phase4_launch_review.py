"""Negative regressions for the four prelaunch review findings."""
from collections import Counter
import ast
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
from unittest.mock import Mock, patch

from evaluation.phase4_execution import ROOT, LOCK, PROTOCOL, LEDGER, sha, verify_lock
from evaluation.phase4_target import capacity, run_target
from evaluation.phase4_workload import build_workload
from scripts.evaluate_phase4_prescreen import evaluate
from scripts.build_phase4_target_notebook import build


class LaunchReviewTests(unittest.TestCase):
    def test_packaged_notebook_gate_in_isolated_stdlib_runtime(self):
        notebook, _ = build()
        tree = ast.parse(notebook["cells"][1]["source"])
        packed = next(node.args[0].value for node in ast.walk(tree)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                      and node.func.attr == "b64decode" and isinstance(node.args[0], ast.Constant))
        files = json.loads(zlib.decompress(base64.b64decode(packed)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, payload in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(base64.b64decode(payload))
            check = "import sys; sys.path.insert(0,sys.argv[1]); from evaluation.phase4_execution import authority; authority()"
            result = subprocess.run([sys.executable, "-I", "-S", "-c", check, str(root)],
                                    cwd=root, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PermissionError", result.stderr)
            self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_bootstrap_full_gate_without_site_packages(self):
        code = "from evaluation.phase4_execution import authority\ntry: authority()\nexcept PermissionError: print('EXPECTED_ZERO_AUTHORIZATION')"
        result = subprocess.run([sys.executable, "-S", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("EXPECTED_ZERO_AUTHORIZATION", result.stdout)

    def test_error_precedence_and_final_checkpoint_retention(self):
        for scenario in ("ready_error", "late_error", "exited_error"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                windows = [{"index": i, "completed": 1100, "seconds": 1100} for i in range(8)]
                state = {"audit": {}, "windows": windows, "cancel_probe_ready": True}
                checkpoint = None
                def launch(argv, **kwargs):
                    nonlocal checkpoint
                    checkpoint = Path(argv[argv.index("--scratch") + 1]) / "state.json"
                    if scenario != "late_error":
                        state["error"] = "server token mismatch"
                    checkpoint.write_text(json.dumps(state))
                    process = Mock(pid=123456)
                    process.poll.return_value = 0 if scenario == "exited_error" else None
                    return process
                def terminate(*args):
                    if scenario == "late_error":
                        state["error"] = "late server failure"
                        checkpoint.write_text(json.dumps(state))
                with patch("evaluation.phase4_target.authority", return_value={"attempt_id": "TEST"}), \
                     patch("evaluation.phase4_target.bind_gpu", return_value={"gpu_uuid": "GPU-TEST"}), \
                     patch("evaluation.phase4_target.subprocess.Popen", side_effect=launch), \
                     patch("evaluation.phase4_target.group_rss_bytes", return_value=1), \
                     patch("evaluation.phase4_target.sample_gpu", return_value={"used_bytes": 1}), \
                     patch("evaluation.phase4_target.terminate_group", side_effect=terminate), \
                     patch("evaluation.phase4_target.group_exists", return_value=False), \
                     patch("evaluation.phase4_target.gpu_pids", return_value=[]):
                    result = run_target(Path(directory), time.monotonic())
                self.assertEqual(result["status"], "failed")
                self.assertIn("error", result["worker"])
                self.assertEqual(json.loads((Path(directory) / "measurement.json").read_text())["worker"], state)
                self.assertFalse(checkpoint.exists())

    def evidence(self):
        workload = build_workload()
        protocol = json.loads((ROOT / PROTOCOL).read_text())
        primary = json.loads((ROOT / "config/operational_primary.yaml").read_text())["primary"]
        windows = []
        for i in range(8):
            counts = Counter(name for a in workload["assignments"] for name in a["requests"][i*10:(i+1)*10])
            windows.append({"index": i, "completed": 1100, "seconds": 1100,
                "server_total_tokens": 1100 * 105,
                "fixture_usage": {name: {"requests": n, "prompt_tokens": n*100,
                                         "completion_tokens": n*5} for name, n in counts.items()}})
        audit = {"workload_sha256": workload["workload_sha256"], "context_limit": 65536,
            "artifact": {"tree_sha256": primary["model_artifact"]["tree_sha256"], "bytes": 100, "file_count": 1},
            "prompt_tokens_by_request_sha256": {f["request_sha256"]: 100 for f in workload["fixtures"]}}
        claim = {"execution_lock_sha256": sha(ROOT / LOCK), "attempt_id": "TEST", "kind": "reserve", "seconds": 28800}
        report = {"execution_lock_sha256": sha(ROOT / LOCK), "attempt_id": "TEST",
            "status": "passed_fixture_prescreen_only", "scope": protocol["scope"], "phase4_complete": False,
            "cleanup_verified": True, "scratch_removed": True, "cancellation_seconds": 1,
            "elapsed_since_first_cell_seconds": 10000, "windows": windows, "capacity": capacity(windows),
            "stop_reason": "model_process_cancellation_probe", "charged_or_reserved_seconds": 28800,
            "peak_group_rss_bytes": 100, "peak_vram_bytes": 100, "peak_scratch_bytes": 100,
            "gpu_uuid": "GPU-TEST", "gpu_samples": 10,
            "worker": {"model_inference": True, "cancel_probe_ready": True, "completed_requests": 8800,
                "windows": windows, "startup_including_preflight_seconds": 100, "max_queue_age_seconds": 1, "audit": audit}}
        return {"measurement.json": report, "claim.json": claim,
            "notebook-cost.json": {"charged_or_reserved_seconds": 28800, "status": "target_command_completed",
                "elapsed_since_first_cell_seconds": 10001, "scope": "all_accelerator_time_including_setup_and_failures",
                "provider_reconciliation_required": True},
            Path(LEDGER).name: {"authorized_seconds": 28800, "approval_reference": "TEST_ONLY", "events": [claim]},
            "gpu_binding.json": {"gpu_uuid": "GPU-TEST", "max_used_vram_bytes": protocol["limits"]["vram_bytes"],
                "initial_telemetry": {"uuid": "GPU-TEST", "name": "RTX PRO 6000", "used_bytes": 0, "total_bytes": 96*1024**3}}}

    def evaluate_fixture(self, files):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name in (LOCK, PROTOCOL):
                (path / Path(name).name).write_bytes((ROOT / name).read_bytes())
            for name, value in files.items():
                (path / name).write_text(json.dumps(value))
            return evaluate(path)

    def test_complete_fixture_passes_but_missing_evidence_fails(self):
        files = self.evidence()
        self.assertTrue(self.evaluate_fixture(files)["capacity_passed"])
        for name in files:
            with self.subTest(missing=name):
                broken = copy.deepcopy(files)
                del broken[name]
                with self.assertRaises(ValueError):
                    self.evaluate_fixture(broken)
        for field in ("worker", "gpu_samples", "peak_vram_bytes"):
            broken = copy.deepcopy(files)
            del broken["measurement.json"][field]
            with self.assertRaises(ValueError):
                self.evaluate_fixture(broken)

    def test_resource_and_token_parity_failures_rejected(self):
        for field, value in (("peak_vram_bytes", 100*1024**3), ("peak_group_rss_bytes", float("nan")),
                             ("peak_scratch_bytes", 5*1024**3), ("gpu_uuid", "wrong")):
            files = self.evidence()
            files["measurement.json"][field] = value
            with self.assertRaises(ValueError):
                self.evaluate_fixture(files)
        files = self.evidence()
        usage = next(iter(files["measurement.json"]["windows"][0]["fixture_usage"].values()))
        usage["prompt_tokens"] += 1
        with self.assertRaises(ValueError):
            self.evaluate_fixture(files)
        files = self.evidence()
        files["measurement.json"]["worker"]["audit"]["prompt_tokens_by_request_sha256"] = {}
        with self.assertRaises(ValueError):
            self.evaluate_fixture(files)
