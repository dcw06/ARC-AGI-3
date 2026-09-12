"""Validate the implemented Plan 8 Phase 0F/M0 gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(condition: bool, label: str, failures: list[str]) -> None:
    print(f"{'PASS' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def load(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text())


def main() -> int:
    failures: list[str] = []
    evidence = load("evidence_policy.yaml")
    representation = load("representation_manifest.yaml")
    experiments = load("experiment_registry.yaml")
    models = load("model_manifest.yaml")
    launches = {
        "M0-Q38-27B-FP8": load("m0_launch_spec_q38.json"),
        "M0-Q3VL-30B-A3B-FP8": load("m0_launch_spec_q3vl30.json"),
        "M0-Q3VL-8B-FP8": load("m0_launch_spec_q3vl8.json"),
    }
    runtime = load("runtime_profiles.yaml")
    profile_schema = load("m0_profile_schema.json")

    check(
        evidence.get("status") == "phase0f_foundation_active",
        "evidence policy activated",
        failures,
    )
    check(
        evidence.get("availability_values")
        == [
            "exact",
            "summarized",
            "omitted_capacity",
            "evicted_pressure",
            "unavailable_storage",
            "corrupt",
        ],
        "evidence loss states are complete and explicit",
        failures,
    )
    check(
        evidence.get("failure_policy", {}).get("silent_loss_allowed") is False
        and evidence.get("failure_policy", {}).get("storage_failure_preserves_T0") is True,
        "storage degradation is fail-soft and loss-explicit",
        failures,
    )
    check(
        representation.get("raw_observation", {}).get("arm") == "R"
        and representation.get("engineered_observation", {}).get("arm") == "F"
        and representation.get("engineered_observation", {}).get("toggleable") is True,
        "R and toggleable E0F contracts are registered",
        failures,
    )
    check(
        representation.get("raw_observation", {}).get("engineered_features_model_visible") is False
        and representation.get("raw_observation", {}).get("intermediate_frames_model_visible") is False,
        "R excludes F and intermediate-frame policy features",
        failures,
    )

    production = "\n".join(path.read_text() for path in (ROOT / "agent").glob("*.py"))
    check(".layers" not in production, "temporal frames are not treated as layers", failures)

    from scripts.build_notebook import bundled_sources

    bundled = bundled_sources()
    check(
        {"agent/evidence.py", "agent/representation.py"}.issubset(bundled),
        "Phase 0F runtime modules are in the offline notebook bundle",
        failures,
    )
    from scripts.build_m0_profile_notebook import bundled_sources as m0_bundled_sources

    m0_bundled = {
        candidate: m0_bundled_sources(candidate)
        for candidate in ("q38", "q3vl30", "q3vl8")
    }
    check(
        all(
            {
                "evaluation/__init__.py",
                "evaluation/metrics.py",
                "evaluation/m0_profile.py",
                "scripts/profile_m0_openai.py",
            }.issubset(bundle)
            and len([name for name in bundle if name.startswith("config/m0_launch_spec_")]) == 1
            for bundle in m0_bundled.values()
        ),
        "all M0 notebook bundles contain the complete profiler import chain",
        failures,
    )
    from scripts.build_m0_profile_notebook import PROFILE_SPECS

    kernel_metadata = [
        json.loads((ROOT / spec["output_dir"] / "kernel-metadata.json").read_text())
        for spec in PROFILE_SPECS.values()
    ]
    check(
        all(
            metadata.get("machine_shape") == "NvidiaRtxPro6000"
            and metadata.get("enable_internet") is False
            and metadata.get("enable_gpu") is True
            for metadata in kernel_metadata
        ),
        "all M0 kernels pin the target accelerator and offline execution",
        failures,
    )
    check(
        experiments.get("current_phase")
        in {"phase_0f_m0_complete", "phase_1_implementation_complete_execution_pending"}
        and models.get("status") == "M0_provisional_selection_complete",
        "M0 completion and candidate freeze are registered",
        failures,
    )
    candidates = models.get("candidates", [])
    required_candidate_fields = set(models.get("required_fields", []))
    check(
        models.get("candidate_set_frozen") is True
        and len(candidates) == 3
        and all(required_candidate_fields.issubset(candidate) for candidate in candidates)
        and all(
            len(candidate.get("revision", "")) == 40
            and candidate.get("license") == "Apache-2.0"
            for candidate in candidates
        ),
        "small candidate set has immutable revisions and model licenses",
        failures,
    )
    check(
        runtime.get("M0", {}).get("status") == "provisional_primary_and_fallback_selected"
        and len(runtime.get("M0", {}).get("measurements", [])) == 7
        and profile_schema.get("$id") == "arc3_m0_profile_v1",
        "target-RTX measurement protocol and result schema are frozen",
        failures,
    )
    check(
        models.get("engine", {}).get("bundle_runtime_use_status")
        == "pass_public_Kaggle_input_no_repo_redistribution"
        and models.get("engine", {}).get("release_redistribution_license_status")
        == "pending_exact_dependency_closure_review",
        "engine runtime use passes while redistribution review stays explicit",
        failures,
    )
    check(
        len(models.get("engine", {}).get("wheelhouse_sha256s_manifest_sha256", "")) == 64
        and len(models.get("engine", {}).get("wheelhouse_index_manifest_sha256", "")) == 64
        and models.get("engine", {}).get("wheelhouse_manifest_file_count") == 179
        and models.get("engine", {}).get("wheelhouse_runtime_verified_file_count") == 178,
        "offline wheelhouse checksum contract is frozen",
        failures,
    )
    check(
        models.get("engine", {}).get("compatibility_status")
        == "target_RTX_all_frozen_candidates_profiled"
        and models.get("engine", {}).get("compatibility_observation", {}).get("gpu")
        == "NVIDIA_RTX_PRO_6000"
        and models.get("engine", {}).get("published_notebook_source_bundle"),
        "target engine launch evidence and source-bundle dependency are explicit",
        failures,
    )
    candidates_by_id = {candidate.get("candidate_id"): candidate for candidate in candidates}
    package_pins = {"torch": "2.10.0+cu128", "transformers": "4.57.6", "vllm": "0.19.0"}
    check(
        all(
            launch.get("candidate_id") == candidate_id
            and launch.get("model_id") == candidates_by_id[candidate_id].get("model_id")
            and launch.get("model_revision") == candidates_by_id[candidate_id].get("revision")
            and launch.get("engine") == candidates_by_id[candidate_id].get("engine")
            and launch.get("reasoning_setting")
            in candidates_by_id[candidate_id].get("reasoning_settings", [])
            and launch.get("base_url") == "http://127.0.0.1:8000/v1"
            and launch.get("required_packages") == package_pins
            for candidate_id, launch in launches.items()
        ),
        "all target launch contracts match the frozen candidates",
        failures,
    )

    from evaluation.m0_profile import validate_profile_record

    profiles = {
        candidate_id: json.loads((ROOT / candidate["profile_record"]).read_text())
        for candidate_id, candidate in candidates_by_id.items()
    }
    check(
        all(
            not validate_profile_record(profiles[candidate_id], candidate)
            and profiles[candidate_id].get("artifact", {}).get("tree_sha256")
            == candidate.get("artifact_sha256")
            and "RTX PRO 6000"
            in profiles[candidate_id].get("hardware", {}).get("observed_gpu", "").upper()
            for candidate_id, candidate in candidates_by_id.items()
        ),
        "all frozen candidate profiles are valid, exact, and target-RTX measured",
        failures,
    )
    check(
        models.get("provisional_primary") == "M0-Q3VL-30B-A3B-FP8"
        and models.get("provisional_fallback") == "M0-Q3VL-8B-FP8"
        and all(candidate.get("kaggle_artifact_public") is True for candidate in candidates),
        "provisional primary and fallback are frozen from public artifacts",
        failures,
    )

    if failures:
        print(f"PHASE0F_M0_FAILED count={len(failures)}")
        return 1
    print("PHASE0F_FOUNDATION_PASSED")
    print("PHASE0F_M0_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
