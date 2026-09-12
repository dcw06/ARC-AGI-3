"""Run the frozen causal E1 four-cell experiment in an offline RTX notebook."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.competition_loop import CompetitionOrchestrator
from agent.e1_policy import E1Policy, OpenAICompatibleCompletionClient, binding_from_registry
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import LocalFrameworkAdapter
from agent.scheduler import QueuedInferenceExecutor
from agent.watchdog import DeadlineWatchdog
from evaluation.e1_experiment import (
    SCORE_UNIT,
    analysis_payload,
    exact_score_map,
    frozen_feature_registry_sha256,
    frozen_protocol_sha256,
    validate_experiment_record,
)
from evaluation.m0_profile import inventory_artifact_tree
from evaluation.phase1 import E1_FACTORIAL_CELLS
from scripts.profile_m0_openai import ResourceSampler, _gpu_description, _validate_launch_spec, _wait_ready


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--launch-spec", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--environments-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server-log", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--expected-artifact-sha256", required=True)
    parser.add_argument("--expected-gpu-substring", default="RTX PRO 6000")
    parser.add_argument("--hard-seconds", type=float, default=32_400)
    parser.add_argument("--finalization-reserve-seconds", type=float, default=600)
    parser.add_argument("--ready-timeout-seconds", type=float, default=900)
    parser.add_argument("--request-timeout-seconds", type=float, default=300)
    return parser.parse_args()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"registry is not an object: {path}")
    return value


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _quiet_logger(cell_id: str) -> logging.Logger:
    logger = logging.getLogger(f"arc3-e1-four-cell.{cell_id}")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


def _run_cell(
    cell_id: str,
    *,
    protocol: dict[str, Any],
    manifests: Any,
    binding: Any,
    base_url: str,
    request_timeout_seconds: float,
    environments_dir: Path,
    remaining_seconds: float,
    finalization_reserve_seconds: float,
) -> dict[str, Any]:
    from arc_agi import Arcade, OperationMode

    pairs = protocol["development_game_seed_pairs"]
    game_ids = tuple(item["game_id"] for item in pairs)
    seeds = {item["game_id"]: item["seed"] for item in pairs}
    folds = {item["game_id"]: item["fold"] for item in pairs}

    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments_dir),
        recordings_dir="/tmp/arc3-e1-four-cell/recordings-disabled",
        logger=_quiet_logger(cell_id),
    )
    adapter = LocalFrameworkAdapter(arcade, seed_by_game=seeds)
    available = set(adapter.list_game_ids())
    missing = sorted(set(game_ids) - available)
    if missing:
        raise RuntimeError(f"frozen development games unavailable: {missing}")

    completion_clients: list[OpenAICompatibleCompletionClient] = []
    started = time.monotonic()
    with QueuedInferenceExecutor(
        maxsize=110,
        max_age_seconds=300,
        worker_count=8,
    ) as inference:
        def policy_factory(client: Any) -> E1Policy:
            completion = OpenAICompatibleCompletionClient(
                base_url,
                timeout_seconds=request_timeout_seconds,
            )
            completion_clients.append(completion)
            return E1Policy(
                manifest=manifests[cell_id],
                binding=binding,
                client=completion,
                inference=inference,
                max_new_tokens=protocol["design"]["max_new_tokens_per_request"],
                seed=seeds[client.game_id],
                request_timeout_seconds=request_timeout_seconds,
            )

        reserve = min(finalization_reserve_seconds, max(0.5, remaining_seconds / 2))
        result = CompetitionOrchestrator(
            adapter,
            game_ids,
            max_workers=8,
            max_actions=80,
            watchdog=DeadlineWatchdog(remaining_seconds, reserve),
            policy_factory=policy_factory,
            run_tag=f"plan8-{cell_id.lower()}",
        ).run()
        queue_record = {
            "policy": "minimum_fair_v1",
            "capacity": 110,
            "worker_count": 8,
            "max_age_seconds": 300,
            "max_observed_size": inference.queue.max_observed_size,
            "max_observed_age": inference.queue.max_observed_age,
        }
    for completion in completion_clients:
        completion.session.close()

    scores = exact_score_map(result.scorecard, game_ids)
    by_game = []
    for game_result in result.results:
        item = asdict(game_result)
        item.update(
            score=scores[game_result.game_id],
            score_unit=SCORE_UNIT,
            seed=seeds[game_result.game_id],
            fold=folds[game_result.game_id],
        )
        by_game.append(item)
    totals = {
        field: sum(int(item[field]) for item in by_game)
        for field in (
            "controller_iterations",
            "policy_failures",
            "inference_requests",
            "inference_completions",
            "inference_transport_failures",
            "inference_queue_failures",
            "inference_prompt_tokens",
            "inference_completion_tokens",
            "workspace_invocations",
            "parser_repairs",
        )
    }
    totals["inference_elapsed_seconds"] = sum(
        float(item["inference_elapsed_seconds"]) for item in by_game
    )
    totals["workspace_elapsed_seconds"] = sum(
        float(item["workspace_elapsed_seconds"]) for item in by_game
    )
    return {
        "cell_id": cell_id,
        "elapsed_seconds": time.monotonic() - started,
        "finalization_status": result.finalization_status,
        "scorecard_reported_mean": None
        if result.scorecard is None
        else result.scorecard.get("score"),
        "fixed_set_mean": sum(scores.values()) / len(scores),
        "queue": queue_record,
        "charged_totals": totals,
        "games": by_game,
    }


def main() -> int:
    args = parse_args()
    if args.base_url != "http://127.0.0.1:8000/v1":
        raise SystemExit("base-url must use the frozen loopback endpoint")
    if args.hard_seconds <= args.finalization_reserve_seconds or args.request_timeout_seconds <= 0:
        raise SystemExit("invalid experiment time bounds")
    if not args.environments_dir.is_dir():
        raise SystemExit("the frozen offline environment directory is missing")

    protocol = _load(args.protocol)
    feature_registry = _load(args.feature_registry)
    manifests = load_e1_feature_manifests(args.feature_registry)
    binding = binding_from_registry(args.feature_registry)
    if protocol.get("model_binding") != feature_registry.get("model_binding"):
        raise SystemExit("protocol and feature registry model bindings differ")
    spec = _load(args.launch_spec)
    identity = SimpleNamespace(
        candidate_id=binding.candidate_id,
        model_id=binding.model_id,
        model_revision=binding.revision,
        engine=binding.engine,
        reasoning_setting=binding.reasoning_setting,
        base_url=args.base_url,
        model_path=args.model_path,
    )
    argv, observed_packages = _validate_launch_spec(spec, identity)
    observed_gpu = _gpu_description()
    if args.expected_gpu_substring.lower() not in observed_gpu.lower():
        raise SystemExit(f"target GPU mismatch: {observed_gpu}")
    artifact = inventory_artifact_tree(args.model_path)
    if artifact.tree_sha256 != args.expected_artifact_sha256:
        raise SystemExit("frozen model artifact tree hash mismatch")

    output = {
        "schema_version": 1,
        "status": "running",
        "experiment_id": "E1-causal-four-cell-v1",
        "score_unit": SCORE_UNIT,
        "model_binding": protocol["model_binding"],
        "game_seed_pairs": protocol["development_game_seed_pairs"],
        "protocol_sha256": frozen_protocol_sha256(protocol),
        "feature_registry_sha256": frozen_feature_registry_sha256(feature_registry),
        "artifact": {
            "tree_sha256": artifact.tree_sha256,
            "file_count": artifact.file_count,
            "total_bytes": artifact.total_bytes,
        },
        "runtime": {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "observed_gpu": observed_gpu,
            "observed_packages": observed_packages,
            "python": sys.version,
        },
        "cells": {},
        "analysis": None,
    }
    _write_atomic(args.output, output)

    server_log_path = args.server_log or args.output.with_suffix(".server.log")
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    run_started = time.monotonic()
    environment = os.environ.copy()
    environment.update(spec["env"])
    environment["PYTHONUNBUFFERED"] = "1"
    with server_log_path.open("wb") as server_log:
        process = subprocess.Popen(argv, env=environment, stdout=server_log, stderr=subprocess.STDOUT)
        sampler = ResourceSampler(process.pid)
        sampler.start()
        try:
            _wait_ready(f"{args.base_url}/models", process, args.ready_timeout_seconds)
            output["runtime"]["model_ready_seconds"] = time.monotonic() - run_started
            canary_client = OpenAICompatibleCompletionClient(
                args.base_url,
                timeout_seconds=args.request_timeout_seconds,
            )
            try:
                canary = canary_client.complete(
                    {
                        "model": binding.model_id,
                        "messages": [{"role": "user", "content": "Reply exactly OK."}],
                        "temperature": 0,
                        "seed": 0,
                        "max_tokens": 8,
                        "chat_template_kwargs": {"enable_thinking": False},
                    }
                )
            finally:
                canary_client.session.close()
            output["runtime"]["completion_canary"] = {
                "response_nonempty": bool(canary.content),
                "prompt_tokens": canary.prompt_tokens,
                "completion_tokens": canary.completion_tokens,
                "elapsed_seconds": canary.elapsed_seconds,
            }
            if not canary.content:
                raise RuntimeError("completion endpoint canary returned empty content")
            _write_atomic(args.output, output)
            for cell_id in E1_FACTORIAL_CELLS:
                remaining = args.hard_seconds - (time.monotonic() - run_started)
                if remaining <= args.finalization_reserve_seconds:
                    raise TimeoutError("global four-cell finalization reserve reached")
                output["cells"][cell_id] = _run_cell(
                    cell_id,
                    protocol=protocol,
                    manifests=manifests,
                    binding=binding,
                    base_url=args.base_url,
                    request_timeout_seconds=args.request_timeout_seconds,
                    environments_dir=args.environments_dir,
                    remaining_seconds=remaining,
                    finalization_reserve_seconds=args.finalization_reserve_seconds,
                )
                _write_atomic(args.output, output)

            scores = {
                cell_id: {
                    game["game_id"]: game["score"]
                    for game in output["cells"][cell_id]["games"]
                }
                for cell_id in E1_FACTORIAL_CELLS
            }
            folds = {
                item["game_id"]: item["fold"]
                for item in protocol["development_game_seed_pairs"]
            }
            output["analysis"] = analysis_payload(
                scores,
                folds,
                minimum_nonzero_pairs=protocol["selection"]["minimum_nonzero_game_pairs"],
            )
            output["runtime"]["completed_at"] = datetime.now(timezone.utc).isoformat()
            output["runtime"]["elapsed_seconds"] = time.monotonic() - run_started
            output["runtime"]["peak_vram_bytes"] = sampler.peak_vram_bytes
            output["runtime"]["peak_ram_bytes"] = sampler.peak_ram_bytes
            output["status"] = "complete"
            validate_experiment_record(output, protocol, feature_registry)
            _write_atomic(args.output, output)
        except BaseException as exc:
            output["status"] = "failed_closed"
            output["failure"] = type(exc).__name__
            output["runtime"]["elapsed_seconds"] = time.monotonic() - run_started
            _write_atomic(args.output, output)
            raise
        finally:
            sampler.stop()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    print(json.dumps({"status": output["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
