"""Profile the four frozen E1 request shapes on an offline target RTX server."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.e1_profile import E1_CELLS, capacity_projection, workload_sha256
from evaluation.m0_profile import inventory_artifact_tree, observed_gpu_memory_bytes
from scripts.profile_m0_openai import (
    ResourceSampler,
    _gpu_description,
    _percentile,
    _stream_fragment,
    _validate_launch_spec,
    _wait_ready,
)


MODEL_ID = "Qwen/Qwen3-VL-30B-A3B-Instruct-FP8"
MODEL_REVISION = "d9748a51ae66354c4dad665aab2c71f26cf2c8cd"
CANDIDATE_ID = "M0-Q3VL-30B-A3B-FP8"
ENGINE = "vllm==0.19.0"
REASONING = "instruct_non_thinking"
ARTIFACT_SHA256 = "052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627"
SAFE_OPERATIONS = {
    "array_shape", "cell_value", "palette", "changed_cells",
    "change_bounding_box", "connected_components", "region_summary",
    "translation_candidates",
}


def _request(messages: list[dict[str, str]], *, max_tokens: int, stream: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0,
        "seed": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "stream": stream,
    }
    if stream:
        result["stream_options"] = {"include_usage": True}
    return result


def _protocol_kind(text: str) -> str:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return "invalid"
    if not isinstance(value, Mapping):
        return "invalid"
    if (
        set(value) == {"operation", "arguments"}
        and value["operation"] in SAFE_OPERATIONS
        and isinstance(value["arguments"], Mapping)
    ):
        return "operation"
    action = value.get("action")
    if not set(value).issubset({"intent", "rationale", "action"}) or not isinstance(action, Mapping):
        return "invalid"
    if any(field in value and not isinstance(value[field], str) for field in ("intent", "rationale")):
        return "invalid"
    if set(action) != {"action_id", "action_data"}:
        return "invalid"
    action_id, action_data = action["action_id"], action["action_data"]
    if isinstance(action_id, bool) or not isinstance(action_id, int) or action_id not in range(1, 8):
        return "invalid"
    if not isinstance(action_data, Mapping):
        return "invalid"
    if action_id == 6:
        if set(action_data) != {"x", "y"}:
            return "invalid"
        x, y = action_data["x"], action_data["y"]
        if any(isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= 63 for item in (x, y)):
            return "invalid"
    elif action_data:
        return "invalid"
    return "action"


def _stream_once(
    endpoint: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.monotonic()
    first_token_at: float | None = None
    fragments: list[str] = []
    completion_tokens = 0
    prompt_tokens = 0
    with requests.post(
        endpoint,
        json=_request(messages, max_tokens=max_tokens, stream=True),
        stream=True,
        timeout=(30, timeout_seconds),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines(chunk_size=1, decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            item = json.loads(data)
            usage = item.get("usage") or {}
            completion_tokens = max(completion_tokens, int(usage.get("completion_tokens") or 0))
            prompt_tokens = max(prompt_tokens, int(usage.get("prompt_tokens") or 0))
            choices = item.get("choices") or []
            delta = choices[0].get("delta", {}) if choices else {}
            fragment = _stream_fragment(delta)
            if fragment:
                fragments.append(fragment)
                if first_token_at is None:
                    first_token_at = time.monotonic()
    finished = time.monotonic()
    if first_token_at is None:
        raise RuntimeError("E1 profile request returned no model text")
    text = "".join(fragments)
    return {
        "first_token_seconds": first_token_at - started,
        "elapsed_seconds": finished - started,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens or len(fragments),
        "protocol_kind": _protocol_kind(text),
        "response_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def _cancel_and_recover(
    endpoint: str,
    models_url: str,
    messages: list[dict[str, str]],
    timeout_seconds: float,
) -> float:
    response = requests.post(
        endpoint,
        json=_request(messages, max_tokens=4096, stream=True),
        stream=True,
        timeout=(30, timeout_seconds),
    )
    response.raise_for_status()
    for line in response.iter_lines(chunk_size=1, decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data != "[DONE]" and _stream_fragment((json.loads(data).get("choices") or [{}])[0].get("delta", {})):
            break
    else:
        response.close()
        raise RuntimeError("E1 cancellation request returned no token")
    started = time.monotonic()
    response.close()
    deadline = started + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if requests.get(models_url, timeout=5).ok:
                probe = _stream_once(
                    endpoint,
                    messages,
                    max_tokens=16,
                    timeout_seconds=min(timeout_seconds, 60),
                )
                if probe["completion_tokens"]:
                    return time.monotonic() - started
        except (requests.RequestException, RuntimeError):
            pass
        time.sleep(0.25)
    raise TimeoutError("E1 server did not recover after cancellation")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--launch-spec", type=Path, required=True)
    parser.add_argument("--workloads", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server-log", type=Path)
    parser.add_argument("--trials-per-cell", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--ready-timeout-seconds", type=float, default=900)
    parser.add_argument("--request-timeout-seconds", type=float, default=600)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.trials_per_cell < 1 or args.concurrency < 1 or args.max_new_tokens < 2:
        raise SystemExit("invalid E1 profile trial limits")
    workloads = json.loads(args.workloads.read_text())
    if tuple(workloads) != E1_CELLS or any(not isinstance(workloads[cell], list) for cell in E1_CELLS):
        raise SystemExit("workload file does not contain the exact ordered E1 cells")
    if "profile-fixture-never-model-visible" in json.dumps(workloads):
        raise SystemExit("workload fixture leaked the game identity")

    spec = json.loads(args.launch_spec.read_text())
    identity = argparse.Namespace(
        candidate_id=CANDIDATE_ID,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        engine=ENGINE,
        reasoning_setting=REASONING,
        base_url="http://127.0.0.1:8000/v1",
        model_path=args.model_path,
    )
    argv, observed_packages = _validate_launch_spec(spec, identity)
    observed_gpu = _gpu_description()
    if "rtx pro 6000" not in observed_gpu.lower():
        raise SystemExit(f"target GPU mismatch: {observed_gpu}")

    environment = os.environ.copy()
    environment.update(spec["env"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.server_log or args.output.with_suffix(".server.log")
    launch_started = time.monotonic()
    with log_path.open("wb") as server_log:
        process = subprocess.Popen(argv, env=environment, stdout=server_log, stderr=subprocess.STDOUT)
        sampler = ResourceSampler(process.pid)
        sampler.start()
        try:
            _wait_ready("http://127.0.0.1:8000/v1/models", process, args.ready_timeout_seconds)
            cold_load = time.monotonic() - launch_started
            endpoint = "http://127.0.0.1:8000/v1/chat/completions"
            # The required canary is deliberately first and isolated.
            canary = _stream_once(
                endpoint,
                workloads["E1S-R"],
                max_tokens=args.max_new_tokens,
                timeout_seconds=args.request_timeout_seconds,
            )
            cell_results: dict[str, Any] = {}
            for cell in E1_CELLS:
                started = time.monotonic()
                with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
                    trials = list(
                        executor.map(
                            lambda _index, selected=cell: _stream_once(
                                endpoint,
                                workloads[selected],
                                max_tokens=args.max_new_tokens,
                                timeout_seconds=args.request_timeout_seconds,
                            ),
                            range(args.trials_per_cell),
                        )
                    )
                wall = time.monotonic() - started
                allowed_kinds = {"action"} if cell.startswith("E1S") else {"action", "operation"}
                cell_results[cell] = {
                    "trials": trials,
                    "wall_seconds": wall,
                    "request_latency_p95_seconds": _percentile(
                        [float(item["elapsed_seconds"]) for item in trials], 0.95
                    ),
                    "first_token_p95_seconds": _percentile(
                        [float(item["first_token_seconds"]) for item in trials], 0.95
                    ),
                    "protocol_valid_count": sum(item["protocol_kind"] in allowed_kinds for item in trials),
                    "aggregate_completion_tokens_per_second": sum(
                        int(item["completion_tokens"]) for item in trials
                    ) / max(wall, 1e-9),
                }
            cancellation = _cancel_and_recover(
                endpoint,
                "http://127.0.0.1:8000/v1/models",
                workloads["E1C-F"],
                args.request_timeout_seconds,
            )
        finally:
            sampler.stop()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    artifact = inventory_artifact_tree(args.model_path)
    if artifact.tree_sha256 != ARTIFACT_SHA256:
        raise RuntimeError("the mounted model tree no longer matches the frozen M0 artifact")
    cell_projections = {
        cell: capacity_projection(
            cold_load_seconds=cold_load,
            latency_guard_seconds=float(cell_results[cell]["request_latency_p95_seconds"]),
            request_count=8_800 if cell.startswith("E1S") else 70_400,
            concurrency=args.concurrency,
        )
        for cell in E1_CELLS
    }
    projection = {
        "by_cell": cell_projections,
        "all_cells_pass_request_admission": all(
            bool(item["passes_request_admission"]) for item in cell_projections.values()
        ),
        "all_cells_pass_operational_target": all(
            bool(item["passes_operational_target"]) for item in cell_projections.values()
        ),
    }
    total_vram = observed_gpu_memory_bytes(observed_gpu)
    safety = {
        "canary_protocol_valid": canary["protocol_kind"] == "action",
        "all_cells_protocol_valid": all(
            cell_results[cell]["protocol_valid_count"] == args.trials_per_cell
            for cell in E1_CELLS
        ),
        "vram_headroom_at_least_5_percent": sampler.peak_vram_bytes <= total_vram * 0.95,
        "cancellation_within_queue_age": cancellation <= 300,
        "C_admit_pass": bool(projection["all_cells_pass_request_admission"]),
        "operational_target_pass": bool(projection["all_cells_pass_operational_target"]),
    }
    record = {
        "schema_version": 1,
        "status": "resource_profile_passed_game_runs_pending" if all(safety.values()) else "resource_profile_failed",
        "candidate_id": CANDIDATE_ID,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "engine": ENGINE,
        "reasoning_setting": REASONING,
        "workload_sha256": workload_sha256(workloads),
        "hardware": {
            "machine": os.getenv("KAGGLE_MACHINE_TYPE", "g4-standard-48_expected"),
            "accelerator": "nvidiaRtxPro6000_expected",
            "observed_gpu": observed_gpu,
            "observed_packages": observed_packages,
            "measured_at": datetime.now(timezone.utc).isoformat(),
        },
        "artifact": {
            "tree_sha256": artifact.tree_sha256,
            "file_count": artifact.file_count,
            "total_bytes": artifact.total_bytes,
        },
        "measurements": {
            "cold_load_seconds": cold_load,
            "peak_vram_bytes": sampler.peak_vram_bytes,
            "peak_ram_bytes": sampler.peak_ram_bytes,
            "cancellation_seconds": cancellation,
            "canary": canary,
            "cells": cell_results,
        },
        "projection": projection,
        "safety": safety,
    }
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.output)
    print(json.dumps({"status": record["status"], "output": str(args.output)}))
    return 0 if record["status"] != "resource_profile_failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
