"""Policy-inert Phase 2 transition diagnostics and deterministic replay.

The recorder is a write-only observer from the policy's point of view.  Its
contents are never used by observation construction or action selection.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .action import ActionDecision, normalize_legal_actions
from .evidence import PackedGrid, TransitionEvidence


DIAGNOSTIC_SCHEMA_VERSION = 1
MAX_RETAINED_PROPOSAL_BYTES = 16_384
NO_REJECTION = "none"
REJECTION_CATEGORIES = frozenset(
    {
        NO_REJECTION,
        "malformed_json",
        "invalid_proposal_shape",
        "disabled_feature",
        "illegal_action",
        "invalid_action_data",
        "unknown_workspace_operation",
        "workspace_failure",
        "workspace_exhausted",
        "inference_queue_failure",
        "inference_transport_failure",
        "invalid_completion",
        "policy_exception",
        "fallback_only",
        "pre_dispatch_failure",
        "outcome_unknown",
    }
)
OUTCOME_PHASES = frozenset({"none", "pre_transport", "action_dispatch_post_entry"})


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def classify_proposal_rejection(exc: BaseException) -> str:
    """Map policy/transport exceptions to the frozen diagnostic vocabulary."""

    message = str(exc).lower()
    name = type(exc).__name__.lower()
    if "strict json" in message or "not one strict json" in message:
        return "malformed_json"
    if "disabled or unknown proposal fields" in message:
        return "disabled_feature"
    if "not currently legal" in message or "illegal" in message:
        return "illegal_action"
    if "action_data" in message or "action6" in message or "coordinate" in message:
        return "invalid_action_data"
    if "unknown safe operation" in message:
        return "unknown_workspace_operation"
    if "workspace budget" in message or "budget exhausted" in message:
        return "workspace_exhausted"
    if "safe operation" in message or "workspace" in message:
        return "workspace_failure"
    if "queue" in name or "queue" in message:
        return "inference_queue_failure"
    if "connection" in name or "request" in name or "transport" in message:
        return "inference_transport_failure"
    if "completion client" in message or "model server" in message:
        return "invalid_completion"
    if "proposal" in message or "model response must" in message:
        return "invalid_proposal_shape"
    return "policy_exception"


@dataclass(slots=True)
class _PendingTransition:
    iteration: int
    pre_observation_hash: str
    pre_frame: PackedGrid
    pre_state: str
    pre_levels_completed: int
    pre_win_levels: int
    pre_legal_actions: tuple[int, ...]
    proposals: list[dict[str, Any]] = field(default_factory=list)
    workspace_operations: list[dict[str, Any]] = field(default_factory=list)
    workspace_exhausted: bool = False
    proposal_rejection_category: str = NO_REJECTION
    rejection_detail: str | None = None
    executed_decision: dict[str, Any] | None = None


class TransitionDiagnosticRecorder:
    """Bounded, local recorder whose outputs cannot feed policy context."""

    def __init__(
        self,
        *,
        game_id: str,
        treatment_id: str,
        seed: int | None = None,
        run_id: str = "local-diagnostic",
        capacity: int = 256,
    ) -> None:
        if not game_id or not treatment_id or not run_id:
            raise ValueError("diagnostic identity fields must be non-empty")
        if capacity < 1:
            raise ValueError("diagnostic capacity must be positive")
        self.game_id = game_id
        self.treatment_id = treatment_id
        self.seed = seed
        self.run_id = run_id
        self.capacity = capacity
        self._pending: _PendingTransition | None = None
        self._records: list[dict[str, Any]] = []
        self._frames: dict[str, dict[str, Any]] = {}
        self._last_action_key: tuple[int, str] | None = None
        self._action_repeat_count = 0
        self._seen_post_states: Counter[str] = Counter()
        self.capture_errors: list[dict[str, str]] = []

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._records)

    def capture_error(self, phase: str, exc: BaseException) -> None:
        if len(self.capture_errors) >= self.capacity:
            self.capture_errors.pop(0)
        self.capture_errors.append({"phase": str(phase), "error_type": type(exc).__name__})

    def begin_transition(self, observation: Any, *, iteration: int) -> None:
        self._pending = _PendingTransition(
            iteration=int(iteration),
            pre_observation_hash=str(observation.canonical_hash),
            pre_frame=PackedGrid.pack(observation.latest_frame, frame_index=0),
            pre_state=str(observation.state.value),
            pre_levels_completed=int(observation.levels_completed),
            pre_win_levels=int(observation.win_levels),
            pre_legal_actions=tuple(int(item) for item in observation.available_actions),
        )

    def note_model_proposal(self, content: str) -> None:
        pending = self._require_pending()
        encoded = content.encode("utf-8")
        retained = encoded[:MAX_RETAINED_PROPOSAL_BYTES]
        retained_text = retained.decode("utf-8", errors="ignore")
        pending.proposals.append(
            {
                "kind": "model",
                "content": retained_text,
                "content_sha256": hashlib.sha256(encoded).hexdigest(),
                "content_bytes": len(encoded),
                "content_availability": "exact"
                if len(encoded) <= MAX_RETAINED_PROPOSAL_BYTES
                else "truncated_capacity",
            }
        )

    def note_workspace_operation(
        self,
        operation: str,
        arguments: Mapping[str, Any],
        *,
        succeeded: bool,
        result: Any = None,
        error_category: str | None = None,
    ) -> None:
        pending = self._require_pending()
        item: dict[str, Any] = {
            "operation": operation,
            "arguments_sha256": canonical_sha256(dict(arguments)),
            "succeeded": bool(succeeded),
            "result_sha256": canonical_sha256(result) if succeeded else None,
            "error_category": error_category,
        }
        pending.workspace_operations.append(item)
        if error_category == "workspace_exhausted":
            pending.workspace_exhausted = True

    def note_rejection(self, category: str, detail: str | None = None) -> None:
        pending = self._require_pending()
        if category not in REJECTION_CATEGORIES:
            category = "policy_exception"
        pending.proposal_rejection_category = category
        pending.rejection_detail = (detail or "")[:256] or None
        if category == "workspace_exhausted":
            pending.workspace_exhausted = True

    def note_decision(self, decision: ActionDecision) -> None:
        pending = self._require_pending()
        pending.executed_decision = {
            "decision_id": decision.decision_id,
            "source": decision.source,
            "action_id": decision.action_id,
            "action_data": dict(decision.action_data),
            "action_data_sha256": canonical_sha256(dict(decision.action_data)),
            "local_rationale_reference": decision.local_rationale_reference,
        }
        if not pending.proposals and decision.source == "deterministic_fallback":
            pending.proposal_rejection_category = "fallback_only"

    def finish_acknowledged(self, before: Any, after: Any, evidence: TransitionEvidence) -> None:
        pending = self._require_pending()
        post_frame = PackedGrid.pack(after.latest_frame, frame_index=0)
        self._retain_frame(pending.pre_frame)
        self._retain_frame(post_frame)
        changed_cells = evidence.delta.changed_cells
        no_change = (
            changed_cells == 0
            and pending.pre_state == str(after.state.value)
            and pending.pre_levels_completed == int(after.levels_completed)
            and pending.pre_win_levels == int(after.win_levels)
            and pending.pre_legal_actions == tuple(int(item) for item in after.available_actions)
        )
        progress = (
            changed_cells != 0
            or int(after.levels_completed) > pending.pre_levels_completed
            or str(after.state.value) == "WIN"
        )
        record = self._base_record(pending)
        record.update(
            {
                "dispatch_status": "acknowledged",
                "action_legal": self._action_legal(pending),
                "outcome_unknown_phase": "none",
                "post": {
                    "observation_sha256": str(after.canonical_hash),
                    "frame_content_sha256": post_frame.content_sha256,
                    "state": str(after.state.value),
                    "levels_completed": int(after.levels_completed),
                    "win_levels": int(after.win_levels),
                    "legal_actions": [int(item) for item in after.available_actions],
                },
                "transition": {
                    "transition_id": evidence.transition_id,
                    "sequence_sha256": evidence.sequence_sha256,
                    "frame_count": evidence.frame_count,
                    "distinct_frame_count": evidence.distinct_frame_count,
                    "changed_cells": changed_cells,
                    "no_change": no_change,
                    "bounding_box": list(evidence.delta.bounding_box)
                    if evidence.delta.bounding_box is not None
                    else None,
                    "palette_added": list(evidence.delta.palette_added),
                    "palette_removed": list(evidence.delta.palette_removed),
                },
                "evidence_availability": {
                    tier.value: availability.value
                    for tier, availability in evidence.availability.items()
                },
                "measurable_progress": progress,
            }
        )
        self._complete(record)

    def finish_unresolved(self, *, phase: str, category: str) -> None:
        pending = self._require_pending()
        if phase not in OUTCOME_PHASES - {"none"}:
            raise ValueError("unknown diagnostic outcome phase")
        if pending.proposal_rejection_category == NO_REJECTION:
            pending.proposal_rejection_category = category
        self._retain_frame(pending.pre_frame)
        record = self._base_record(pending)
        record.update(
            {
                "dispatch_status": "pre_dispatch_failed"
                if phase == "pre_transport"
                else "outcome_unknown",
                "action_legal": self._action_legal(pending),
                "outcome_unknown_phase": phase,
                "post": None,
                "transition": None,
                "evidence_availability": {
                    "T0": "exact",
                    "T1": "not_observed",
                    "T2": "not_observed",
                    "T3": "not_observed",
                },
                "measurable_progress": False,
            }
        )
        self._complete(record)

    def bundle(self) -> dict[str, Any]:
        core = {
            "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
            "record_type": "phase2_diagnostic_bundle",
            "run_id": self.run_id,
            "game_id": self.game_id,
            "treatment_id": self.treatment_id,
            "seed": self.seed,
            "policy_visibility": "diagnostics_not_in_policy_observation",
            "progress_rule": "grid_change_or_level_increment_or_win_v1",
            "records": list(self._records),
            "retained_frames": dict(sorted(self._frames.items())),
            "capture_errors": list(self.capture_errors),
        }
        return {**core, "bundle_sha256": canonical_sha256(core)}

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.bundle(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(prefix=".diagnostic-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return target

    def _base_record(self, pending: _PendingTransition) -> dict[str, Any]:
        action_key = self._decision_key(pending)
        if action_key is not None and action_key == self._last_action_key:
            self._action_repeat_count += 1
        else:
            self._action_repeat_count = 0
        self._last_action_key = action_key
        return {
            "game_id": self.game_id,
            "treatment_id": self.treatment_id,
            "iteration": pending.iteration,
            "proposal_or_fallback": {
                "model_proposals": list(pending.proposals),
                "executed_decision": pending.executed_decision,
            },
            "proposal_rejection_category": pending.proposal_rejection_category,
            "rejection_detail": pending.rejection_detail,
            "repeated_action_count": self._action_repeat_count,
            "repeated_state_count": 0,
            "workspace": {
                "operations": list(pending.workspace_operations),
                "invocations": len(pending.workspace_operations),
                "exhausted": pending.workspace_exhausted,
            },
            "pre": {
                "observation_sha256": pending.pre_observation_hash,
                "frame_content_sha256": pending.pre_frame.content_sha256,
                "state": pending.pre_state,
                "levels_completed": pending.pre_levels_completed,
                "win_levels": pending.pre_win_levels,
                "legal_actions": list(pending.pre_legal_actions),
            },
        }

    def _complete(self, record: dict[str, Any]) -> None:
        post = record.get("post")
        if isinstance(post, Mapping):
            post_hash = str(post["observation_sha256"])
            record["repeated_state_count"] = self._seen_post_states[post_hash]
            self._seen_post_states[post_hash] += 1
        signature_body = {key: value for key, value in record.items() if key != "failure_signature_sha256"}
        record["failure_signature_sha256"] = canonical_sha256(signature_body)
        if len(self._records) >= self.capacity:
            self._records.pop(0)
        self._records.append(record)
        self._pending = None

    def _action_legal(self, pending: _PendingTransition) -> bool:
        decision = pending.executed_decision
        return bool(
            decision
            and (
                int(decision["action_id"]) in normalize_legal_actions(pending.pre_legal_actions)
                or (int(decision["action_id"]) == 0 and pending.pre_state == "GAME_OVER")
            )
        )

    @staticmethod
    def _decision_key(pending: _PendingTransition) -> tuple[int, str] | None:
        if pending.executed_decision is None:
            return None
        return (
            int(pending.executed_decision["action_id"]),
            str(pending.executed_decision["action_data_sha256"]),
        )

    def _retain_frame(self, frame: PackedGrid) -> None:
        self._frames.setdefault(
            frame.content_sha256,
            {
                "shape": list(frame.shape),
                "dtype": "uint8",
                "order": "C",
                "payload_base64": base64.b64encode(frame.payload).decode("ascii"),
            },
        )

    def _require_pending(self) -> _PendingTransition:
        if self._pending is None:
            raise RuntimeError("diagnostic transition was not started")
        return self._pending


class DiagnosticReplayError(ValueError):
    pass


def replay_bundle(value: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute transition facts from retained frames and reject drift."""

    if value.get("schema_version") != 1 or value.get("record_type") != "phase2_diagnostic_bundle":
        raise DiagnosticReplayError("unknown diagnostic bundle")
    core = {key: item for key, item in value.items() if key != "bundle_sha256"}
    if canonical_sha256(core) != value.get("bundle_sha256"):
        raise DiagnosticReplayError("diagnostic bundle hash mismatch")
    frames = value.get("retained_frames")
    records = value.get("records")
    if not isinstance(frames, Mapping) or not isinstance(records, list):
        raise DiagnosticReplayError("diagnostic bundle is incomplete")
    decoded: dict[str, np.ndarray] = {}
    for digest, frame in frames.items():
        try:
            shape = tuple(int(item) for item in frame["shape"])
            payload = base64.b64decode(frame["payload_base64"], validate=True)
            array = np.frombuffer(payload, dtype=np.uint8).reshape(shape).copy(order="C")
        except Exception as exc:
            raise DiagnosticReplayError("retained frame is corrupt") from exc
        packed = PackedGrid.pack(array, frame_index=0)
        if packed.content_sha256 != digest:
            raise DiagnosticReplayError("retained frame content hash mismatch")
        decoded[str(digest)] = array

    reproduced_failures = 0
    last_action_key: tuple[int, str] | None = None
    action_repeat_count = 0
    seen_post_states: Counter[str] = Counter()
    for record in records:
        if not isinstance(record, Mapping):
            raise DiagnosticReplayError("transition record is not an object")
        expected_signature = canonical_sha256(
            {key: item for key, item in record.items() if key != "failure_signature_sha256"}
        )
        if expected_signature != record.get("failure_signature_sha256"):
            raise DiagnosticReplayError("transition signature mismatch")
        if (
            record.get("game_id") != value.get("game_id")
            or record.get("treatment_id") != value.get("treatment_id")
        ):
            raise DiagnosticReplayError("transition identity differs from bundle")
        proposal_block = record.get("proposal_or_fallback")
        if not isinstance(proposal_block, Mapping):
            raise DiagnosticReplayError("proposal or fallback block is missing")
        proposals = proposal_block.get("model_proposals")
        if not isinstance(proposals, list):
            raise DiagnosticReplayError("model proposal list is invalid")
        for proposal in proposals:
            if not isinstance(proposal, Mapping):
                raise DiagnosticReplayError("model proposal is invalid")
            content = proposal.get("content")
            if not isinstance(content, str):
                raise DiagnosticReplayError("retained proposal is invalid")
            encoded = content.encode("utf-8")
            availability = proposal.get("content_availability")
            if availability == "exact" and (
                proposal.get("content_bytes") != len(encoded)
                or proposal.get("content_sha256") != hashlib.sha256(encoded).hexdigest()
            ):
                raise DiagnosticReplayError("exact proposal hash mismatch")
            if availability == "truncated_capacity" and (
                len(encoded) > MAX_RETAINED_PROPOSAL_BYTES
                or int(proposal.get("content_bytes", 0)) <= len(encoded)
            ):
                raise DiagnosticReplayError("proposal capacity marker is invalid")
        decision = proposal_block.get("executed_decision")
        if not isinstance(decision, Mapping):
            raise DiagnosticReplayError("executed decision is missing")
        action_data = decision.get("action_data")
        if not isinstance(action_data, Mapping) or canonical_sha256(dict(action_data)) != decision.get(
            "action_data_sha256"
        ):
            raise DiagnosticReplayError("executed action data hash mismatch")
        action_key = (int(decision["action_id"]), str(decision["action_data_sha256"]))
        if action_key == last_action_key:
            action_repeat_count += 1
        else:
            action_repeat_count = 0
        last_action_key = action_key
        if record.get("repeated_action_count") != action_repeat_count:
            raise DiagnosticReplayError("repeated action count differs")
        legal = (
            action_key[0] in normalize_legal_actions(record["pre"]["legal_actions"])
            or (action_key[0] == 0 and record["pre"]["state"] == "GAME_OVER")
        )
        if record.get("action_legal") is not legal:
            raise DiagnosticReplayError("replayed action legality differs")
        workspace = record.get("workspace")
        operations = workspace.get("operations") if isinstance(workspace, Mapping) else None
        if (
            not isinstance(workspace, Mapping)
            or not isinstance(operations, list)
            or workspace.get("invocations") != len(operations)
        ):
            raise DiagnosticReplayError("workspace invocation count differs")
        transition = record.get("transition")
        post = record.get("post")
        if transition is not None and isinstance(post, Mapping):
            try:
                before = decoded[record["pre"]["frame_content_sha256"]]
                after = decoded[post["frame_content_sha256"]]
            except (KeyError, TypeError) as exc:
                raise DiagnosticReplayError("transition references unavailable frame") from exc
            changed = -1 if before.shape != after.shape else int(np.count_nonzero(before != after))
            no_change = bool(
                changed == 0
                and record["pre"]["state"] == post["state"]
                and record["pre"]["levels_completed"] == post["levels_completed"]
                and record["pre"]["win_levels"] == post["win_levels"]
                and record["pre"]["legal_actions"] == post["legal_actions"]
            )
            progress = bool(
                changed != 0
                or post["levels_completed"] > record["pre"]["levels_completed"]
                or post["state"] == "WIN"
            )
            if (
                transition.get("changed_cells") != changed
                or transition.get("no_change") is not no_change
                or record.get("measurable_progress") is not progress
            ):
                raise DiagnosticReplayError("replayed transition facts differ")
            post_hash = str(post["observation_sha256"])
            if record.get("repeated_state_count") != seen_post_states[post_hash]:
                raise DiagnosticReplayError("repeated state count differs")
            seen_post_states[post_hash] += 1
        elif record.get("repeated_state_count") != 0:
            raise DiagnosticReplayError("unresolved transition has a repeated state")
        category = failure_category(record)
        if category != "none":
            reproduced_failures += 1
    return {
        "bundle_sha256": value["bundle_sha256"],
        "game_id": value.get("game_id"),
        "treatment_id": value.get("treatment_id"),
        "transition_count": len(records),
        "reproduced_failures": reproduced_failures,
        "status": "reproduced",
    }


