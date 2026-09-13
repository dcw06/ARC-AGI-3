"""Fail-closed validation of the Phase 2 treatment-selection decision."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .phase2_contract import (
    REGISTERED_TREATMENTS,
    Phase2ContractError,
    file_sha256,
    validate_contract,
    validate_failure_record,
)


SELECTION_FIELDS = {
    "schema_version",
    "record_type",
    "selection_id",
    "status",
    "evaluated_at",
    "contract",
    "evidence_review",
    "frozen_parent",
    "prospective_plan",
    "candidates",
    "decision",
}


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise Phase2ContractError(f"invalid treatment-selection artifact: {path}") from exc
    if not isinstance(value, dict):
        raise Phase2ContractError(f"treatment-selection artifact is not an object: {path}")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Phase2ContractError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise Phase2ContractError(f"{label} fields drifted")


def validate_treatment_selection(
    root: str | Path,
    selection_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate either one evidence-backed choice or the explicit no-choice exit."""

    source_root = Path(root)
    contract = validate_contract(source_root)
    contract_path = source_root / "config/phase2_contract.yaml"
    contract_sha256 = file_sha256(contract_path)
    selection_path = source_root / "config/phase2_treatment_selection.yaml"
    selection = (
        _load(selection_path)
        if selection_record is None
        else dict(selection_record)
    )
    capture = _load(source_root / "config/phase2_diagnostic_capture.yaml")
    registry = _load(source_root / "config/experiment_registry.yaml")
    schema = _load(source_root / "config/phase2_treatment_selection_schema.json")

    _exact_keys(selection, SELECTION_FIELDS, "selection")
    if (
        selection.get("schema_version") != 1
        or selection.get("record_type") != "phase2_treatment_selection"
        or schema.get("$id") != "phase2_treatment_selection_v1"
        or schema.get("additionalProperties") is not False
    ):
        raise Phase2ContractError("selection identity or closed schema drifted")

    frozen_at = datetime.fromisoformat(str(contract["frozen_at"]))
    try:
        evaluated_at = datetime.fromisoformat(str(selection["evaluated_at"]))
    except ValueError as exc:
        raise Phase2ContractError("selection evaluation timestamp is invalid") from exc
    contract_ref = _mapping(selection.get("contract"), "selection contract")
    if (
        contract_ref.get("path") != "config/phase2_contract.yaml"
        or contract_ref.get("sha256") != contract_sha256
        or contract_ref.get("thresholds_frozen_before_diagnostic_review") is not True
        or evaluated_at < frozen_at
    ):
        raise Phase2ContractError("selection uses retrospective or drifted contract rules")

    evidence = _mapping(selection.get("evidence_review"), "evidence review")
    for path_key, hash_key in (
        ("phase1_factorial_result", "phase1_factorial_sha256"),
        ("phase1_whole_run_result", "phase1_whole_run_sha256"),
    ):
        evidence_path = source_root / str(evidence.get(path_key, ""))
        if not evidence_path.is_file() or file_sha256(evidence_path) != evidence.get(hash_key):
            raise Phase2ContractError(f"selection evidence drifted: {path_key}")
    if (
        evidence.get("diagnostic_capture_contract") != "config/phase2_diagnostic_capture.yaml"
        or evidence.get("historical_transition_replay_status")
        != "pending_no_historical_transition_bundle"
        or capture.get("exit_gate", {}).get("historical_phase1_transition_reproduced") is not False
    ):
        raise Phase2ContractError("historical diagnostic availability is overstated")

    parent = _mapping(selection.get("frozen_parent"), "frozen parent")
    contract_parent = contract["parent_policy"]
    expected_parent = {
        "applies_to_all_candidates": True,
        "policy_id": contract_parent["cell_id"],
        "frozen": True,
        "operational_config": contract_parent["operational_config"],
        "operational_config_sha256": contract_parent["operational_config_sha256"],
        "feature_manifest": contract_parent["feature_manifest"],
        "feature_manifest_sha256": contract_parent["feature_manifest_sha256"],
        "model_binding": contract_parent["model_binding"],
        "observation_bundle": contract_parent["observation_bundle"],
        "context_mode": contract_parent["context_mode"],
        "scheduler": contract_parent["scheduler"],
        "proposal_action_count": contract_parent["proposal_action_count"],
    }
    if dict(parent) != expected_parent:
        raise Phase2ContractError("selection does not use the exact frozen parent manifest")

    plan = _mapping(selection.get("prospective_plan"), "prospective plan")
    metric = _mapping(plan.get("success_metric"), "prospective success metric")
    compute = _mapping(plan.get("compute_allocation_if_admitted"), "conditional compute")
    stops = _mapping(plan.get("stop_rules"), "prospective stop rules")
    decision_rules = contract["decision_rules"]
    comparison = contract["comparison"]
    allowance = contract["compute_allowance"]
    if (
        plan.get("applies_conditionally_to_each_admitted_candidate") is not True
        or metric.get("primary_outcome") != comparison["primary_outcome"]
        or metric.get("minimum_delta_percent")
        != decision_rules["primary_delta_min_official_RHAE_percent"]
        or metric.get("overall_score_noninferiority_margin_percent")
        != decision_rules["reliability_noninferiority_margin_percent"]
        or metric.get("catastrophic_tail_floor_percent")
        != decision_rules["catastrophic_tail_regression_percent"]
        or metric.get("sample_rule") != contract["stop_rules"]["sample_rule"]
    ):
        raise Phase2ContractError("prospective success metric was changed retrospectively")
    if (
        compute.get("target_accelerator") != allowance["target_accelerator"]
        or compute.get("maximum_accelerator_hours")
        != allowance["maximum_accelerator_hours_per_treatment"]
        or compute.get("complete_workload_runs")
        != allowance["complete_workload_runs_per_treatment"]
        or compute.get("maximum_game_plays") != 60
        or compute.get("maximum_actions_per_game") != allowance["maximum_actions_per_game"]
        or compute.get("maximum_model_requests") != 4800
        or compute.get("scored_submissions") != 0
        or compute.get("current_allocation_hours") != 0.0
    ):
        raise Phase2ContractError("candidate compute allocation exceeds or changes the frozen allowance")
    if (
        stops.get("immediate") != contract["stop_rules"]["stop_immediately_on"]
        or stops.get("maximum_treatment_accelerator_hours")
        != allowance["maximum_accelerator_hours_per_treatment"]
        or stops.get("no_early_positive_stop") is not True
        or "futility" not in stops
        or "regression" not in stops
    ):
        raise Phase2ContractError("prospective futility or regression stops drifted")

    candidate_values = _mapping(selection.get("candidates"), "candidate reviews")
    if set(candidate_values) != set(REGISTERED_TREATMENTS):
        raise Phase2ContractError("candidate review does not cover every registered treatment")
    admitted_failures: dict[str, set[str]] = {}
    failure_paths = evidence.get("admissible_failure_records")
    if not isinstance(failure_paths, list):
        raise Phase2ContractError("admissible failure-record inventory must be a list")
    for relative in failure_paths:
        failure = _load(source_root / str(relative))
        validate_failure_record(
            failure,
            contract,
            contract_sha256=contract_sha256,
            require_admitted=True,
            evidence_root=source_root,
        )
        admitted_failures.setdefault(str(failure["candidate_treatment"]), set()).add(
            str(failure["failure_id"])
        )
    if evidence.get("reproduced_failure_count") != len(failure_paths):
        raise Phase2ContractError("reproduced failure count differs from admitted records")

    for treatment_id in REGISTERED_TREATMENTS:
        candidate = _mapping(candidate_values[treatment_id], f"candidate {treatment_id}")
        registered = contract["registered_treatments"][treatment_id]
        if (
            candidate.get("taxonomy_id") != registered["taxonomy_id"]
            or candidate.get("one_feature_delta") != registered["enabled_feature"]
            or candidate.get("parent_manifest_ref") != "frozen_parent"
            or candidate.get("prospective_success_metric_ref") != "prospective_plan.success_metric"
            or candidate.get("compute_allocation_ref")
            != "prospective_plan.compute_allocation_if_admitted"
            or candidate.get("stop_rules_ref") != "prospective_plan.stop_rules"
        ):
            raise Phase2ContractError(f"{treatment_id} changes more than its registered feature")
        is_admitted = treatment_id in admitted_failures
        if is_admitted != (candidate.get("reproduction_status") == "admitted"):
            raise Phase2ContractError(f"{treatment_id} reproduction status lacks a valid failure record")
        if not is_admitted and (
            candidate.get("concrete_reproduced_failure") is not None
            or candidate.get("disposition") != "not_admitted"
            or not candidate.get("evidence_gap")
        ):
            raise Phase2ContractError(f"{treatment_id} is claimed without reproduced evidence")
        if is_admitted and candidate.get("concrete_reproduced_failure") not in admitted_failures[
            treatment_id
        ]:
            raise Phase2ContractError(f"{treatment_id} does not name its admitted failure")

    decision = _mapping(selection.get("decision"), "selection decision")
    selected = decision.get("selected_treatment")
    if not admitted_failures:
        if (
            selection.get("status") != "complete_no_justified_treatment"
            or selected is not None
            or decision.get("conclusion") != "phase2_has_no_justified_treatment"
            or decision.get("activated_treatments") != []
            or decision.get("allocated_accelerator_hours") != 0.0
        ):
            raise Phase2ContractError("no-evidence exit must select and allocate no treatment")
    else:
        selected_candidates = {
            treatment_id
            for treatment_id, candidate in candidate_values.items()
            if candidate.get("disposition") == "selected"
        }
        if (
            selection.get("status") != "complete_one_treatment_selected"
            or selected not in admitted_failures
            or selected_candidates != {selected}
            or decision.get("conclusion") != "one_treatment_selected"
        ):
            raise Phase2ContractError("selected treatment has no unique admitted reproduced failure")

    activation = registry["phase_2_activation"]
    registry_selection = _mapping(registry.get("phase_2_selection"), "registry selection")
    if (
        decision.get("activated_treatments") != activation["activated_treatments"]
        or activation["currently_activated_treatments"] != len(activation["activated_treatments"])
    ):
        raise Phase2ContractError("selection and activation registry disagree")
    if (
        registry_selection.get("status") != selection.get("status")
        or registry_selection.get("record") != "config/phase2_treatment_selection.yaml"
        or registry_selection.get("record_sha256") != file_sha256(selection_path)
        or registry_selection.get("schema")
        != "config/phase2_treatment_selection_schema.json"
        or registry_selection.get("schema_sha256")
        != file_sha256(source_root / "config/phase2_treatment_selection_schema.json")
        or registry_selection.get("selected_treatment") != selected
        or registry_selection.get("activated_treatments")
        != decision.get("activated_treatments")
        or registry_selection.get("allocated_accelerator_hours")
        != decision.get("allocated_accelerator_hours")
    ):
        raise Phase2ContractError("selection registry record or hash drifted")
    return selection


