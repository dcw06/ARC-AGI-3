"""Verify two independently captured parent trajectories; never infer a treatment."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from agent.diagnostics import canonical_sha256, replay_bundle
from agent.e1_policy import e1_system_prompt
from agent.feature_manifest import load_e1_feature_manifests, validate_e1_proposal

GAME = "cd82-fb555c5d"
SEED = 104759


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_lock(root, lock):
    if any(lock.get(key) != expected for key,expected in {
        "schema_version":1,"protocol_id":"phase2.cd82.parent-diagnostic.v1",
        "game_id":GAME,"environment_seed":SEED,"request_seed":SEED,
        "runs":2,"actions_per_run":80,"requests_per_run":80,
        "per_run_seconds":3000,"maximum_diagnostic_accelerator_hours":2,
        "automatic_admission":False,"attribution_default":"unsupported_other",
    }.items()):
        raise ValueError("diagnostic execution parameters drifted")
    required = {"agent/e1_policy.py", "agent/representation.py", "agent/feature_manifest.py",
        "agent/diagnostics.py", "agent/competition_loop.py", "agent/framework_adapter.py",
        "scripts/run_phase2_diagnostics.py", "scripts/run_e1_four_cell.py",
        "scripts/run_e1_whole_run.py", "evaluation/phase2_reproduction.py",
        "config/operational_primary.yaml", "config/e1_feature_manifests.yaml",
        "config/phase2_contract.yaml", "config/phase2_diagnostic_schema.json"}
    if not required <= set(lock["sources"]):
        raise ValueError("incomplete diagnostic source lock")
    for name, digest in lock["sources"].items():
        if sha(Path(root) / name) != digest:
            raise ValueError(f"diagnostic source drift: {name}")
    manifest = load_e1_feature_manifests(Path(root) / "config/e1_feature_manifests.yaml")["E1S-R"]
    if hashlib.sha256(e1_system_prompt(manifest).encode()).hexdigest() != lock["prompt_sha256"]:
        raise ValueError("diagnostic prompt drift")
    return manifest


def validate_run(root, path, lock):
    manifest = verify_lock(root, lock)
    value = json.loads(Path(path).read_text())
    if value["lock_sha256"] != canonical_sha256(lock):
        raise ValueError("run provenance differs from frozen lock")
    if value["game_id"] != GAME or value["seed"] != SEED or value["request_seed"] != SEED:
        raise ValueError("game or seed drift")
    if value["model_artifact_sha256"] != lock["model_artifact_sha256"]:
        raise ValueError("model artifact drift")
    spec = json.loads((Path(root) / "config/m0_launch_spec_q3vl30.json").read_text())
    if "RTX PRO 6000" not in value["observed_gpu"] or value["observed_packages"] != spec["required_packages"]:
        raise ValueError("target runtime drift")
    bundle = value["bundle"]
    if bundle["run_id"] != value["run_id"] or bundle["game_id"] != GAME or bundle["treatment_id"] != "E1S-R" or bundle["seed"] != SEED:
        raise ValueError("bundle identity drift")
    replay_bundle(bundle)
    if bundle["capture_errors"]:
        raise ValueError("diagnostic capture was incomplete")
    cell = value["cell"]
    if cell["cell_id"] != "E1S-R" or len(cell["games"]) != 1 or cell["finalization_status"] != "acknowledged":
        raise ValueError("incomplete parent lifecycle")
    fresh = cell["fresh_runtime"]
    if fresh["block_id"] != value["run_id"] or not fresh["fresh_process"] or not fresh["completion_canary_passed"]:
        raise ValueError("fresh model process not attested")
    if value["elapsed_seconds"] > lock["per_run_seconds"] or fresh["peak_vram_bytes"] > 90 * 1024**3 or fresh["peak_ram_bytes"] > 180 * 1024**3:
        raise ValueError("diagnostic resource ceiling exceeded")
    game = cell["games"][0]
    if game["score_unit"] != "official_RHAE_percent":
        raise ValueError("score unit drift")
    records = bundle["records"]
    queue = cell["queue"]
    if any(queue[k] != v for k, v in {"policy":"minimum_fair_v1", "capacity":110,"worker_count":8,"max_age_seconds":300}.items()):
        raise ValueError("queue drift")
    if game["game_id"] != GAME or game["seed"] != SEED or len(records) != game["controller_iterations"]:
        raise ValueError("missing transition records")
    signatures = []
    valid = 0
    for index, record in enumerate(records, 1):
        if record["iteration"] != index:
            raise ValueError("noncontiguous trajectory")
        if index > 1 and records[index-2]["post"] != record["pre"]:
            raise ValueError("disconnected trajectory")
        proposal = record["proposal_or_fallback"]
        if record["proposal_rejection_category"] == "none":
            if len(proposal["model_proposals"]) != 1 or proposal["model_proposals"][0]["content_availability"] != "exact":
                raise ValueError("missing exact model proposal")
            decision = validate_e1_proposal(json.loads(proposal["model_proposals"][0]["content"]), manifest=manifest, legal_actions=record["pre"]["legal_actions"])
            actual = proposal["executed_decision"]
            if actual["source"] != "model:E1S-R" or actual["action_id"] != decision.action_id or actual["action_data"] != dict(decision.action_data):
                raise ValueError("silent fallback or proposal/dispatch mismatch")
            valid += 1
        signatures.append({
            "pre": record["pre"], "post": record["post"],
            "action_id": proposal["executed_decision"]["action_id"],
            "action_data": proposal["executed_decision"]["action_data"],
            "category": record["proposal_rejection_category"],
            "dispatch": record["dispatch_status"],
        })
    clean = (
        len(records) == 80 and valid == 80 and game["acknowledged_actions"] == 80
        and game["ambiguous_actions"] == 0 and game["policy_failures"] == 0
        and game["inference_requests"] == 80 and game["inference_completions"] == 80
        and game["inference_queue_failures"] == 0 and game["inference_transport_failures"] == 0
        and game["workspace_invocations"] == 0 and game["terminal_reason"] == "action_cap"
        and all(r["dispatch_status"] == "acknowledged" and r["action_legal"] for r in records)
    )
    zero_levels = game["levels_completed"] == 0 and all(r["post"] and r["post"]["levels_completed"] == 0 for r in records)
    return {
        "run_id":value["run_id"], "file_sha256":sha(path),
        "trajectory_sha256":canonical_sha256(signatures),
        "valid_proposals":valid, "grid_change_transitions":sum(bool(r["transition"] and r["transition"]["changed_cells"] != 0) for r in records),
        "levels_completed":game["levels_completed"], "score":game["score"],
        "terminal_reason":game["terminal_reason"],
        "rejection_categories":dict(Counter(r["proposal_rejection_category"] for r in records)),
        "dispatch_statuses":dict(Counter(r["dispatch_status"] for r in records)),
        "outcome_unknown_phases":dict(Counter(r["outcome_unknown_phase"] for r in records)),
        "clean_unproductive_trajectory":clean and zero_levels and game["score"] == 0,
    }


def compare_runs(root, paths, lock):
    if len(paths) != 2:
        raise ValueError("exactly two fresh parent runs required")
    runs = [validate_run(root, path, lock) for path in paths]
    if len({r["run_id"] for r in runs}) != 2:
        raise ValueError("duplicate run IDs")
    matched = len({r["trajectory_sha256"] for r in runs}) == 1
    reproduced = matched and all(r["clean_unproductive_trajectory"] for r in runs)
    return {
        "schema_version":1, "record_type":"phase2_cross_run_reproduction",
        "runs":runs, "matching_trajectory_signatures":matched,
        "failure_reproduced":reproduced, "taxonomy_id":"unsupported_other",
        "selected_treatment":None, "admission_passed":False,
        "conclusion":"stable_unproductive_trajectory_without_capability_attribution" if reproduced else "target_failure_not_reproduced",
        "score_unit":"official_RHAE_percent",
        "signature_rule":"ordered_pre_post_action_category_dispatch_excluding_run_ids_and_model_wording_v1",
    }
