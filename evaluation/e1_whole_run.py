"""Validation and block-level analysis for shared-resource E1 runs."""

from __future__ import annotations

import itertools
import hashlib
import json
from statistics import fmean
from typing import Any, Mapping

from .phase1 import E1_FACTORIAL_CELLS


CONTRASTS = (
    "representation_F_minus_R",
    "safe_operations_C_minus_S",
    "interaction_difference_in_differences",
)


def block_contrasts(cell_means: Mapping[str, float]) -> dict[str, float]:
    if set(cell_means) != set(E1_FACTORIAL_CELLS):
        raise ValueError("whole-run block requires the exact four E1 cells")
    sr, sf, cr, cf = (float(cell_means[cell]) for cell in E1_FACTORIAL_CELLS)
    return {
        "representation_F_minus_R": 0.5 * ((sf - sr) + (cf - cr)),
        "safe_operations_C_minus_S": 0.5 * ((cr - sr) + (cf - sf)),
        "interaction_difference_in_differences": (cf - cr) - (sf - sr),
    }


def _two_sided_sign_flip(values: list[float]) -> float | None:
    nonzero = [value for value in values if value != 0]
    if not nonzero:
        return None
    observed = abs(fmean(values))
    exceedances = 0
    permutations = 1 << len(nonzero)
    for signs in itertools.product((-1.0, 1.0), repeat=len(nonzero)):
        permuted = abs(sum(sign * value for sign, value in zip(signs, nonzero)) / len(values))
        if permuted >= observed - 1e-15:
            exceedances += 1
    return exceedances / permutations


def analyze_blocks(
    blocks: list[Mapping[str, Any]],
    *,
    minimum_nonzero_blocks: int,
) -> dict[str, Any]:
    if not blocks or minimum_nonzero_blocks < 1:
        raise ValueError("whole-run analysis requires blocks and a positive threshold")
    seen: set[str] = set()
    block_rows: list[dict[str, Any]] = []
    for block in blocks:
        block_id = block.get("block_id")
        cells = block.get("cells")
        if not isinstance(block_id, str) or block_id in seen or not isinstance(cells, Mapping):
            raise ValueError("whole-run block identity or cells are invalid")
        seen.add(block_id)
        means = {
            cell: float(cells[cell]["fixed_set_mean"])
            for cell in E1_FACTORIAL_CELLS
        }
        block_rows.append(
            {
                "block_id": block_id,
                "cell_means": means,
                "factorial_contrasts": block_contrasts(means),
            }
        )

    cell_means = {
        cell: fmean(row["cell_means"][cell] for row in block_rows)
        for cell in E1_FACTORIAL_CELLS
    }
    rank = {cell: index for index, cell in enumerate(E1_FACTORIAL_CELLS)}
    fixed = min(cell_means, key=lambda cell: (-cell_means[cell], rank[cell]))
    contrasts: dict[str, Any] = {}
    for name in CONTRASTS:
        values = [row["factorial_contrasts"][name] for row in block_rows]
        nonzero = sum(value != 0 for value in values)
        contrasts[name] = {
            "per_block": {
                row["block_id"]: row["factorial_contrasts"][name]
                for row in block_rows
            },
            "mean_effect": fmean(values),
            "nonzero_blocks": nonzero,
            "two_sided_p_value": _two_sided_sign_flip(values)
            if nonzero >= minimum_nonzero_blocks
            else None,
            "status": "Estimable" if nonzero >= minimum_nonzero_blocks else "Provisional",
        }
    return {
        "unit": "paired_complete_workload_run_block",
        "blocks": block_rows,
        "cell_means": cell_means,
        "factorial_contrasts": contrasts,
        "fixed_candidate_by_frozen_tie_break": fixed,
        "fixed_candidate_mean": cell_means[fixed],
        "fixed_candidate_status": "Provisional primary",
        "per_game_results_use": "diagnostic_only",
    }


