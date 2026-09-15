"""Validate the supplied H1 draft's no-candidate disposition without H1 access.

This module does not execute or reserve a holdout. A future eligible candidate
requires a separate validated runner, complete bindings and a new decision.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


DRAFT_PATH = "config/h1_architecture_guardrail_protocol_v3.yaml"


def validate_inactive_guardrail(root: Path, decision: dict) -> dict:
    root = root.resolve()
    h1 = decision["H1"]
    path = root / DRAFT_PATH
    if (h1.get("protocol") != DRAFT_PATH
            or hashlib.sha256(path.read_bytes()).hexdigest() != h1.get("protocol_sha256")):
        raise ValueError("H1 supplied draft binding drift")
    draft = json.loads(path.read_text())
    eligibility = draft["architecture_eligibility"]
    candidate = draft["candidate_binding"]
    compute = draft["compute_contract"]
    if (draft["schema_version"] != 3
            or draft["status"] != "draft_inactive_no_eligible_candidate"
            or eligibility["current_state"] != "ineligible"
            or eligibility["no_candidate_rule"] != "do_not_freeze_do_not_run_and_do_not_reserve_or_consume_H1"
            or decision["admitted_treatments"] != []
            or decision["selected_policy"] != decision["parent_policy"]
            or decision["selected_policy"] != "E1S-R"):
        raise ValueError("H1 no-candidate closure is not applicable")
    null_fields = ("architecture_id", "manifest_sha256", "source_tree_sha256",
                   "configuration_sha256", "model_artifact_sha256", "prompt_sha256",
                   "scheduler_sha256", "development_protocol_sha256",
                   "development_decision_sha256", "maximum_model_requests_per_game",
                   "distinct_from_parent")
    if any(candidate[key] is not None for key in null_fields):
        raise ValueError("candidate bindings require a new eligibility decision")
    if (compute["authorized_accelerator_hours"] != 0
            or compute["authorization_status"] != "not_reserved"
            or compute["compute_ledger_reservation_id"] is not None
            or draft["runner_boundary"]["runner_sha256"] is not None):
        raise ValueError("inactive H1 cannot authorize compute or a runner")
    freeze = draft["immutable_freeze_and_reservation"]
    if any(freeze[key] is not None for key in (
            "pre_reservation_ledger_snapshot_sha256", "reservation_event_id", "run_id")):
        raise ValueError("inactive H1 cannot have a reservation")
    frozen_path = (root / freeze["frozen_artifact_path"]).resolve()
    if not frozen_path.is_relative_to(root) or frozen_path.exists():
        raise ValueError("no-candidate H1 must not be frozen")
    ledger_path = root / "config/holdout_ledger.yaml"
    if hashlib.sha256(ledger_path.read_bytes()).hexdigest() != h1["ledger_sha256_at_closure"]:
        raise ValueError("holdout ledger changed since no-candidate closure")
    ledger = json.loads(ledger_path.read_text())
    if (ledger["consumption_events"] or h1["consumed"] is not False
            or h1["reserved"] is not False or h1["executed"] is not False
            or h1["result"] is not None
            or h1["status"] != "not_applicable_no_distinct_development_qualified_candidate"
            or h1["exposure_classification"] != ledger["h1_classification"]
            or h1["privacy_claim"] != "process_redacted_not_independently_blinded"
            or h1["positive_performance_claim"] is not False):
        raise ValueError("unsupported H1 execution, exposure or result claim")
    parent = json.loads((root / "config/operational_primary.yaml").read_text())["primary"]
    binding = draft["parent_binding"]
    if (binding["cell_id"] != parent["cell_id"]
            or binding["operational_config_sha256"] != hashlib.sha256(
                (root / binding["operational_config"]).read_bytes()).hexdigest()
            or any(binding[key] != parent["model_binding"][key]
                   for key in ("model_id", "engine", "reasoning_setting"))
            or binding["model_revision"] != parent["model_binding"]["revision"]
            or binding["model_artifact_tree_sha256"] != parent["model_artifact"]["tree_sha256"]):
        raise ValueError("H1 rollback parent drift")
    return draft
