from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch

import numpy as np
import requests

from arcengine import GameAction

from agent.e1_policy import (
    CompletionResult,
    E1ModelBinding,
    E1Policy,
    OpenAICompatibleCompletionClient,
)
from agent.feature_manifest import (
    FeatureManifestError,
    load_e1_feature_manifests,
    validate_e1_proposal,
)
from agent.safe_operations import (
    SafeOperationError,
    SafeOperationLimits,
    SafeOperationWorkspace,
    execute_safe_operation,
)
from agent.production_policy import ModelService, load_operational_primary
from agent.scheduler import QueuedInferenceExecutor
from agent.state import GameRuntimeState, Observation
from evaluation.phase1 import causal_four_cell_analysis, cross_validated_selection, paired_inference
from evaluation.e1_experiment import (
    analysis_payload,
    exact_score_map,
    frozen_feature_registry_sha256,
    frozen_protocol_sha256,
    validate_experiment_record,
)
from evaluation.e1_profile import E1_CELLS, build_e1_workload_fixtures, capacity_projection
from evaluation.e1_whole_run import analyze_blocks, block_contrasts, validate_whole_run_record
from scripts.build_e1_profile_notebook import (
    build as build_e1_profile_notebook,
    bundled_sources as e1_profile_bundled_sources,
)
from scripts.build_notebook import build as build_submission_notebook, bundled_sources as submission_bundled_sources
from scripts.build_e1_four_cell_notebook import (
    build as build_e1_four_cell_notebook,
    bundled_sources as e1_four_cell_bundled_sources,
)
from scripts.profile_e1_openai import _protocol_kind


ROOT = Path(__file__).resolve().parents[1]


def observation(*, game_id: str = "secret-game") -> Observation:
    return Observation.from_value(
        {
            "game_id": game_id,
            "frame": [[[0, 2, 0], [0, 0, 0]]],
            "state": "NOT_FINISHED",
            "levels_completed": 0,
            "win_levels": 2,
            "guid": "secret-guid",
            "full_reset": False,
            "available_actions": [1, 6],
        }
    )


class ScriptedClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.requests: list[Mapping[str, Any]] = []

    def complete(self, request: Mapping[str, Any]) -> CompletionResult:
        self.requests.append(request)
        return CompletionResult(self.responses.pop(0), prompt_tokens=10, completion_tokens=5)


class TransportFailingClient:
    def complete(self, _request: Mapping[str, Any]) -> CompletionResult:
        raise requests.ConnectionError("transport unavailable")