def validate_conditional_implementation(
    root: str | Path,
    closure_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Prove conditional treatment code stayed absent after a no-choice exit."""

    source_root = Path(root)
    selection = validate_treatment_selection(source_root)
    closure_path = source_root / "config/phase2_conditional_implementation.yaml"
    closure = _load(closure_path) if closure_record is None else dict(closure_record)
    expected_top = {
        "schema_version",
        "record_type",
        "status",
        "selection_record",
        "selection_record_sha256",
        "selected_treatment",
        "chunk_2_3_evidence_treatment",
        "chunk_2_4_memory_retrieval",
        "protected_E1_parent",
        "activation_guard",
        "exit",
    }
    _exact_keys(closure, expected_top, "conditional implementation closure")
    if (
        closure.get("schema_version") != 1
        or closure.get("record_type") != "phase2_conditional_implementation"
        or closure.get("status") != "closed_not_applicable_no_selected_treatment"
        or closure.get("selection_record") != "config/phase2_treatment_selection.yaml"
        or closure.get("selection_record_sha256")
        != file_sha256(source_root / "config/phase2_treatment_selection.yaml")
        or closure.get("selected_treatment") is not None
        or selection["decision"]["selected_treatment"] is not None
    ):
        raise Phase2ContractError("conditional implementation contradicts treatment selection")

    e2 = _mapping(closure.get("chunk_2_3_evidence_treatment"), "Chunk 2.3 closure")
    empty_e2_fields = (
        "phase2_feature_manifests",
        "deterministic_enrichers",
        "rich_evidence_triggers",
        "new_resource_limits",
        "new_derived_features",
        "representation_fixtures",
    )
    if (
        e2.get("status") != "not_implemented_no_selected_E2_treatment"
        or e2.get("implemented_variant") is not None
        or any(e2.get(field) != [] for field in empty_e2_fields)
    ):
        raise Phase2ContractError("an unselected E2 evidence treatment was implemented")

    conditional = _mapping(closure.get("chunk_2_4_memory_retrieval"), "Chunk 2.4 closure")
    e3 = _mapping(conditional.get("E3"), "E3 closure")
    e4 = _mapping(conditional.get("E4"), "E4 closure")
    if (
        conditional.get("status") != "not_implemented_no_reproduced_E3_or_E4_failure"
        or e3.get("justified") is not False
        or e3.get("implemented") is not False
        or e3.get("stores") != []
        or e3.get("cross_game_mutable_memory") is not False
        or e4.get("justified") is not False
        or e4.get("implemented") is not False
        or e4.get("query_schemas") != []
        or e4.get("retrodiction_schemas") != []
        or e4.get("depends_on_E3") is not False
    ):
        raise Phase2ContractError("unjustified E3 memory or E4 retrieval was implemented")

    protected = _mapping(closure.get("protected_E1_parent"), "protected E1 parent")
    protected_paths = (
        ("feature_registry", "feature_registry_sha256"),
        ("feature_validator", "feature_validator_sha256"),
        ("representation", "representation_sha256"),
        ("policy", "policy_sha256"),
    )
    for path_key, hash_key in protected_paths:
        path = source_root / str(protected.get(path_key, ""))
        if not path.is_file() or file_sha256(path) != protected.get(hash_key):
            raise Phase2ContractError(f"protected E1 surface drifted: {path_key}")
    forbidden = protected.get("forbidden_treatment_features")
    contract = validate_contract(source_root)
    expected_forbidden = [
        contract["registered_treatments"][treatment_id]["enabled_feature"]
        for treatment_id in REGISTERED_TREATMENTS
    ]
    if forbidden != expected_forbidden:
        raise Phase2ContractError("forbidden treatment feature inventory drifted")
    agent_source = "\n".join(path.read_text() for path in sorted((source_root / "agent").glob("*.py")))
    leaked = [feature for feature in forbidden if feature in agent_source]
    if leaked:
        raise Phase2ContractError(f"unselected treatment code leaked into agent: {leaked}")
    if ".exact_sequence(" in (source_root / "agent/e1_policy.py").read_text():
        raise Phase2ContractError("E1 policy gained exact historical retrieval")
    prohibited_modules = (
        "agent/e2.py",
        "agent/e2_enrichers.py",
        "agent/phase2_features.py",
        "agent/memory.py",
        "agent/retrieval.py",
        "agent/retrodiction.py",
    )
    if any((source_root / relative).exists() for relative in prohibited_modules):
        raise Phase2ContractError("unselected treatment module exists")

    registry = _load(source_root / "config/experiment_registry.yaml")
    for treatment_id in REGISTERED_TREATMENTS:
        if registry["treatments"][treatment_id]["status"] != (
            "inactive_pending_reproduced_failure_admission"
        ):
            raise Phase2ContractError(f"{treatment_id} activated without selection")
    registry_closure = _mapping(
        registry.get("phase_2_conditional_implementation"),
        "conditional implementation registry",
    )
    if (
        registry_closure.get("status") != closure.get("status")
        or registry_closure.get("record")
        != "config/phase2_conditional_implementation.yaml"
        or registry_closure.get("record_sha256") != file_sha256(closure_path)
        or registry_closure.get("implemented_E2_variants") != []
        or registry_closure.get("implemented_memory_treatments") != []
        or registry_closure.get("implemented_retrieval_treatments") != []
    ):
        raise Phase2ContractError("conditional implementation registry drifted")
    exit_record = _mapping(closure.get("exit"), "conditional exit")
    if (
        exit_record.get("chunk_2_3") != "not_applicable"
        or exit_record.get("chunk_2_4") != "not_applicable"
        or exit_record.get("legal_play_preserved") is not True
        or exit_record.get("T0_preserved") is not True
        or exit_record.get("unsupported_memory_verified_items") != 0
    ):
        raise Phase2ContractError("conditional exit overstates implementation or safety")
    return closure
