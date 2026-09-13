"""Offline Phase 3 preparation. No policy store, model call or dispatch boundary.

Typed facts are supplied by trusted fixture extractors, never model assertions.
The deliberately small v1 vocabulary does not claim object tracking support.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from pathlib import Path


class Verdict(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Prediction:
    prediction_id: str
    transition_id: str
    committed_sequence: int
    scope: str
    dependency: str
    kind: str
    expected: int
    evidence_id: str
    required: bool = True


@dataclass(frozen=True)
class Transition:
    transition_id: str
    sequence: int
    scope: str
    dependency: str
    kind: str
    observed: int
    evidence_id: str
    evidence_available: bool
    correspondence_known: bool
    prestate_fingerprint: str
    full_state_sha256: str


KINDS = {"bound_cell_value", "bound_entity_x", "bound_entity_y", "scoped_grid_relation"}


def validate_fixture(payload: dict, schema_path: Path) -> None:
    from jsonschema import Draft202012Validator
    if len(json.dumps(payload).encode()) > 131072:
        raise ValueError("fixture byte ceiling exceeded")
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    predictions = payload["predictions"]
    ids = [p["prediction_id"] for p in predictions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate prediction identity")
    hypotheses = payload["hypotheses"]
    if len({h["id"] for h in hypotheses}) != len(hypotheses):
        raise ValueError("duplicate hypothesis identity")
    if any(not set(h["prediction_ids"]).issubset(ids) for h in hypotheses):
        raise ValueError("unresolved prediction reference")


def local_fingerprint(*, entity: str, scope: str, relevant_configuration: tuple[int, ...]) -> str:
    """Fixture extractor contract: exclude HUD/timer; retain full hash separately."""
    if not entity or not scope or not relevant_configuration or len(relevant_configuration) > 4096:
        raise ValueError("unbounded or empty local dependency configuration")
    if any(type(x) is not int for x in relevant_configuration):
        raise ValueError("typed local configuration required")
    return hashlib.sha256(json.dumps([entity, scope, relevant_configuration]).encode()).hexdigest()


def evaluate(prediction: Prediction, transition: Transition) -> Verdict:
    """Only precommitted, required, dependency-scoped exact facts are eligible."""
    if (prediction.kind not in KINDS or not prediction.required
            or type(prediction.expected) is not int or type(transition.observed) is not int
            or not prediction.dependency or not prediction.scope
            or not prediction.evidence_id or not transition.evidence_available
            or not transition.correspondence_known
            or prediction.committed_sequence >= transition.sequence
            or (prediction.transition_id, prediction.scope, prediction.dependency,
                prediction.kind, prediction.evidence_id) !=
               (transition.transition_id, transition.scope, transition.dependency,
                transition.kind, transition.evidence_id)):
        return Verdict.UNKNOWN
    return Verdict.MATCH if prediction.expected == transition.observed else Verdict.MISMATCH


def discriminates(first: Prediction, second: Prediction, transition: Transition) -> bool:
    """Incompatible exact outcomes for the same bound probe, not free-text labels."""
    return (first.prediction_id != second.prediction_id
            and first.expected != second.expected
            and {evaluate(first, transition), evaluate(second, transition)} ==
                {Verdict.MATCH, Verdict.MISMATCH})


def support_gate(records: list[tuple[Prediction, Transition, Prediction | None]], *,
                 variant: str, scope: str, dependency: str, kind: str,
                 alternatives_unresolved: bool, retired: bool = False) -> bool:
    if variant not in {"E6-DISC", "E6-REPEAT"}:
        raise ValueError("unregistered gate")
    if retired or not records or len(records) > 64:
        return False
    distinct = {}
    discriminating = False
    for prediction, transition, competitor in records:
        if (prediction.scope, prediction.dependency, prediction.kind) != (scope, dependency, kind):
            return False
        if evaluate(prediction, transition) != Verdict.MATCH:
            return False  # unavailable evidence and contradictions revoke support
        if not transition.prestate_fingerprint or len(transition.full_state_sha256) != 64:
            return False
        prior = distinct.get(transition.transition_id)
        if prior is not None and prior != transition:
            return False
        distinct[transition.transition_id] = transition
        discriminating |= competitor is not None and discriminates(prediction, competitor, transition)
    if len(distinct) >= 2 and discriminating:
        return True
    return (variant == "E6-REPEAT" and not alternatives_unresolved and len(distinct) >= 3
            and len({t.prestate_fingerprint for t in distinct.values()}) >= 2)


GUARDS = frozenset({"same_session", "same_context_generation", "authoritative_frontier",
                    "lifecycle_permits", "currently_legal", "support_and_bindings",
                    "no_cancellation", "within_budget_and_deadline"})


def continuation(*, e6_enabled: bool, unresolved_dispatch: bool,
                 predicates: dict[str, Verdict], dependencies: set[str],
                 guards: dict[str, Verdict]) -> str:
    """Offline controller oracle; ambiguous dispatch takes precedence over recovery."""
    if unresolved_dispatch:
        return "QUARANTINED"
    if not e6_enabled:
        return "SINGLE_ACTION"
    if (not dependencies or set(predicates) != dependencies or set(guards) != GUARDS
            or any(v != Verdict.MATCH for v in [*predicates.values(), *guards.values()])):
        return "CANCEL_QUEUE"
    return "CONTINUE_ONE_ACTION"


def validate_preparation(root: Path) -> dict:
    config = json.loads((root / "config/phase3_preparation.json").read_text())
    if (config["status"] != "draft_inactive_parent_unresolved"
            or config["activated_treatments"] or config["allocated_accelerator_hours"] != 0
            or config["parent_manifest_sha256"] is not None
            or config["registered_candidates"] != ["E5", "E6-DISC", "E6-REPEAT"]):
        raise ValueError("preparation must remain inactive and unresolved")
    return config


def require_execution_closure(config: dict) -> None:
    # This draft intentionally cannot authorize experiments, even if edited in memory.
    raise ValueError("Phase 3 execution unavailable: freeze and validate a separately admitted protocol")


def paired_report(records: list[dict]) -> dict:
    """Descriptive complete-workload pairs, never transition-level pseudo-replication.

    Input metrics must include setup, probes, support-building and failed work.
    Real promotion requires the separate prospective protocol, not this report.
    """
    if not records:
        raise ValueError("no complete workload evidence")
    metrics = ("official_RHAE_percent", "actions", "inference_calls", "tokens", "probes",
               "blocked_continuations", "false_continuations", "scope_failures", "elapsed_seconds",
               "peak_vram_bytes", "peak_ram_bytes")
    bindings = ("parent_sha256", "model_sha256", "scheduler_sha256", "workload_sha256",
                "ceilings_sha256", "protocol_sha256", "treatment_manifest_sha256")
    pairs, run_ids = {}, set()
    reference = tuple(records[0].get(k) for k in bindings)
    for row in records:
        if any(not isinstance(x, str) or len(x) != 64 or any(c not in "0123456789abcdef" for c in x)
               for x in reference):
            raise ValueError("exact frozen bindings required")
        if tuple(row.get(k) for k in bindings) != reference:
            raise ValueError("mixed bindings")
        if (row.get("mode") != "shared_resource_whole_run" or not row.get("complete_workload")
                or row.get("cost_scope") != "all_work_including_setup_probes_support_and_failures"
                or row.get("arm") not in {"parent", "treatment"}
                or row.get("order") not in {"AB", "BA"}):
            raise ValueError("comparison unit or cost accounting invalid")
        if not row.get("run_id") or row["run_id"] in run_ids:
            raise ValueError("fresh unique runs required")
        run_ids.add(row["run_id"])
        pair = pairs.setdefault(row["pair_id"], {})
        if row["arm"] in pair:
            raise ValueError("duplicate arm")
        pair[row["arm"]] = row
        for key in metrics:
            value = row["metrics"].get(key)
            if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
                raise ValueError("missing or invalid charged metric: " + key)
    differences, orders = [], []
    for pair in pairs.values():
        if set(pair) != {"parent", "treatment"} or pair["parent"]["order"] != pair["treatment"]["order"]:
            raise ValueError("incomplete or inconsistent pair")
        orders.append(pair["parent"]["order"])
        differences.append({k: pair["treatment"]["metrics"][k] - pair["parent"]["metrics"][k]
                            for k in metrics})
    return {"status": "descriptive_only_not_admission_or_promotion", "pairs": len(pairs),
            "uncertainty_unit": "paired_complete_workloads", "pair_differences": differences,
            "counterbalanced": orders.count("AB") == orders.count("BA"),
            "acceptance_claim": False, "uncertainty": "pending_frozen_inferential_rule",
            "input_sha256": hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()}