class E1FeatureManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifests = load_e1_feature_manifests(
            ROOT / "config/e1_feature_manifests.yaml"
        )

    def test_four_cells_differ_only_on_registered_factors(self) -> None:
        self.assertEqual(set(self.manifests), {"E1S-R", "E1S-F", "E1C-R", "E1C-F"})
        shared = {
            (
                item.proposal_action_count,
                item.context_mode,
                item.recent_transition_limit,
                item.intent_max_bytes,
                item.rationale_max_bytes,
                item.scheduler,
                item.prompt_revision,
                item.workspace_invocation_limit,
            )
            for item in self.manifests.values()
        }
        self.assertEqual(len(shared), 1)
        self.assertTrue(
            all(
                item.context_mode
                == "stateless_reconstruction_visible_compaction_v1"
                and item.recent_transition_limit == 1
                and item.history_loss_reporting
                == "lifetime_count_and_rolling_sha256_v1"
                for item in self.manifests.values()
            )
        )
        self.assertEqual(self.manifests["E1S-R"].observation_bundle, "R")
        self.assertEqual(self.manifests["E1C-F"].workspace, "safe_operations_v1")
        self.assertEqual(self.manifests["E1C-F"].workspace_invocation_limit, 7)

    def test_strict_single_action_proposal(self) -> None:
        decision = validate_e1_proposal(
            {
                "intent": "inspect",
                "rationale": "move",
                "action": {"action_id": 1, "action_data": {}},
            },
            manifest=self.manifests["E1S-R"],
            legal_actions=[1, 6],
        )
        self.assertEqual(decision.action_id, 1)
        self.assertEqual(decision.source, "model:E1S-R")

    def test_click_is_typed_and_bounded(self) -> None:
        decision = validate_e1_proposal(
            {"action": {"action_id": 6, "action_data": {"x": 12, "y": 34}}},
            manifest=self.manifests["E1C-F"],
            legal_actions=[GameAction.ACTION6],
        )
        self.assertEqual(dict(decision.action_data), {"x": 12, "y": 34})
        with self.assertRaises(FeatureManifestError):
            validate_e1_proposal(
                {"action": {"action_id": 6, "action_data": {"x": 64, "y": 0}}},
                manifest=self.manifests["E1C-F"],
                legal_actions=[6],
            )

    def test_later_treatment_fields_are_rejected(self) -> None:
        base = {"action": {"action_id": 1, "action_data": {}}}
        for forbidden in (
            "queue",
            "memory",
            "retrieval",
            "hypotheses",
            "predictions",
            "python",
        ):
            with self.subTest(forbidden=forbidden), self.assertRaisesRegex(
                FeatureManifestError, "disabled or unknown"
            ):
                validate_e1_proposal(
                    {**base, forbidden: []},
                    manifest=self.manifests["E1S-F"],
                    legal_actions=[1],
                )

    def test_illegal_reset_and_oversized_text_are_rejected(self) -> None:
        with self.assertRaises(FeatureManifestError):
            validate_e1_proposal(
                {"action": {"action_id": 0, "action_data": {}}},
                manifest=self.manifests["E1S-R"],
                legal_actions=[0, 1],
            )
        with self.assertRaisesRegex(FeatureManifestError, "byte limit"):
            validate_e1_proposal(
                {
                    "rationale": "界" * 2000,
                    "action": {"action_id": 1, "action_data": {}},
                },
                manifest=self.manifests["E1S-R"],
                legal_actions=[1],
            )


class SafeOperationTests(unittest.TestCase):
    def test_registered_operations_are_deterministic(self) -> None:
        arrays = {
            "before": [[0, 2, 0], [0, 0, 0]],
            "after": [[0, 0, 2], [0, 0, 0]],
            "current": [[0, 0, 2], [0, 0, 0]],
        }
        self.assertEqual(
            execute_safe_operation("array_shape", arrays, {}),
            [2, 3],
        )
        self.assertEqual(
            execute_safe_operation("change_bounding_box", arrays, {}),
            [0, 1, 0, 2],
        )
        self.assertIn(
            {"color": 2, "size": 1, "row_delta": 0, "column_delta": 1},
            execute_safe_operation("translation_candidates", arrays, {}),
        )
        components = execute_safe_operation(
            "connected_components", arrays, {"array": "current"}
        )
        self.assertTrue(any(item["color"] == 2 for item in components))

    def test_workspace_is_spawn_isolated_bounded_and_input_immutable(self) -> None:
        source = np.array([[0, 1], [1, 0]], dtype=np.uint8)
        workspace = SafeOperationWorkspace(
            {"current": source},
            limits=SafeOperationLimits(invocations_per_proposal=2),
        )
        source[0, 0] = 9
        self.assertEqual(workspace.invoke("cell_value", {"row": 0, "column": 0}), 0)
        self.assertEqual(workspace.invoke("palette", {}), {"0": 2, "1": 2})
        with self.assertRaisesRegex(SafeOperationError, "budget exhausted"):
            workspace.invoke("array_shape", {})

    def test_workspace_denies_unknown_authority_and_bad_coordinates(self) -> None:
        arrays = {"current": [[0]]}
        with self.assertRaises(SafeOperationError):
            execute_safe_operation("python", arrays, {})
        with self.assertRaises(SafeOperationError):
            execute_safe_operation("cell_value", arrays, {"row": 1, "column": 0})
        with self.assertRaises(SafeOperationError):
            execute_safe_operation("array_shape", arrays, {"array": "not_visible"})


