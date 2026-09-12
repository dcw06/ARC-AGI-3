"""Profile one frozen M0 candidate through an OpenAI-compatible local server.

This script is intended to run inside an internet-disabled Kaggle RTX notebook.
It launches a pinned server from an argv-only JSON spec, hashes the mounted
artifact, performs sequential/concurrent streaming trials, verifies cancellation
recovery, samples RAM/VRAM, and writes a schema-shaped JSON record.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.m0_profile import (
    inventory_artifact_tree,
    project_execution_seconds,
    validate_profile_record,
)


DEFAULT_PROMPT = (
    "You control an unfamiliar grid environment. State one legal next action "
    "and briefly explain the visible evidence for it. Legal actions: 1, 2, 3, 4, 5, 6."
)


class ResourceSampler:
    def __init__(self, root_pid: int, interval_seconds: float = 0.1) -> None:
        self.root_pid = root_pid
        self.interval_seconds = interval_seconds
        self.peak_ram_bytes = 0
        self.peak_vram_bytes = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="m0-resource-sampler", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            pids = _process_family(self.root_pid)
            self.peak_ram_bytes = max(self.peak_ram_bytes, sum(_rss_bytes(pid) for pid in pids))
            self.peak_vram_bytes = max(self.peak_vram_bytes, _vram_bytes(pids))


def _process_family(root_pid: int) -> set[int]:
    parents: dict[int, int] = {}
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            fields = (entry / "stat").read_text().split()
            parents[int(fields[0])] = int(fields[3])
        except (OSError, ValueError, IndexError):
            continue
    family = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in family and pid not in family:
                family.add(pid)
                changed = True
    return family


def _rss_bytes(pid: int) -> int:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _vram_bytes(pids: set[int]) -> int:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    total_mib = 0
    for line in result.stdout.splitlines():
        try:
            pid_text, memory_text = (part.strip() for part in line.split(",", 1))
            if int(pid_text) in pids:
                total_mib += int(memory_text)
        except (ValueError, TypeError):
            continue
    return total_mib * 1024 * 1024


def _gpu_description() -> str:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "; ".join(line.strip() for line in result.stdout.splitlines() if line.strip())
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def _request_payload(model_id: str, prompt: str, max_tokens: int, reasoning: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
    }
    if reasoning in {"low", "medium", "xhigh"}:
        payload["reasoning_effort"] = reasoning
    elif reasoning == "instruct_non_thinking":
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    else:
        raise ValueError(f"unsupported reasoning setting: {reasoning}")
    return payload


def _stream_fragment(delta: dict[str, Any]) -> str:
    """Return visible or reasoning text across current and legacy vLLM fields."""
    for field in ("content", "reasoning", "reasoning_content"):
        value = delta.get(field)
        if isinstance(value, str) and value:
            return value
    return ""


def _stream_once(
    endpoint: str,
    *,
    model_id: str,
    prompt: str,
    max_tokens: int,
    reasoning: str,
    timeout_seconds: float,
) -> dict[str, float | int | str]:
    started = time.monotonic()
    first_token_at: float | None = None
    fragment_count = 0
    completion_tokens = 0
    with requests.post(
        endpoint,
        json=_request_payload(model_id, prompt, max_tokens, reasoning),
        stream=True,
        timeout=(30, timeout_seconds),
    ) as response:
        response.raise_for_status()
        # Prevent requests' default 512-byte buffering from inflating TTFT.
        for line in response.iter_lines(chunk_size=1, decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            item = json.loads(data)
            usage = item.get("usage") or {}
            completion_tokens = max(completion_tokens, int(usage.get("completion_tokens") or 0))
            choices = item.get("choices") or []
            delta = choices[0].get("delta", {}) if choices else {}
            fragment = _stream_fragment(delta)
            if fragment:
                fragment_count += 1
                if first_token_at is None:
                    first_token_at = time.monotonic()
    finished = time.monotonic()
    if first_token_at is None:
        raise RuntimeError("stream completed without a content or reasoning token")
    token_count = completion_tokens or fragment_count
    decode_seconds = max(finished - first_token_at, 1e-9)
    return {
        "first_token_seconds": first_token_at - started,
        "elapsed_seconds": finished - started,
        "decode_tokens_per_second": token_count / decode_seconds,
        "completion_tokens": token_count,
        "token_count_source": "server_usage" if completion_tokens else "stream_fragment_fallback",
    }


def _wait_ready(models_url: str, process: subprocess.Popen[Any], timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"model server exited during cold load with {process.returncode}")
        try:
            response = requests.get(models_url, timeout=5)
            if response.ok:
                return
            last_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error = type(exc).__name__
        time.sleep(1)
    raise TimeoutError(f"model server readiness exceeded {timeout_seconds}s; last={last_error}")


def _validate_launch_spec(spec: dict[str, Any], args: argparse.Namespace) -> tuple[list[str], dict[str, str]]:
    expected_identity = {
        "candidate_id": args.candidate_id,
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "engine": args.engine,
        "reasoning_setting": args.reasoning_setting,
        "base_url": args.base_url,
    }
    for field, expected in expected_identity.items():
        if spec.get(field) != expected:
            raise SystemExit(f"launch spec {field} does not match CLI identity")

    argv = spec.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        raise SystemExit("launch spec must contain a non-empty string argv list")
    replacements = {"{python}": sys.executable, "{model_path}": str(args.model_path)}
    resolved_argv = [replacements.get(item, item) for item in argv]

    launch_env = spec.get("env", {})
    if not isinstance(launch_env, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in launch_env.items()
    ):
        raise SystemExit("launch spec env must contain string keys and values")

    required_packages = spec.get("required_packages", {})
    if not isinstance(required_packages, dict) or not required_packages:
        raise SystemExit("launch spec must pin required_packages")
    observed_packages: dict[str, str] = {}
    for package, expected in required_packages.items():
        if not isinstance(package, str) or not isinstance(expected, str):
            raise SystemExit("launch spec required_packages must contain string pins")
        try:
            observed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise SystemExit(f"required package is not installed: {package}") from exc
        if observed != expected:
            raise SystemExit(
                f"required package mismatch: {package} expected={expected} observed={observed}"
            )
        observed_packages[package] = observed
    return resolved_argv, observed_packages


def _cancel_and_recover(
    endpoint: str,
    models_url: str,
    *,
    model_id: str,
    prompt: str,
    reasoning: str,
    timeout_seconds: float,
) -> float:
    response = requests.post(
        endpoint,
        json=_request_payload(model_id, prompt, 4096, reasoning),
        stream=True,
        timeout=(30, timeout_seconds),
    )
    response.raise_for_status()
    saw_fragment = False
    for line in response.iter_lines(chunk_size=1, decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        item = json.loads(data)
        choices = item.get("choices") or []
        delta = choices[0].get("delta", {}) if choices else {}
        if _stream_fragment(delta):
            saw_fragment = True
            break
    if not saw_fragment:
        response.close()
        raise RuntimeError("cancellation trial produced no token")
    started = time.monotonic()
    response.close()
    deadline = started + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if requests.get(models_url, timeout=5).ok:
                probe = _stream_once(
                    endpoint,
                    model_id=model_id,
                    prompt="Reply with OK.",
                    max_tokens=1,
                    reasoning="instruct_non_thinking",
                    timeout_seconds=min(60, timeout_seconds),
                )
                if probe["completion_tokens"]:
                    return time.monotonic() - started
        except (requests.RequestException, RuntimeError):
            pass
        time.sleep(0.25)
    raise TimeoutError("server did not recover after stream cancellation")


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires observations")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--reasoning-setting", required=True)
    parser.add_argument("--launch-spec", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server-log", type=Path)
    parser.add_argument("--sequential-trials", type=int, default=3)
    parser.add_argument("--concurrent-trials", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--ready-timeout-seconds", type=float, default=900)
    parser.add_argument("--request-timeout-seconds", type=float, default=600)
    parser.add_argument("--projected-requests", type=int)
    parser.add_argument("--projection-safety-factor", type=float, default=1.25)
    parser.add_argument("--expected-gpu-substring", default="RTX PRO 6000")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.sequential_trials < 1 or args.concurrent_trials < 1 or args.max_new_tokens < 2:
        raise SystemExit("trial counts must be positive and max-new-tokens must be at least 2")
    if args.ready_timeout_seconds <= 0 or args.request_timeout_seconds <= 0:
        raise SystemExit("timeouts must be positive")
    if args.projected_requests is not None and args.projected_requests < 0:
        raise SystemExit("projected-requests must be non-negative")
    if not math.isfinite(args.projection_safety_factor) or args.projection_safety_factor < 1:
        raise SystemExit("projection-safety-factor must be finite and at least 1")
    if args.base_url != "http://127.0.0.1:8000/v1":
        raise SystemExit("base-url must use the frozen local endpoint")
    if len(args.model_revision) != 40 or any(
        character not in "0123456789abcdef" for character in args.model_revision
    ):
        raise SystemExit("model-revision must be a lowercase 40-character commit hash")
    # Reject unsupported reasoning settings before allocating a GPU or loading weights.
    _request_payload(args.model_id, DEFAULT_PROMPT, args.max_new_tokens, args.reasoning_setting)
    spec = json.loads(args.launch_spec.read_text())
    argv, observed_packages = _validate_launch_spec(spec, args)
    launch_env = spec["env"]

    prompt = args.prompt_file.read_text() if args.prompt_file else DEFAULT_PROMPT
    observed_gpu = _gpu_description()
    if args.expected_gpu_substring.lower() not in observed_gpu.lower():
        raise SystemExit(
            "target GPU mismatch: "
            f"expected substring={args.expected_gpu_substring!r} observed={observed_gpu!r}"
        )
    environment = os.environ.copy()
    environment.update(launch_env)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    server_log_path = args.server_log or args.output.with_suffix(".server.log")
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    launch_started = time.monotonic()
    with server_log_path.open("wb") as server_log:
        process = subprocess.Popen(
            argv,
            env=environment,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        sampler = ResourceSampler(process.pid)
        sampler.start()
        try:
            _wait_ready(f"{args.base_url}/models", process, args.ready_timeout_seconds)
            cold_load = time.monotonic() - launch_started
            endpoint = f"{args.base_url}/chat/completions"
            sequential = [
                _stream_once(
                    endpoint,
                    model_id=args.model_id,
                    prompt=prompt,
                    max_tokens=args.max_new_tokens,
                    reasoning=args.reasoning_setting,
                    timeout_seconds=args.request_timeout_seconds,
                )
                for _ in range(args.sequential_trials)
            ]
            concurrent_started = time.monotonic()
            with ThreadPoolExecutor(max_workers=args.concurrent_trials) as executor:
                concurrent = list(
                    executor.map(
                        lambda _: _stream_once(
                            endpoint,
                            model_id=args.model_id,
                            prompt=prompt,
                            max_tokens=args.max_new_tokens,
                            reasoning=args.reasoning_setting,
                            timeout_seconds=args.request_timeout_seconds,
                        ),
                        range(args.concurrent_trials),
                    )
                )
            concurrent_wall = time.monotonic() - concurrent_started
            aggregate_tokens = sum(int(item["completion_tokens"]) for item in concurrent)
            cancellation = _cancel_and_recover(
                endpoint,
                f"{args.base_url}/models",
                model_id=args.model_id,
                prompt=prompt,
                reasoning=args.reasoning_setting,
                timeout_seconds=args.request_timeout_seconds,
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

    # Hash only after the timed server run. Reading every weight shard before
    # launch would populate the host page cache and invalidate cold-load timing.
    artifact = inventory_artifact_tree(args.model_path)

    first_token_p95 = _percentile(
        [float(item["first_token_seconds"]) for item in sequential], 0.95
    )
    request_latency_p95 = _percentile(
        [float(item["elapsed_seconds"]) for item in concurrent], 0.95
    )
    projection = None
    if args.projected_requests is not None:
        projection = {
            "request_count": args.projected_requests,
            "measured_concurrency": args.concurrent_trials,
            "safety_factor": args.projection_safety_factor,
            "request_latency_p95_seconds": request_latency_p95,
            "projected_execution_seconds": project_execution_seconds(
                cold_load_seconds=cold_load,
                request_latency_seconds=request_latency_p95,
                request_count=args.projected_requests,
                measured_concurrency=args.concurrent_trials,
                safety_factor=args.projection_safety_factor,
            ),
        }
    record = {
        "schema_version": 1,
        "candidate_id": args.candidate_id,
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "engine": args.engine,
        "reasoning_setting": args.reasoning_setting,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "hardware": {
            "machine": os.getenv("KAGGLE_MACHINE_TYPE", "g4-standard-48_expected"),
            "accelerator": "nvidiaRtxPro6000_expected",
            "observed_gpu": observed_gpu,
            "observed_packages": observed_packages,
            "launch_spec_sha256": hashlib.sha256(args.launch_spec.read_bytes()).hexdigest(),
            "measured_at": datetime.now(timezone.utc).isoformat(),
        },
        "measurements": {
            "cold_load_seconds": cold_load,
            "first_token_seconds": first_token_p95,
            "decode_tokens_per_second": aggregate_tokens / max(concurrent_wall, 1e-9),
            "cancellation_seconds": cancellation,
            "peak_vram_bytes": sampler.peak_vram_bytes,
            "peak_ram_bytes": sampler.peak_ram_bytes,
            "offline_artifact_bytes": artifact.total_bytes,
            "sequential_trials": sequential,
            "concurrent_trials": concurrent,
            "concurrent_wall_seconds": concurrent_wall,
        },
        "artifact": {
            "tree_sha256": artifact.tree_sha256,
            "file_count": artifact.file_count,
            "symlinks_rejected": True,
        },
        "projection": projection,
        "status": "measured_unselected",
    }
    candidate_contract = {
        "candidate_id": args.candidate_id,
        "model_id": args.model_id,
        "revision": args.model_revision,
        "engine": args.engine,
        "artifact_sha256": None,
    }
    validation_failures = validate_profile_record(record, candidate_contract)
    if validation_failures:
        raise RuntimeError(
            "refusing to write an invalid M0 profile: " + ", ".join(validation_failures)
        )
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.output)
    print(json.dumps({"status": record["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
