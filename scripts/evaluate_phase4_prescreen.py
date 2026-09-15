"""Evaluate retained target fixture evidence, never mark Phase 4 complete."""
import argparse
import json
from pathlib import Path
import sys
import math
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4 import sha
from evaluation.phase4_execution import verify_lock, LOCK, PROTOCOL, LEDGER
from evaluation.phase4_target import capacity
from evaluation.phase4_workload import build_workload


def evaluate(directory, root=ROOT):
    try:
        return _evaluate(Path(directory), root)
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        raise ValueError("missing or malformed prescreen evidence") from exc


def number(value, lower, upper):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper


def _evaluate(directory, root):
    verify_lock(root)
    protocol = json.loads((root / PROTOCOL).read_text())
    limits = protocol["limits"]
    if sum(p.stat().st_size for p in directory.rglob("*") if p.is_file()) > limits["retained_bytes"]:
        raise ValueError("retained evidence ceiling exceeded")
    for name in (LOCK, PROTOCOL):
        if sha(directory / Path(name).name) != sha(root / name):
            raise ValueError("retained protocol or execution lock mismatch")
    report = json.loads((directory / "measurement.json").read_text())
    cost = json.loads((directory / "notebook-cost.json").read_text())
    claim = json.loads((directory / "claim.json").read_text())
    ledger = json.loads((directory / Path(LEDGER).name).read_text())
    binding = json.loads((directory / "gpu_binding.json").read_text())
    if (ledger["authorized_seconds"] != 28800 or not ledger["approval_reference"]
            or ledger["events"] != [claim] or claim["kind"] != "reserve" or claim["seconds"] != 28800):
        raise ValueError("retained reservation does not substantiate attempt")
    if (report["execution_lock_sha256"] != sha(root / LOCK)
            or claim["execution_lock_sha256"] != sha(root / LOCK)
            or claim["attempt_id"] != report["attempt_id"]
            or cost["charged_or_reserved_seconds"] != 28800
            or cost["status"] != "target_command_completed"
            or report["status"] != "passed_fixture_prescreen_only"
            or report["phase4_complete"] is not False
            or report["cleanup_verified"] is not True
            or report["scratch_removed"] is not True
            or not number(report["cancellation_seconds"], 0, 15)
            or not number(report["elapsed_since_first_cell_seconds"], .000001, 27539.999999)
            or not number(cost["elapsed_since_first_cell_seconds"], report["elapsed_since_first_cell_seconds"], 27539.999999)):
        raise ValueError("incomplete, unbound, or failed target prescreen")
    if (report.get("error") or report.get("checkpoint_error")
            or report["stop_reason"] != "model_process_cancellation_probe"
            or report["scope"] != protocol["scope"]
            or report["charged_or_reserved_seconds"] != 28800
            or cost["scope"] != "all_accelerator_time_including_setup_and_failures"
            or cost["provider_reconciliation_required"] is not True):
        raise ValueError("failed or wrongly scoped attempt")
    for field, ceiling in (("peak_group_rss_bytes", limits["group_rss_bytes"]),
                           ("peak_vram_bytes", limits["vram_bytes"]),
                           ("peak_scratch_bytes", limits["scratch_bytes"])):
        if not number(report[field], 1, ceiling):
            raise ValueError("resource evidence missing or over limit: " + field)
    gpu = binding["initial_telemetry"]
    if (not isinstance(binding["gpu_uuid"], str) or not binding["gpu_uuid"]
            or report["gpu_uuid"] != binding["gpu_uuid"] or gpu["uuid"] != binding["gpu_uuid"]
            or "RTX PRO 6000" not in gpu["name"]
            or binding["max_used_vram_bytes"] != limits["vram_bytes"]
            or not number(gpu["total_bytes"], limits["vram_bytes"], 1024**4)
            or not number(gpu["used_bytes"], 0, limits["vram_bytes"])
            or type(report["gpu_samples"]) is not int or report["gpu_samples"] < 1):
        raise ValueError("missing or inconsistent GPU evidence")
    worker = report["worker"]
    if (worker.get("error") or worker["model_inference"] is not True
            or worker["cancel_probe_ready"] is not True or worker["completed_requests"] != 8800
            or worker["windows"] != report["windows"]
            or not number(worker["startup_including_preflight_seconds"], 0, limits["startup_seconds"])
            or not number(worker["max_queue_age_seconds"], 0, limits["request_seconds"])):
        raise ValueError("missing or failed worker evidence")
    audit = worker["audit"]
    workload = build_workload(root)
    primary = json.loads((root / "config/operational_primary.yaml").read_text())["primary"]
    if (audit["workload_sha256"] != workload["workload_sha256"] or audit["context_limit"] != 65536
            or audit["artifact"]["tree_sha256"] != primary["model_artifact"]["tree_sha256"]
            or not number(audit["artifact"]["bytes"], 1, 1024**4)
            or type(audit["artifact"]["file_count"]) is not int or audit["artifact"]["file_count"] < 1):
        raise ValueError("artifact or tokenizer audit mismatch")
    counts = audit["prompt_tokens_by_request_sha256"]
    fixtures = {f["fixture_id"]: f for f in workload["fixtures"]}
    if set(counts) != {f["request_sha256"] for f in fixtures.values()}:
        raise ValueError("tokenizer audit inventory mismatch")
    for count in counts.values():
        if type(count) is not int or not 0 < count <= 65536 - 128:
            raise ValueError("invalid tokenizer length")
    for index, window in enumerate(report["windows"]):
        expected = Counter(name for assignment in workload["assignments"]
                           for name in assignment["requests"][index * 10:(index + 1) * 10])
        usage = window["fixture_usage"]
        if set(usage) != set(expected):
            raise ValueError("per-fixture server evidence inventory mismatch")
        total = 0
        for name, count in expected.items():
            item = usage[name]
            if (any(type(item[k]) is not int for k in ("requests", "prompt_tokens", "completion_tokens"))
                    or item["requests"] != count
                    or item["prompt_tokens"] != counts[fixtures[name]["request_sha256"]] * count
                    or not 0 <= item["completion_tokens"] <= 128 * count):
                raise ValueError("server token-count parity failure")
            total += item["prompt_tokens"] + item["completion_tokens"]
        if type(window["server_total_tokens"]) is not int or window["server_total_tokens"] != total:
            raise ValueError("server token total mismatch")
    result = capacity(report["windows"])
    if not result["capacity_passed"] or result != report["capacity"]:
        raise ValueError("capacity calculation mismatch or failure")
    return {**result, "phase4_complete": False, "provider_reconciliation_required": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.directory), indent=2))
