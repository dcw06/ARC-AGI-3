"""Fail-closed validation for the frozen Phase 2 treatment contract."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REGISTERED_TREATMENTS = ("E2a", "E2b", "E2c", "E2d", "E3", "E4")
INACTIVE_STATUS = "inactive_pending_reproduced_failure_admission"
DISALLOWED_ALTERNATIVE_CAUSES = {
    "model_protocol_invalidity",
    "resource_or_queue_failure",
    "environment_or_transport_failure",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class Phase2ContractError(ValueError):
    """Raised before treatment implementation or execution when closure fails."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise Phase2ContractError(f"invalid Phase 2 artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise Phase2ContractError(f"Phase 2 artifact is not an object: {path.name}")
    return value


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Phase2ContractError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise Phase2ContractError(
            f"{label} fields drifted: missing={sorted(expected - observed)} "
            f"extra={sorted(observed - expected)}"
        )


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise Phase2ContractError(f"{label} timestamp is missing")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Phase2ContractError(f"{label} timestamp is invalid") from exc


def validate_contract(root: str | Path) -> dict[str, Any]:
    """Validate Phase 2 parameter closure without activating a treatment."""

    source_root = Path(root)
    contract_path = source_root / "config/phase2_contract.yaml"
    contract = _load(contract_path)
    registry = _load(source_root / "config/experiment_registry.yaml")
    holdout = _load(source_root / "config/holdout_ledger.yaml")
    operational = _load(source_root / "config/operational_primary.yaml")
    phase1 = _load(source_root / "config/phase1_decision.yaml")
    feature_registry = _load(source_root / "config/e1_feature_manifests.yaml")
    success = _load(source_root / "config/success_criteria.yaml")
    failure_schema_path = source_root / "config/phase2_failure_record_schema.json"
    treatment_schema_path = source_root / "config/phase2_treatment_manifest_schema.json"
    failure_schema = _load(failure_schema_path)
    treatment_schema = _load(treatment_schema_path)

    if (
        contract.get("schema_version") != 1
        or contract.get("contract_id") != "phase2.failure-driven.v1"
        or contract.get("status") != "frozen_no_treatment_admitted"
    ):
        raise Phase2ContractError("Phase 2 contract identity or freeze status drifted")

    activation = _mapping(registry.get("phase_2_activation"), "registry activation")
    cap = _mapping(contract.get("treatment_cap"), "treatment cap")
    registered = _mapping(contract.get("registered_treatments"), "registered treatments")
    registered_ids = set(REGISTERED_TREATMENTS)
    if (
        set(registered) != registered_ids
        or set(activation.get("registered_treatments", [])) != registered_ids
        or activation.get("contract") != "config/phase2_contract.yaml"
        or activation.get("contract_sha256") != file_sha256(contract_path)
        or registry.get("current_phase") not in {
            "phase_2_contract_frozen_no_treatment_admitted",
            "complete_no_justified_treatment_H1_not_applicable",
        }
        or activation.get("status") != "contract_frozen_no_treatment_admitted"
        or activation.get("maximum_activated_treatments") != 2
        or cap.get("maximum_activated_treatments") != 2
        or activation.get("evaluation_order") != "strictly_sequential"
        or cap.get("evaluation_order") != "strictly_sequential"
        or activation.get("currently_activated_treatments") != 0
        or activation.get("concurrent_treatment_evaluations") != 0
        or activation.get("activated_treatments") != []
        or cap.get("simultaneous_activated_treatments") != 0
        or cap.get("activated_treatments") != []
        or cap.get("activation_order") != []
        or cap.get("selection_rule")
        != "first_admitted_by_frozen_taxonomy_priority_then_failure_id_lexicographic"
        or registry.get("budgets", {}).get("phase_2_target_accelerator_hours") != 8.0
        or registry.get("budgets", {}).get("phase_2_scored_submissions") != 0
        or success.get("phase_2_contract", {}).get("maximum_activated_treatments") != 2
        or success.get("phase_2_contract", {}).get("activated_treatments") != []
    ):
        raise Phase2ContractError("numerical treatment cap or sequential activation drifted")
    for treatment_id in REGISTERED_TREATMENTS:
        registry_entry = _mapping(
            registry.get("treatments", {}).get(treatment_id),
            f"registry treatment {treatment_id}",
        )
        contract_entry = _mapping(registered[treatment_id], f"contract treatment {treatment_id}")
        if (
            registry_entry.get("status") != INACTIVE_STATUS
            or registry_entry.get("parent") != "E1S-R"
            or contract_entry.get("status") != INACTIVE_STATUS
        ):
            raise Phase2ContractError(f"{treatment_id} activated before admission")

    pairs = contract.get("development_game_seed_pairs")
    if not isinstance(pairs, list) or len(pairs) != 15:
        raise Phase2ContractError("development game/seed manifest is not frozen")
    if canonical_sha256(pairs) != contract.get("development_game_seed_pairs_sha256"):
        raise Phase2ContractError("development game/seed manifest digest drifted")
    if [item.get("game_id") for item in pairs] != holdout.get("development"):
        raise Phase2ContractError("Phase 2 development games differ from the frozen ledger")
    if len({item.get("seed") for item in pairs}) != 15:
        raise Phase2ContractError("Phase 2 seeds are not unique and frozen")

    parent = _mapping(contract.get("parent_policy"), "parent policy")
    primary = _mapping(operational.get("primary"), "operational primary")
    if (
        parent.get("status") != "frozen"
        or parent.get("cell_id") != "E1S-R"
        or parent.get("cell_id") != primary.get("cell_id")
        or parent.get("cell_id") != phase1.get("operational", {}).get("primary")
        or parent.get("model_binding") != primary.get("model_binding")
        or parent.get("operational_config_sha256")
        != file_sha256(source_root / str(parent.get("operational_config")))
        or parent.get("feature_manifest_sha256")
        != file_sha256(source_root / str(parent.get("feature_manifest")))
        or parent.get("phase1_decision_sha256")
        != file_sha256(source_root / str(parent.get("phase1_decision")))
        or feature_registry.get("cells", {}).get("E1S-R", {}).get("observation_bundle") != "R"
        or feature_registry.get("cells", {}).get("E1S-R", {}).get("workspace") != "none"
    ):
        raise Phase2ContractError("Phase 2 parent is absent, mutable, or hash-drifted")

    comparison = _mapping(contract.get("comparison"), "comparison")
    if (
        comparison.get("execution_mode") != "shared_resource_whole_run"
        or comparison.get("randomization_unit") != "paired_complete_workload_run_block"
        or comparison.get("uncertainty_unit") != "paired_complete_workload_run_block"
        or comparison.get("paired_run_blocks") != 2
        or comparison.get("block_orders")
        != ["parent_then_treatment", "treatment_then_parent"]
        or comparison.get("per_game_results")
        != "diagnostic_only_never_independent_resamples"
    ):
        raise Phase2ContractError("Phase 2 comparison mode or unit drifted")

    allowance = _mapping(contract.get("compute_allowance"), "compute allowance")
    stop = _mapping(contract.get("stop_rules"), "stop rules")
    rules = _mapping(contract.get("decision_rules"), "decision rules")
    if (
        allowance.get("maximum_activated_treatments") != 2
        or allowance.get("maximum_family_accelerator_hours") != 8.0
        or allowance.get("maximum_accelerator_hours_per_treatment") != 4.0
        or allowance.get("maximum_complete_workload_runs") != 8
        or allowance.get("complete_workload_runs_per_treatment") != 4
        or allowance.get("maximum_game_plays") != 120
        or allowance.get("maximum_model_requests_per_complete_workload")
        != len(pairs) * allowance.get("maximum_actions_per_game", 0)
        or allowance.get("maximum_family_model_requests")
        != allowance.get("maximum_model_requests_per_complete_workload", 0)
        * allowance.get("maximum_complete_workload_runs", 0)
        or allowance.get("maximum_valid_target_notebook_runs") != 2
        or allowance.get("failed_infrastructure_run_allowance") != 1
        or allowance.get("accelerator_hour_accounting")
        != "all_valid_and_failed_runs_from_kernel_start_to_exit"
        or allowance.get("family_deadline") != "2026-09-20T23:59:59+08:00"
        or allowance.get("maximum_scored_submissions") != 0
        or stop.get("sample_rule")
        != "fixed_two_paired_complete_workload_blocks_no_early_positive_stop"
        or stop.get("stop_family_after_activated_treatments") != 2
        or stop.get("stop_family_at_accelerator_hours") != 8.0
        or stop.get("stop_treatment_at_accelerator_hours") != 4.0
        or rules.get("status") != "prospectively_frozen"
        or rules.get("primary_delta_min_official_RHAE_percent") != 0.10
        or rules.get("catastrophic_tail_regression_percent") != -0.10
        or rules.get("reliability_noninferiority_margin_percent") != -0.02
        or rules.get("familywise_alpha") != 0.10
        or rules.get("multiplicity") != "sequential_gatekeeping_in_activation_order"
        or rules.get("retrospective_threshold_changes")
        != "forbidden_new_contract_revision_and_fresh_experiment_required"
    ):
        raise Phase2ContractError("Phase 2 compute allowance, thresholds, or stop rules drifted")

    taxonomy = _mapping(contract.get("diagnostic_taxonomy"), "diagnostic taxonomy")
    if set(taxonomy) != {
        "inter_action_event_loss",
        "animation_summary_aliasing",
        "selective_rich_animation_need",
        "correspondence_identity_failure",
        "cross_level_memory_recurrence",
        "out_of_window_exact_evidence_need",
        *DISALLOWED_ALTERNATIVE_CAUSES,
        "unsupported_other",
    }:
        raise Phase2ContractError("diagnostic taxonomy drifted")
    for treatment_id, treatment in registered.items():
        taxonomy_entry = _mapping(
            taxonomy.get(treatment.get("taxonomy_id")),
            f"taxonomy for {treatment_id}",
        )
        if taxonomy_entry.get("admissible_treatments") != [treatment_id]:
            raise Phase2ContractError(f"taxonomy mapping drifted for {treatment_id}")

    expected_taxonomy_priority = [
        registered[treatment_id]["taxonomy_id"] for treatment_id in REGISTERED_TREATMENTS
    ]
    if cap.get("taxonomy_priority") != expected_taxonomy_priority:
        raise Phase2ContractError("diagnostic taxonomy priority drifted")

    gate = _mapping(contract.get("admission_gate"), "admission gate")
    if (
        gate.get("status") != "frozen_before_failure_review"
        or gate.get("minimum_reproductions") != 2
        or gate.get("minimum_distinct_parent_run_ids") != 2
        or gate.get("same_game_and_seed_required") is not True
        or gate.get("same_failure_signature_required") is not True
        or gate.get("parent_only_reproduction_required") is not True
        or gate.get("policy_visible_evidence_only") is not True
        or gate.get("evaluator_or_holdout_evidence_allowed") is not False
        or gate.get("causal_attribution_to_exactly_one_registered_missing_capability")
        is not True
        or set(gate.get("alternative_causes_that_must_be_excluded", []))
        != DISALLOWED_ALTERNATIVE_CAUSES
        or gate.get("admission_decision") != "all_rules_conjunctive"
        or gate.get("no_matching_failure_behavior") != "remain_inactive"
    ):
        raise Phase2ContractError("failure admission gate drifted")

    boundary = _mapping(contract.get("feature_boundary"), "feature boundary")
    if (
        boundary.get("exactly_one_registered_feature_delta") is not True
        or boundary.get("unregistered_fields") != "reject_not_ignore"
        or set(boundary.get("features_that_must_remain_disabled", []))
        != {
            "typed_competing_hypotheses",
            "prediction_checked_action_queue",
            "multi_action_execution",
            "executable_python",
            "executable_transition_model",
            "search",
            "specialist",
            "advanced_scheduler",
            "cross_game_mutable_memory",
        }
    ):
        raise Phase2ContractError("Phase 2 feature boundary drifted")

    schemas = _mapping(contract.get("schemas"), "schema bindings")
    if (
        schemas.get("failure_record") != "config/phase2_failure_record_schema.json"
        or schemas.get("failure_record_sha256") != file_sha256(failure_schema_path)
        or schemas.get("treatment_manifest")
        != "config/phase2_treatment_manifest_schema.json"
        or schemas.get("treatment_manifest_sha256") != file_sha256(treatment_schema_path)
        or failure_schema.get("$id") != "phase2_failure_record_v1"
        or failure_schema.get("additionalProperties") is not False
        or set(failure_schema.get("properties", {}).get("candidate_treatment", {}).get("enum", []))
        != registered_ids
        or treatment_schema.get("$id") != "phase2_treatment_manifest_v1"
        or treatment_schema.get("additionalProperties") is not False
        or set(treatment_schema.get("properties", {}).get("treatment_id", {}).get("enum", []))
        != registered_ids
    ):
        raise Phase2ContractError("Phase 2 schemas are missing, open, or unregistered")
    return contract


