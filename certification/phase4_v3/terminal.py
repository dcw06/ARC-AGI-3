"""v3: stop on acknowledged GAME_OVER; never synthesize frames or reset."""
from agent.competition_loop import (CompetitionAgentLoop, GameState, GameResult,
    PreDispatchFailure, OutcomeUnknown, classify_proposal_rejection)


class TerminalAwareLoop(CompetitionAgentLoop):
    def run(self) -> GameResult:
        reason = "action_cap"
        try:
            while self.state.counters.conservative_spent_actions < self.max_actions:
                if self.watchdog.stop_admission:
                    reason = "global_finalization_reserve"
                    break
                if self.state.observation.state is GameState.GAME_OVER:
                    reason = "game_over"
                    break
                if self.state.observation.state is GameState.WIN:
                    reason = "win"
                    break
                self.state.counters.controller_iterations += 1
                before = self.state.observation
                self._diagnostic(
                    "begin_transition",
                    before,
                    iteration=self.state.counters.controller_iterations,
                )
                try:
                    decision = self.policy.propose(self.state)
                except Exception as exc:
                    self.state.counters.policy_failures += 1
                    self._diagnostic(
                        "note_rejection",
                        classify_proposal_rejection(exc),
                        str(exc),
                    )
                    try:
                        decision = self.fallback.propose(self.state)
                    except Exception:
                        reason = "policy_failure_no_legal_fallback"
                        break
                self._diagnostic("note_decision", decision)
                try:
                    self.state.mark_pending_action(decision.decision_id)
                    observation = self.adapter.dispatch(self.client, decision)
                except PreDispatchFailure:
                    self.state.clear_pending_action()
                    self._diagnostic(
                        "finish_unresolved",
                        phase="pre_transport",
                        category="pre_dispatch_failure",
                    )
                    reason = "pre_dispatch_failure"
                    break
                except OutcomeUnknown:
                    self.state.quarantined = True
                    self.state.counters.actions_ambiguous += 1
                    self.state.counters.conservative_spent_actions += 1
                    self.state.mark_pending_action(decision.decision_id)
                    self._diagnostic(
                        "finish_unresolved",
                        phase="action_dispatch_post_entry",
                        category="outcome_unknown",
                    )
                    reason = "outcome_unknown_quarantine"
                    break
                self.state.counters.actions_acknowledged += 1
                self.state.counters.conservative_spent_actions += 1
                if decision.action_id == 0:
                    self.state.counters.later_resets_acknowledged += 1
                self.state.replace_observation(
                    observation,
                    action_id=decision.action_id,
                    action_data=decision.action_data,
                    transition_id=decision.decision_id,
                )
                if self.state.evidence.transitions:
                    self._diagnostic(
                        "finish_acknowledged",
                        before,
                        observation,
                        self.state.evidence.transitions[-1],
                    )
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
            controller_iterations=self.state.counters.controller_iterations,
            policy_failures=self.state.counters.policy_failures,
            inference_requests=self.state.counters.inference_requests,
            inference_completions=self.state.counters.inference_completions,
            inference_transport_failures=self.state.counters.inference_transport_failures,
            inference_queue_failures=self.state.counters.inference_queue_failures,
            inference_prompt_tokens=self.state.counters.inference_prompt_tokens,
            inference_completion_tokens=self.state.counters.inference_completion_tokens,
            inference_elapsed_seconds=self.state.counters.inference_elapsed_seconds,
            workspace_invocations=self.state.counters.workspace_invocations,
            workspace_elapsed_seconds=self.state.counters.workspace_elapsed_seconds,
            parser_repairs=self.state.counters.parser_repairs,
        )
        return result
