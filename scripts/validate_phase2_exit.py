"""Validate the evidence-backed no-treatment Phase 2 closure."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase2_budget import read_ledger
from evaluation.phase2_contract import validate_contract
from evaluation.phase2_reproduction import compare_runs, sha


def validate(root=ROOT):
    validate_contract(root)
    closure = json.loads((root / "config/phase2_closure.json").read_text())
    review = "reports/phase2_cd82_evidence_review.md"
    if (closure.get("evidence_review") != review
            or sha(root / review) != closure.get("evidence_review_sha256")):
        raise ValueError("Phase 2 required evidence review missing or changed")
    if (closure["status"] != "complete_no_justified_treatment" or closure["decision"] != "retain_E1S-R"
            or closure["admitted_treatments"] or closure["implemented_treatments"]
            or closure["taxonomy_id"] != "unsupported_other" or closure["phase2_complete"] is not True):
        raise ValueError("unsupported Phase 2 closure")
    directory = root / closure["execution_directory"]
    paths = []
    for reference in closure["runs"]:
        path = (directory / reference["path"]).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path) != reference["sha256"]:
            raise ValueError("closure run artifact mismatch")
        paths.append(path)
    lock = json.loads((root / "notebooks/phase2-cd82/execution-lock.json").read_text())
    report = compare_runs(root, paths, lock)
    if (not report["failure_reproduced"] or report["admission_passed"]
            or any(r["trajectory_sha256"] != closure["trajectory_sha256"] for r in report["runs"])):
        raise ValueError("closure reproduction mismatch")
    ledger = read_ledger(root / closure["compute_ledger"])
    if (not ledger["inventory_confirmed"] or ledger["over_budget"]
            or not all(a["reconciled"] for a in ledger["attempts"].values())
            or ledger["charged_or_reserved_seconds"] != closure["charged_accelerator_seconds"]
            or ledger["remaining_seconds"] != closure["remaining_family_seconds"]):
        raise ValueError("closure accounting mismatch")
    registry = json.loads((root / "config/experiment_registry.yaml").read_text())
    if registry["phase_2_live_status"]["phase2_complete"] is not True:
        raise ValueError("registry disagrees with closure")
    return closure


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--historical", action="store_true")
    mode.add_argument("--current", action="store_true")
    args = parser.parse_args()
    if args.historical:
        from scripts.phase23_evidence import historical
        historical(ROOT)
        print("PHASE23_HISTORICAL_COMPLETION_PASSED current_eligibility_evaluated=false")
    else:
        record = validate()
        print(f"PHASE2_EXIT_PASSED scope=current_applicability decision=retain_E1S-R admitted_treatments=0 charged_seconds={record['charged_accelerator_seconds']}")