class E1PolicyTests(unittest.TestCase):
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

    def policy(self, cell: str, client: ScriptedClient, service: QueuedInferenceExecutor) -> E1Policy:
        return E1Policy(
            manifest=self.manifests[cell],
            binding=self.binding,
            client=client,
            inference=service,
        )

    def test_openai_client_normalizes_exact_v1_prefix_once(self) -> None:
        self.assertEqual(
            OpenAICompatibleCompletionClient("http://127.0.0.1:8000/v1").base_url,
            "http://127.0.0.1:8000",
        )
        self.assertEqual(
            OpenAICompatibleCompletionClient("http://127.0.0.1:8000").base_url,
            "http://127.0.0.1:8000",
        )

    def test_e1s_r_is_stateless_identity_free_and_has_no_f_features(self) -> None:
        client = ScriptedClient(
            ['{"intent":"move","action":{"action_id":1,"action_data":{}}}']
        )
        state = GameRuntimeState(observation())
        state.counters.controller_iterations = 1
        with QueuedInferenceExecutor(worker_count=1) as service:
            decision = self.policy("E1S-R", client, service).propose(state)
        visible = str(client.requests[0]["messages"])
        self.assertEqual(decision.action_id, 1)
        self.assertNotIn("secret-game", visible)
        self.assertNotIn("secret-guid", visible)
        self.assertNotIn('"features"', visible)
        self.assertEqual(
            client.requests[0]["chat_template_kwargs"], {"enable_thinking": False}
        )
        self.assertEqual(state.counters.inference_requests, 1)
        self.assertEqual(state.counters.inference_completions, 1)
        self.assertEqual(state.counters.workspace_invocations, 0)

    def test_e1s_f_exposes_only_the_registered_feature_bundle(self) -> None:
        client = ScriptedClient(['{"action":{"action_id":1,"action_data":{}}}'])
        state = GameRuntimeState(observation())
        state.counters.controller_iterations = 1
        with QueuedInferenceExecutor(worker_count=1) as service:
            self.policy("E1S-F", client, service).propose(state)
        visible = str(client.requests[0]["messages"])
        self.assertIn('"features"', visible)
        self.assertNotIn("secret-game", visible)

    def test_e1c_charges_tool_and_model_calls_then_returns_one_action(self) -> None:
        client = ScriptedClient(
            [
                '{"operation":"palette","arguments":{"array":"current"}}',
                '{"rationale":"observed","action":{"action_id":6,"action_data":{"x":63,"y":0}}}',
            ]
        )
        state = GameRuntimeState(observation())
        state.counters.controller_iterations = 1
        with QueuedInferenceExecutor(worker_count=1) as service:
            decision = self.policy("E1C-R", client, service).propose(state)
        self.assertEqual(decision.action_id, 6)
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(state.counters.inference_requests, 2)
        self.assertEqual(state.counters.inference_prompt_tokens, 20)
        self.assertEqual(state.counters.inference_completion_tokens, 10)
        self.assertEqual(state.counters.workspace_invocations, 1)
        self.assertGreater(state.counters.workspace_elapsed_seconds, 0)
        follow_up = str(client.requests[1]["messages"])
        self.assertIn("operation_result", follow_up)
        self.assertIn('"2":1', follow_up)

    def test_e1s_rejects_tool_requests_and_illegal_actions(self) -> None:
        for response in (
            '{"operation":"palette","arguments":{}}',
            '{"action":{"action_id":2,"action_data":{}}}',
        ):
            with self.subTest(response=response):
                client = ScriptedClient([response])
                state = GameRuntimeState(observation())
                state.counters.controller_iterations = 1
                with QueuedInferenceExecutor(worker_count=1) as service:
                    with self.assertRaises(FeatureManifestError):
                        self.policy("E1S-R", client, service).propose(state)

    def test_queue_propagates_callback_failure_without_hanging(self) -> None:
        with QueuedInferenceExecutor(worker_count=1) as service:
            with self.assertRaisesRegex(RuntimeError, "model failed"):
                service.execute(
                    client_id="client",
                    generation=1,
                    state_hash="hash",
                    callback=lambda: (_ for _ in ()).throw(RuntimeError("model failed")),
                    timeout_seconds=1,
                )

    def test_transport_failures_are_charged_and_classified(self) -> None:
        state = GameRuntimeState(observation())
        state.counters.controller_iterations = 1
        with QueuedInferenceExecutor(worker_count=1) as service:
            with self.assertRaises(requests.ConnectionError):
                self.policy("E1S-R", TransportFailingClient(), service).propose(state)
        self.assertEqual(state.counters.inference_requests, 1)
        self.assertEqual(state.counters.inference_completions, 0)
        self.assertEqual(state.counters.inference_transport_failures, 1)
        self.assertEqual(state.counters.inference_queue_failures, 0)


