"""Compatibility registration for the upstream development framework.

Kaggle production uses ``agent.production_main`` and the Plan 8 adapter. This
class remains intentionally small for upstream smoke tests; it owns no game
mechanics, mutable action payload, or production lifecycle behavior.
"""
from __future__ import annotations

from typing import Any

from arcengine import FrameData, GameAction, GameState
from agents.agent import Agent


class MyAgent(Agent):
    """Deterministic compatibility policy; not the production loop."""

    # Upper bound on actions per game; the framework also enforces global limits.
    MAX_ACTIONS = 80

    @property
    def name(self) -> str:
        return f"{super().name}.{self.MAX_ACTIONS}"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return GameAction.RESET
        legal = [GameAction.from_id(value) for value in latest_frame.available_actions]
        # ACTION6 needs a request-local payload, which the upstream interface
        # cannot provide safely. The compatibility policy leaves it to the
        # production adapter and selects the first legal simple action here.
        simple = [action for action in legal if not action.is_complex() and action is not GameAction.RESET]
        return simple[0] if simple else GameAction.RESET
