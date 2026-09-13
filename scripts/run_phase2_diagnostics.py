"""Two fresh offline parent processes with retained diagnostic provenance."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.diagnostics import canonical_sha256
from agent.e1_policy import binding_from_registry
from agent.feature_manifest import load_e1_feature_manifests
from evaluation.m0_profile import inventory_artifact_tree
from evaluation.phase2_reproduction import GAME, SEED, verify_lock, compare_runs
from scripts.profile_m0_openai import _validate_launch_spec, _gpu_description
from scripts.run_e1_whole_run import _run_fresh, _write_atomic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--environments-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--worker-run-id")
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    verify_lock(ROOT, lock)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    if args.worker_run_id is None:
        paths = []
        try:
            for ordinal in (1, 2):
                run_id = f"cd82-{uuid.uuid4().hex}-R{ordinal}"
                run_dir = args.output_dir / run_id
                command = [sys.executable, str(Path(__file__).resolve()),
                    "--model-path",str(args.model_path),"--environments-dir",str(args.environments_dir),
                    "--output-dir",str(run_dir),"--lock",str(args.lock),"--worker-run-id",run_id]
                subprocess.run(command, check=True, timeout=lock["per_run_seconds"] + 120)
                paths.append(run_dir / "run.json")
                _write_atomic(args.output_dir / "execution.json", {"status":"running", "runs":[str(p.relative_to(args.output_dir)) for p in paths], "elapsed_seconds":time.monotonic()-started})
            report = compare_runs(ROOT, paths, lock)
            report["elapsed_seconds"] = time.monotonic()-started
            report["allocated_accelerator_hours"] = lock["maximum_diagnostic_accelerator_hours"]
            _write_atomic(args.output_dir / "comparison.json", report)
            _write_atomic(args.output_dir / "execution.json", {"status":"complete", "runs":[str(p.relative_to(args.output_dir)) for p in paths], "elapsed_seconds":time.monotonic()-started})
            print(json.dumps(report), flush=True)
        except BaseException as exc:
            _write_atomic(args.output_dir / "execution.json", {"status":"failed", "error":type(exc).__name__, "runs":[str(p.relative_to(args.output_dir)) for p in paths],"elapsed_seconds":time.monotonic()-started})
            raise
        return 0

    binding = binding_from_registry(ROOT / "config/e1_feature_manifests.yaml")
    gpu = _gpu_description()
    if "RTX PRO 6000" not in gpu:
        raise RuntimeError("diagnostic target GPU mismatch")
    artifact = inventory_artifact_tree(args.model_path)
    if artifact.tree_sha256 != lock["model_artifact_sha256"]:
        raise RuntimeError("model artifact hash mismatch")
    args.base_url = "http://127.0.0.1:8000/v1"
    args.request_timeout_seconds = 300
    args.diagnostics_dir = args.output_dir / "bundles"
    spec = json.loads((ROOT / "config/m0_launch_spec_q3vl30.json").read_text())
    identity = SimpleNamespace(candidate_id=binding.candidate_id,model_id=binding.model_id,
        model_revision=binding.revision,engine=binding.engine,reasoning_setting=binding.reasoning_setting,
        base_url=args.base_url,model_path=args.model_path)
    argv, packages = _validate_launch_spec(spec, identity)
    protocol = json.loads((ROOT / "config/e1_experiment_protocol.yaml").read_text())
    protocol["development_game_seed_pairs"] = [p for p in protocol["development_game_seed_pairs"] if p["game_id"] == GAME]
    if len(protocol["development_game_seed_pairs"]) != 1 or protocol["development_game_seed_pairs"][0]["seed"] != SEED:
        raise RuntimeError("frozen development pair missing")
    env = os.environ.copy()
    env.update(spec["env"])
    env["PYTHONUNBUFFERED"] = "1"
    cell = _run_fresh("E1S-R", block_id=args.worker_run_id, argv=argv,server_env=env,
        log_path=args.output_dir / "server.log",args=args,source_protocol=protocol,
        manifests=load_e1_feature_manifests(ROOT / "config/e1_feature_manifests.yaml"),binding=binding,
        deadline=started+lock["per_run_seconds"],reserve=600)
    bundle_paths = list(args.diagnostics_dir.rglob("*.json"))
    if len(bundle_paths) != 1:
        raise RuntimeError("expected one diagnostic bundle")
    envelope = {"schema_version":1,"run_id":args.worker_run_id,"game_id":GAME,"seed":SEED,
        "request_seed":SEED,"lock_sha256":canonical_sha256(lock),"model_artifact_sha256":artifact.tree_sha256,
        "observed_gpu":gpu,"observed_packages":packages,"cell":cell,
        "bundle":json.loads(bundle_paths[0].read_text()),"elapsed_seconds":time.monotonic()-started}
    _write_atomic(args.output_dir / "run.json", envelope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
