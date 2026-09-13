"""Bounded typed state used by the competition loop.

``FrameData.frame`` is an ordered temporal sequence produced by one engine
action.  It is deliberately named ``frames`` here; treating it as visual
layers would destroy animation evidence and make retention policy ambiguous.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from arcengine import FrameData, FrameDataRaw, GameState

from .evidence import EvidenceStore


def _pack_frames(frames: Any) -> tuple[np.ndarray, ...]:
    packed: list[np.ndarray] = []
    for frame in frames or []:
        source = np.asarray(frame)
        if source.ndim != 2 or not np.issubdtype(source.dtype, np.integer):
            raise ValueError("observation frames must be two-dimensional integer grids")
        if source.size and (int(source.min()) < 0 or int(source.max()) > 255):
            raise ValueError("observation frames must fit uint8 without loss")
        item = np.ascontiguousarray(source, dtype=np.uint8)
        item.setflags(write=False)
        packed.append(item)
    if not packed:
        raise ValueError("observation has no rendered frames")
    return tuple(packed)


@dataclass(frozen=True, slots=True)
class Observation:
    game_id: str
    frames: tuple[np.ndarray, ...]
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
            frames=_pack_frames(getattr(source, "frame", [])),
            state=getattr(source, "state", GameState.NOT_PLAYED),
            levels_completed=int(getattr(source, "levels_completed", 0)),
            win_levels=int(getattr(source, "win_levels", 0)),
            guid=str(guid),
            available_actions=tuple(int(x.value if hasattr(x, "value") else x) for x in getattr(source, "available_actions", [])),
            full_reset=bool(getattr(source, "full_reset", False)),
        )

    @property
    def canonical_hash(self) -> str:
        header = {
            "version": "arc3-observation-v2",
            "game_id": self.game_id,
            "state": str(self.state.value),
            "levels_completed": self.levels_completed,
            "win_levels": self.win_levels,
            "available_actions": list(self.available_actions),
            "dtype": "uint8",
            "byte_order": "not_applicable",
            "order": "C",
            "frames": [list(frame.shape) for frame in self.frames],
        }
        digest = hashlib.sha256(json.dumps(header, sort_keys=True, separators=(",", ":")).encode())
        for frame in self.frames:
            digest.update(b"\0")
            digest.update(frame.tobytes(order="C"))
        return digest.hexdigest()

    @property
    def latest_frame(self) -> np.ndarray:
        return self.frames[-1]


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
    policy_failures: int = 0
    inference_requests: int = 0
    inference_completions: int = 0
    inference_transport_failures: int = 0
    inference_queue_failures: int = 0
    inference_prompt_tokens: int = 0
    inference_completion_tokens: int = 0
    inference_elapsed_seconds: float = 0.0
    parser_repairs: int = 0
    workspace_invocations: int = 0
    workspace_elapsed_seconds: float = 0.0
    evidence_retrievals: int = 0


@dataclass(slots=True)
class GameRuntimeState:
    observation: Observation
    action_budget_limit: int | None = None
    counters: LifecycleCounters = field(default_factory=LifecycleCounters)
    evidence: EvidenceStore = field(default_factory=EvidenceStore)
    # Write-only observational side channel. Representation builders do not
    # read it, so diagnostic capture cannot enter the model's policy context.
    diagnostics: Any | None = None
    quarantined: bool = False
    terminal_reason: str | None = None

    def __post_init__(self) -> None:
        self.evidence.capture_t0(self.observation, budgets=self._live_budgets())

    def _live_budgets(self) -> Mapping[str, int]:
        if self.action_budget_limit is None:
            return {}
        return {
            "action_limit": self.action_budget_limit,
            "conservative_spent_actions": self.counters.conservative_spent_actions,
            "actions_remaining": max(
                0, self.action_budget_limit - self.counters.conservative_spent_actions
            ),
        }

    def mark_pending_action(self, transition_id: str) -> None:
        self.evidence.capture_t0(
            self.observation,
            budgets=self._live_budgets(),
            pending_action_reference=transition_id,
        )

    def clear_pending_action(self) -> None:
        self.evidence.capture_t0(self.observation, budgets=self._live_budgets())

    def replace_observation(
        self,
        observation: Observation,
        *,
        action_id: int | None = None,
        action_data: Mapping[str, Any] | None = None,
        transition_id: str | None = None,
    ) -> None:
        if observation.guid != self.observation.guid:
            raise ValueError("session guid changed")
        previous = self.observation
        if action_id is None:
            self.evidence.capture_t0(observation, budgets=self._live_budgets())
        else:
            self.evidence.record_transition(
                previous,
                observation,
                action_id=action_id,
                action_data=action_data,
                transition_id=transition_id,
                budgets=self._live_budgets(),
            )
        self.observation = observation
