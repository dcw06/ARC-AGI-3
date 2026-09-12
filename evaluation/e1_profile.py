"""Deterministic mixed-prompt fixtures and projections for the E1 RTX profile."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

E1_CELLS = ("E1S-R", "E1S-F", "E1C-R", "E1C-F")


def _observation(grid: Any, *, frames: tuple[Any, ...] | None = None) -> Any:
    from agent.state import Observation

    visible = frames or (grid,)
    return Observation.from_value(
        {
            "game_id": "profile-fixture-never-model-visible",
            "frame": [frame.tolist() for frame in visible],
            "state": "NOT_FINISHED",
            "levels_completed": 0,
            "win_levels": 3,
            "guid": "profile-guid-never-model-visible",
            "full_reset": False,
            "available_actions": [1, 2, 3, 4, 5, 6, 7],
        }
    )


def build_e1_workload_fixtures(manifest_path: str) -> dict[str, list[dict[str, str]]]:
    """Build one exact, history-rich request shape for every frozen E1 cell."""
    import numpy as np

    from agent.e1_policy import e1_system_prompt
    from agent.evidence import EvidenceStore
    from agent.feature_manifest import load_e1_feature_manifests
    from agent.representation import build_feature_bundle, build_raw_bundle

    manifests = load_e1_feature_manifests(manifest_path)
    evidence = EvidenceStore(recent_capacity=16, t3_memory_bytes=0)
    before_grid = np.zeros((32, 32), dtype=np.uint8)
    before_grid[4:10, 4:10] = 2
    before = _observation(before_grid)
    for index in range(8):
        after_grid = np.roll(before_grid, shift=1, axis=1)
        after_grid[(index * 3) % 32, (index * 5) % 32] = (index % 7) + 1
        after = _observation(after_grid)
        evidence.record_transition(
            before,
            after,
            action_id=(index % 5) + 1,
            transition_id=f"profile-transition-{index}",
        )
        before, before_grid = after, after_grid

    middle = before_grid.copy()
    middle[16, 16] = 7
    current_grid = np.roll(before_grid, shift=1, axis=0)
    current = _observation(current_grid, frames=(before_grid, middle, current_grid))
    fixtures: dict[str, list[dict[str, str]]] = {}
    for cell in E1_CELLS:
        manifest = manifests[cell]
        if manifest.observation_bundle == "R":
            bundle = build_raw_bundle(current, evidence, recent_limit=8)
        else:
            bundle = build_feature_bundle(current, evidence, recent_limit=8)
        messages = [
            {"role": "system", "content": e1_system_prompt(manifest)},
            {
                "role": "user",
                "content": json.dumps(
                    {"observation": bundle.policy_payload()},
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            },
        ]
        if manifest.workspace == "safe_operations_v1":
            messages.extend(
                (
                    {
                        "role": "assistant",
                        "content": '{"operation":"region_summary","arguments":{"array":"current"}}',
                    },
                    {
                        "role": "user",
                        "content": '{"operation_result":[{"bounding_box":[0,0,31,31],"color":0,"size":980}]}',
                    },
                )
            )
        fixtures[cell] = messages
    return fixtures


def workload_sha256(fixtures: Mapping[str, Any]) -> str:
    payload = json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def capacity_projection(
    *,
    cold_load_seconds: float,
    latency_guard_seconds: float,
    request_count: int = 70_400,
    concurrency: int = 8,
    busy_window_seconds: int = 19_800,
    headroom_factor: float = 1.25,
    non_model_allowance_seconds: int = 6_840,
) -> dict[str, float | int | bool]:
    if latency_guard_seconds <= 0 or cold_load_seconds < 0:
        raise ValueError("projection latencies must be positive")
    nominal = math.floor(busy_window_seconds * concurrency / latency_guard_seconds)
    admitted = math.floor(
        busy_window_seconds * concurrency / (latency_guard_seconds * headroom_factor)
    )
    model_seconds = cold_load_seconds + headroom_factor * math.ceil(
        request_count / concurrency
    ) * latency_guard_seconds
    total_seconds = model_seconds + non_model_allowance_seconds
    return {
        "request_count": request_count,
        "concurrency": concurrency,
        "latency_guard_seconds": latency_guard_seconds,
        "headroom_factor": headroom_factor,
        "C_nominal": nominal,
        "C_admit": admitted,
        "projected_model_seconds": model_seconds,
        "projected_total_seconds": total_seconds,
        "operational_target_seconds": 27_540,
        "passes_request_admission": request_count <= admitted,
        "passes_operational_target": total_seconds <= 27_540,
    }
