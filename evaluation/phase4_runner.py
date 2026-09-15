"""Supervised Phase 4 service runner, with an offline fault backend.

The supervisor owns the deadline and process group; a timed-out Python thread
is never mistaken for cancellation of model computation.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from evaluation.phase4 import ROOT, sha
from evaluation.phase4_workload import build_workload

FAULTS = ("none", "startup", "inference", "timeout", "storage", "finalization", "hang", "finalization_hang")


def group_rss_bytes(pgid):
    """Host RSS for our dedicated process group, including descendants.

    A failed resource probe fails the run closed instead of returning zero.
    RSS can double-count shared pages; that is conservative for this limit.
    """
    result = subprocess.run(["ps", "-axo", "pgid=,rss="], capture_output=True,
                            text=True, check=True, timeout=1)
    return sum(int(parts[1]) * 1024 for line in result.stdout.splitlines()
               if len(parts := line.split()) == 2 and int(parts[0]) == pgid)


def require_target_authority(root=ROOT):
    from evaluation.phase4_execution import authority
    return authority(root)


def tree_bytes(root):
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink())


def terminate_group(process, grace_seconds):
    """Stop only the dedicated child session we launched, including model children."""
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            pass
    # The group may still contain model workers after its leader has exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=max(1, grace_seconds))


def supervise(*, fault="none", root=ROOT, timeout_seconds=15, reserve_seconds=2,
              disk_limit_bytes=16 * 1024 * 1024, memory_limit_bytes=2 * 1024**3,
              backend="fake"):
    if backend != "fake":
        require_target_authority(root)
        raise ValueError("Use scripts/run_phase4_target.py with a retained output directory for target execution")
    if fault not in FAULTS or not 0 < reserve_seconds < timeout_seconds:
        raise ValueError("invalid fault/deadline configuration")
    if min(disk_limit_bytes, memory_limit_bytes) < 1:
        raise ValueError("resource limits must be positive")
    started = time.monotonic()
    report = {"schema_version": 1, "run_id": "p4-service-" + uuid.uuid4().hex,
              "evidence_class": "offline_fake_service_fault_probe", "fault": fault,
              "target_gpu_certified": False, "phase4_complete": False,
              "status": "failed", "finalization_status": "not_started",
              "peak_group_rss_bytes": 0}
    with tempfile.TemporaryDirectory(prefix="p4-service-") as directory:
        scratch = Path(directory)
        result = scratch / "result.json"
        command = [sys.executable, str(root / "scripts/run_phase4_service.py"),
                   "--worker", "--fault", fault, "--scratch", str(scratch),
                   "--admission-seconds", str(timeout_seconds - reserve_seconds)]
        with (scratch / "worker.log").open("wb") as log:
            process = subprocess.Popen(command, cwd=root, start_new_session=True,
                                       stdout=log, stderr=subprocess.STDOUT)
            stop_reason = None
            try:
                while process.poll() is None:
                    elapsed = time.monotonic() - started
                    if elapsed >= timeout_seconds - reserve_seconds:
                        stop_reason = "admission_deadline"
                        break
                    if tree_bytes(scratch) > disk_limit_bytes:
                        stop_reason = "scratch_limit"
                        break
                    try:
                        rss = group_rss_bytes(process.pid)
                    except (OSError, ValueError, subprocess.SubprocessError):
                        stop_reason = "resource_monitor_failure"
                        break
                    report["peak_group_rss_bytes"] = max(report["peak_group_rss_bytes"], rss)
                    if rss > memory_limit_bytes:
                        stop_reason = "host_memory_limit"
                        break
                    time.sleep(.02)
            finally:
                cleanup_start = time.monotonic()
                terminate_group(process, min(.25, reserve_seconds / 2))
                report["process_group_cleanup_seconds"] = time.monotonic() - cleanup_start
            if result.exists() and result.stat().st_size <= disk_limit_bytes:
                try:
                    report["worker"] = json.loads(result.read_text())
                except (OSError, ValueError):
                    stop_reason = stop_reason or "invalid_result"
            worker = report.get("worker", {})
            report["finalization_status"] = worker.get("finalization_status", "unknown")
            report["status"] = ("passed" if process.returncode == 0 and not stop_reason
                                and worker.get("status") == "passed" else "failed")
            report["stop_reason"] = stop_reason or worker.get("error")
            report["child_returncode"] = process.returncode
            report["scratch_bytes"] = tree_bytes(scratch)
    report["elapsed_seconds"] = time.monotonic() - started
    report["within_deadline"] = report["elapsed_seconds"] < timeout_seconds
    report["scratch_removed"] = not scratch.exists()
    report["runner_sha256"] = sha(Path(__file__))
    return report


class TargetServiceBackend:
    """Production transport/lifecycle adapter; spending gate precedes startup.

    Hardware operations are mocked in tests. Spending authority is never inferred
    from a successful preflight or a changed draft boolean.
    """
    def __init__(self, root=ROOT):
        from agent.production_policy import ModelService, load_operational_primary
        self.root = root
        self.primary = load_operational_primary(root)
        self.service = ModelService(self.primary)
        self.audit = None
        self.monitor = None
        self.started = False

    def preflight(self):
        from evaluation.phase4_preflight import preflight
        self.audit = preflight(self.primary, build_workload(self.root), self.root)
        return self.audit

    def start(self):
        require_target_authority(self.root)
        from evaluation.phase4_preflight import GPUMonitor
        self.preflight()
        lock = json.loads((self.root / "config/phase4_preflight_lock.json").read_text())
        binding = getattr(self, "gpu_binding", lock)
        self.monitor = GPUMonitor(binding["gpu_uuid"], binding["max_used_vram_bytes"])
        try:
            self.monitor.start()
            elapsed = self.service.start()
            self.monitor.check()
            self.started = True
            return elapsed
        except Exception:
            self.close()
            raise

    def complete(self, request):
        from agent.e1_policy import OpenAICompatibleCompletionClient
        from evaluation.phase4_workload import canonical
        import hashlib
        import requests
        if not self.started or self.audit is None or self.monitor is None:
            raise RuntimeError("target backend is not preflighted and started")
        digest = hashlib.sha256(canonical(request)).hexdigest()
        expected = self.audit["prompt_tokens_by_request_sha256"].get(digest)
        if expected is None:
            raise ValueError("request outside audited workload")
        self.monitor.check()
        with requests.Session() as session:
            result = OpenAICompatibleCompletionClient(self.primary.base_url, session=session,
                timeout_seconds=self.primary.request_timeout_seconds).complete(request)
        self.monitor.check()
        if (type(result.prompt_tokens) is not int or result.prompt_tokens != expected
                or type(result.completion_tokens) is not int
                or not 0 <= result.completion_tokens <= request["max_tokens"]):
            raise ValueError("server token usage missing or differs from offline context audit")
        return result

    def close(self):
        self.started = False
        try:
            self.service.close()
        finally:
            if self.monitor is not None:
                self.monitor.close()


def fake_worker(scratch, fault, admission_seconds):
    from agent.scheduler import QueuedInferenceExecutor
    scratch = Path(scratch)
    started = time.monotonic()
    report = {"status": "failed", "finalization_status": "not_started",
              "model_inference": False, "completed_requests": 0, "windows": []}
    executor = None
    try:
        if fault == "startup":
            raise RuntimeError("injected_startup_failure")
        if fault == "hang":
            # Deliberately noncooperative backend: supervisor must end process.
            while True:
                time.sleep(1)
        workload = build_workload()
        requests = {f["fixture_id"]: f["request"] for f in workload["fixtures"]}
        executor = QueuedInferenceExecutor(worker_count=8)
        if fault == "storage":
            raise OSError("injected_evidence_storage_failure")
        for window in range(8):
            window_started = time.monotonic()
            def client(index):
                completed = 0
                for step in range(window * 10, (window + 1) * 10):
                    if time.monotonic() - started >= admission_seconds:
                        raise TimeoutError("admission_cutoff")
                    request = requests[workload["assignments"][index]["requests"][step]]
                    def complete():
                        if fault == "inference":
                            raise RuntimeError("injected_inference_failure")
                        if fault == "timeout":
                            time.sleep(.1)
                        # Exercise exact captured requests but do not invent token usage.
                        if request["max_tokens"] != 128:
                            raise ValueError("request drift")
                        return "fake_completion"
                    executor.execute(client_id=f"opaque-{index}", generation=step,
                        state_hash=str(step), callback=complete,
                        timeout_seconds=.01 if fault == "timeout" else max(.001,
                            admission_seconds - (time.monotonic() - started)))
                    completed += 1
                return completed
            with ThreadPoolExecutor(max_workers=110) as pool:
                completed = sum(pool.map(client, range(110)))
            report["completed_requests"] += completed
            report["windows"].append({"index": window, "completed": completed,
                                       "seconds": time.monotonic() - window_started})
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ":" + str(exc)
    finally:
        finalization_start = time.monotonic()
        if executor is not None:
            executor.close()
        if fault == "finalization_hang":
            while True:
                time.sleep(1)
        if fault == "finalization":
            report["status"] = "failed"
            report["error"] = "injected_finalization_failure"
            report["finalization_status"] = "unknown"
        else:
            report["finalization_status"] = "acknowledged_fake_service_only"
        report["finalization_seconds"] = time.monotonic() - finalization_start
        report["elapsed_seconds"] = time.monotonic() - started
        # Exclusive result creation; parent only trusts a bounded parseable file.
        with (scratch / "result.json").open("x") as stream:
            json.dump(report, stream)
    return 0 if report["status"] == "passed" else 1
