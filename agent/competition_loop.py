"""Bounded per-game loop and all-game competition orchestration."""

from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Protocol

from arcengine import GameState

from .action import ActionDecision
from .controller import DeterministicFallback
from .framework_adapter import FinalizationUnknown, OutcomeUnknown, PreDispatchFailure
from .state import GameRuntimeState
from .watchdog import DeadlineWatchdog


class Policy(Protocol):
    def propose(self, state: GameRuntimeState) -> ActionDecision: ...


@dataclass(frozen=True, slots=True)
class GameResult:
    game_id: str
    status: str
    levels_completed: int
    acknowledged_actions: int
    ambiguous_actions: int
    terminal_reason: str


class CompetitionAgentLoop:
    """Owns one client lifecycle without retaining an unbounded frame list."""

    def __init__(
        self,
        adapter: Any,
        client: Any,
        *,
        policy: Policy | None = None,
        max_actions: int = 80,
        watchdog: DeadlineWatchdog | None = None,
    ) -> None:
        if max_actions < 1:
            raise ValueError("max_actions must be positive")
        self.adapter = adapter
        self.client = client
        self.policy = policy or DeterministicFallback()
        self.max_actions = max_actions
        self.watchdog = watchdog or DeadlineWatchdog(32_400, 600)
        self.state = GameRuntimeState(client.observation)
        self.state.counters.lifecycle_attempted = 1
        self.state.counters.lifecycle_acknowledged = 1
        self.state.counters.bootstrap_starts = 1

    def run(self) -> GameResult:
        reason = "action_cap"
        try:
            while self.state.counters.conservative_spent_actions < self.max_actions:
                if self.watchdog.stop_admission:
                    reason = "global_finalization_reserve"
                    break
                if self.state.observation.state is GameState.WIN:
                    reason = "win"
                    break
                self.state.counters.controller_iterations += 1
                try:
                    decision = self.policy.propose(self.state)
                except Exception:
                    try:
                        decision = DeterministicFallback().propose(self.state)
                    except Exception:
                        reason = "policy_failure_no_legal_fallback"
                        break
                try:
                    observation = self.adapter.dispatch(self.client, decision)
                except PreDispatchFailure:
                    reason = "pre_dispatch_failure"
                    break
                except OutcomeUnknown:
                    self.state.quarantined = True
                    self.state.counters.actions_ambiguous += 1
                    self.state.counters.conservative_spent_actions += 1
                    reason = "outcome_unknown_quarantine"
                    break
                self.state.counters.actions_acknowledged += 1
                self.state.counters.conservative_spent_actions += 1
                if decision.action_id == 0:
                    self.state.counters.later_resets_acknowledged += 1
                self.state.replace_observation(observation)
        finally:
            finalize = getattr(self.adapter, "finalize_client", None)
            if finalize is not None:
                finalize(self.client)

        self.state.terminal_reason = reason
        result = GameResult(
            game_id=self.client.game_id,
            status="quarantined" if self.state.quarantined else "complete",
            levels_completed=self.state.observation.levels_completed,
            acknowledged_actions=self.state.counters.actions_acknowledged,
            ambiguous_actions=self.state.counters.actions_ambiguous,
            terminal_reason=reason,
        )
        return result


@dataclass(frozen=True, slots=True)
class CompetitionRunResult:
    results: tuple[GameResult, ...]
    finalization_status: str
    scorecard: dict[str, Any] | None


class CompetitionOrchestrator:
    """One scorecard, at most one bootstrap per game, streaming worker start."""

    def __init__(
        self,
        adapter: Any,
        game_ids: list[str] | tuple[str, ...],
        *,
        max_workers: int = 8,
        max_actions: int = 80,
        watchdog: DeadlineWatchdog | None = None,
        hung_worker_grace_seconds: float = 15.0,
    ) -> None:
        if len(set(game_ids)) != len(game_ids):
            raise ValueError("game inventory contains duplicates")
        self.adapter = adapter
        self.game_ids = tuple(game_ids)
        self.max_workers = max(1, max_workers)
        self.max_actions = max_actions
        self.watchdog = watchdog or DeadlineWatchdog(32_400, 600)
        self.hung_worker_grace_seconds = max(0.0, hung_worker_grace_seconds)

    def run(self) -> CompetitionRunResult:
        self.watchdog.start_supervisor()
        results: dict[str, GameResult] = {}
        try:
            self.adapter.open_scorecard(tags=["plan8-e0"])
        except OutcomeUnknown:
            self.watchdog.stop_supervisor()
            return CompetitionRunResult(
                tuple(self._untouched(game_id, "scorecard_open_unknown") for game_id in self.game_ids),
                "open_unknown",
                None,
            )

        futures: dict[Future[GameResult], str] = {}
        executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="arc3-client")
        try:
            for game_id in self.game_ids:
                if self.watchdog.stop_admission:
                    results[game_id] = self._untouched(game_id, "global_finalization_reserve")
                    continue
                try:
                    client = self.adapter.bootstrap(game_id)
                except (OutcomeUnknown, PreDispatchFailure):
                    results[game_id] = self._untouched(game_id, "bootstrap_failed_or_unknown")
                    continue
                loop = CompetitionAgentLoop(
                    self.adapter,
                    client,
                    max_actions=self.max_actions,
                    watchdog=self.watchdog,
                )
                futures[executor.submit(loop.run)] = game_id
            pending = set(futures)
            while pending and not self.watchdog.stop_admission:
                until_stop = max(
                    0.0,
                    self.watchdog.hard_seconds
                    - self.watchdog.finalization_reserve_seconds
                    - self.watchdog.elapsed,
                )
                completed, pending = wait(
                    pending,
                    timeout=min(0.25, until_stop),
                    return_when=FIRST_COMPLETED,
                )
                for future in completed:
                    game_id = futures[future]
                    try:
                        results[game_id] = future.result()
                    except Exception:
                        results[game_id] = self._untouched(game_id, "contained_worker_failure")

            if pending:
                self.watchdog.cancel()
                completed, pending = wait(pending, timeout=self.hung_worker_grace_seconds)
                for future in completed:
                    game_id = futures[future]
                    try:
                        results[game_id] = future.result()
                    except Exception:
                        results[game_id] = self._untouched(game_id, "contained_worker_failure")
                for future in pending:
                    future.cancel()
                    results[futures[future]] = self._untouched(futures[future], "hung_worker_quarantined")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        scorecard: dict[str, Any] | None = None
        finalization_status = "acknowledged"
        try:
            scorecard = self.adapter.close_scorecard()
        except FinalizationUnknown:
            finalization_status = "finalization_unknown"
        except PreDispatchFailure:
            finalization_status = "close_not_dispatched"
        ordered = tuple(results.get(game_id, self._untouched(game_id, "not_attempted")) for game_id in self.game_ids)
        self.watchdog.stop_supervisor()
        return CompetitionRunResult(ordered, finalization_status, scorecard)

    @staticmethod
    def _untouched(game_id: str, reason: str) -> GameResult:
        return GameResult(game_id, "untouched", 0, 0, 0, reason)
