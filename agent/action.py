"""Immutable action values and request-local serialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from arcengine import GameAction

MAX_DISPLAY_COORDINATE = 63


class ActionValidationError(ValueError):
    """An action cannot be dispatched under the current contract."""


@dataclass(frozen=True, slots=True)
class DisplayPoint:
    x: int
    y: int

    def __post_init__(self) -> None:
        if isinstance(self.x, bool) or isinstance(self.y, bool):
            raise ActionValidationError("display coordinates must be integers")
        if not (0 <= self.x <= MAX_DISPLAY_COORDINATE):
            raise ActionValidationError("x must be in [0, 63]")
        if not (0 <= self.y <= MAX_DISPLAY_COORDINATE):
            raise ActionValidationError("y must be in [0, 63]")


def _freeze_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not values:
        return MappingProxyType({})
    frozen: dict[str, Any] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            raise ActionValidationError("action-data keys must be strings")
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise ActionValidationError("action-data values must be JSON scalars")
        frozen[key] = value
    return MappingProxyType(frozen)


@dataclass(frozen=True, slots=True)
class ActionDecision:
    action_id: int
    action_data: Mapping[str, Any] = field(default_factory=dict)
    wire_reasoning: Mapping[str, Any] = field(default_factory=dict)
    local_rationale_reference: str | None = None
    source: str = "deterministic_fallback"
    controller_mode: str = "explore"
    expected_effect_predicates: tuple[str, ...] = ()
    stop_condition_predicates: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    decision_id: str = ""

    def __post_init__(self) -> None:
        try:
            GameAction.from_id(self.action_id)
        except ValueError as exc:
            raise ActionValidationError(f"unknown action id: {self.action_id}") from exc
        object.__setattr__(self, "action_data", _freeze_mapping(self.action_data))
        object.__setattr__(self, "wire_reasoning", _freeze_mapping(self.wire_reasoning))
        if not self.decision_id:
            body = json.dumps(
                [self.action_id, dict(self.action_data), self.source],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            object.__setattr__(self, "decision_id", hashlib.sha256(body).hexdigest()[:20])

    @classmethod
    def simple(cls, action: int | GameAction, **kwargs: Any) -> "ActionDecision":
        return cls(action_id=int(action.value if isinstance(action, GameAction) else action), **kwargs)

    @classmethod
    def click(cls, point: DisplayPoint, **kwargs: Any) -> "ActionDecision":
        return cls(action_id=GameAction.ACTION6.value, action_data={"x": point.x, "y": point.y}, **kwargs)


@dataclass(frozen=True, slots=True)
class SerializedAction:
    endpoint: str
    payload: Mapping[str, Any]
    payload_bytes: bytes
    payload_sha256: str


def normalize_legal_actions(actions: Iterable[int | GameAction]) -> frozenset[int]:
    normalized: set[int] = set()
    for action in actions:
        value = int(action.value if isinstance(action, GameAction) else action)
        try:
            GameAction.from_id(value)
        except ValueError:
            continue
        normalized.add(value)
    return frozenset(normalized)


def serialize_action(
    decision: ActionDecision,
    *,
    game_id: str,
    guid: str,
    legal_actions: Iterable[int | GameAction],
    reasoning_limit_bytes: int = 16_000,
    request_limit_bytes: int = 65_536,
) -> SerializedAction:
    legal = normalize_legal_actions(legal_actions)
    if decision.action_id not in legal:
        raise ActionValidationError(
            f"action {decision.action_id} is not currently legal: {sorted(legal)}"
        )
    data = dict(decision.action_data)
    if decision.action_id == GameAction.ACTION6.value:
        if set(data) != {"x", "y"}:
            raise ActionValidationError("ACTION6 requires exactly x and y")
        DisplayPoint(x=data["x"], y=data["y"])
    elif data:
        raise ActionValidationError("only ACTION6 may carry action data")

    endpoint = "RESET" if decision.action_id == 0 else f"ACTION{decision.action_id}"
    payload: dict[str, Any] = {"game_id": game_id, "guid": guid}
    payload.update(data)
    if decision.wire_reasoning:
        # Match arc-agi 0.9.9: the logical object is compact JSON encoded into
        # the server-parsed reasoning string field.
        logical = json.dumps(dict(decision.wire_reasoning), sort_keys=True, separators=(",", ":"))
        parsed_value_bytes = json.dumps(logical, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(parsed_value_bytes) >= reasoning_limit_bytes:
            raise ActionValidationError("server-parsed reasoning exceeds byte limit")
        payload["reasoning"] = logical
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(payload_bytes) > request_limit_bytes:
        raise ActionValidationError("request body exceeds internal byte limit")
    return SerializedAction(
        endpoint=endpoint,
        payload=MappingProxyType(payload),
        payload_bytes=payload_bytes,
        payload_sha256=hashlib.sha256(payload_bytes).hexdigest(),
    )
