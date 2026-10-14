"""Build a deterministic, GPU-disabled fixture bundle and request schedule."""
import hashlib
import json
import zipfile
from pathlib import Path

from research.mechanic_prediction_v1 import fixtures
from research.mechanic_prediction_v1.independent_keys import derive
from research.mechanic_prediction_v1.oracle import adjudicate
from research.mechanic_prediction_v1.prompts import MAX_COMPLETION_TOKENS, render_request
from research.mechanic_prediction_v1.schema import validate_response
from research.mechanic_prediction_v1 import prompts
from research.mechanic_prediction_v1 import shortcuts


REQUEST_BYTE_CEILING = 16_384
ARMS = ("reference", "candidate")


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _public_artifact(scenarios):
    return {
        "version": "mechanic_prediction_public_v1",
        "cases": [{
            "scenario_id": scenario["scenario_id"], "split": scenario["split"],
            "family": scenario["family"], "evidence": fixtures.public_scenario(scenario),
        } for scenario in scenarios],
    }


def _key_artifact(scenarios):
    rows = []
    for scenario in scenarios:
        oracle = adjudicate(scenario["mechanisms"], scenario["history"], scenario["proposed_action"], scenario["current_observation"])
        independent = derive(scenario)
        for field in ("status", "prediction", "compatible_mechanism_ids", "declared_mechanism_count"):
            if oracle[field] != independent[field]:
                raise ValueError(f"independent answer derivations disagree for {scenario['scenario_id']}: {field}")
        rows.append({
            **independent,
            "family": scenario["family"],
            "split": scenario["split"],
            "declared_mechanisms": scenario["mechanisms"],
        })
    return {"version": "mechanic_prediction_keys_v1", "scope": "declared_mechanism_space_only", "cases": rows}


def _schedule(scenarios):
    entries = []
    request_digests = set()
    evidence_digests = {}
    for index, scenario in enumerate(scenarios):
        arms = ARMS if index % 2 == 0 else tuple(reversed(ARMS))
        user_evidence = None
        for arm in arms:
            request = render_request(scenario, arm)
            request_hash = sha256(request)
            user_hash = hashlib.sha256(request["messages"][1]["content"].encode("utf-8")).hexdigest()
            if request_hash in request_digests:
                raise ValueError("duplicate rendered model request")
            request_digests.add(request_hash)
            if user_evidence is not None and user_hash != user_evidence:
                raise ValueError("paired arms differ in evidence bytes")
            user_evidence = user_hash
            request_bytes = len(canonical_bytes(request))
            if request_bytes > REQUEST_BYTE_CEILING:
                raise ValueError("request exceeds frozen UTF-8 byte ceiling")
            if request["max_tokens"] != MAX_COMPLETION_TOKENS:
                raise ValueError("completion ceiling drift")
            evidence_digests[(scenario["scenario_id"], arm)] = user_hash
            entries.append({
                "request_id": f"Q{len(entries) + 1:03d}", "scenario_id": scenario["scenario_id"],
                "split": scenario["split"], "arm": arm, "request_sha256": request_hash,
                "evidence_sha256": user_hash, "request_utf8_bytes": request_bytes,
                "max_completion_tokens": request["max_tokens"], "temperature": request["temperature"],
                "seed": request["seed"],
            })
    return {"version": "mechanic_prediction_schedule_v1", "request_count": len(entries),
            "ordering": "scenario-id order; within each scenario, arm order alternates by scenario index",
            "entries": entries}


def make_bundle():
    scenarios = fixtures.all_scenarios()
    public = _public_artifact(scenarios)
    keys = _key_artifact(scenarios)
    schedule = _schedule(scenarios)
    manifest = {"version": "mechanic_prediction_manifest_v1", "sha256": {
        "fixtures": sha256(public), "keys": sha256(keys), "schedule": sha256(schedule),
    }}
    shortcut = shortcuts_report(scenarios, keys)
    byte_counts = [entry["request_utf8_bytes"] for entry in schedule["entries"]]
    token_audit = {
        "request_count": len(schedule["entries"]),
        "maximum_request_utf8_bytes": max(byte_counts),
        "mean_request_utf8_bytes": sum(byte_counts) / len(byte_counts),
        "request_utf8_byte_ceiling": REQUEST_BYTE_CEILING,
        "completion_token_ceiling": MAX_COMPLETION_TOKENS,
        "model_tokenizer": "not frozen; no compatible model tokenizer is installed in this Windows environment",
        "token_count_status": "not_measured; UTF-8 byte measurements are not represented as model tokens",
        "duplicate_request_count": 0,
        "paired_evidence_bytes_identical": True,
    }
    return {"fixtures": public, "keys": keys, "schedule": schedule, "manifest": manifest,
            "shortcuts": shortcut, "token_audit": token_audit}


def shortcuts_report(scenarios, key_artifact):
    from research.mechanic_prediction_v1.score import shortcut_report
    keys = {row["scenario_id"]: row for row in key_artifact["cases"]}
    return shortcut_report(scenarios, keys)


