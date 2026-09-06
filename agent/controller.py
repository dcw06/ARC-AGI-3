"""Deterministic legal fallback controller for Phase 0."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from arcengine import GameAction, GameState

from .action import ActionDecision, DisplayPoint, normalize_legal_actions
from .state import GameRuntimeState


@dataclass(slots=True)
class DeterministicFallback:
    stable_seed: str = "arc3-e0-v1"
    _rng_by_session: dict[str, random.Random] = field(default_factory=dict, init=False)
    _click_index_by_session: dict[str, int] = field(default_factory=dict, init=False)
    _decision_index_by_session: dict[str, int] = field(default_factory=dict, init=False)

    def _rng(self, guid: str) -> random.Random:
        if guid not in self._rng_by_session:
            # The GUID is only an isolation key. It does not influence policy.
            seed_bytes = hashlib.sha256(self.stable_seed.encode()).digest()
            self._rng_by_session[guid] = random.Random(int.from_bytes(seed_bytes[:8], "big"))
        return self._rng_by_session[guid]

    def propose(self, state: GameRuntimeState) -> ActionDecision:
        obs = state.observation
        decision_index = self._decision_index_by_session.get(obs.guid, 0)
        self._decision_index_by_session[obs.guid] = decision_index + 1
        decision_id = f"fallback:{decision_index}"
        legal = normalize_legal_actions(obs.available_actions)
        if not legal:
            raise RuntimeError("environment exposed no legal actions")
        if obs.state is GameState.GAME_OVER and GameAction.RESET.value in legal:
            return ActionDecision.simple(GameAction.RESET, controller_mode="recovery", decision_id=decision_id)

        non_reset = sorted(value for value in legal if value != GameAction.RESET.value)
        candidates = non_reset or sorted(legal)
        chosen = self._rng(obs.guid).choice(candidates)
        if chosen == GameAction.ACTION6.value:
            # Deterministic low-discrepancy traversal of the 64x64 display.
            index = self._click_index_by_session.get(obs.guid, 0)
            self._click_index_by_session[obs.guid] = index + 1
            point = DisplayPoint(x=(index * 37) % 64, y=(index * 23) % 64)
            return ActionDecision.click(point, controller_mode="explore", decision_id=decision_id)
        return ActionDecision.simple(chosen, controller_mode="explore", decision_id=decision_id)
