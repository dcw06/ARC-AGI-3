"""Private fixture-only model prescreen. Supervisor retains aggregate evidence."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

from evaluation.phase4 import ROOT, sha
from evaluation.phase4_execution import authority, LOCK, PROTOCOL
from evaluation.phase4_preflight import sample_gpu
from evaluation.phase4_runner import TargetServiceBackend, group_rss_bytes, tree_bytes, terminate_group
from evaluation.phase4_workload import build_workload


def save(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def retain_checkpoint(path, report, output, max_bytes):
    """Copy the last atomic checkpoint before scratch disappears, even on failure."""
    if not path.exists():
        return
    try:
        if path.stat().st_size > max_bytes:
            raise ValueError("oversized evidence")
        worker = json.loads(path.read_text())
        if not isinstance(worker, dict):
            raise ValueError("invalid worker checkpoint")
        report["worker"] = worker
        report["windows"] = worker.get("windows", [])
    except (OSError, ValueError) as exc:
        report["checkpoint_error"] = type(exc).__name__ + ": " + str(exc)
    save(output / "measurement.json", report)


def gpu_pids():
    result = subprocess.run(["nvidia-smi", "--query-compute-apps=pid",
        "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True, timeout=2)
    return [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def bind_gpu(limit):
    result = subprocess.run(["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True, timeout=2)
    uuids = result.stdout.strip().splitlines()
    if len(uuids) != 1 or gpu_pids():
        raise ValueError("one exclusive idle target GPU required")
    row = sample_gpu(uuids[0].strip(), limit)
    return {"gpu_uuid": row["uuid"], "max_used_vram_bytes": limit,
            "initial_telemetry": row}


def capacity(windows):
    if (len(windows) != 8 or [w["index"] for w in windows] != list(range(8))
            or any(type(w["completed"]) is not int or w["completed"] != 1100
                   or type(w["seconds"]) not in (float, int)
                   or not math.isfinite(w["seconds"]) or w["seconds"] <= 0 for w in windows)):
        raise ValueError("eight complete finite fixed windows required")
    nominal = math.floor(19800 * 8800 / sum(w["seconds"] for w in windows))
    guard = .8 * min(1100 / w["seconds"] for w in windows)
    admit = min(nominal, math.floor(15840 * guard))
    return {"C_nominal": nominal, "C_admit": admit, "guard_requests_per_second": guard,
            "capacity_passed": admit >= 8800,
            "scope": "fixture_empirical_projection_not_full_game_or_hard_capacity"}


def group_exists(pgid):
    result = subprocess.run(["ps", "-axo", "pgid="], capture_output=True,
                            text=True, check=True, timeout=1)
    return str(pgid) in result.stdout.split()


def run_target(output, started, root=ROOT):
    reservation = authority(root)
    protocol = json.loads((root / PROTOCOL).read_text())
    limits = protocol["limits"]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Refuse reusing an output directory. The full reservation remains charged
    # even when provider startup fails or a notebook is accidentally replayed.
    with (output / "claim.json").open("x") as stream:
        json.dump(reservation, stream)
    report = {"schema_version": 1, "attempt_id": reservation["attempt_id"],
        "execution_lock_sha256": sha(root / LOCK), "status": "failed",
        "scope": protocol["scope"], "phase4_complete": False,
        "charged_or_reserved_seconds": 28800, "provider_reconciliation_required": True,
        "windows": [], "peak_group_rss_bytes": 0, "peak_vram_bytes": 0,
        "cleanup_verified": False, "peak_scratch_bytes": 0}
    process = None
    try:
        binding = bind_gpu(limits["vram_bytes"])
        report["gpu_uuid"] = binding["gpu_uuid"]
        report["gpu_samples"] = 0
        save(output / "gpu_binding.json", binding)
        with tempfile.TemporaryDirectory(prefix="p4-target-") as temporary:
            scratch = Path(temporary)
            state = scratch / "state.json"
            with (scratch / "worker.log").open("wb") as log:
                process = subprocess.Popen([sys.executable, str(root / "scripts/run_phase4_target.py"),
                    "--worker", "--output", str(output.resolve()), "--scratch", str(scratch),
                    "--started", str(started)], cwd=root, start_new_session=True,
                    stdout=log, stderr=subprocess.STDOUT)
                reason = "worker_exit"
                worker_started = time.monotonic()
                try:
                    while process.poll() is None:
                        elapsed = time.monotonic() - started
                        if elapsed >= limits["admission_cutoff_seconds"]:
                            raise TimeoutError("admission cutoff")
                        if ("audit" not in report.get("worker", {})
                                and time.monotonic() - worker_started >= limits["startup_seconds"]):
                            raise TimeoutError("startup/preflight ceiling")
                        rss = group_rss_bytes(process.pid)
                        row = sample_gpu(binding["gpu_uuid"], limits["vram_bytes"])
                        report["gpu_samples"] += 1
                        report["peak_group_rss_bytes"] = max(report["peak_group_rss_bytes"], rss)
                        report["peak_vram_bytes"] = max(report["peak_vram_bytes"], row["used_bytes"])
                        report["peak_scratch_bytes"] = max(report["peak_scratch_bytes"], tree_bytes(scratch))
                        if rss > limits["group_rss_bytes"] or report["peak_scratch_bytes"] > limits["scratch_bytes"]:
                            raise MemoryError("host RAM or scratch ceiling")
                        if state.exists():
                            retain_checkpoint(state, report, output, limits["retained_bytes"])
                            if report.get("checkpoint_error"):
                                raise ValueError(report["checkpoint_error"])
                            worker = report["worker"]
                            if worker.get("error"):
                                raise RuntimeError(worker["error"])
                            if worker.get("cancel_probe_ready"):
                                reason = "model_process_cancellation_probe"
                                break
                        time.sleep(limits["monitor_interval_seconds"])
                finally:
                    cleanup_started = time.monotonic()
                    try:
                        terminate_group(process, limits["cancellation_grace_seconds"])
                        deadline = cleanup_started + 15
                        while time.monotonic() < deadline:
                            if not group_exists(process.pid) and not gpu_pids():
                                report["cleanup_verified"] = True
                                break
                            time.sleep(.1)
                    finally:
                        report["cancellation_seconds"] = time.monotonic() - cleanup_started
                        report["stop_reason"] = reason
                        retain_checkpoint(state, report, output, limits["retained_bytes"])
            report["scratch_peak_final_bytes"] = tree_bytes(scratch)
        report["scratch_removed"] = not scratch.exists()
        if report.get("checkpoint_error") or report.get("worker", {}).get("error"):
            raise RuntimeError(report.get("checkpoint_error") or report["worker"]["error"])
        if (reason != "model_process_cancellation_probe" or not report["cleanup_verified"]
                or report["cancellation_seconds"] > 15):
            raise RuntimeError("model process cancellation not verified")
        report["capacity"] = capacity(report["windows"])
        if not report["capacity"]["capacity_passed"]:
            raise ValueError("fixture capacity admission failed")
        report["status"] = "passed_fixture_prescreen_only"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        report["elapsed_since_first_cell_seconds"] = time.monotonic() - started
        if report["elapsed_since_first_cell_seconds"] >= limits["lifecycle_seconds"]:
            report["status"] = "failed"
            report["error"] = "lifecycle limit exceeded"
        save(output / "measurement.json", report)
    return report


def worker(output, scratch, started, root=ROOT):
    authority(root)
    limits = json.loads((root / PROTOCOL).read_text())["limits"]
    workload = build_workload(root)
    binding = json.loads((output / "gpu_binding.json").read_text())
    backend = TargetServiceBackend(root)
    backend.gpu_binding = binding
    backend.primary = replace(backend.primary, scratch_log=scratch / "model.log")
    backend.service.primary = backend.primary
    state = {"windows": [], "completed_requests": 0, "model_inference": True}
    state_path = scratch / "state.json"
    requests = {f["fixture_id"]: f["request"] for f in workload["fixtures"]}
    stopped = threading.Event()
    from agent.scheduler import QueuedInferenceExecutor
    try:
        startup = time.monotonic()
        backend.start()
        state["startup_including_preflight_seconds"] = time.monotonic() - startup
        if state["startup_including_preflight_seconds"] > limits["startup_seconds"]:
            raise TimeoutError("startup/preflight ceiling")
        state["audit"] = backend.audit
        save(state_path, state)
        with QueuedInferenceExecutor(worker_count=8) as executor:
            for window in range(8):
                begin = time.monotonic()
                def client(index):
                    usage = {}
                    for step in range(window * 10, (window + 1) * 10):
                        if stopped.is_set():
                            raise RuntimeError("attempt already failed")
                        remaining = limits["admission_cutoff_seconds"] - (time.monotonic() - started)
                        if remaining <= 0:
                            raise TimeoutError("admission cutoff")
                        request = requests[workload["assignments"][index]["requests"][step]]
                        try:
                            completion = executor.execute(client_id=f"opaque-{index}", generation=step,
                                state_hash=str(step), callback=lambda request=request: backend.complete(request),
                                timeout_seconds=min(300, remaining))
                        except Exception:
                            stopped.set()
                            raise
                        fixture_id = workload["assignments"][index]["requests"][step]
                        entry = usage.setdefault(fixture_id, {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0})
                        entry["requests"] += 1
                        entry["prompt_tokens"] += completion.prompt_tokens
                        entry["completion_tokens"] += completion.completion_tokens
                    return usage
                with ThreadPoolExecutor(max_workers=110) as pool:
                    usage = {}
                    for client_usage in pool.map(client, range(110)):
                        for fixture_id, entry in client_usage.items():
                            total = usage.setdefault(fixture_id, {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0})
                            for key in total:
                                total[key] += entry[key]
                tokens = sum(v["prompt_tokens"] + v["completion_tokens"] for v in usage.values())
                state["windows"].append({"index": window, "completed": 1100,
                    "seconds": time.monotonic() - begin, "server_total_tokens": tokens,
                    "fixture_usage": usage})
                state["completed_requests"] += 1100
                state["max_queue_age_seconds"] = executor.queue.max_observed_age
                if executor.queue.max_observed_age > 300:
                    raise TimeoutError("queue age ceiling")
                save(state_path, state)
        # This certifies process-level service termination, not a vLLM
        # per-request abort API. Extra probe work is outside throughput windows.
        state["cancel_probe_ready"] = True
        save(state_path, state)
        backend.complete(next(iter(requests.values())))
        while True:
            time.sleep(1)
    except Exception as exc:
        state["error"] = type(exc).__name__ + ": " + str(exc)
        save(state_path, state)
        raise
    finally:
        backend.close()
