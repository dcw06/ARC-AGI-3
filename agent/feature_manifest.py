"""Fail-closed Phase 1 feature manifests and baseline proposal validation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from arcengine import GameAction

from .action import ActionDecision, DisplayPoint, normalize_legal_actions
from .config import load_registry


EXPECTED_E1_CELLS = frozenset({"E1S-R", "E1S-F", "E1C-R", "E1C-F"})
DISABLED_E1_CAPABILITIES = (
    "durable_memory",
    "historical_retrieval",
    "typed_hypotheses",
    "prediction_checked_queue",
    "executable_python",
    "executable_transition_model",
    "search",
    "specialist",
)
PROPOSAL_FIELDS = frozenset({"intent", "rationale", "action"})


class FeatureManifestError(ValueError):
    """An E1 manifest or proposal violates the frozen treatment surface."""


@dataclass(frozen=True, slots=True)
class E1FeatureManifest:
    treatment_id: str
    observation_bundle: str
    harness: str
    workspace: str
    proposal_action_count: int
    context_mode: str
    recent_transition_limit: int
    intent_max_bytes: int
    rationale_max_bytes: int
    scheduler: str
    prompt_revision: str
    workspace_invocation_limit: int
    history_loss_reporting: str


def load_e1_feature_manifests(path: str | Path) -> Mapping[str, E1FeatureManifest]:
    registry = load_registry(path)
    if registry.get("manifest_revision") != "E1.v3":
        raise FeatureManifestError("unsupported E1 manifest revision")
    model_binding = registry.get("model_binding")
    if model_binding is not None and (
        not isinstance(model_binding, dict)
        or set(model_binding) != {"candidate_id", "model_id", "revision", "engine", "reasoning_setting"}
    ):
        raise FeatureManifestError("invalid E1 model binding")

    shared = registry.get("shared")
    cells = registry.get("cells")
    if not isinstance(shared, dict) or not isinstance(cells, dict):
        raise FeatureManifestError("E1 registry must contain shared and cells objects")
    if set(cells) != EXPECTED_E1_CELLS:
        raise FeatureManifestError("E1 registry must contain exactly the four factorial cells")
    if shared.get("proposal_action_count") != 1:
        raise FeatureManifestError("baseline E1 requires exactly one action per proposal")
    if shared.get("prompt_revision") != "E1.prompt.v4_lifetime_visible_compaction":
        raise FeatureManifestError("unknown or unfrozen E1 prompt revision")
    if shared.get("context_mode") != "stateless_reconstruction_visible_compaction_v1":
        raise FeatureManifestError("unknown or unfrozen E1 context mode")
    if shared.get("recent_transition_limit") != 1:
        raise FeatureManifestError("visible compaction must retain exactly one transition")
    if shared.get("history_loss_reporting") != "lifetime_count_and_rolling_sha256_v1":
        raise FeatureManifestError("visible compaction loss reporting is not frozen")
    if shared.get("workspace_invocation_limit") != 7:
        raise FeatureManifestError("E1 workspace invocation limit must be seven")
    for capability in DISABLED_E1_CAPABILITIES:
        if shared.get(capability) is not False:
            raise FeatureManifestError(f"baseline E1 capability must be disabled: {capability}")

    manifests: dict[str, E1FeatureManifest] = {}
    for treatment_id, cell in cells.items():
        if not isinstance(cell, dict):
            raise FeatureManifestError(f"invalid E1 cell: {treatment_id}")
        observation = cell.get("observation_bundle")
        harness = cell.get("harness")
        workspace = cell.get("workspace")
        expected_observation = treatment_id[-1]
        expected_harness = (
            "structured_single_action"
            if treatment_id.startswith("E1S")
            else "safe_operation_single_action"
        )
        expected_workspace = "none" if treatment_id.startswith("E1S") else "safe_operations_v1"
        if (
            observation != expected_observation
            or harness != expected_harness
            or workspace != expected_workspace
        ):
            raise FeatureManifestError(f"factor assignment mismatch: {treatment_id}")
        manifests[treatment_id] = E1FeatureManifest(
            treatment_id=treatment_id,
            observation_bundle=observation,
            harness=harness,
            workspace=workspace,
            proposal_action_count=shared["proposal_action_count"],
            context_mode=shared["context_mode"],
            recent_transition_limit=shared["recent_transition_limit"],
            intent_max_bytes=shared["intent_max_bytes"],
            rationale_max_bytes=shared["rationale_max_bytes"],
            scheduler=shared["scheduler"],
            prompt_revision=shared["prompt_revision"],
            workspace_invocation_limit=shared["workspace_invocation_limit"],
            history_loss_reporting=shared["history_loss_reporting"],
        )
    return manifests


def _bounded_optional_text(payload: Mapping[str, Any], field: str, maximum: int) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise FeatureManifestError(f"{field} must be a string")
    if len(value.encode("utf-8")) > maximum:
        raise FeatureManifestError(f"{field} exceeds its UTF-8 byte limit")
    return value


def validate_e1_proposal(
    payload: Mapping[str, Any],
    *,
    manifest: E1FeatureManifest,
    legal_actions: Iterable[int | GameAction],
) -> ActionDecision:
    if not isinstance(payload, Mapping):
        raise FeatureManifestError("proposal must be an object")
    extra = set(payload) - PROPOSAL_FIELDS
    if extra:
        raise FeatureManifestError(f"disabled or unknown proposal fields: {sorted(extra)}")
    _bounded_optional_text(payload, "intent", manifest.intent_max_bytes)
    rationale = _bounded_optional_text(payload, "rationale", manifest.rationale_max_bytes)

    action = payload.get("action")
    if not isinstance(action, Mapping) or set(action) != {"action_id", "action_data"}:
        raise FeatureManifestError("proposal must contain exactly one complete action")
    action_id = action["action_id"]
    action_data = action["action_data"]
    if isinstance(action_id, bool) or not isinstance(action_id, int) or action_id not in range(1, 8):
        raise FeatureManifestError("model action_id must be an integer in [1, 7]")
    if action_id not in normalize_legal_actions(legal_actions):
        raise FeatureManifestError("model action is not currently legal")
    if not isinstance(action_data, Mapping):
        raise FeatureManifestError("action_data must be an object")

    source = f"model:{manifest.treatment_id}"
    rationale_reference = (
        hashlib.sha256(rationale.encode("utf-8")).hexdigest() if rationale is not None else None
    )
    if action_id == GameAction.ACTION6.value:
        if set(action_data) != {"x", "y"}:
            raise FeatureManifestError("ACTION6 requires exactly x and y")
        try:
            return ActionDecision.click(
                DisplayPoint(x=action_data["x"], y=action_data["y"]),
                source=source,
                local_rationale_reference=rationale_reference,
            )
        except (TypeError, ValueError) as exc:
            raise FeatureManifestError(str(exc)) from exc
    if action_data:
        raise FeatureManifestError("only ACTION6 may carry action data")
    return ActionDecision.simple(
        action_id,
        source=source,
        local_rationale_reference=rationale_reference,
    )
