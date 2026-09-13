from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping
from unittest.mock import patch

from arcengine import GameState
from jsonschema import Draft202012Validator

from agent.competition_loop import CompetitionAgentLoop
from agent.diagnostics import (
    DiagnosticReplayError,
    TransitionDiagnosticRecorder,
    grouped_failure_report,
    replay_bundle,
)
from agent.e1_policy import CompletionResult, E1ModelBinding, E1Policy
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import OutcomeUnknown
from agent.scheduler import QueuedInferenceExecutor
from agent.safe_operations import SafeOperationError
from agent.state import GameRuntimeState, Observation


ROOT = Path(__file__).resolve().parents[1]


def observation() -> Observation:
    return Observation.from_value(
        {
            "game_id": "ar25-0c556536",
            "frame": [[[0, 2, 0], [0, 0, 0]]],
            "state": "NOT_FINISHED",
            "levels_completed": 0,
            "win_levels": 2,
            "guid": "diagnostic-fixture-guid",
            "full_reset": False,
            "available_actions": [1],
        }
    )


class CompletionClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.requests: list[Mapping[str, Any]] = []

    def complete(self, request: Mapping[str, Any]) -> CompletionResult:
        self.requests.append(copy.deepcopy(request))
        return CompletionResult(self.responses.pop(0), prompt_tokens=10, completion_tokens=5)


class LoopClient:
    def __init__(self) -> None:
        self.game_id = "ar25-0c556536"
        self.observation = observation()
        self.actions: list[tuple[int, tuple[tuple[str, Any], ...]]] = []


class NoChangeAdapter:
    def dispatch(self, client: LoopClient, decision: Any) -> Observation:
        client.actions.append((decision.action_id, tuple(sorted(decision.action_data.items()))))
        client.observation = observation()
        return client.observation


class UnknownAdapter(NoChangeAdapter):
    def dispatch(self, client: LoopClient, decision: Any) -> Observation:
        client.actions.append((decision.action_id, tuple(sorted(decision.action_data.items()))))
        raise OutcomeUnknown("fixture entered transport")