class OperationalPrimaryTests(unittest.TestCase):
    def test_operational_primary_is_exact_provisional_e1s_r(self) -> None:
        primary = load_operational_primary(ROOT)
        self.assertEqual(primary.cell_id, "E1S-R")
        self.assertEqual(primary.operational_label, "Provisional primary")
        self.assertEqual(primary.binding.candidate_id, "M0-Q3VL-30B-A3B-FP8")
        self.assertEqual(primary.queue_capacity, 110)
        self.assertEqual(primary.queue_workers, 8)
        self.assertEqual(primary.queue_max_age_seconds, 300)
        self.assertEqual(primary.hard_seconds, 27540)
        self.assertEqual(primary.finalization_reserve_seconds, 600)

    def test_model_service_completion_canary_uses_exact_binding(self) -> None:
        primary = load_operational_primary(ROOT)
        service = ModelService(primary)
        response = unittest.mock.Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "OK"}}]
        }
        with patch("agent.production_policy.requests.post", return_value=response) as post:
            service._completion_canary()
        response.raise_for_status.assert_called_once_with()
        request = post.call_args.kwargs
        self.assertEqual(request["json"]["model"], primary.binding.model_id)
        self.assertEqual(request["json"]["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(request["timeout"], primary.completion_canary_timeout_seconds)

    def test_model_service_completion_canary_rejects_empty_content(self) -> None:
        service = ModelService(load_operational_primary(ROOT))
        response = unittest.mock.Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        with patch("agent.production_policy.requests.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "empty content"):
                service._completion_canary()

    def test_model_service_fails_before_launch_when_model_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "not-mounted"
            with patch.dict(os.environ, {"ARC_MODEL_PATH": str(missing)}):
                primary = load_operational_primary(ROOT)
            service = ModelService(primary)
            with self.assertRaisesRegex(FileNotFoundError, "not mounted"):
                service.start()
            self.assertIsNone(service.process)

    def test_submission_bundle_contains_runnable_primary_and_offline_inputs(self) -> None:
        notebook = build_submission_notebook()
        sources = submission_bundled_sources()
        self.assertIn("agent/production_policy.py", sources)
        self.assertIn("config/operational_primary.yaml", sources)
        self.assertIn("config/e1_feature_manifests.yaml", sources)
        self.assertIn("config/m0_launch_spec_q3vl30.json", sources)
        self.assertEqual(
            notebook["metadata"]["kaggle"]["accelerator"],
            "nvidiaRtxPro6000",
        )
        combined = "\n".join(
            cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code"
        )
        self.assertIn("vllm==0.19.0", combined)
        self.assertIn("agent.production_main", combined)

    def test_phase1_decision_closes_on_valid_whole_run_without_acceptance(self) -> None:
        decision = json.loads((ROOT / "config/phase1_decision.yaml").read_text())
        protocol = json.loads((ROOT / "config/e1_whole_run_protocol.yaml").read_text())
        evidence_path = ROOT / decision["comparison"]["canonical_evidence"]
        evidence_bytes = evidence_path.read_bytes()
        record = json.loads(evidence_bytes)
        validate_whole_run_record(record, protocol)
        self.assertEqual(
            hashlib.sha256(evidence_bytes).hexdigest(),
            decision["comparison"]["evidence_sha256"],
        )
        self.assertEqual(decision["result"]["fixed_candidate"], "E1S-R")
        self.assertEqual(decision["result"]["fixed_candidate_status"], "Provisional primary")
        self.assertFalse(decision["result"]["factorial_effect_acceptance_claim"])
        self.assertEqual(decision["operational"]["remaining_phase_1_exit_gates"], [])


class Phase1StatisticsTests(unittest.TestCase):
    @staticmethod
    def _whole_run_cell(mean: float) -> dict[str, Any]:
        source = json.loads((ROOT / "config/e1_experiment_protocol.yaml").read_text())
        return {
            "fixed_set_mean": mean,
            "finalization_status": "acknowledged",
            "queue": {
                "policy": "minimum_fair_v1",
                "capacity": 110,
                "worker_count": 8,
                "max_age_seconds": 300,
                "max_observed_size": 2,
                "max_observed_age": 0.1,
            },
            "charged_totals": {
                "inference_requests": 10,
                "inference_completions": 10,
                "inference_transport_failures": 0,
                "inference_queue_failures": 0,
                "parser_repairs": 0,
            },
            "fresh_runtime": {
                "fresh_process": True,
                "completion_canary_passed": True,
                "server_log": "server.log",
                "server_log_sha256": "0" * 64,
            },
            "games": [
                {
                    "game_id": item["game_id"],
                    "seed": item["seed"],
                    "fold": item["fold"],
                }
                for item in source["development_game_seed_pairs"]
            ],
        }

    def test_whole_run_analysis_uses_blocks_not_games(self) -> None:
        blocks = []
        for block_id in ("B1", "B2"):
            blocks.append(
                {
                    "block_id": block_id,
                    "cells": {
                        "E1S-R": self._whole_run_cell(0.0),
                        "E1S-F": self._whole_run_cell(2.0),
                        "E1C-R": self._whole_run_cell(1.0),
                        "E1C-F": self._whole_run_cell(4.0),
                    },
                }
            )
        analysis = analyze_blocks(blocks, minimum_nonzero_blocks=4)
        self.assertEqual(analysis["unit"], "paired_complete_workload_run_block")
        self.assertEqual(
            analysis["factorial_contrasts"]["representation_F_minus_R"]["mean_effect"],
            2.5,
        )
        self.assertEqual(
            analysis["factorial_contrasts"]["representation_F_minus_R"]["nonzero_blocks"],
            2,
        )
        self.assertIsNone(
            analysis["factorial_contrasts"]["representation_F_minus_R"]["two_sided_p_value"]
        )
        self.assertEqual(
            analysis["factorial_contrasts"]["representation_F_minus_R"]["status"],
            "Provisional",
        )

    def test_whole_run_record_requires_fresh_isolated_treatment_processes(self) -> None:
        protocol = json.loads((ROOT / "config/e1_whole_run_protocol.yaml").read_text())
        blocks = []
        for spec in protocol["execution"]["blocks"]:
            blocks.append(
                {
                    "block_id": spec["block_id"],
                    "order": spec["order"],
                    "cells": {
                        cell: self._whole_run_cell(0.0)
                        for cell in spec["order"]
                    },
                }
            )
        record = {
            "schema_version": 1,
            "status": "complete",
            "experiment_id": protocol["experiment_id"],
            "score_unit": "official_RHAE_percent",
            "protocol_sha256": hashlib.sha256(
                json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "model_binding": protocol["model_binding"],
            "artifact": {"tree_sha256": protocol["artifact_tree_sha256"]},
            "runtime": {
                "observed_gpu": "NVIDIA RTX PRO 6000 Blackwell Server Edition",
                "elapsed_seconds": 100.0,
            },
            "blocks": blocks,
            "analysis": analyze_blocks(
                blocks,
                minimum_nonzero_blocks=protocol["analysis"]["minimum_nonzero_blocks"],
            ),
        }
        validate_whole_run_record(record, protocol)
        blocks[0]["cells"]["E1S-R"]["fresh_runtime"]["fresh_process"] = False
        with self.assertRaisesRegex(ValueError, "fresh model process"):
            validate_whole_run_record(record, protocol)

    def test_block_contrasts_require_exact_factorial_cells(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact four"):
            block_contrasts({"E1S-R": 0.0})

    def test_exact_score_map_charges_missing_game_as_zero(self) -> None:
        scorecard = {"environments": [{"id": "a", "score": 12.5}]}
        self.assertEqual(exact_score_map(scorecard, ("a", "b")), {"a": 12.5, "b": 0.0})

    def test_complete_four_cell_record_recomputes_and_validates(self) -> None:
        protocol = json.loads((ROOT / "config/e1_experiment_protocol.yaml").read_text())
        feature_registry = json.loads((ROOT / "config/e1_feature_manifests.yaml").read_text())
        pairs = protocol["development_game_seed_pairs"]
        game_ids = tuple(item["game_id"] for item in pairs)
        folds = {item["game_id"]: item["fold"] for item in pairs}
        scores = {
            cell: {game_id: float(index) for game_id in game_ids}
            for index, cell in enumerate(("E1S-R", "E1S-F", "E1C-R", "E1C-F"))
        }
        cells = {}
        for cell, cell_scores in scores.items():
            cells[cell] = {
                "finalization_status": "acknowledged",
                "queue": {
                    "policy": "minimum_fair_v1",
                    "capacity": 110,
                    "worker_count": 8,
                    "max_age_seconds": 300,
                    "max_observed_size": 0,
                    "max_observed_age": 0.0,
                },
                "games": [
                    {
                        "game_id": game_id,
                        "score": cell_scores[game_id],
                        "seed": next(
                            item["seed"] for item in pairs if item["game_id"] == game_id
                        ),
                        "fold": folds[game_id],
                        "controller_iterations": 0,
                        "inference_requests": 0,
                        "inference_completions": 0,
                        "inference_transport_failures": 0,
                        "inference_queue_failures": 0,
                        "workspace_invocations": 0,
                        "parser_repairs": 0,
                    }
                    for game_id in game_ids
                ],
            }
        record = {
            "schema_version": 1,
            "status": "complete",
            "score_unit": "official_RHAE_percent",
            "model_binding": protocol["model_binding"],
            "game_seed_pairs": pairs,
            "protocol_sha256": frozen_protocol_sha256(protocol),
            "feature_registry_sha256": frozen_feature_registry_sha256(feature_registry),
            "artifact": {
                "tree_sha256": protocol["design"]["artifact_tree_sha256"]
            },
            "runtime": {
                "observed_gpu": "NVIDIA RTX PRO 6000 Blackwell Server Edition",
                "completion_canary": {
                    "response_nonempty": True,
                    "completion_tokens": 1,
                },
            },
            "cells": cells,
            "analysis": analysis_payload(scores, folds),
        }
        validate_experiment_record(record, protocol, feature_registry)
        protocol["execution_status"]["four_cell_runs"] = "complete"
        feature_registry["status"] = "execution_complete"
        validate_experiment_record(record, protocol, feature_registry)
        protocol["design"]["temperature"] = 0.1
        with self.assertRaisesRegex(ValueError, "protocol digest drifted"):
            validate_experiment_record(record, protocol, feature_registry)

    def test_incomplete_four_cell_record_fails_closed(self) -> None:
        protocol = json.loads((ROOT / "config/e1_experiment_protocol.yaml").read_text())
        features = json.loads((ROOT / "config/e1_feature_manifests.yaml").read_text())
        incomplete = {
            "schema_version": 1,
            "status": "running",
            "model_binding": protocol["model_binding"],
        }
        with self.assertRaisesRegex(ValueError, "not complete"):
            validate_experiment_record(incomplete, protocol, features)

    def test_causal_four_cell_uses_paired_main_effects_and_interaction(self) -> None:
        games = tuple(f"g{index}" for index in range(6))
        folds = {game: 1 + index % 2 for index, game in enumerate(games)}
        scores = {
            "E1S-R": {game: 0.0 for game in games},
            "E1S-F": {game: 2.0 for game in games},
            "E1C-R": {game: 1.0 for game in games},
            "E1C-F": {game: 4.0 for game in games},
        }
        analysis = causal_four_cell_analysis(scores, folds)
        contrasts = {item.name: item for item in analysis.contrasts}
        self.assertEqual(dict(analysis.cell_means)["E1C-F"], 4.0)
        self.assertEqual(contrasts["representation_F_minus_R"].mean_effect, 2.5)
        self.assertEqual(contrasts["safe_operations_C_minus_S"].mean_effect, 1.5)
        self.assertEqual(
            contrasts["interaction_difference_in_differences"].mean_effect, 1.0
        )
        self.assertEqual(contrasts["representation_F_minus_R"].two_sided_p_value, 0.03125)

    def test_cross_validation_separates_procedure_and_fixed_candidate(self) -> None:
        games = ("a", "b", "c", "d")
        folds = {"a": 1, "b": 1, "c": 2, "d": 2}
        scores = {
            "first": {"a": 1.0, "b": 1.0, "c": 0.0, "d": 0.0},
            "second": {"a": 0.0, "b": 0.0, "c": 0.9, "d": 0.9},
        }
        result = cross_validated_selection(
            scores, folds, tie_break_order=("first", "second")
        )
        self.assertEqual(result.fold_choices, ("second", "first"))
        self.assertEqual(result.selection_procedure_mean, 0.0)
        self.assertEqual(result.final_fixed_candidate, "first")
        self.assertEqual(result.final_fixed_candidate_mean, 0.5)

    def test_sparse_ties_are_provisional_and_strong_pairs_can_accept(self) -> None:
        sparse = paired_inference(
            {"a": 1, "b": 0, "c": 0},
            {"a": 0, "b": 0, "c": 0},
            minimum_nonzero_pairs=2,
        )
        self.assertEqual(sparse.status, "Provisional primary")
        self.assertIsNone(sparse.one_sided_p_value)

        candidate = {str(index): 1.0 for index in range(6)}
        comparator = {str(index): 0.0 for index in range(6)}
        accepted = paired_inference(candidate, comparator, minimum_nonzero_pairs=5)
        self.assertEqual(accepted.status, "Accepted")
        self.assertLessEqual(accepted.one_sided_p_value or 1, 0.10)
        unsafe = paired_inference(
            candidate, comparator, minimum_nonzero_pairs=5, safety_passed=False
        )
        self.assertEqual(unsafe.status, "Provisional primary")


class ControlFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads((ROOT / "config/control_registry.yaml").read_text())
        cls.candidates = {
            item["id"]: item for item in cls.registry.get("candidates", [])
        }

    def test_cutoff_roles_are_frozen(self) -> None:
        self.assertEqual(
            self.registry["status"],
            "cutoff_frozen_availability_and_license_decisions_closed",
        )
        self.assertEqual(
            self.registry["frozen_published_workspace_control"],
            "duck-qwen3.8-flash-next-nvfp4-anim",
        )
        self.assertEqual(
            self.registry["frozen_published_structured_reference"],
            "reki-milestone1",
        )
        self.assertEqual(
            self.registry["strongest_eligible_structured_control"],
            "e1s-r-project-structured-fallback",
        )

    def test_duck_is_unavailable_not_silently_adapted(self) -> None:
        duck = self.candidates["duck-qwen3.8-flash-next-nvfp4-anim"]
        decision = duck["python_runner_decision"]
        self.assertFalse(duck["production_eligible"])
        self.assertEqual(decision["status"], "unavailable_isolation_unproven")
        self.assertEqual(
            decision["decision"],
            "do_not_execute_model_authored_python_in_production",
        )
        self.assertIn("native_code_boundary", decision["missing_required_controls"])
        self.assertIn("credential_boundary", decision["missing_required_controls"])

    def test_unknown_control_distributions_fail_closed(self) -> None:
        duck = self.candidates["duck-qwen3.8-flash-next-nvfp4-anim"]
        reki = self.candidates["reki-milestone1"]
        self.assertEqual(
            duck["license_components"]["source_dataset"],
            "Kaggle_metadata_unknown",
        )
        self.assertEqual(
            reki["license_components"]["wheelhouse_dataset"],
            "Kaggle_metadata_unknown",
        )
        self.assertFalse(reki["production_eligible"])

    def test_safe_operation_substitute_is_explicitly_adapted(self) -> None:
        substitute = self.candidates["e1c-f-safe-operations-duck-substitute"]
        self.assertTrue(substitute["production_eligible"])
        self.assertEqual(substitute["result_class"], "adapted_control")
        self.assertIn(
            "python_repl_replaced_by_fixed_safe_operations",
            substitute["changed_from_duck"],
        )
        self.assertIn("not_a_faithful", substitute["control_fidelity"])


class E1ProfileNotebookTests(unittest.TestCase):
    def test_four_cell_notebook_is_offline_exact_and_fail_closed(self) -> None:
        notebook = build_e1_four_cell_notebook()
        kaggle = notebook["metadata"]["kaggle"]
        self.assertEqual(kaggle["accelerator"], "nvidiaRtxPro6000")
        self.assertFalse(kaggle["isInternetEnabled"])
        sources = e1_four_cell_bundled_sources()
        self.assertIn("scripts/run_e1_four_cell.py", sources)
        self.assertIn("scripts/run_e1_whole_run.py", sources)
        self.assertIn("evaluation/e1_experiment.py", sources)
        self.assertIn("evaluation/e1_whole_run.py", sources)
        combined = "\n".join(
            cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code"
        )
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                compile(cell["source"], f"e1-four-cell-{index}", "exec")
        self.assertIn("E1_FOUR_CELL_PREFLIGHT_OK games=15", combined)
        self.assertIn("e1-whole-run-four-cell-v1.json", combined)
        self.assertIn("--whole-run-protocol", combined)
        self.assertIn("--server-log-dir", combined)
        self.assertLess(combined.index("E1_FOUR_CELL_PREFLIGHT_OK"), combined.index("pip', 'install"))

    def test_four_cell_bundle_imports_in_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            for relative, payload in e1_four_cell_bundled_sources().items():
                target = isolated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(base64.b64decode(payload))
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(isolated)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import scripts.run_e1_four_cell, scripts.run_e1_whole_run",
                ],
                cwd=isolated,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_workloads_use_exact_cells_without_identity_leakage(self) -> None:
        workloads = build_e1_workload_fixtures(
            str(ROOT / "config/e1_feature_manifests.yaml")
        )
        self.assertEqual(tuple(workloads), E1_CELLS)
        serialized = str(workloads)
        self.assertNotIn("profile-fixture-never-model-visible", serialized)
        self.assertNotIn("profile-guid-never-model-visible", serialized)
        self.assertNotIn('"features"', str(workloads["E1S-R"]))
        self.assertIn('"features"', str(workloads["E1S-F"]))
        self.assertEqual(len(workloads["E1C-R"]), 4)
        self.assertIn("under 64 tokens", workloads["E1S-F"][0]["content"])

    def test_profile_notebook_is_offline_target_rtx_and_compiles(self) -> None:
        notebook = build_e1_profile_notebook()
        kaggle = notebook["metadata"]["kaggle"]
        self.assertEqual(kaggle["accelerator"], "nvidiaRtxPro6000")
        self.assertFalse(kaggle["isInternetEnabled"])
        combined = "\n".join(
            cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code"
        )
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                compile(cell["source"], f"e1-profile-cell-{index}", "exec")
        self.assertIn("scripts/profile_e1_openai.py", e1_profile_bundled_sources())
        self.assertIn("evaluation/metrics.py", e1_profile_bundled_sources())
        self.assertIn("e1-q3vl30-mixed-profile.json", combined)
        self.assertIn("NvidiaRtxPro6000", (ROOT / "notebooks/e1-q3vl30/kernel-metadata.json").read_text())

    def test_profile_bundle_imports_in_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            for relative, payload in e1_profile_bundled_sources().items():
                target = isolated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(base64.b64decode(payload))
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(isolated)
            completed = subprocess.run(
                [sys.executable, "-c", "import scripts.profile_e1_openai"],
                cwd=isolated,
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_profile_projection_uses_headroom_adjusted_admission(self) -> None:
        result = capacity_projection(cold_load_seconds=200, latency_guard_seconds=0.4)
        self.assertEqual(result["request_count"], 70_400)
        self.assertLess(result["C_admit"], result["C_nominal"])
        self.assertTrue(result["passes_request_admission"])
        self.assertTrue(result["passes_operational_target"])

    def test_profile_protocol_classifier_is_strict(self) -> None:
        self.assertEqual(
            _protocol_kind('{"action":{"action_id":1,"action_data":{}}}'), "action"
        )
        self.assertEqual(
            _protocol_kind('{"operation":"palette","arguments":{}}'), "operation"
        )
        self.assertEqual(
            _protocol_kind('{"action":{"action_id":6,"action_data":{"x":64,"y":0}}}'),
            "invalid",
        )
        self.assertEqual(
            _protocol_kind('{"operation":"python","arguments":{}}'), "invalid"
        )
        self.assertEqual(_protocol_kind("```json\n{}\n```"), "invalid")


if __name__ == "__main__":
    unittest.main()
