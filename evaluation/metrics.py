"""Typed local replica of documented RHAE arithmetic.

Human baselines are accepted only by this evaluator module. The agent package
does not import this module and cannot access evaluator inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class NormalizedRHAE:
    value: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or not (0.0 <= self.value <= 1.15):
            raise ValueError("NormalizedRHAE must be finite and in [0, 1.15]")

    def as_official_percent(self) -> "OfficialRHAEPercent":
        return OfficialRHAEPercent(100.0 * self.value)


@dataclass(frozen=True, slots=True)
class OfficialRHAEPercent:
    value: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or not (0.0 <= self.value <= 115.0):
            raise ValueError("OfficialRHAEPercent must be finite and in [0, 115]")

    def as_normalized(self) -> NormalizedRHAE:
        return NormalizedRHAE(self.value / 100.0)


def normalized_level_rhae(human_baseline_actions: int, agent_actions: int) -> NormalizedRHAE:
    if human_baseline_actions <= 0 or agent_actions <= 0:
        raise ValueError("action counts must be positive")
    return NormalizedRHAE(min(1.15, (human_baseline_actions / agent_actions) ** 2))


def normalized_game_rhae(
    human_baseline_actions: Sequence[int],
    agent_actions: Sequence[int | None],
) -> NormalizedRHAE:
    if len(human_baseline_actions) != len(agent_actions) or not human_baseline_actions:
        raise ValueError("baseline and agent arrays must have the same non-zero length")
    denominator = sum(range(1, len(human_baseline_actions) + 1))
    weighted_score = 0.0
    completed_weight = 0
    for level_index, (baseline, actions) in enumerate(zip(human_baseline_actions, agent_actions), start=1):
        if actions is None:
            continue
        weighted_score += level_index * normalized_level_rhae(baseline, actions).value
        completed_weight += level_index
    raw = weighted_score / denominator
    completion_cap = completed_weight / denominator
    return NormalizedRHAE(min(1.0, raw, completion_cap))


def normalized_total_rhae(games: Sequence[NormalizedRHAE]) -> NormalizedRHAE:
    if not games:
        raise ValueError("at least one game is required")
    if any(game.value > 1.0 for game in games):
        raise ValueError("game scores cannot exceed 1.0")
    return NormalizedRHAE(sum(game.value for game in games) / len(games))
