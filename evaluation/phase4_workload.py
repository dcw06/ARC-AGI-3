"""Offline request-shape fixtures captured through the unchanged E1S-R policy.

These are generated development fixtures, not recorded games or GPU evidence.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from agent.e1_policy import E1Policy, E1ModelBinding, CompletionResult
from agent.feature_manifest import load_e1_feature_manifests
from agent.scheduler import QueuedInferenceExecutor
from agent.state import Observation, GameRuntimeState
from evaluation.phase4 import ROOT, validate_contract, sha


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def build_workload(root=ROOT):
    validate_contract(root)
    primary = json.loads((root / "config/operational_primary.yaml").read_text())["primary"]
    manifest = load_e1_feature_manifests(root / "config/e1_feature_manifests.yaml")["E1S-R"]
    fixtures = []
    class CaptureClient:
        def complete(self, request):
            self.request = json.loads(json.dumps(request))
            return CompletionResult('{"action":{"action_id":1,"action_data":{}}}')

    def observation(size, step):
        grid = ((np.arange(size * size).reshape(size, size) + step) % 16).tolist()
        return Observation.from_value({"game_id": "opaque-fixture-isolation",
            "guid": "fixture-guid-not-policy-visible", "frame": [grid],
            "state": "NOT_FINISHED", "levels_completed": 0, "win_levels": 3,
            "available_actions": [1, 2, 3, 4, 5, 6, 7], "full_reset": False})

    with QueuedInferenceExecutor(worker_count=8) as inference:
        for size in (16, 32, 64):
            for history in (0, 1, 79):
                state = GameRuntimeState(observation(size, 0), action_budget_limit=80)
                for step in range(1, history + 1):
                    state.replace_observation(observation(size, step), action_id=1,
                                              transition_id=f"fixture-transition-{step}")
                capture = CaptureClient()
                policy = E1Policy(manifest=manifest,
                    binding=E1ModelBinding.from_mapping(primary["model_binding"]),
                    client=capture, inference=inference,
                    max_new_tokens=primary["inference"]["max_new_tokens"],
                    seed=primary["inference"]["request_seed"])
                policy.propose(state)
                payload = canonical(capture.request)
                if b"opaque-fixture-isolation" in payload or b"fixture-guid" in payload:
                    raise ValueError("fixture identity leaked into model request")
                fixtures.append({"fixture_id": f"grid{size}-history{history}",
                    "grid_size": size, "history_transitions": history,
                    "request": capture.request, "request_bytes": len(payload),
                    "request_sha256": hashlib.sha256(payload).hexdigest(),
                    "prompt_tokens": None})
    assignments = [{"client_slot": index, "requests": [
        fixtures[(index + step) % len(fixtures)]["fixture_id"] for step in range(80)]}
        for index in range(110)]
    value = {"schema_version": 1, "workload_id": "P4-E1SR-request-shapes-v1",
        "evidence_class": "generated_grid_request_shapes_not_empirical_game_distribution",
        "capture_method": "E1Policy.propose_with_capture_completion_client",
        "contract_sha256": sha(root / "config/phase4_contract.json"),
        "generator_sha256": sha(Path(__file__)), "request_seed": 0,
        "clients": 110, "requests_per_client": 80, "total_requests": 8800,
        "fixtures": fixtures, "assignments": assignments,
        "environment_execution": False, "model_inference": False,
        "target_gpu_certified": False}
    value["workload_sha256"] = hashlib.sha256(canonical(value)).hexdigest()
    return value


def validate_workload(value, root=ROOT):
    # Exact regeneration checks all request fields and assignments, not merely
    # a self-reported digest. Small enough for offline validation.
    if value != build_workload(root):
        raise ValueError("request workload differs from frozen production-path fixtures")
    return value