def validate_whole_run_record(
    record: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> None:
    if record.get("schema_version") != 1 or record.get("status") != "complete":
        raise ValueError("whole-run record is not complete schema version 1")
    if record.get("experiment_id") != protocol.get("experiment_id"):
        raise ValueError("whole-run experiment identity drifted")
    if record.get("score_unit") != protocol.get("analysis", {}).get("score_unit"):
        raise ValueError("whole-run score unit drifted")
    expected_protocol_sha256 = hashlib.sha256(
        json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if record.get("protocol_sha256") != expected_protocol_sha256:
        raise ValueError("whole-run protocol digest drifted")
    if record.get("model_binding") != protocol.get("model_binding"):
        raise ValueError("whole-run model binding drifted")
    artifact = record.get("artifact", {})
    if artifact.get("tree_sha256") != protocol.get("artifact_tree_sha256"):
        raise ValueError("whole-run model artifact drifted")
    runtime = record.get("runtime", {})
    if (
        "RTX PRO 6000" not in str(runtime.get("observed_gpu", ""))
        or not isinstance(runtime.get("elapsed_seconds"), (int, float))
        or runtime.get("elapsed_seconds") > protocol.get("execution", {}).get("hard_seconds", 0)
    ):
        raise ValueError("whole-run target runtime or hard deadline is invalid")
    expected_blocks = protocol.get("execution", {}).get("blocks")
    blocks = record.get("blocks")
    if not isinstance(expected_blocks, list) or not isinstance(blocks, list):
        raise ValueError("whole-run blocks are missing")
    if len(blocks) != len(expected_blocks):
        raise ValueError("whole-run block count drifted")
    for expected, observed in zip(expected_blocks, blocks):
        if observed.get("block_id") != expected.get("block_id"):
            raise ValueError("whole-run block order drifted")
        if observed.get("order") != expected.get("order"):
            raise ValueError("whole-run treatment order drifted")
        cells = observed.get("cells")
        if not isinstance(cells, Mapping) or set(cells) != set(E1_FACTORIAL_CELLS):
            raise ValueError("whole-run block does not contain four complete workloads")
        for cell_id, cell in cells.items():
            if cell.get("finalization_status") != "acknowledged":
                raise ValueError(f"{cell_id} finalization was not acknowledged")
            queue = cell.get("queue", {})
            if (
                queue.get("policy") != "minimum_fair_v1"
                or queue.get("capacity") != 110
                or queue.get("worker_count") != 8
                or queue.get("max_age_seconds") != 300
                or queue.get("max_observed_size", 111) > 110
                or queue.get("max_observed_age", 301) > 300
            ):
                raise ValueError(f"{cell_id} queue contract drifted")
            totals = cell.get("charged_totals", {})
            if totals.get("inference_requests") != totals.get("inference_completions"):
                raise ValueError(f"{cell_id} inference transport is incomplete")
            if totals.get("inference_transport_failures") != 0 or totals.get("inference_queue_failures") != 0:
                raise ValueError(f"{cell_id} inference service failed")
            if totals.get("parser_repairs") != 0:
                raise ValueError(f"{cell_id} used parser repair")
            runtime = cell.get("fresh_runtime", {})
            if (
                runtime.get("fresh_process") is not True
                or runtime.get("completion_canary_passed") is not True
                or not isinstance(runtime.get("server_log"), str)
                or len(str(runtime.get("server_log_sha256", ""))) != 64
            ):
                raise ValueError(f"{cell_id} did not use a verified fresh model process")
            games = cell.get("games")
            if not isinstance(games, list) or len(games) != 15:
                raise ValueError(f"{cell_id} does not contain the complete workload")
            pairs = [
                {
                    "game_id": game.get("game_id"),
                    "seed": game.get("seed"),
                    "fold": game.get("fold"),
                }
                for game in games
            ]
            pairs_sha256 = hashlib.sha256(
                json.dumps(pairs, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if pairs_sha256 != protocol.get("game_seed_pairs_sha256"):
                raise ValueError(f"{cell_id} workload identity or order drifted")

    expected_analysis = analyze_blocks(
        blocks,
        minimum_nonzero_blocks=protocol["analysis"]["minimum_nonzero_blocks"],
    )
    if record.get("analysis") != expected_analysis:
        raise ValueError("whole-run analysis does not recompute from block evidence")