def failure_category(record: Mapping[str, Any]) -> str:
    rejection = str(record.get("proposal_rejection_category", NO_REJECTION))
    if rejection != NO_REJECTION:
        return rejection
    if record.get("outcome_unknown_phase") != "none":
        return "outcome_unknown"
    workspace = record.get("workspace")
    if isinstance(workspace, Mapping) and workspace.get("exhausted") is True:
        return "workspace_exhausted"
    if record.get("action_legal") is False:
        return "illegal_action"
    if record.get("measurable_progress") is False:
        return "no_measurable_progress"
    return "none"


def grouped_failure_report(bundles: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Group local diagnostic failures; this result is never a policy input."""

    grouped: Counter[tuple[str, str, str]] = Counter()
    transition_count = 0
    reproduced_failures = 0
    replayed = []
    for bundle in bundles:
        result = replay_bundle(bundle)
        replayed.append(result)
        transition_count += result["transition_count"]
        for record in bundle["records"]:
            category = failure_category(record)
            if category != "none":
                grouped[(str(record["game_id"]), str(record["treatment_id"]), category)] += 1
                reproduced_failures += 1
    rows = [
        {"game_id": game, "treatment_id": treatment, "category": category, "count": count}
        for (game, treatment, category), count in sorted(grouped.items())
    ]
    return {
        "schema_version": 1,
        "record_type": "phase2_diagnostic_report",
        "policy_visibility": "local_report_only_never_model_input",
        "bundle_count": len(bundles),
        "transition_count": transition_count,
        "reproduced_failures": reproduced_failures,
        "groups": rows,
        "replays": replayed,
    }


def load_bundles(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    paths = sorted(source.glob("*.json")) if source.is_dir() else [source]
    if not paths:
        raise DiagnosticReplayError("no diagnostic bundles found")
    bundles: list[dict[str, Any]] = []
    for item in paths:
        try:
            value = json.loads(item.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise DiagnosticReplayError(f"invalid diagnostic bundle: {item}") from exc
        if not isinstance(value, dict) or value.get("record_type") != "phase2_diagnostic_bundle":
            continue
        bundles.append(value)
    if not bundles:
        raise DiagnosticReplayError("no diagnostic bundles found")
    return bundles
