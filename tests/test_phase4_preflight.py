from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agent.production_policy import load_operational_primary
from agent.e1_policy import CompletionResult
from evaluation.m0_profile import inventory_artifact_tree
from evaluation.phase4 import ROOT
from evaluation.phase4_preflight import verify_artifact, audit_context, sample_gpu, GPUMonitor
from evaluation.phase4_runner import TargetServiceBackend
from evaluation.phase4_workload import build_workload


class Phase4PreflightTests(unittest.TestCase):
    def test_artifact_bytes_and_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "config.json").write_text("{}")
            (path / "model-1.safetensors").write_bytes(b"fixture")
            primary = replace(load_operational_primary(ROOT), model_path=path,
                model_tree_sha256=inventory_artifact_tree(path).tree_sha256,
                required_files=("config.json",), shard_count=1)
            self.assertEqual(verify_artifact(primary)["file_count"], 2)
            (path / "model-1.safetensors").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_artifact(primary)
            (path / "alias").symlink_to(path / "config.json")
            with self.assertRaises(ValueError):
                verify_artifact(primary)

    def test_context_includes_completion_without_truncation(self):
        fixtures = build_workload()["fixtures"]
        tokenizer = Mock()
        tokenizer.apply_chat_template.return_value = [1] * 100
        self.assertEqual(len(audit_context(fixtures, tokenizer, 228)), 9)
        kwargs = tokenizer.apply_chat_template.call_args.kwargs
        self.assertTrue(kwargs["add_generation_prompt"])
        self.assertFalse(kwargs["truncation"])
        self.assertFalse(kwargs["enable_thinking"])
        with self.assertRaises(ValueError):
            audit_context(fixtures, tokenizer, 227)
        tokenizer.apply_chat_template.return_value = []
        with self.assertRaises(ValueError):
            audit_context(fixtures, tokenizer, 228)

    def test_gpu_identity_usage_and_missing_telemetry(self):
        with patch("evaluation.phase4_preflight.subprocess.run") as run:
            run.return_value = SimpleNamespace(stdout="GPU-test, NVIDIA RTX PRO 6000 Blackwell, 96000, 80000\n")
            self.assertEqual(sample_gpu("GPU-test", 90000 * 1024**2)["used_bytes"], 80000 * 1024**2)
            with self.assertRaises(MemoryError):
                sample_gpu("GPU-test", 70000 * 1024**2)
            with self.assertRaises(ValueError):
                sample_gpu("GPU-wrong", 90000 * 1024**2)
            run.return_value.stdout += run.return_value.stdout
            with self.assertRaises(ValueError):
                sample_gpu("GPU-test", 90000 * 1024**2)
            run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 2)
            with self.assertRaises(subprocess.TimeoutExpired):
                sample_gpu("GPU-test", 90000 * 1024**2)

    def test_monitor_failure_is_sticky(self):
        monitor = GPUMonitor("GPU-test", 1)
        with patch("evaluation.phase4_preflight.sample_gpu", side_effect=MemoryError):
            with self.assertRaises(MemoryError):
                monitor.check()
        with self.assertRaises(RuntimeError):
            monitor.check()
        monitor.close()

    def test_transport_requires_start_and_exact_server_token_parity(self):
        backend = TargetServiceBackend()
        request = build_workload()["fixtures"][0]
        with self.assertRaises(RuntimeError):
            backend.complete(request["request"])
        backend.started = True
        backend.monitor = Mock()
        backend.audit = {"prompt_tokens_by_request_sha256": {request["request_sha256"]: 100}}
        with patch("agent.e1_policy.OpenAICompatibleCompletionClient.complete") as complete:
            complete.return_value = CompletionResult("fixture", prompt_tokens=100, completion_tokens=5)
            self.assertEqual(backend.complete(request["request"]).completion_tokens, 5)
            complete.return_value = CompletionResult("fixture", prompt_tokens=99, completion_tokens=5)
            with self.assertRaises(ValueError):
                backend.complete(request["request"])
            complete.return_value = CompletionResult("fixture")
            with self.assertRaises(ValueError):
                backend.complete(request["request"])

    def test_failed_start_cleans_model_and_monitor(self):
        backend = TargetServiceBackend()
        backend.service = Mock()
        backend.service.start.side_effect = RuntimeError("startup failed")
        with patch("evaluation.phase4_runner.require_target_authority"), \
             patch.object(backend, "preflight"), \
             patch("evaluation.phase4_preflight.GPUMonitor") as monitor:
            with self.assertRaises(RuntimeError):
                backend.start()
            monitor.return_value.start.assert_called_once()
            backend.service.close.assert_called_once()
            monitor.return_value.close.assert_called_once()
        self.assertFalse(backend.started)


if __name__ == "__main__":
    unittest.main()
