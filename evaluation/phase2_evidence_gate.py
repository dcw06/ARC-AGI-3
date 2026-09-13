"""Resolve admission claims to retained, independently replayed parent artifacts."""
import json
from pathlib import Path

from evaluation.phase2_reproduction import compare_runs, sha


def artifact(root, reference):
    root = Path(root).resolve()
    path = (root / reference["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or sha(path) != reference["sha256"]:
        raise ValueError("missing, escaping or corrupt admission artifact")
    return path


def resolve_admission(record, root):
    root = Path(root)
    index = json.loads((root / "config/phase2_admission_index.json").read_text())
    entry = index["failures"][record["failure_id"]]
    lock = json.loads(artifact(root, entry["lock"]).read_text())
    paths = [artifact(root, ref) for ref in entry["runs"]]
    comparison = compare_runs(root, paths, lock)
    if not comparison["failure_reproduced"]:
        raise ValueError("target failure not reproduced from retained evidence")
    runs = {run["run_id"]: (run, json.loads(path.read_text()))
            for run, path in zip(comparison["runs"], paths)}
    if set(runs) != {r["run_id"] for r in record["reproductions"]}:
        raise ValueError("failure references different parent runs")
    for reference in record["reproductions"]:
        run, envelope = runs[reference["run_id"]]
        transitions = {r["transition"]["transition_id"] for r in envelope["bundle"]["records"] if r["transition"]}
        if (reference["evidence_sha256"] != run["file_sha256"]
                or (reference["game_id"], reference["seed"]) != (envelope["game_id"], envelope["seed"])
                or record["failure_signature_sha256"] != run["trajectory_sha256"]
                or reference["failure_signature_sha256"] != run["trajectory_sha256"]
                or not set(reference["transition_ids"]) <= transitions):
            raise ValueError("claimed signature, content hash or transition is not in retained evidence")
    # Reproduction is necessary, not causal attribution. Require a separately
    # retained human-reviewed diagnosis, bound to these exact evidence artifacts.
    review = json.loads(artifact(root, entry["attribution_review"]).read_text())
    if (review.get("status") != "reviewed_single_capability" or not review.get("reviewer")
            or not review.get("rationale") or review.get("failure_id") != record["failure_id"]
            or review.get("missing_capabilities") != [record["diagnosis"]["missing_capability"]]
            or review.get("run_sha256s") != sorted(run["file_sha256"] for run, _ in runs.values())
            or review.get("evidence_refs") != record["diagnosis"]["evidence_refs"]
            or review.get("excluded_alternative_causes") != record["diagnosis"]["excluded_alternative_causes"]):
        raise ValueError("single-capability attribution review is absent or not evidence-bound")
    available_refs = set()
    for run_id, (_, envelope) in runs.items():
        for transition in envelope["bundle"]["records"]:
            if transition["transition"]:
                available_refs.add(run_id + "/" + transition["transition"]["transition_id"])
    if not set(review["evidence_refs"]) <= available_refs:
        raise ValueError("attribution cites unresolved transitions")
    if record["candidate_treatment"] in {"E2a", "E2b", "E2c", "E2d", "E4"}:
        from evaluation.phase2_sequences import validate_sequences
        extension = json.loads(artifact(root, entry["capture_extension"]).read_text())
        from agent.diagnostics import canonical_sha256
        if extension.get("version") != 2 or extension.get("policy_delta") != "none" or extension.get("parent_lock_sha256") != canonical_sha256(lock):
            raise ValueError("sequence capture lacks an exact registered parent")
        expected_sources = {"evaluation/phase2_sequences.py", "scripts/run_phase2_diagnostics_v2.py"}
        if set(extension["sources"]) != expected_sources:
            raise ValueError("sequence capture source inventory drift")
        for name, digest in extension["sources"].items():
            artifact(root, {"path":name,"sha256":digest})
        resolved = set()
        for ref in entry.get("sequences", []):
            sidecar = json.loads(artifact(root, ref).read_text())
            run_id = sidecar["run_id"]
            if run_id not in runs:
                raise ValueError("sequence belongs to another run")
            resolved.update(validate_sequences(sidecar, runs[run_id][1]["bundle"]))
        if not set(review["evidence_refs"]) <= resolved:
            raise ValueError("required exact sequence evidence absent, omitted or corrupt")
    return comparison
