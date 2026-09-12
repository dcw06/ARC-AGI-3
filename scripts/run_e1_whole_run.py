"""Run counterbalanced complete-workload E1 blocks with fresh model state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.e1_policy import OpenAICompatibleCompletionClient, binding_from_registry
from agent.feature_manifest import load_e1_feature_manifests
from evaluation.e1_experiment import SCORE_UNIT, frozen_feature_registry_sha256, frozen_protocol_sha256
from evaluation.e1_whole_run import analyze_blocks, validate_whole_run_record
from evaluation.m0_profile import inventory_artifact_tree
from scripts.profile_m0_openai import ResourceSampler, _gpu_description, _validate_launch_spec, _wait_ready
from scripts.run_e1_four_cell import _run_cell


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--launch-spec", type=Path, required=True)
    parser.add_argument("--source-protocol", type=Path, required=True)
    parser.add_argument("--whole-run-protocol", type=Path, required=True)
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--environments-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server-log-dir", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--expected-artifact-sha256", required=True)
    parser.add_argument("--expected-gpu-substring", default="RTX PRO 6000")
    parser.add_argument("--request-timeout-seconds", type=float, default=300)
    return parser.parse_args()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"registry is not an object: {path}")
    return value


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _run_fresh(
    cell_id: str,
    *,
    block_id: str,
    argv: list[str],
    server_env: dict[str, str],
    log_path: Path,
    args: argparse.Namespace,
    source_protocol: dict[str, Any],
    manifests: Any,
    binding: Any,
    deadline: float,
    reserve: float,
) -> dict[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= reserve:
        raise TimeoutError("whole-run finalization reserve reached before model start")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cell: dict[str, Any] | None = None
    with log_path.open("wb") as server_log:
        process = subprocess.Popen(argv, env=server_env, stdout=server_log, stderr=subprocess.STDOUT)
        sampler = ResourceSampler(process.pid)
        sampler.start()
        try:
            _wait_ready(args.base_url + "/models", process, min(900, remaining - reserve))
            ready_seconds = time.monotonic() - started
            canary_client = OpenAICompatibleCompletionClient(
                args.base_url,
                timeout_seconds=args.request_timeout_seconds,
            )
            try:
                canary = canary_client.complete(
                    {
                        "model": binding.model_id,
                        "messages": [{"role": "user", "content": "Reply exactly OK."}],
                        "temperature": 0,
                        "seed": 0,
                        "max_tokens": 8,
                        "chat_template_kwargs": {"enable_thinking": False},
                    }
                )
            finally:
                canary_client.session.close()
            if not canary.content:
                raise RuntimeError("fresh completion canary returned empty content")
            cell = _run_cell(
                cell_id,
                protocol=source_protocol,
                manifests=manifests,
                binding=binding,
                base_url=args.base_url,
                request_timeout_seconds=args.request_timeout_seconds,
                environments_dir=args.environments_dir,
                remaining_seconds=deadline - time.monotonic(),
                finalization_reserve_seconds=reserve,
            )
            cell["fresh_runtime"] = {
                "block_id": block_id,
                "fresh_process": True,
                "model_ready_seconds": ready_seconds,
                "completion_canary_passed": True,
                "completion_canary_tokens": canary.completion_tokens,
                "peak_vram_bytes": sampler.peak_vram_bytes,
                "peak_ram_bytes": sampler.peak_ram_bytes,
            }
        finally:
            sampler.stop()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=30)
    if cell is None:
        raise RuntimeError("complete-workload run returned no evidence")
    digest = hashlib.sha256()
    with log_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    cell["fresh_runtime"]["server_log"] = log_path.name
    cell["fresh_runtime"]["server_log_sha256"] = digest.hexdigest()
    return cell


def main() -> int:
    args = parse_args()
    source_protocol = _load(args.source_protocol)
    protocol = _load(args.whole_run_protocol)
    feature_registry = _load(args.feature_registry)
    manifests = load_e1_feature_manifests(args.feature_registry)
    binding = binding_from_registry(args.feature_registry)
    if protocol.get("status") != "frozen_pending_execution":
        raise SystemExit("whole-run protocol is not frozen pending execution")
    if protocol.get("source_protocol_sha256") != frozen_protocol_sha256(source_protocol):
        raise SystemExit("source E1 protocol digest drifted")
    if protocol.get("feature_registry_sha256") != frozen_feature_registry_sha256(feature_registry):
        raise SystemExit("E1 feature registry digest drifted")
    if protocol.get("model_binding") != source_protocol.get("model_binding"):
        raise SystemExit("whole-run model binding drifted")
    if args.base_url != "http://127.0.0.1:8000/v1":
        raise SystemExit("base URL must use the frozen loopback endpoint")

    spec = _load(args.launch_spec)
    identity = SimpleNamespace(
        candidate_id=binding.candidate_id,
        model_id=binding.model_id,
        model_revision=binding.revision,
        engine=binding.engine,
        reasoning_setting=binding.reasoning_setting,
        base_url=args.base_url,
        model_path=args.model_path,
    )
    argv, packages = _validate_launch_spec(spec, identity)
    gpu = _gpu_description()
    if args.expected_gpu_substring.lower() not in gpu.lower():
        raise SystemExit(f"target GPU mismatch: {gpu}")
    artifact = inventory_artifact_tree(args.model_path)
    if artifact.tree_sha256 != args.expected_artifact_sha256:
        raise SystemExit("frozen model artifact tree hash mismatch")

    execution = protocol["execution"]
    started = time.monotonic()
    deadline = started + float(execution["hard_seconds"])
    reserve = float(execution["finalization_reserve_seconds"])
    server_env = os.environ.copy()
    server_env.update(spec["env"])
    server_env["PYTHONUNBUFFERED"] = "1"
    output: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "experiment_id": protocol["experiment_id"],
        "score_unit": SCORE_UNIT,
        "protocol_sha256": hashlib.sha256(
            json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "model_binding": protocol["model_binding"],
        "artifact": {
            "tree_sha256": artifact.tree_sha256,
            "file_count": artifact.file_count,
            "total_bytes": artifact.total_bytes,
        },
        "runtime": {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "observed_gpu": gpu,
            "observed_packages": packages,
            "python": sys.version,
        },
        "blocks": [],
        "analysis": None,
    }
    _write_atomic(args.output, output)
    try:
        for block_spec in execution["blocks"]:
            block = {
                "block_id": block_spec["block_id"],
                "order": block_spec["order"],
                "cells": {},
            }
            output["blocks"].append(block)
            for cell_id in block_spec["order"]:
                log_path = args.server_log_dir / f"{block_spec['block_id']}-{cell_id}.server.log"
                block["cells"][cell_id] = _run_fresh(
                    cell_id,
                    block_id=block_spec["block_id"],
                    argv=argv,
                    server_env=server_env,
                    log_path=log_path,
                    args=args,
                    source_protocol=source_protocol,
                    manifests=manifests,
                    binding=binding,
                    deadline=deadline,
                    reserve=reserve,
                )
                _write_atomic(args.output, output)
        output["analysis"] = analyze_blocks(
            output["blocks"],
            minimum_nonzero_blocks=protocol["analysis"]["minimum_nonzero_blocks"],
        )
        output["runtime"]["completed_at"] = datetime.now(timezone.utc).isoformat()
        output["runtime"]["elapsed_seconds"] = time.monotonic() - started
        output["status"] = "complete"
        validate_whole_run_record(output, protocol)
        _write_atomic(args.output, output)
        return 0
    except BaseException as exc:
        output["status"] = "failed_closed"
        output["failure"] = type(exc).__name__
        output["runtime"]["elapsed_seconds"] = time.monotonic() - started
        _write_atomic(args.output, output)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
