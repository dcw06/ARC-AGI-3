"""Fail-closed validation for the Plan 8 Phase 0F/M0 exit gate."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.m0_profile import (
    bounded_profile_projection,
    observed_gpu_memory_bytes,
    validate_profile_record,
)


def load(path: str | Path) -> dict:
    return json.loads((ROOT / path).read_text())


def check(condition: bool, label: str, failures: list[str]) -> None:
    print(f"{'PASS' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    models = load("config/model_manifest.yaml")
    runtime = load("config/runtime_profiles.yaml")
    m0 = runtime.get("M0", {})
    candidates = models.get("candidates", [])
    by_id = {candidate.get("candidate_id"): candidate for candidate in candidates}

    primary = models.get("provisional_primary")
    fallback = models.get("provisional_fallback")
    check(
        isinstance(primary, str)
        and isinstance(fallback, str)
        and primary != fallback
        and primary in by_id
        and fallback in by_id,
        "distinct provisional primary and fallback are frozen",
        failures,
    )
    check(
        models.get("status") == "M0_provisional_selection_complete"
        and m0.get("status") == "provisional_primary_and_fallback_selected",
        "M0 manifests declare the same completed gate",
        failures,
    )
    check(
        models.get("engine", {}).get("bundle_runtime_use_status")
        == "pass_public_Kaggle_input_no_repo_redistribution",
        "engine bundle is cleared for public-input runtime use",
        failures,
    )

    request_count = m0.get("projected_request_ceiling")
    safety_factor = m0.get("projection_safety_factor")
    operational_limit = runtime.get("operational_target_seconds")
    service_limit = runtime.get("model_service_busy_ceiling_seconds")
    check(
        request_count == 110 * 80
        and isinstance(safety_factor, (int, float))
        and safety_factor >= 1,
        "8,800-call production ceiling and projection guard are frozen",
        failures,
    )

    profiled_ids: set[str] = set()
    prompt_hashes: set[str] = set()
    launch_specs = {
        "M0-Q38-27B-FP8": ROOT / "config/m0_launch_spec_q38.json",
        "M0-Q3VL-30B-A3B-FP8": ROOT / "config/m0_launch_spec_q3vl30.json",
        "M0-Q3VL-8B-FP8": ROOT / "config/m0_launch_spec_q3vl8.json",
    }
    expected_packages = {
        "torch": "2.10.0+cu128",
        "transformers": "4.57.6",
        "vllm": "0.19.0",
    }
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id", "missing-candidate-id")
        record_name = candidate.get("profile_record")
        record_path = ROOT / record_name if isinstance(record_name, str) else None
        if record_path is None or not record_path.is_file():
            check(False, f"{candidate_id} target profile exists", failures)
            continue
        record = json.loads(record_path.read_text())
        profile_failures = validate_profile_record(record, candidate)
        check(not profile_failures, f"{candidate_id} identity and measurements validate", failures)
        if profile_failures:
            continue
        profiled_ids.add(candidate_id)
        hardware = record.get("hardware", {})
        measurements = record.get("measurements", {})
        prompt_hashes.add(record.get("prompt_sha256", ""))
        launch_spec = launch_specs.get(candidate_id)
        expected_launch_hash = (
            hashlib.sha256(launch_spec.read_bytes()).hexdigest()
            if launch_spec is not None and launch_spec.is_file()
            else None
        )
        check(
            record.get("reasoning_setting") in candidate.get("reasoning_settings", [])
            and hardware.get("observed_packages") == expected_packages
            and hardware.get("launch_spec_sha256") == expected_launch_hash,
            f"{candidate_id} reasoning, package, and launch pins match",
            failures,
        )
        observed_gpu = hardware.get("observed_gpu", "")
        target_gpu = isinstance(observed_gpu, str) and "RTX PRO 6000" in observed_gpu.upper()
        check(target_gpu, f"{candidate_id} ran on target RTX", failures)
        try:
            gpu_total = observed_gpu_memory_bytes(observed_gpu)
            vram_ratio = float(measurements["peak_vram_bytes"]) / gpu_total
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            vram_ratio = float("inf")
        check(vram_ratio <= 0.95, f"{candidate_id} retains at least 5% VRAM headroom", failures)
        check(
            measurements.get("offline_artifact_bytes") == candidate.get("kaggle_artifact_bytes")
            and candidate.get("kaggle_artifact_public") is True
            and candidate.get("artifact_sha256")
            == record.get("artifact", {}).get("tree_sha256"),
            f"{candidate_id} offline artifact is public, exact, and hash-frozen",
            failures,
        )
        try:
            projected = bounded_profile_projection(
                record,
                request_count=int(request_count),
                safety_factor=float(safety_factor),
            )
            service_seconds = projected - float(measurements["cold_load_seconds"])
        except (KeyError, TypeError, ValueError):
            projected = float("inf")
            service_seconds = float("inf")
        check(
            measurements.get("cold_load_seconds", float("inf"))
            <= runtime.get("startup_target_seconds", 0),
            f"{candidate_id} cold load fits startup allowance",
            failures,
        )
        check(
            projected <= operational_limit and service_seconds <= service_limit,
            f"{candidate_id} 8,800-call projection fits service and 7.65-hour envelopes",
            failures,
        )
        check(
            measurements.get("cancellation_seconds", float("inf"))
            <= runtime.get("maximum_queue_age_seconds", 300),
            f"{candidate_id} cancellation fits queue-age bound",
            failures,
        )
        print(
            f"INFO {candidate_id} projected_seconds={projected:.3f} "
            f"vram_ratio={vram_ratio:.4f}"
        )

    check(
        len(profiled_ids) == len(candidates) == 3,
        "the complete frozen three-candidate set is profiled",
        failures,
    )
    check(
        prompt_hashes == {
            "292307326672eac68114c93a576f339bca457a340745158ff928fae9b17d42c7"
        }
        and m0.get("request_contract", {}).get("max_new_tokens") == 128
        and m0.get("request_contract", {}).get("measured_concurrency") == 8,
        "candidate measurements share the frozen M0 request contract",
        failures,
    )
    check(
        all(
            by_id[candidate_id].get("selection_status")
            in {"provisional_primary", "provisional_fallback", "measured_not_selected"}
            for candidate_id in profiled_ids
        ),
        "every measured candidate has an explicit selection disposition",
        failures,
    )

    if failures:
        print(f"M0_EXIT_GATE_FAILED count={len(failures)}")
        return 1
    print("M0_EXIT_GATE_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
