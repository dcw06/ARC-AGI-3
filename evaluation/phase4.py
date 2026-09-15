"""Phase 4 local-only contract and synthetic service measurements.

Uses the production queue, not a replacement scheduler. Callback timings are
synthetic Python timings and confer no model or target-hardware certification.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import random
import threading
import time
import uuid

from agent.scheduler import QueuedInferenceExecutor

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "config/phase4_contract.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_contract(root=ROOT):
    value = json.loads((root / CONTRACT).read_text())
    lock = json.loads((root / "config/phase4_contract_lock.json").read_text())
    if sha(root / CONTRACT) != lock["contract_sha256"]:
        raise ValueError("Phase 4 contract drift; register a new version")
    required = {
        "config/operational_primary.yaml", "config/e1_feature_manifests.yaml",
        "config/e1_experiment_protocol.yaml", "config/runtime_profiles.yaml",
        "config/phase23_evidence_package.json", "config/phase2_closure.json",
        "config/phase3_decision.json", "config/holdout_ledger.yaml",
        "agent/scheduler.py", "agent/watchdog.py", "agent/e1_policy.py",
        "agent/competition_loop.py", "agent/production_policy.py",
    }
    if set(value["bindings"]) != required:
        raise ValueError("missing or extra Phase 4 binding")
    for name, digest in value["bindings"].items():
        if sha(root / name) != digest:
            raise ValueError("Phase 4 binding drift: " + name)
    if value["parent"] != "E1S-R" or value["phase4_complete"]:
        raise ValueError("invalid preparation disposition")
    return value


def quantiles(values):
    ordered = sorted(values)
    return {label: ordered[max(0, math.ceil(len(ordered) * p) - 1)] if ordered else None
            for label, p in (("p50", .5), ("p90", .9), ("p99", .99))}


def run_synthetic(root=ROOT, *, requests_per_client=None):
    contract = validate_contract(root)
    workload = contract["workload"]
    rounds = workload["requests_per_client"] if requests_per_client is None else requests_per_client
    if not 1 <= rounds <= workload["requests_per_client"]:
        raise ValueError("request count outside frozen local ceiling")
    clients = workload["clients"]
    started = time.monotonic()
    deadline = started + contract["budget"]["local_harness_deadline_seconds"]
    barrier = threading.Barrier(clients)
    mutex = threading.Lock()
    waits, services, failures = [], [], []
    counts = [0] * clients
    payloads = [b"x" * size for size in workload["payload_bytes"]]
    cfg = contract["scheduler"]
    with QueuedInferenceExecutor(maxsize=cfg["capacity"], worker_count=cfg["worker_count"],
                                 max_age_seconds=cfg["max_age_seconds"]) as executor:
        def client(index):
            barrier.wait(timeout=10)
            for generation in range(rounds):
                submitted = time.monotonic()
                remaining = deadline - submitted
                if remaining <= 0:
                    with mutex:
                        failures.append("local_deadline")
                    break
                payload = payloads[(index + generation) % len(payloads)]

                def callback(payload=payload, submitted=submitted):
                    service_start = time.monotonic()
                    result = hashlib.sha256(payload).hexdigest()
                    time.sleep(workload["synthetic_service_seconds"])
                    with mutex:
                        waits.append(service_start - submitted)
                        services.append(time.monotonic() - service_start)
                    return result

                try:
                    result = executor.execute(client_id=f"opaque-{index}", generation=generation,
                                              state_hash=str(generation), callback=callback,
                                              timeout_seconds=remaining)
                    if result != hashlib.sha256(payload).hexdigest():
                        raise ValueError("request-local result mismatch")
                    counts[index] += 1
                except Exception as exc:
                    with mutex:
                        failures.append(type(exc).__name__)
                    break

        order = list(range(clients))
        random.Random(workload["synthetic_seed"]).shuffle(order)
        with ThreadPoolExecutor(max_workers=clients) as pool:
            list(pool.map(client, order))
        maximum_size = executor.queue.max_observed_size
        maximum_age = executor.queue.max_observed_age
    elapsed = time.monotonic() - started
    complete = rounds == workload["requests_per_client"]
    passed = (not failures and all(n == rounds for n in counts)
              and maximum_size <= cfg["capacity"] and maximum_age <= cfg["max_age_seconds"]
              and elapsed < contract["budget"]["local_harness_deadline_seconds"])
    return {
        "schema_version": 1, "run_id": "p4-local-" + uuid.uuid4().hex,
        "evidence_class": "synthetic_queue_load_not_model_inference",
        "contract_sha256": sha(root / CONTRACT),
        "harness_sha256": sha(Path(__file__)),
        "parent_binding": contract["bindings"]["config/operational_primary.yaml"],
        "clients": clients, "requests_per_client": rounds, "complete_workload": complete,
        "completed_requests": sum(counts), "failed_requests": len(failures),
        "failure_types": failures, "per_client_completions": counts,
        "queue_wait_seconds": quantiles(waits), "service_seconds": quantiles(services),
        "max_queue_size": maximum_size, "max_queue_age_seconds": maximum_age,
        "elapsed_seconds": elapsed, "synthetic_requests_per_second": sum(counts) / elapsed,
        "local_load_passed": passed and complete, "smoke_passed": passed,
        "fault_tests_evaluated": False, "target_gpu_certified": False,
        "phase4_complete": False, "C_nominal": None, "C_admit": None,
    }
