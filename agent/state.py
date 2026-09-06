"""Bounded typed state used by the competition loop."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from arcengine import FrameData, FrameDataRaw, GameState


def _pack_layers(layers: Any) -> tuple[np.ndarray, ...]:
    return tuple(np.ascontiguousarray(layer, dtype=np.uint8) for layer in (layers or []))


@dataclass(frozen=True, slots=True)
class Observation:
    game_id: str
    layers: tuple[np.ndarray, ...]
    state: GameState
    levels_completed: int
    win_levels: int
    guid: str
    available_actions: tuple[int, ...]
    full_reset: bool = False

    @classmethod
    def from_value(cls, value: FrameData | FrameDataRaw | dict[str, Any]) -> "Observation":
        if isinstance(value, dict):
            frame = FrameData.model_validate(value)
            source = frame
        else:
            source = value
        guid = getattr(source, "guid", None)
        if not guid:
            raise ValueError("observation has no bound guid")
        return cls(
            game_id=str(getattr(source, "game_id", "")),
            layers=_pack_layers(getattr(source, "frame", [])),
            state=getattr(source, "state", GameState.NOT_PLAYED),
            levels_completed=int(getattr(source, "levels_completed", 0)),
            win_levels=int(getattr(source, "win_levels", 0)),
            guid=str(guid),
            available_actions=tuple(int(x.value if hasattr(x, "value") else x) for x in getattr(source, "available_actions", [])),
            full_reset=bool(getattr(source, "full_reset", False)),
        )

    @property
    def canonical_hash(self) -> str:
        digest = hashlib.sha256(b"arc3-observation-v1\0")
        digest.update(self.game_id.encode())
        digest.update(self.state.value.encode())
        digest.update(bytes([self.levels_completed, self.win_levels]))
        for layer in self.layers:
            digest.update(str(layer.shape).encode())
            digest.update(layer.tobytes(order="C"))
        digest.update(bytes(self.available_actions))
        return digest.hexdigest()


@dataclass(slots=True)
class LifecycleCounters:
    lifecycle_attempted: int = 0
    lifecycle_acknowledged: int = 0
    lifecycle_ambiguous: int = 0
    bootstrap_starts: int = 0
    actions_acknowledged: int = 0
    actions_ambiguous: int = 0
    later_resets_acknowledged: int = 0
    later_resets_ambiguous: int = 0
    conservative_spent_actions: int = 0
    controller_iterations: int = 0
    inference_requests: int = 0
    parser_repairs: int = 0
    workspace_invocations: int = 0
    evidence_retrievals: int = 0


@dataclass(slots=True)
class GameRuntimeState:
    observation: Observation
    counters: LifecycleCounters = field(default_factory=LifecycleCounters)
    quarantined: bool = False
    terminal_reason: str | None = None

    def replace_observation(self, observation: Observation) -> None:
        if observation.guid != self.observation.guid:
            raise ValueError("session guid changed")
        self.observation = observation