class Phase2DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifests = load_e1_feature_manifests(ROOT / "config/e1_feature_manifests.yaml")
        cls.binding = E1ModelBinding(
            candidate_id="M0-Q3VL-30B-A3B-FP8",
            model_id="Qwen/Qwen3-VL-30B-A3B-Instruct-FP8",
            revision="d9748a51ae66354c4dad665aab2c71f26cf2c8cd",
            engine="vllm==0.19.0",
            reasoning_setting="instruct_non_thinking",
        )

    def _policy(self, responses: list[str], service: QueuedInferenceExecutor) -> tuple[E1Policy, CompletionClient]:
        client = CompletionClient(responses)
        return (
            E1Policy(
                manifest=self.manifests["E1S-R"],
                binding=self.binding,
                client=client,
                inference=service,
            ),
            client,
        )

    def _malformed_bundle(self, actions: int = 2) -> tuple[dict[str, Any], list[Any], list[Any]]:
        loop_client = LoopClient()
        recorder = TransitionDiagnosticRecorder(
            game_id=loop_client.game_id,
            treatment_id="E1S-R",
            seed=104729,
            run_id="phase1-failure-replay-fixture",
        )
        with QueuedInferenceExecutor(worker_count=1) as service:
            policy, completion = self._policy(["not-json"] * actions, service)
            result = CompetitionAgentLoop(
                NoChangeAdapter(),
                loop_client,
                policy=policy,
                max_actions=actions,
                diagnostics=recorder,
            ).run()
        self.assertEqual(result.policy_failures, actions)
        return recorder.bundle(), loop_client.actions, completion.requests

    def test_malformed_phase1_proposal_replays_from_exact_retained_frames(self) -> None:
        bundle, actions, _requests = self._malformed_bundle()
        records = bundle["records"]
        self.assertEqual(actions, [(1, ()), (1, ())])
        self.assertEqual([item["proposal_rejection_category"] for item in records], ["malformed_json"] * 2)
        self.assertTrue(all(item["proposal_or_fallback"]["model_proposals"][0]["content"] == "not-json" for item in records))
        self.assertTrue(all(item["proposal_or_fallback"]["executed_decision"]["source"] == "deterministic_fallback" for item in records))
        self.assertEqual([item["repeated_action_count"] for item in records], [0, 1])
        self.assertEqual([item["repeated_state_count"] for item in records], [0, 1])
        self.assertTrue(all(item["transition"]["no_change"] for item in records))
        self.assertTrue(all(item["transition"]["changed_cells"] == 0 for item in records))
        self.assertTrue(all(item["action_legal"] for item in records))
        self.assertTrue(all(not item["measurable_progress"] for item in records))
        self.assertTrue(all(item["evidence_availability"]["T3"] == "exact" for item in records))
        replay = replay_bundle(bundle)
        self.assertEqual(replay["status"], "reproduced")
        self.assertEqual(replay["reproduced_failures"], 2)

    def test_bundle_conforms_to_closed_schema(self) -> None:
        bundle, _actions, _requests = self._malformed_bundle(1)
        schema = json.loads((ROOT / "config/phase2_diagnostic_schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(bundle)

    def test_diagnostics_do_not_change_policy_requests_or_actions(self) -> None:
        plain_client = LoopClient()
        observed_client = LoopClient()
        recorder = TransitionDiagnosticRecorder(
            game_id=observed_client.game_id,
            treatment_id="E1S-R",
            seed=104729,
        )
        with QueuedInferenceExecutor(worker_count=1) as service:
            plain_policy, plain_completion = self._policy(
                ['{"action":{"action_id":1,"action_data":{}}}'], service
            )
            CompetitionAgentLoop(
                NoChangeAdapter(), plain_client, policy=plain_policy, max_actions=1
            ).run()
        with QueuedInferenceExecutor(worker_count=1) as service:
            observed_policy, observed_completion = self._policy(
                ['{"action":{"action_id":1,"action_data":{}}}'], service
            )
            CompetitionAgentLoop(
                NoChangeAdapter(),
                observed_client,
                policy=observed_policy,
                max_actions=1,
                diagnostics=recorder,
            ).run()
        self.assertEqual(plain_client.actions, observed_client.actions)
        self.assertEqual(plain_completion.requests, observed_completion.requests)
        model_visible = json.dumps(observed_completion.requests, sort_keys=True)
        self.assertNotIn(observed_client.game_id, model_visible)
        self.assertNotIn("diagnostic", model_visible)

    def test_recorder_failure_is_contained_and_does_not_change_legal_play(self) -> None:
        class BrokenRecorder:
            def __getattr__(self, _name: str) -> Any:
                raise RuntimeError("diagnostic sink unavailable")

        client = LoopClient()
        result = CompetitionAgentLoop(
            NoChangeAdapter(), client, max_actions=1, diagnostics=BrokenRecorder()  # type: ignore[arg-type]
        ).run()
        self.assertEqual(result.acknowledged_actions, 1)
        self.assertEqual(client.actions, [(1, ())])

    def test_outcome_unknown_phase_is_explicit(self) -> None:
        client = LoopClient()
        recorder = TransitionDiagnosticRecorder(
            game_id=client.game_id,
            treatment_id="E1S-R",
            seed=104729,
        )
        result = CompetitionAgentLoop(
            UnknownAdapter(), client, max_actions=1, diagnostics=recorder
        ).run()
        self.assertEqual(result.terminal_reason, "outcome_unknown_quarantine")
        record = recorder.bundle()["records"][0]
        self.assertEqual(record["outcome_unknown_phase"], "action_dispatch_post_entry")
        self.assertEqual(record["dispatch_status"], "outcome_unknown")
        self.assertIsNone(record["post"])
        self.assertEqual(record["evidence_availability"]["T1"], "not_observed")

    def test_workspace_operations_and_exhaustion_are_captured(self) -> None:
        class BoundedWorkspace:
            def __init__(self, _arrays: Any, *, limits: Any) -> None:
                self.limits = SimpleNamespace(invocations_per_proposal=limits.invocations_per_proposal)
                self.invocations = 0

            def invoke(self, _operation: str, _arguments: Mapping[str, Any]) -> Any:
                if self.invocations >= self.limits.invocations_per_proposal:
                    raise SafeOperationError("safe-operation invocation budget exhausted")
                self.invocations += 1
                return [2, 3]

        operation = '{"operation":"array_shape","arguments":{"array":"current"}}'
        completion = CompletionClient([operation] * 8)
        client = LoopClient()
        recorder = TransitionDiagnosticRecorder(
            game_id=client.game_id,
            treatment_id="E1C-R",
            seed=104729,
        )
        with QueuedInferenceExecutor(worker_count=1) as service:
            policy = E1Policy(
                manifest=self.manifests["E1C-R"],
                binding=self.binding,
                client=completion,
                inference=service,
            )
            with patch("agent.e1_policy.SafeOperationWorkspace", BoundedWorkspace):
                result = CompetitionAgentLoop(
                    NoChangeAdapter(),
                    client,
                    policy=policy,
                    max_actions=1,
                    diagnostics=recorder,
                ).run()
        self.assertEqual(result.policy_failures, 1)
        record = recorder.bundle()["records"][0]
        self.assertEqual(record["proposal_rejection_category"], "workspace_exhausted")
        self.assertEqual(record["workspace"]["invocations"], 8)
        self.assertTrue(record["workspace"]["exhausted"])
        self.assertTrue(all(item["succeeded"] for item in record["workspace"]["operations"][:7]))
        self.assertFalse(record["workspace"]["operations"][7]["succeeded"])

    def test_report_groups_by_game_treatment_and_failure_category(self) -> None:
        bundle, _actions, _requests = self._malformed_bundle(2)
        report = grouped_failure_report([bundle])
        self.assertEqual(
            report["groups"],
            [{
                "game_id": "ar25-0c556536",
                "treatment_id": "E1S-R",
                "category": "malformed_json",
                "count": 2,
            }],
        )
        self.assertEqual(report["policy_visibility"], "local_report_only_never_model_input")

    def test_local_replay_cli_and_tamper_detection(self) -> None:
        bundle, _actions, _requests = self._malformed_bundle(1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            path.write_text(json.dumps(bundle))
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/replay_phase2_diagnostics.py"),
                    str(path),
                    "--require-failure",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PHASE2_DIAGNOSTIC_REPLAY_PASSED", result.stdout)
        damaged = copy.deepcopy(bundle)
        damaged["records"][0]["transition"]["changed_cells"] = 1
        with self.assertRaisesRegex(DiagnosticReplayError, "bundle hash mismatch"):
            replay_bundle(damaged)

    def test_historical_exit_gate_is_not_retroactively_overclaimed(self) -> None:
        capture = json.loads((ROOT / "config/phase2_diagnostic_capture.yaml").read_text())
        self.assertEqual(capture["status"], "capture_and_replay_implemented_historical_exit_pending")
        self.assertFalse(capture["exit_gate"]["historical_phase1_transition_reproduced"])
        phase2 = json.loads((ROOT / "config/phase2_contract.yaml").read_text())
        self.assertTrue(
            all(
                item["status"] == "inactive_pending_reproduced_failure_admission"
                for item in phase2["registered_treatments"].values()
            )
        )


if __name__ == "__main__":
    unittest.main()
