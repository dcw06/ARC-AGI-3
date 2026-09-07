"""Keep local safety bounds separate from authoritative scorer totals."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocalActionBounds:
    acknowledged_actions: int
    ambiguous_actions: int
    acknowledged_resets: int
    ambiguous_resets: int

    @property
    def minimum_actions(self) -> int:
        return self.acknowledged_actions

    @property
    def maximum_actions(self) -> int:
        return self.acknowledged_actions + self.ambiguous_actions

    @property
    def minimum_resets(self) -> int:
        return self.acknowledged_resets

    @property
    def maximum_resets(self) -> int:
        return self.acknowledged_resets + self.ambiguous_resets


@dataclass(frozen=True, slots=True)
class AuthoritativeCounters:
    actions: int
    resets: int


@dataclass(frozen=True, slots=True)
class CounterReconciliation:
    local: LocalActionBounds
    authoritative: AuthoritativeCounters
    actions_within_local_bounds: bool
    resets_within_local_bounds: bool


def reconcile(local: LocalActionBounds, authoritative: AuthoritativeCounters) -> CounterReconciliation:
    return CounterReconciliation(
        local=local,
        authoritative=authoritative,
        actions_within_local_bounds=local.minimum_actions <= authoritative.actions <= local.maximum_actions,
        resets_within_local_bounds=local.minimum_resets <= authoritative.resets <= local.maximum_resets,
    )