def validate_failure_structure(
    record: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    contract_sha256: str,
    require_admitted: bool = False,
) -> None:
    """Validate a candidate diagnosis and its reproduced-parent admission proof."""

    _exact_keys(
        record,
        {
            "schema_version",
            "record_type",
            "failure_id",
            "status",
            "created_at",
            "taxonomy_id",
            "candidate_treatment",
            "parent",
            "development_case",
            "failure_signature_sha256",
            "diagnosis",
            "consequence",
            "reproductions",
            "admission",
        },
        "failure record",
    )
    if record.get("schema_version") != 1 or record.get("record_type") != "phase2_failure":
        raise Phase2ContractError("failure record identity drifted")
    if (
        not re.fullmatch(r"P2F-[0-9]{4}-[a-z0-9-]+", str(record.get("failure_id", "")))
        or record.get("status") not in {"candidate", "admitted", "rejected"}
        or not SHA256_PATTERN.fullmatch(str(record.get("failure_signature_sha256", "")))
    ):
        raise Phase2ContractError("failure record identifier, status, or signature is invalid")
    _timestamp(record.get("created_at"), "failure creation")
    taxonomy_id = record.get("taxonomy_id")
    treatment_id = record.get("candidate_treatment")
    registered = _mapping(contract.get("registered_treatments"), "registered treatments")
    taxonomy = _mapping(contract.get("diagnostic_taxonomy"), "diagnostic taxonomy")
    if treatment_id not in registered or taxonomy_id not in taxonomy:
        raise Phase2ContractError("unregistered Phase 2 treatment or taxonomy")
    expected = _mapping(registered[treatment_id], f"registered treatment {treatment_id}")
    if (
        expected.get("taxonomy_id") != taxonomy_id
        or taxonomy[taxonomy_id].get("admissible_treatments") != [treatment_id]
    ):
        raise Phase2ContractError("failure taxonomy does not admit this treatment")

    parent = _mapping(record.get("parent"), "failure parent")
    _exact_keys(
        parent,
        {"policy_id", "frozen", "operational_config_sha256", "feature_manifest_sha256"},
        "failure parent",
    )
    frozen_parent = _mapping(contract.get("parent_policy"), "contract parent")
    if (
        parent.get("policy_id") != frozen_parent.get("cell_id")
        or parent.get("frozen") is not True
        or parent.get("operational_config_sha256")
        != frozen_parent.get("operational_config_sha256")
        or parent.get("feature_manifest_sha256")
        != frozen_parent.get("feature_manifest_sha256")
    ):
        raise Phase2ContractError("failure was not reproduced under the frozen parent")

    case = _mapping(record.get("development_case"), "development case")
    _exact_keys(case, {"game_id", "seed"}, "development case")
    pairs = {
        (item["game_id"], item["seed"])
        for item in contract.get("development_game_seed_pairs", [])
    }
    case_pair = (case.get("game_id"), case.get("seed"))
    if case_pair not in pairs:
        raise Phase2ContractError("failure uses an unfrozen game or seed")

    diagnosis = _mapping(record.get("diagnosis"), "diagnosis")
    _exact_keys(
        diagnosis,
        {
            "missing_capability",
            "action_relevance",
            "excluded_alternative_causes",
            "evidence_availability",
            "evidence_refs",
        },
        "diagnosis",
    )
    if (
        diagnosis.get("missing_capability") != expected.get("enabled_feature")
        or set(diagnosis.get("excluded_alternative_causes", []))
        != DISALLOWED_ALTERNATIVE_CAUSES
        or not diagnosis.get("action_relevance")
        or not diagnosis.get("evidence_refs")
        or diagnosis.get("evidence_availability") not in {"exact", "summarized"}
    ):
        raise Phase2ContractError("failure attribution or evidence is insufficient")
    if treatment_id == "E4" and diagnosis.get("evidence_availability") != "exact":
        raise Phase2ContractError("E4 admission requires available exact historical evidence")

    gate = _mapping(contract.get("admission_gate"), "admission gate")
    signature = record.get("failure_signature_sha256")
    reproductions = record.get("reproductions")
    if not isinstance(reproductions, Sequence) or isinstance(reproductions, (str, bytes)):
        raise Phase2ContractError("failure reproductions are missing")
    if len(reproductions) < gate.get("minimum_reproductions", 0):
        raise Phase2ContractError("failure was not reproduced enough times")
    if len(reproductions) > 4:
        raise Phase2ContractError("failure reproduction count exceeds the schema")
    run_ids: set[str] = set()
    for index, value in enumerate(reproductions):
        reproduction = _mapping(value, f"reproduction {index}")
        _exact_keys(
            reproduction,
            {
                "run_id",
                "game_id",
                "seed",
                "failure_signature_sha256",
                "parent_only",
                "policy_visible_evidence_only",
                "evaluator_or_holdout_access",
                "transition_ids",
                "evidence_sha256",
            },
            f"reproduction {index}",
        )
        run_ids.add(str(reproduction.get("run_id")))
        if (
            (reproduction.get("game_id"), reproduction.get("seed")) != case_pair
            or reproduction.get("failure_signature_sha256") != signature
            or reproduction.get("parent_only") is not True
            or reproduction.get("policy_visible_evidence_only") is not True
            or reproduction.get("evaluator_or_holdout_access") is not False
            or not reproduction.get("transition_ids")
            or not SHA256_PATTERN.fullmatch(str(reproduction.get("evidence_sha256", "")))
        ):
            raise Phase2ContractError("failure reproduction violates the admission gate")
    if len(run_ids) < gate.get("minimum_distinct_parent_run_ids", 0):
        raise Phase2ContractError("failure reproductions do not use distinct parent runs")
    if record.get("consequence") not in gate.get("required_consequence", []):
        raise Phase2ContractError("failure consequence is not admission-eligible")

    admission = _mapping(record.get("admission"), "admission decision")
    _exact_keys(
        admission,
        {"decision", "evaluated_at", "contract_sha256", "thresholds_frozen_before_review", "reasons"},
        "admission decision",
    )
    if (
        admission.get("contract_sha256") != contract_sha256
        or admission.get("thresholds_frozen_before_review") is not True
        or _timestamp(admission.get("evaluated_at"), "admission")
        < _timestamp(contract.get("frozen_at"), "contract freeze")
    ):
        raise Phase2ContractError("admission used retrospective or unknown thresholds")
    if require_admitted and (
        record.get("status") != "admitted" or admission.get("decision") != "passed"
    ):
        raise Phase2ContractError("treatment requires an admitted reproduced failure")


