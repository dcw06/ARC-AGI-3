"""Validate downloaded diagnostic evidence against the pre-launch lock."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.phase2_reproduction import compare_runs
from evaluation.phase2_budget import read_ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--report-only", action="store_true", help="validate integrity without requiring target reproduction")
    parser.add_argument("--capture-lock",type=Path, default=ROOT / "notebooks/phase2-cd82-v2/capture-extension.json")
    args = parser.parse_args()
    local = json.loads((ROOT / "notebooks/phase2-cd82/execution-lock.json").read_text())
    remote = json.loads((args.directory / "execution-lock.json").read_text())
    if local != remote:
        raise ValueError("downloaded lock differs from pre-launch lock")
    execution = json.loads((args.directory / "execution.json").read_text())
    if execution["status"] != "complete":
        raise ValueError("diagnostic execution incomplete")
    paths = [(args.directory / name).resolve() for name in execution["runs"]]
    if any(not path.is_relative_to(args.directory.resolve()) for path in paths):
        raise ValueError("run path escapes evidence directory")
    cost = json.loads((args.directory / "notebook-cost.json").read_text())
    if not 0 < cost["elapsed_seconds"] <= 7200:
        raise ValueError("diagnostic family allocation exceeded")
    report = compare_runs(ROOT,paths,local)
    extension_path = args.directory / "capture-extension.json"
    report["capture_version"] = 1
    report["intermediate_sequence_evidence"] = "not_retained"
    if extension_path.exists():
        extension = json.loads(extension_path.read_text())
        if extension != json.loads(args.capture_lock.read_text()) or not extension.get("execution_authorized"):
            raise ValueError("capture extension differs from funded pre-launch lock")
        from evaluation.phase2_sequences import validate_sequences
        from evaluation.phase2_reproduction import sha
        from agent.diagnostics import canonical_sha256
        if extension["parent_lock_sha256"] != canonical_sha256(local):
            raise ValueError("capture extension parent mismatch")
        for name,digest in extension["sources"].items():
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT) or sha(path) != digest:
                raise ValueError("capture extension source drift")
        exact_refs = []
        for path in paths:
            sidecars = list(path.parent.rglob("*.sequences"))
            if len(sidecars) != 1:
                raise ValueError("missing or ambiguous sequence sidecar")
            envelope = json.loads(path.read_text())
            exact_refs.extend(validate_sequences(json.loads(sidecars[0].read_text()),envelope["bundle"]))
        report["capture_version"] = 2
        report["intermediate_sequence_evidence"] = {"exact_transition_refs":sorted(exact_refs)}
    report["charged_accelerator_hours"] = cost["elapsed_seconds"] / 3600
    report["compute_ledger"] = read_ledger(ROOT / "config/phase2_compute_ledger.json")
    report["remaining_phase2_hours"] = report["compute_ledger"]["remaining_seconds"] / 3600
    report["cost_reconciliation_required"] = True
    report["phase2_complete"] = False
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if args.report_only or report["failure_reproduced"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
