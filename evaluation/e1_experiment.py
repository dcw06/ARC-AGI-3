"""Validation and analysis for the frozen causal Phase 1 four-cell run."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .phase1 import E1_FACTORIAL_CELLS, causal_four_cell_analysis


SCHEMA_VERSION = 1
SCORE_UNIT = "official_RHAE_percent"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_protocol_sha256(protocol: Mapping[str, Any]) -> str:
    return canonical_sha256(
        {
            field: protocol[field]
            for field in (
                "schema_version",
                "frozen_at",
                "design",
                "model_binding",
                "development_game_seed_pairs",
                "selection",
            )
        }
    )


def frozen_feature_registry_sha256(feature_registry: Mapping[str, Any]) -> str:
    return canonical_sha256(
        {
            field: feature_registry[field]
            for field in (
                "schema_version",
                "manifest_revision",
                "model_binding",
                "shared",
                "cells",
                "activation_requires",
            )
        }
    )


def exact_score_map(
    scorecard: Mapping[str, Any] | None,
    game_ids: Sequence[str],
) -> dict[str, float]:
    """Extract official per-game scores, charging absent games as registered zero."""
    expected = set(game_ids)
    if len(expected) != len(game_ids):
        raise ValueError("frozen game IDs must be unique")
    scores = {game_id: 0.0 for game_id in game_ids}
    environments = [] if scorecard is None else scorecard.get("environments", [])
    if not isinstance(environments, list):
        raise ValueError("scorecard environments must be a list")
    seen: set[str] = set()
    for environment in environments:
        if not isinstance(environment, Mapping):
            raise ValueError("scorecard environment must be an object")
        game_id = environment.get("id")
        score = environment.get("score")
        if game_id not in expected or game_id in seen:
            raise ValueError("scorecard contains an unexpected or duplicate game")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("scorecard game score must be numeric")
        value = float(score)
        if not math.isfinite(value) or not 0 <= value <= 115:
            raise ValueError("scorecard game score is outside official percent bounds")
        scores[str(game_id)] = value
        seen.add(str(game_id))
    return scores


def analysis_payload(
    scores: Mapping[str, Mapping[str, float]],
    folds: Mapping[str, int],
    *,
    minimum_nonzero_pairs: int = 5,
) -> dict[str, Any]:
    result = causal_four_cell_analysis(
        scores,
        folds,
        minimum_nonzero_pairs=minimum_nonzero_pairs,
    )
    return {
        "cell_means": dict(result.cell_means),
        "selection_procedure": {
            "fold_choices": list(result.selection.fold_choices),
            "held_out_scores": list(result.selection.held_out_scores),
            "selection_procedure_mean": result.selection.selection_procedure_mean,
            "final_fixed_candidate": result.selection.final_fixed_candidate,
            "final_fixed_candidate_mean": result.selection.final_fixed_candidate_mean,
        },
        "factorial_contrasts": {
            contrast.name: {
                "per_game": dict(contrast.per_game),
                "mean_effect": contrast.mean_effect,
                "nonzero_pairs": contrast.nonzero_pairs,
                "two_sided_p_value": contrast.two_sided_p_value,
                "status": contrast.status,
            }
            for contrast in result.contrasts
        },
    }


def validate_experiment_record(
    record: Mapping[str, Any],
    protocol: Mapping[str, Any],
    feature_registry: Mapping[str, Any],
) -> None:
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported E1 experiment schema")
    if record.get("status") != "complete":
        raise ValueError("E1 four-cell record is not complete")
    if record.get("score_unit") != SCORE_UNIT:
        raise ValueError("E1 score unit is not explicit official percent")
    if record.get("model_binding") != protocol.get("model_binding"):
        raise ValueError("E1 experiment model binding drifted")
    if record.get("protocol_sha256") != frozen_protocol_sha256(protocol):
        raise ValueError("E1 experiment protocol digest drifted")
    if record.get("feature_registry_sha256") != frozen_feature_registry_sha256(feature_registry):
        raise ValueError("E1 feature-registry digest drifted")
    artifact = record.get("artifact")
    if (
        not isinstance(artifact, Mapping)
        or artifact.get("tree_sha256")
        != protocol.get("design", {}).get("artifact_tree_sha256")
    ):
        raise ValueError("E1 model artifact digest drifted")
    runtime = record.get("runtime")
    canary = runtime.get("completion_canary") if isinstance(runtime, Mapping) else None
    if (
        not isinstance(runtime, Mapping)
        or "RTX PRO 6000" not in str(runtime.get("observed_gpu", ""))
        or not isinstance(canary, Mapping)
        or canary.get("response_nonempty") is not True
        or not isinstance(canary.get("completion_tokens"), int)
        or canary.get("completion_tokens", 0) < 1
    ):
        raise ValueError("E1 target runtime completion canary is invalid")

    pairs = protocol.get("development_game_seed_pairs")
    if not isinstance(pairs, list) or record.get("game_seed_pairs") != pairs:
        raise ValueError("E1 experiment game/seed pairs drifted")
    game_ids = tuple(item["game_id"] for item in pairs)
    folds = {item["game_id"]: item["fold"] for item in pairs}
    seeds = {item["game_id"]: item["seed"] for item in pairs}
    cells = record.get("cells")
    if not isinstance(cells, Mapping) or set(cells) != set(E1_FACTORIAL_CELLS):
        raise ValueError("E1 experiment must contain the exact frozen four-cell set")

    scores: dict[str, dict[str, float]] = {}
    for cell_id in E1_FACTORIAL_CELLS:
        cell = cells[cell_id]
        if not isinstance(cell, Mapping):
            raise ValueError("E1 cell record must be an object")
        if cell.get("finalization_status") != "acknowledged":
            raise ValueError(f"{cell_id} scorecard finalization was not acknowledged")
        games = cell.get("games")
        if not isinstance(games, list) or tuple(item.get("game_id") for item in games) != game_ids:
            raise ValueError(f"{cell_id} does not contain the exact frozen game order")
        ceiling = 1 if cell_id.startswith("E1S") else 8
        cell_scores: dict[str, float] = {}
        for game in games:
            score = game.get("score")
            iterations = game.get("controller_iterations")
            requests = game.get("inference_requests")
            completions = game.get("inference_completions")
            transport_failures = game.get("inference_transport_failures")
            queue_failures = game.get("inference_queue_failures")
            workspace = game.get("workspace_invocations")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ValueError(f"{cell_id} contains a non-numeric score")
            if game.get("seed") != seeds.get(game.get("game_id")) or game.get("fold") != folds.get(
                game.get("game_id")
            ):
                raise ValueError(f"{cell_id} game seed or fold drifted")
            if not math.isfinite(float(score)) or not 0 <= float(score) <= 115:
                raise ValueError(f"{cell_id} score is outside official percent bounds")
            if not all(
                isinstance(value, int) and value >= 0
                for value in (
                    iterations,
                    requests,
                    completions,
                    transport_failures,
                    queue_failures,
                    workspace,
                )
            ):
                raise ValueError(f"{cell_id} contains invalid charged counters")
            if completions != requests:
                raise ValueError(f"{cell_id} contains incomplete inference transport")
            if transport_failures != 0 or queue_failures != 0:
                raise ValueError(f"{cell_id} contains inference service failures")
            if requests > iterations * ceiling:
                raise ValueError(f"{cell_id} exceeded its model-request ceiling")
            if cell_id.startswith("E1S") and workspace != 0:
                raise ValueError(f"{cell_id} accessed the safe-operation workspace")
            if cell_id.startswith("E1C") and workspace > iterations * 7:
                raise ValueError(f"{cell_id} exceeded its workspace ceiling")
            if game.get("parser_repairs") != 0:
                raise ValueError(f"{cell_id} used an unregistered parser repair")
            cell_scores[game["game_id"]] = float(score)
        queue = cell.get("queue")
        if not isinstance(queue, Mapping):
            raise ValueError(f"{cell_id} queue evidence is missing")
        if queue.get("policy") != "minimum_fair_v1":
            raise ValueError(f"{cell_id} used a different queue policy")
        if queue.get("capacity") != 110 or queue.get("worker_count") != 8:
            raise ValueError(f"{cell_id} queue capacity or worker count drifted")
        if queue.get("max_age_seconds") != 300:
            raise ValueError(f"{cell_id} queue age ceiling drifted")
        if queue.get("max_observed_size", 111) > 110 or queue.get("max_observed_age", 301) > 300:
            raise ValueError(f"{cell_id} observed queue bounds were exceeded")
        scores[cell_id] = cell_scores

    expected_analysis = analysis_payload(
        scores,
        folds,
        minimum_nonzero_pairs=protocol["selection"]["minimum_nonzero_game_pairs"],
    )
    if record.get("analysis") != expected_analysis:
        raise ValueError("E1 analysis does not recompute from the retained score matrix")
    if feature_registry.get("shared", {}).get("scheduler") != "minimum_fair_v1":
        raise ValueError("feature registry queue policy drifted")