def validate_failure_record(record, contract, *, contract_sha256, require_admitted=True, evidence_root=None):
    """Admission requires actual artifacts; structural checks alone never suffice."""
    validate_failure_structure(record, contract, contract_sha256=contract_sha256,
                               require_admitted=require_admitted)
    if require_admitted:
        from .phase2_evidence_gate import resolve_admission
        try:
            resolve_admission(record, evidence_root or Path(__file__).resolve().parents[1])
        except (ValueError, KeyError, OSError, TypeError) as exc:
            raise Phase2ContractError(f"unverified admission evidence: {exc}") from exc


def validate_treatment_manifest(
    manifest: Mapping[str, Any],
    failure_record: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    contract_sha256: str,
    evidence_root: str | Path | None = None,
) -> None:
    """Reject unregistered, leaking, retrospective, or parentless experiments."""

    _exact_keys(
        manifest,
        {
            "schema_version",
            "record_type",
            "manifest_id",
            "treatment_id",
            "status",
            "contract_sha256",
            "failure_record",
            "parent",
            "feature_delta",
            "comparison",
            "compute_allocation",
            "decision_rules",
            "activation",
        },
        "treatment manifest",
    )
    if (
        manifest.get("schema_version") != 1
        or manifest.get("record_type") != "phase2_treatment_manifest"
        or manifest.get("status") != "admitted_frozen"
        or manifest.get("contract_sha256") != contract_sha256
    ):
        raise Phase2ContractError("treatment manifest is not prospectively frozen")
    if not re.fullmatch(
        r"P2T-(E2a|E2b|E2c|E2d|E3|E4)-v[0-9]+",
        str(manifest.get("manifest_id", "")),
    ):
        raise Phase2ContractError("treatment manifest identifier is invalid")
    treatment_id = manifest.get("treatment_id")
    registered = _mapping(contract.get("registered_treatments"), "registered treatments")
    if treatment_id not in registered:
        raise Phase2ContractError("unregistered Phase 2 treatment")
    expected = _mapping(registered[treatment_id], f"registered treatment {treatment_id}")

    validate_failure_structure(
        failure_record,
        contract,
        contract_sha256=contract_sha256,
        require_admitted=True,
    )
    failure_ref = _mapping(manifest.get("failure_record"), "failure reference")
    _exact_keys(
        failure_ref,
        {"failure_id", "record_sha256", "admission_decision"},
        "failure reference",
    )
    if (
        failure_record.get("candidate_treatment") != treatment_id
        or failure_ref.get("failure_id") != failure_record.get("failure_id")
        or failure_ref.get("record_sha256") != canonical_sha256(failure_record)
        or failure_ref.get("admission_decision") != "passed"
    ):
        raise Phase2ContractError("treatment is not bound to its admitted failure")

    parent = _mapping(manifest.get("parent"), "manifest parent")
    _exact_keys(
        parent,
        {"policy_id", "frozen", "operational_config_sha256", "feature_manifest_sha256"},
        "manifest parent",
    )
    frozen_parent = _mapping(contract.get("parent_policy"), "contract parent")
    if (
        parent.get("policy_id") != frozen_parent.get("cell_id")
        or parent.get("frozen") is not True
        or parent.get("operational_config_sha256")
        != frozen_parent.get("operational_config_sha256")
        or parent.get("feature_manifest_sha256")
        != frozen_parent.get("feature_manifest_sha256")
    ):
        raise Phase2ContractError("experiment has no exact frozen parent")

    boundary = _mapping(contract.get("feature_boundary"), "feature boundary")
    delta = _mapping(manifest.get("feature_delta"), "feature delta")
    _exact_keys(
        delta,
        {"enabled_feature", "enabled", "changed_parent_fields", "disabled_features"},
        "feature delta",
    )
    expected_feature = expected.get("enabled_feature")
    if (
        delta.get("enabled_feature") != expected_feature
        or delta.get("enabled") is not True
        or delta.get("changed_parent_fields") != [expected_feature]
        or set(delta.get("disabled_features", []))
        != set(boundary.get("features_that_must_remain_disabled", []))
    ):
        raise Phase2ContractError("feature leakage or non-registered parent delta")

    comparison = _mapping(manifest.get("comparison"), "manifest comparison")
    _exact_keys(
        comparison,
        {
            "execution_mode",
            "game_seed_pairs_sha256",
            "parent_arm",
            "treatment_arm",
            "paired_run_blocks",
            "block_orders",
            "randomization_unit",
            "uncertainty_unit",
            "per_game_results",
        },
        "manifest comparison",
    )
    frozen_comparison = _mapping(contract.get("comparison"), "contract comparison")
    if (
        comparison.get("execution_mode") != frozen_comparison.get("execution_mode")
        or comparison.get("game_seed_pairs_sha256")
        != contract.get("development_game_seed_pairs_sha256")
        or comparison.get("parent_arm") != frozen_parent.get("cell_id")
        or comparison.get("treatment_arm") != treatment_id
        or comparison.get("paired_run_blocks") != frozen_comparison.get("paired_run_blocks")
        or comparison.get("block_orders") != frozen_comparison.get("block_orders")
        or comparison.get("randomization_unit") != frozen_comparison.get("randomization_unit")
        or comparison.get("uncertainty_unit") != frozen_comparison.get("uncertainty_unit")
        or comparison.get("per_game_results") != frozen_comparison.get("per_game_results")
    ):
        raise Phase2ContractError("treatment comparison differs from the frozen design")

    allocation = _mapping(manifest.get("compute_allocation"), "compute allocation")
    _exact_keys(
        allocation,
        {
            "target_accelerator",
            "maximum_accelerator_hours",
            "complete_workload_runs",
            "maximum_game_plays",
            "maximum_actions_per_game",
            "maximum_model_requests",
            "scored_submissions",
        },
        "compute allocation",
    )
    family = _mapping(contract.get("compute_allowance"), "family compute allowance")
    if (
        allocation.get("target_accelerator") != family.get("target_accelerator")
        or allocation.get("maximum_accelerator_hours", 1e99)
        > family.get("maximum_accelerator_hours_per_treatment", 0)
        or allocation.get("complete_workload_runs") != 4
        or allocation.get("maximum_game_plays") != 60
        or allocation.get("maximum_actions_per_game") != 80
        or allocation.get("maximum_model_requests") != 4800
        or allocation.get("scored_submissions") != 0
    ):
        raise Phase2ContractError("treatment compute allocation exceeds the frozen allowance")

    manifest_rules = _mapping(manifest.get("decision_rules"), "manifest decision rules")
    frozen_rules = _mapping(contract.get("decision_rules"), "contract decision rules")
    expected_rules = {
        "frozen_before_implementation": True,
        "contract_sha256": contract_sha256,
        "primary_delta_min_official_RHAE_percent": frozen_rules.get(
            "primary_delta_min_official_RHAE_percent"
        ),
        "catastrophic_tail_regression_percent": frozen_rules.get(
            "catastrophic_tail_regression_percent"
        ),
        "reliability_noninferiority_margin_percent": frozen_rules.get(
            "reliability_noninferiority_margin_percent"
        ),
        "familywise_alpha": frozen_rules.get("familywise_alpha"),
        "sample_rule": contract.get("stop_rules", {}).get("sample_rule"),
    }
    if dict(manifest_rules) != expected_rules:
        raise Phase2ContractError("retrospective treatment threshold or sample rule")

    activation = _mapping(manifest.get("activation"), "manifest activation")
    _exact_keys(
        activation,
        {"sequence_position", "sequential_predecessor_finalized", "activated_at"},
        "manifest activation",
    )
    position = activation.get("sequence_position")
    if (
        not isinstance(position, int)
        or position < 1
        or position > contract.get("treatment_cap", {}).get("maximum_activated_treatments", 0)
        or activation.get("sequential_predecessor_finalized") is not True
        or _timestamp(activation.get("activated_at"), "activation")
        < _timestamp(contract.get("frozen_at"), "contract freeze")
    ):
        raise Phase2ContractError("treatment violates sequential activation or the numerical cap")
    validate_failure_record(failure_record, contract, contract_sha256=contract_sha256,
                            require_admitted=True, evidence_root=evidence_root)
    from .phase2_budget import read_ledger
    ledger = read_ledger(Path(evidence_root or Path(__file__).resolve().parents[1]) / "config/phase2_compute_ledger.json")
    if (not ledger["new_execution_allowed"]
            or allocation["maximum_accelerator_hours"] * 3600 > ledger["remaining_seconds"]):
        raise Phase2ContractError("unreconciled or insufficient Phase 2 family compute")
