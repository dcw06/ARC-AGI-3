"""Validate locally provable Plan 8 Phase 0 activation prerequisites."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = {
    "competition_constraints.yaml", "authority_registry.yaml", "experiment_registry.yaml",
    "statistics_protocol.yaml", "control_registry.yaml", "model_manifest.yaml",
    "source_manifest.yaml", "dependency_manifest.lock", "runtime_profiles.yaml",
    "output_policy.yaml", "framework_adapter_manifest.yaml", "context_policy.yaml",
    "representation_manifest.yaml", "holdout_ledger.yaml", "success_criteria.yaml",
    "prediction_schema.json", "action_journal_schema.json", "lifecycle_journal_schema.json",
    "sealed_output_schema.json", "activation_record.json",
    "scorer_fixture.json",
}

REQUIRED_CONSTRAINTS = {
    "submission_mechanism",
    "runtime_seconds",
    "internet",
    "external_inputs",
    "evaluation_games",
    "leaderboard_split",
    "scorecards",
    "makes_per_environment",
    "in_flight_score_access",
    "reset_behavior",
    "reasoning_field_bytes_inclusive_max",
    "submission_allowance_per_day",
    "final_selection_count",
    "submission_filename",
    "submission_size_mb",
    "maximum_team_size",
    "identity_verification_required",
    "milestone_2_deadline",
    "entry_deadline_conservative",
    "team_merger_deadline",
    "final_deadline",
    "competition_data_license",
    "private_sharing_outside_team",
    "winner_license",
}


def check(condition: bool, label: str, failures: list[str]) -> None:
    print(f"{'PASS' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[str] = []
    check((ROOT / ".git").is_dir(), "version control initialized", failures)
    missing = REQUIRED - {path.name for path in CONFIG.iterdir()}
    check(not missing, "required registries and schemas exist", failures)
    for name in sorted(REQUIRED - missing):
        try:
            value = json.loads((CONFIG / name).read_text())
            valid = (
                isinstance(value.get("schema_version"), int)
                and value.get("schema_version", 0) >= 1
            )
        except Exception:
            valid = False
        check(valid, f"registry parses: {name}", failures)

    ignored = all(
        subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT, check=False).returncode == 0
        for path in (".env", ".kaggle/access_token", "notebooks/submission.ipynb")
    )
    check(ignored, "secrets and generated notebook are ignored", failures)

    production = "\n".join(path.read_text() for path in (ROOT / "agent").glob("*.py"))
    holdout = json.loads((CONFIG / "holdout_ledger.yaml").read_text())
    public_ids = holdout["development"] + holdout["h1"] + holdout["h2"]
    check(not any(game_id in production for game_id in public_ids), "no public game ID in production source", failures)
    check(".set_data(" not in production, "no shared GameAction mutation", failures)
    check("random.seed(" not in production, "no module-global RNG seed", failures)

    source_manifest = json.loads((CONFIG / "source_manifest.yaml").read_text())
    license_text = (ROOT / "LICENSE").read_text() if (ROOT / "LICENSE").exists() else ""
    check(
        source_manifest.get("project_license") == "Apache-2.0"
        and "Apache License" in license_text
        and "Version 2.0" in license_text,
        "project license is closed and present",
        failures,
    )

    check(version("arc-agi") == "0.9.9", "arc-agi version pinned", failures)
    check(version("arcengine") == "0.9.3", "arcengine version pinned", failures)
    manifest = json.loads((CONFIG / "framework_adapter_manifest.yaml").read_text())
    vendor = ROOT / "vendor" / "ARC-AGI-3-Agents"
    if vendor.exists():
        check(sha256(vendor / "agents" / "agent.py") == manifest["observed_hashes"]["vendor_agent_py"], "vendored Agent hash matches", failures)
        check(sha256(vendor / "agents" / "swarm.py") == manifest["observed_hashes"]["vendor_swarm_py"], "vendored Swarm hash matches", failures)

    constraints = json.loads((CONFIG / "competition_constraints.yaml").read_text())
    required_constraint_fields = {"value", "kind", "source", "verified_at", "verifier", "revalidate_at"}
    check(
        REQUIRED_CONSTRAINTS.issubset(constraints.get("constraints", {}))
        and all(
            required_constraint_fields.issubset(entry)
            for entry in constraints.get("constraints", {}).values()
        )
        and all(constraints.get("manual_checks", {}).values()),
        "required constraints and manual checks are complete and revalidatable",
        failures,
    )

    partitions = [holdout.get("development", []), holdout.get("h1", []), holdout.get("h2", [])]
    flattened = [game_id for partition in partitions for game_id in partition]
    check(
        holdout.get("status") == "active_reduced_exposure"
        and [len(partition) for partition in partitions] == [15, 5, 5]
        and len(flattened) == len(set(flattened))
        and holdout.get("h1_classification") == "reduced_exposure_guardrail_only"
        and holdout.get("h2_classification") == "reduced_exposure_guardrail_only"
        and isinstance(holdout.get("consumption_events"), list),
        "exposure audit and disjoint 15/5/5 reduced-exposure ledger are frozen",
        failures,
    )

    output_policy = json.loads((CONFIG / "output_policy.yaml").read_text())
    check(
        output_policy.get("retained_output_root") == "/kaggle/working"
        and output_policy.get("retained_allowlist") == ["submission.parquet"]
        and output_policy.get("scratch_root") == "/tmp/arc3-agent",
        "retained output and non-retained scratch roots are exact",
        failures,
    )

    adapter_manifest = json.loads((CONFIG / "framework_adapter_manifest.yaml").read_text())
    check(
        adapter_manifest.get("only_environment_call_boundary") == "agent.framework_adapter"
        and adapter_manifest.get("automatic_retries") == 0
        and adapter_manifest.get("redirects") == "disabled"
        and adapter_manifest.get("unknown_revision_policy") == "fail_closed"
        and adapter_manifest.get("startup_topology")
        == "direct_remote_bootstrap_serial_then_stream_play; local Arcade.make serialized",
        "adapter authority, retry policy, revision gate, and startup topology are frozen",
        failures,
    )

    from agent.runtime_audit import validate_mounted_runtime

    runtime_audit = validate_mounted_runtime("local_2026_09_06")
    check(runtime_audit.passed, "exact local runtime/source profile matches", failures)

    gateway = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_local_gateway.py")],
        cwd=ROOT,
        check=False,
    )
    check(gateway.returncode == 0, "production adapter matches pinned local REST gateway", failures)

    notebook = ROOT / "notebooks" / "submission.ipynb"
    check(notebook.exists(), "submission notebook built", failures)
    if notebook.exists():
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_submission.py")], cwd=ROOT, check=False)
        check(result.returncode == 0, "submission output and metadata policy", failures)

    if failures:
        print(f"LOCAL_PHASE0_FAILED count={len(failures)}")
        return 1
    print("LOCAL_PHASE0_PASSED")
    activation = json.loads((CONFIG / "activation_record.json").read_text())
    if (
        activation.get("status") == "active"
        and activation.get("authority") == "Plan 8"
        and not activation.get("blocking_checks")
        and activation.get("competition_rerun", {}).get("status") == "complete"
        and activation.get("competition_rerun", {}).get("expected_environment_inventory") == 110
        and activation.get("competition_rerun", {}).get("submission_output_contract") == "accepted"
        and activation.get("kaggle_notebook_smoke", {}).get("version_2", {}).get("retained_outputs")
        == ["submission.parquet"]
    ):
        print("PLAN8_ACTIVATED")
    else:
        print("PLAN8_ACTIVATION_BLOCKED external_checks_pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