def scripted_rehearsal(bundle):
    scenarios = fixtures.all_scenarios()
    request_by_id = {entry["request_id"]: entry for entry in bundle["schedule"]["entries"]}
    outputs = {}
    cases = {scenario["scenario_id"]: scenario for scenario in scenarios}
    for request_id, entry in request_by_id.items():
        request = render_request(cases[entry["scenario_id"]], entry["arm"])
        if sha256(request) != entry["request_sha256"]:
            raise ValueError("scheduled request replay mismatch")
        rendered = json.dumps(request, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        raw = prompts.scripted_reader(rendered)
        valid_ids = [record["record_id"] for record in cases[entry["scenario_id"]]["history"]]
        parsed = validate_response(raw, valid_ids)
        outputs[request_id] = parsed
    return {"scripted_request_count": len(outputs), "valid_outputs": len(outputs),
            "reader_input_contract": "rendered request JSON only; no fixture or key argument"}


def write_bundle(bundle, root=None):
    root = Path(root) if root else Path(__file__).resolve().parent
    names = {"fixtures": "fixtures.json", "keys": "independent_keys.json", "schedule": "request_schedule.json",
             "manifest": "manifest.json", "shortcuts": "shortcut_report.json", "token_audit": "token_audit.json"}
    for key, filename in names.items():
        (root / filename).write_bytes(canonical_bytes(bundle[key]) + b"\n")
    return {key: str(root / filename) for key, filename in names.items()}


def write_review_package(repo_root=None, output_dir=None):
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    output_dir = Path(output_dir) if output_dir else repo_root / "reports/mechanic_prediction_v1/gpu_disabled_review"
    output_dir.mkdir(parents=True, exist_ok=True)
    include = [
        "research/mechanic_prediction_v1/__init__.py",
        "research/mechanic_prediction_v1/fixtures.py",
        "research/mechanic_prediction_v1/build.py",
        "research/mechanic_prediction_v1/oracle.py",
        "research/mechanic_prediction_v1/independent_keys.py",
        "research/mechanic_prediction_v1/prompts.py",
        "research/mechanic_prediction_v1/schema.py",
        "research/mechanic_prediction_v1/shortcuts.py",
        "research/mechanic_prediction_v1/score.py",
        "research/mechanic_prediction_v1/diagnostics.py",
        "research/mechanic_prediction_v1/replay.py",
        "research/mechanic_prediction_v1/fixtures.json",
        "research/mechanic_prediction_v1/independent_keys.json",
        "research/mechanic_prediction_v1/request_schedule.json",
        "research/mechanic_prediction_v1/manifest.json",
        "research/mechanic_prediction_v1/shortcut_report.json",
        "research/mechanic_prediction_v1/token_audit.json",
        "tests/test_mechanic_prediction_v1.py",
        "tests/test_mechanic_prediction_v1_oracle.py",
        "reports/mechanic_prediction_v1/benchmark_spec.md",
        "reports/mechanic_prediction_v1/prediction_protocol.md",
        "reports/mechanic_prediction_v1/stage_c_experiment_selection_proposal.md",
        "reports/mechanic_prediction_v1/stage_d_closed_loop_transfer_proposal.md",
        "reports/mechanic_prediction_v1/gpu_disabled_review.md",
        "reports/mechanic_prediction_v1/shortcut_report.md",
        "reports/mechanic_prediction_v1/cpu_test_receipt.json",
    ]
    files = {name: hashlib.sha256((repo_root / name).read_bytes()).hexdigest()
             for name in include if (repo_root / name).is_file()}
    manifest = {
        "status": "ready_for_independent_review",
        "gpu_enabled": False,
        "model_calls": 0,
        "live_game_dispatch": False,
        "old_authorizations_reused": False,
        "exact_model_token_count_measured": False,
        "files": files,
    }
    manifest_path = output_dir / "review_manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest) + b"\n")
    archive_path = output_dir.parent / "mechanic_prediction_v1_gpu_disabled_review.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(repo_root / name, arcname=name)
        archive.write(manifest_path, arcname="reports/mechanic_prediction_v1/gpu_disabled_review/review_manifest.json")
    return {"status": manifest["status"], "file_count": len(files), "archive": str(archive_path)}


def write_reports(bundle, repo_root=None):
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    report = bundle["shortcuts"]
    lines = [
        "# Shortcut Baseline Report v1", "",
        "Computed mechanically before any model execution. Unit: one scenario. Accuracy is scored only on determinable scenarios; unsupported certainty is reported separately on underdetermined scenarios.", "",
        "The strongest shortcut is selected on the development split only. The evaluation split is not used for shortcut selection.", "",
        "| Shortcut | Dev determinate accuracy | Eval determinate accuracy | Eval unsupported certainty | Wrong eval determinate scenarios |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, result in report["shortcuts"].items():
        dev = result["development_summary"]["prediction_accuracy_on_determinable"]
        evaluation = result["evaluation_summary"]
        accuracy = evaluation["prediction_accuracy_on_determinable"]
        certainty = evaluation["unsupported_certainty_on_underdetermined"]
        lines.append(f"| {name} | {dev:.3f} | {accuracy:.3f} | {certainty:.3f} | {len(result['wrong_determinable_scenarios'])} |")
    lines.extend(["", f"Development-selected strongest shortcut: `{report['strongest_declared_shortcut']}`.",
                  f"Wrong determinable evaluation scenarios: {', '.join(report['strongest_wrong_determinable_scenarios'])}.",
                  "", "These are small synthetic construction checks, not model results or a generalization estimate.", ""])
    path = repo_root / "reports/mechanic_prediction_v1/shortcut_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


if __name__ == "__main__":
    artifact = make_bundle()
    write_bundle(artifact)
    rehearsal = scripted_rehearsal(artifact)
    shortcut_report_path = write_reports(artifact)
    package = write_review_package()
    print(json.dumps({"built": True, "scenarios": len(artifact["fixtures"]["cases"]),
                      "requests": artifact["schedule"]["request_count"],
                      "strongest_shortcut": artifact["shortcuts"]["strongest_declared_shortcut"],
                      "scripted_rehearsal": rehearsal, "shortcut_report": shortcut_report_path,
                      "review_package": package}, sort_keys=True))