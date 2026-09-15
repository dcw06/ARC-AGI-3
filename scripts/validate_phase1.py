"""Validate completed local Phase 1 implementation and external execution gates."""

from __future__ import annotations

import json
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.e1_policy import binding_from_registry
from agent.feature_manifest import load_e1_feature_manifests
from agent.safe_operations import SAFE_OPERATIONS
from evaluation.e1_experiment import validate_experiment_record
from evaluation.e1_whole_run import validate_whole_run_record


SNAPSHOT_PATTERN = re.compile(r"^kaggle_snapshot_sha256:[0-9a-f]{64}$")


def load(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text())


def check(condition: bool, label: str, failures: list[str]) -> None:
    print(f"{'PASS' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    controls = load("control_registry.yaml")
    experiments = load("experiment_registry.yaml")
    e1 = load("e1_feature_manifests.yaml")
    operations = load("e1_safe_operations.yaml")
    proposal = load("e1_proposal_schema.json")
    models = load("model_manifest.yaml")
    protocol = load("e1_experiment_protocol.yaml")
    statistics = load("statistics_protocol.yaml")
    context = load("context_policy.yaml")
    holdout = load("holdout_ledger.yaml")
    dependencies = load("dependency_manifest.lock")
    operational = load("operational_primary.yaml")
    success = load("success_criteria.yaml")
    decision = load("phase1_decision.yaml")

    candidates = controls.get("candidates", [])
    public_candidates = [item for item in candidates if item.get("source_url") != "local"]
    candidates_by_id = {item.get("id"): item for item in candidates}
    duck = candidates_by_id.get("duck-qwen3.8-flash-next-nvfp4-anim", {})
    reki = candidates_by_id.get("reki-milestone1", {})
    structured_fallback = candidates_by_id.get(
        "e1s-r-project-structured-fallback", {}
    )
    workspace_substitute = candidates_by_id.get(
        "e1c-f-safe-operations-duck-substitute", {}
    )
    inventory = controls.get("inventory_audit", {})
    control_audit_path = ROOT / inventory.get("evidence", "missing")
    try:
        control_audit_bytes = control_audit_path.read_bytes()
        control_audit = json.loads(control_audit_bytes)
    except (OSError, json.JSONDecodeError):
        control_audit_bytes = b""
        control_audit = {}
    check(
        controls.get("status")
        == "cutoff_frozen_availability_and_license_decisions_closed"
        and controls.get("freeze_status")
        == "frozen_after_post_cutoff_inventory_audit"
        and controls.get("frozen_published_workspace_control") == duck.get("id")
        and controls.get("frozen_published_structured_reference") == reki.get("id")
        and controls.get("strongest_eligible_structured_control")
        == structured_fallback.get("id")
        and controls.get("adapted_workspace_substitute")
        == workspace_substitute.get("id"),
        "post-cutoff control inventory is frozen with explicit published and fallback roles",
        failures,
    )
    check(
        hashlib.sha256(control_audit_bytes).hexdigest()
        == inventory.get("evidence_sha256")
        and control_audit.get("status") == "complete_fail_closed"
        and control_audit.get("provenance_cutoff") == controls.get("cutoff")
        and control_audit.get("inventory_query", {}).get(
            "current_post_cutoff_revision_excluded"
        )
        is True,
        "control freeze references immutable post-cutoff inventory evidence",
        failures,
    )
    check(
        len(public_candidates) >= 5
        and all(SNAPSHOT_PATTERN.fullmatch(item.get("source_revision", "")) for item in public_candidates)
        and all(item.get("production_eligible") is False for item in public_candidates)
        and any(item.get("id") == "duck-qwen3.8-flash-next-nvfp4-anim" for item in public_candidates),
        "public controls have immutable snapshots including the current Duck candidate",
        failures,
    )
    duck_runner = duck.get("python_runner_decision", {})
    check(
        duck.get("license_review")
        == "closed_ineligible_unknown_distribution_licenses"
        and duck.get("control_fidelity")
        == "published_snapshot_frozen_faithful_execution_unavailable"
        and duck_runner.get("status") == "unavailable_isolation_unproven"
        and duck_runner.get("decision")
        == "do_not_execute_model_authored_python_in_production"
        and {
            "enforced_filesystem_boundary",
            "credential_boundary",
            "native_code_boundary",
            "process_syscall_boundary",
            "adversarial_escape_pass_on_target_Kaggle_runtime",
        }
        <= set(duck_runner.get("missing_required_controls", []))
        and duck.get("artifact_hashes", {}).get("python_runner")
        == "765e90cf8d141f912f6cfbba498426c9b0de9453e6e44c97d3bc8df45cf9aa91",
        "faithful Duck runner is frozen unavailable on explicit Section 8.12 and license evidence",
        failures,
    )
    check(
        reki.get("license_components", {}).get("notebook")
        == "Apache-2.0_public_Kaggle_notebook"
        and reki.get("license_components", {}).get("model")
        == "Apache-2.0_google_gemma-4-31B-it_revision_4797d2888d4e7a1450a92a7d426967eeca6f3d7e"
        and reki.get("license_components", {}).get("wheelhouse_dataset")
        == "Kaggle_metadata_unknown"
        and reki.get("production_eligible") is False
        and structured_fallback.get("production_eligible") is True
        and structured_fallback.get("control_fidelity")
        == "project_owned_structured_fallback_not_a_published_reproduction"
        and workspace_substitute.get("production_eligible") is True
        and workspace_substitute.get("result_class") == "adapted_control"
        and "python_repl_replaced_by_fixed_safe_operations"
        in workspace_substitute.get("changed_from_duck", []),
        "structured reference fails closed and eligible substitutes cannot masquerade as reproductions",
        failures,
    )
    check(
        controls.get("selection_policy", {}).get("published_score_substitution_allowed") is False,
        "published scores cannot substitute for project reproductions",
        failures,
    )

    manifests = load_e1_feature_manifests(ROOT / "config/e1_feature_manifests.yaml")
    shared_features = e1.get("shared", {})
    disabled_later_treatments = (
        "durable_memory",
        "historical_retrieval",
        "typed_hypotheses",
        "prediction_checked_queue",
        "executable_python",
        "executable_transition_model",
        "search",
        "specialist",
    )
    check(
        set(manifests) == {"E1S-R", "E1S-F", "E1C-R", "E1C-F"}
        and len({item.scheduler for item in manifests.values()}) == 1
        and len({item.proposal_action_count for item in manifests.values()}) == 1
        and all(
            item.context_mode == "stateless_reconstruction_visible_compaction_v1"
            and item.recent_transition_limit == 1
            and item.history_loss_reporting
            == "lifetime_count_and_rolling_sha256_v1"
            for item in manifests.values()
        ),
        "four E1 cells share the frozen scheduler, context, and action surface",
        failures,
    )
    check(
        all(shared_features.get(field) is False for field in disabled_later_treatments)
        and proposal.get("additionalProperties") is False,
        "Section 5.4 later-treatment features are disabled and rejected by the strict schema",
        failures,
    )
    binding = binding_from_registry(ROOT / "config/e1_feature_manifests.yaml")
    model_candidates = {item["candidate_id"]: item for item in models.get("candidates", [])}
    selected = model_candidates.get(models.get("provisional_primary"), {})
    expected_binding = {
        "candidate_id": selected.get("candidate_id"),
        "model_id": selected.get("model_id"),
        "revision": selected.get("revision"),
        "engine": selected.get("engine"),
        "reasoning_setting": "instruct_non_thinking",
    }
    check(
        binding.candidate_id == models.get("provisional_primary")
        and e1.get("model_binding") == expected_binding
        and protocol.get("model_binding") == expected_binding,
        "all factorial cells have one exact M0 primary model/engine/reasoning binding",
        failures,
    )
    check(
        proposal.get("$id") == "e1_proposal_schema_v1"
        and proposal.get("additionalProperties") is False,
        "baseline proposal schema is strict and versioned",
        failures,
    )
    limits = operations.get("limits", {})
    check(
        operations.get("turing_complete") is False
        and operations.get("status") == "isolated_worker_implemented_and_adversarially_tested"
        and set(operations.get("operations", [])) == SAFE_OPERATIONS
        and limits.get("invocations_per_proposal") == 7
        and limits.get("additional_worker_address_space_bytes") == 268435456
        and limits.get("output_bytes_per_proposal") == 8192
        and all(
            limits.get(field) is False
            for field in (
                "persistent_state",
                "network",
                "arbitrary_filesystem",
                "package_install",
                "environment_calls",
            )
        ),
        "safe-operation worker is bounded, isolated, and authority-denying",
        failures,
    )

    pairs = protocol.get("development_game_seed_pairs", [])
    pair_games = [item.get("game_id") for item in pairs]
    fold_counts = {fold: sum(item.get("fold") == fold for item in pairs) for fold in range(1, 6)}
    check(
        protocol.get("status")
        == "four_cell_execution_complete_shared_resource_inference_pending"
        and pair_games == holdout.get("development")
        and len({item.get("seed") for item in pairs}) == 15
        and fold_counts == {1: 3, 2: 3, 3: 3, 4: 3, 5: 3},
        "development game/seed pairs and five balanced folds are frozen without holdout use",
        failures,
    )
    factorial = protocol.get("design", {}).get("factorial_estimands", {})
    check(
        protocol.get("design", {}).get("seed_scope")
        == "frozen_per_game_environment_and_model_request_seed"
        and factorial.get("unit") == "official_RHAE_percent_per_game"
        and factorial.get("minimum_nonzero_game_pairs") == 5
        and factorial.get("inference")
        == "exact_two_sided_paired_sign_flip_on_nonzero_game_contrasts"
        and factorial.get("multiplicity", "").startswith("descriptive_unadjusted"),
        "original same-model estimands and per-game seed scope remain frozen as diagnostic metadata",
        failures,
    )
    selection = protocol.get("selection", {})
    check(
        statistics.get("status")
        == "E1_complete_whole_run_all_effects_provisional"
        and selection.get("minimum_nonzero_game_pairs") == 5
        and selection.get("sparse_or_tied_status") == "Provisional primary"
        and "selection_procedure" in selection.get("selection_procedure_estimand", "")
        and context.get("E1_context_mode")
        == "stateless_reconstruction_visible_compaction_v1"
        and context.get("E1_recent_transition_limit") == 1
        and context.get("compaction_policy")
        == "visible_recent_transitions_v1_lifetime_count_and_rolling_sha256"
        and context.get("visible_compaction_activation")
        == "only_after_demonstrated_context_continuity_bottleneck"
        and context.get("cached_and_programmatic_modes") == "optional_inactive",
        "selection-aware estimands, sparse rule, and context policy are closed",
        failures,
    )

    resources = protocol.get("resource_projection", {})
    actual = resources.get("actual_profile", {})
    evidence_path = ROOT / actual.get("evidence", "missing")
    try:
        evidence_bytes = evidence_path.read_bytes()
        evidence = json.loads(evidence_bytes)
    except (OSError, json.JSONDecodeError):
        evidence_bytes = b""
        evidence = {}
    evidence_sha256 = hashlib.sha256(evidence_bytes).hexdigest()
    projections = evidence.get("projection", {}).get("by_cell", {})
    measured_cells = evidence.get("measurements", {}).get("cells", {})
    expected_cells = {"E1S-R", "E1S-F", "E1C-R", "E1C-F"}
    check(
        evidence_sha256 == actual.get("evidence_sha256")
        and evidence.get("candidate_id") == protocol.get("model_binding", {}).get("candidate_id")
        and evidence.get("model_revision") == protocol.get("model_binding", {}).get("revision")
        and evidence.get("engine") == protocol.get("model_binding", {}).get("engine")
        and set(projections) == expected_cells
        and set(measured_cells) == expected_cells
        and all(measured_cells[cell].get("protocol_valid_count") == 8 for cell in expected_cells)
        and all(projections[cell].get("passes_request_admission") is True for cell in expected_cells)
        and all(projections[cell].get("passes_operational_target") is True for cell in expected_cells)
        and evidence.get("safety", {}).get("vram_headroom_at_least_5_percent") is True
        and evidence.get("safety", {}).get("cancellation_within_queue_age") is True
        and protocol.get("design", {}).get("E1C_actual_request_ceiling_per_proposal") == 8
        and resources.get("maximum_model_requests") == 110 * 80 * 8
        and resources.get("maximum_model_requests")
        <= resources.get("minimum_C_admit_across_E1C_full_workload_cells", -1)
        and resources.get("maximum_projected_total_seconds_across_cells", 1e99)
        < resources.get("operational_target_seconds", 0)
        and resources.get("status") == "actual_mixed_prompt_target_RTX_profile_pass",
        "frozen target-RTX mixed profile passes protocol, memory, cancellation, C_admit, and time gates",
        failures,
    )
    execution = protocol.get("execution_status", {})
    four_cell = execution.get("four_cell_runs", {})
    four_cell_path = ROOT / four_cell.get("evidence", "missing") if isinstance(four_cell, dict) else ROOT / "missing"
    try:
        four_cell_bytes = four_cell_path.read_bytes()
        four_cell_record = json.loads(four_cell_bytes)
        validate_experiment_record(four_cell_record, protocol, e1)
        four_cell_valid = True
    except (OSError, ValueError, json.JSONDecodeError):
        four_cell_bytes = b""
        four_cell_record = {}
        four_cell_valid = False
    four_cell_sha256 = hashlib.sha256(four_cell_bytes).hexdigest()
    four_analysis = four_cell_record.get("analysis", {})
    four_selection = four_analysis.get("selection_procedure", {})
    four_contrasts = four_analysis.get("factorial_contrasts", {})
    check(
        isinstance(four_cell, dict)
        and four_cell.get("status")
        == "complete_valid_as_descriptive_single_block_not_causal_inference"
        and four_cell.get("kaggle_kernel_version") == 5
        and four_cell_sha256 == four_cell.get("evidence_sha256")
        and four_cell_valid
        and four_cell_record.get("status") == "complete"
        and set(four_analysis.get("cell_means", {})) == expected_cells
        and all(value == 0.0 for value in four_analysis.get("cell_means", {}).values())
        and set(four_contrasts) == {
            "representation_F_minus_R",
            "safe_operations_C_minus_S",
            "interaction_difference_in_differences",
        }
        and all(
            item.get("nonzero_pairs") == 0
            and item.get("two_sided_p_value") is None
            and item.get("status") == "Provisional"
            for item in four_contrasts.values()
        )
        and four_selection.get("final_fixed_candidate") == "E1S-R"
        and four_selection.get("selection_procedure_mean") == 0.0
        and four_cell.get("fixed_E1_candidate_status") == "Provisional primary"
        and execution.get("published_control_reproductions")
        == "unavailable_not_run_fail_closed"
        and execution.get("same_model_normalized_controls")
        == "not_justified_without_eligible_faithful_harness"
        and controls.get("faithful_published_reproduction_gate")
        == "closed_unavailable_no_eligible_published_runner"
        and controls.get("published_reproduction_disposition")
        == "unavailable_not_run_fail_closed"
        and controls.get("same_model_normalization_disposition")
        == "not_justified_without_an_eligible_faithful_published_harness"
        and execution.get("control_freeze")
        == "complete_published_runners_closed_unavailable_safe_substitutes_selected"
        and execution.get("actual_E1_mixed_prompt_target_RTX_profile")
        == "version_3_pass_all_safety_resource_and_protocol_gates_evidence_frozen"
        and execution.get("operational_primary") == "E1S-R"
        and execution.get("operational_primary_status")
        == "Provisional primary"
        and execution.get("operational_primary_binding")
        == "config/operational_primary.yaml"
        and experiments.get("treatments", {}).get("E1", {}).get("status")
        == "complete_counterbalanced_whole_run_valid_all_effects_provisional",
        "version-5 evidence is valid as a descriptive shared-resource run",
        failures,
    )

    primary = operational.get("primary", {})
    primary_evidence = primary.get("evidence", {})
    offline = dependencies.get("phase1_production_offline_bundle", {})
    selection_path = ROOT / primary_evidence.get("selection", "missing")
    resource_path = ROOT / primary_evidence.get("resource_profile", "missing")
    try:
        selection_sha256 = hashlib.sha256(selection_path.read_bytes()).hexdigest()
        resource_sha256 = hashlib.sha256(resource_path.read_bytes()).hexdigest()
    except OSError:
        selection_sha256 = resource_sha256 = ""
    from scripts.build_notebook import build as build_submission, bundled_sources

    submission = build_submission()
    submission_sources = bundled_sources()
    kaggle_metadata = json.loads((ROOT / "notebooks/kernel-metadata.json").read_text())
    hierarchical = ROOT / "reports/phase1_hierarchical_decision.md"
    hierarchical_text = hierarchical.read_text() if hierarchical.is_file() else ""
    completion_audit = ROOT / "reports/phase1_completion_audit.md"
    completion_audit_text = completion_audit.read_text() if completion_audit.is_file() else ""
    production_policy_text = (ROOT / "agent/production_policy.py").read_text()
    check(
        operational.get("status") == "active_provisional_primary"
        and primary.get("cell_id") == "E1S-R"
        and primary.get("operational_label") == "Provisional primary"
        and primary.get("acceptance_claim") is False
        and primary.get("model_binding") == expected_binding
        and primary.get("inference", {}).get("queue_policy") == "minimum_fair_v1"
        and primary.get("inference", {}).get("capacity") == 110
        and primary.get("inference", {}).get("worker_count") == 8
        and primary.get("runtime", {}).get("hard_seconds") == 27540
        and primary.get("runtime", {}).get("finalization_reserve_seconds") == 600
        and primary.get("runtime", {}).get("deadline_basis")
        == "full_lifecycle_including_model_load"
        and primary.get("server", {}).get("completion_canary_timeout_seconds") == 300
        and selection_sha256 == primary_evidence.get("selection_sha256")
        and resource_sha256 == primary_evidence.get("resource_profile_sha256")
        and experiments.get("treatments", {}).get("E1S-R", {}).get("status")
        == "operational_provisional_primary_confirmed_by_whole_run_tie"
        and experiments.get("current_phase")
        in {
            "phase_1_complete_provisional_primary",
            "phase_2_contract_frozen_no_treatment_admitted",
            "complete_no_justified_treatment_H1_not_applicable",
        }
        and success.get("phase_1", {}).get("status")
        == "passed_provisional_primary"
        and success.get("phase_1", {}).get("operational_primary") == "E1S-R"
        and success.get("phase_1", {}).get("acceptance_claim") is False
        and success.get("phase_1", {}).get("remaining_exit_gates") == []
        and offline.get("status")
        == "complete_for_public_Kaggle_runtime_use_not_approved_for_redistribution"
        and offline.get("wheelhouse", {}).get("sha256s_manifest_sha256")
        == models.get("engine", {}).get("wheelhouse_sha256s_manifest_sha256")
        and offline.get("model", {}).get("tree_sha256")
        == selected.get("artifact_sha256")
        and "agent/production_policy.py" in submission_sources
        and "config/operational_primary.yaml" in submission_sources
        and submission.get("metadata", {}).get("kaggle", {}).get("accelerator")
        == "nvidiaRtxPro6000"
        and "driessmit1/arc3-vllm-h100-wheelhouse-v3"
        in kaggle_metadata.get("dataset_sources", [])
        and "qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1"
        in kaggle_metadata.get("model_sources", [])
        and "Completed model/runtime table" in hierarchical_text
        and "Provisional primary" in hierarchical_text
        and "acceptance" in hierarchical_text
        and "def _completion_canary" in production_policy_text
        and "There are no remaining Phase 1 exit gates." in completion_audit_text,
        "hierarchical report, runtime table, offline bundle, and operational provisional primary are complete",
        failures,
    )

    comparison = execution.get("comparison_mode_audit", {})
    whole_path = ROOT / "config/e1_whole_run_protocol.yaml"
    try:
        whole = json.loads(whole_path.read_text())
    except (OSError, json.JSONDecodeError):
        whole = {}
    whole_execution = whole.get("execution", {})
    whole_analysis = whole.get("analysis", {})
    decision_comparison = decision.get("comparison", {})
    decision_result = decision.get("result", {})
    canonical_path = ROOT / decision_comparison.get("canonical_evidence", "missing")
    try:
        canonical_bytes = canonical_path.read_bytes()
        canonical_record = json.loads(canonical_bytes)
        validate_whole_run_record(canonical_record, whole)
        canonical_valid = True
    except (OSError, ValueError, json.JSONDecodeError):
        canonical_bytes = b""
        canonical_record = {}
        canonical_valid = False
    canonical_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
    canonical_analysis = canonical_record.get("analysis", {})
    canonical_contrasts = canonical_analysis.get("factorial_contrasts", {})
    recorded_log_hashes = {
        f"{block['block_id']}-{cell_id}": cell["fresh_runtime"]["server_log_sha256"]
        for block in canonical_record.get("blocks", [])
        for cell_id, cell in block.get("cells", {}).items()
    }
    observation_claim = execution.get("observation_bundle_claim", {})
    context_decision = execution.get("context_mode_decision", {})
    check(
        comparison.get("observed_mode") == "shared_resource_whole_run"
        and comparison.get("version_5_paired_run_blocks") == 1
        and comparison.get("version_5_order_counterbalanced") is False
        and comparison.get("causal_factorial_claim_from_version_5") is False
        and comparison.get("required_uncertainty_unit")
        == "paired_complete_workload_run_block"
        and whole.get("status") == "frozen_pending_execution"
        and whole_execution.get("paired_run_blocks") == 2
        and len(whole_execution.get("blocks", [])) == 2
        and whole_execution.get("randomization_unit")
        == "paired_complete_workload_run_block"
        and whole_execution.get("uncertainty_unit")
        == "paired_complete_workload_run_block"
        and whole_execution.get("blocks", [])[0].get("order")
        == list(reversed(whole_execution.get("blocks", [])[1].get("order", [])))
        and whole_analysis.get("per_game_results")
        == "diagnostic_only_never_resampled_as_independent_units"
        and observation_claim.get("R")
        == "latest_final_frame_only_no_raw_or_derived_intermediate_frame_evidence"
        and observation_claim.get("F")
        == "R_plus_registered_E0F_features_derived_from_bounded_intermediate_frame_sequences"
        and observation_claim.get("raw_intermediate_frames_model_visible") is False
        and context_decision.get("cached_mode") == "inactive"
        and context_decision.get("programmatic_mode") == "inactive"
        and decision.get("status") == "phase_1_complete_provisional_primary"
        and decision_comparison.get("mode") == "shared_resource_whole_run"
        and decision_comparison.get("randomization_unit")
        == "paired_complete_workload_run_block"
        and decision_comparison.get("uncertainty_unit")
        == "paired_complete_workload_run_block"
        and decision_comparison.get("paired_blocks") == 2
        and decision_comparison.get("evidence_sha256") == canonical_sha256
        and statistics.get("shared_resource_closure_sha256") == canonical_sha256
        and success.get("phase_1", {}).get("counterbalanced_whole_run_sha256")
        == canonical_sha256
        and canonical_sha256
        == primary.get("evidence", {}).get("whole_run_sha256")
        and canonical_valid
        and canonical_record.get("runtime", {}).get("elapsed_seconds", 1e99) < 27540
        and canonical_analysis.get("unit")
        == "paired_complete_workload_run_block"
        and canonical_analysis.get("fixed_candidate_by_frozen_tie_break") == "E1S-R"
        and canonical_analysis.get("fixed_candidate_status") == "Provisional primary"
        and set(canonical_contrasts) == {
            "representation_F_minus_R",
            "safe_operations_C_minus_S",
            "interaction_difference_in_differences",
        }
        and all(
            item.get("mean_effect") == 0.0
            and item.get("nonzero_blocks") == 0
            and item.get("two_sided_p_value") is None
            and item.get("status") == "Provisional"
            for item in canonical_contrasts.values()
        )
        and recorded_log_hashes == decision_comparison.get("server_log_sha256")
        and decision_result.get("fixed_candidate") == "E1S-R"
        and decision_result.get("fixed_candidate_acceptance_claim") is False
        and decision.get("operational", {}).get("remaining_phase_1_exit_gates") == [],
        "shared-resource whole-run evidence passes and preserves provisional inference",
        failures,
    )

    if failures:
        print(f"PHASE1_IMPLEMENTATION_FAILED count={len(failures)}")
        return 1
    print("PHASE1_IMPLEMENTATION_PASSED")
    print("PHASE1_EXIT_PASSED provisional_primary=E1S-R acceptance_claim=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
