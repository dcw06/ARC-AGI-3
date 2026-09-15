"""Validate Phase 3 closure under the supplied conditional H1 eligibility rule."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.validate_phase2_exit import validate as validate_phase2
from evaluation.h1_guardrail import validate_inactive_guardrail
from evaluation.phase3 import validate_preparation


def validate(root=ROOT, *, require_exit=False):
    validate_phase2(root)
    record = json.loads((root / "config/phase3_decision.json").read_text())
    required = {"config/phase2_closure.json", "config/operational_primary.yaml",
                "config/e1_feature_manifests.yaml", "reports/phase2_cd82_evidence_review.md"}
    if not isinstance(record.get("bindings"), dict) or set(record["bindings"]) != required:
        raise ValueError("Phase 3 requires the exact provenance binding inventory")
    for name,digest in record["bindings"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Phase 3 parent or review provenance drift")
    if (record["parent_policy"] != "E1S-R" or record["selected_policy"] != "E1S-R"
            or record["admitted_treatments"] or record["allocated_accelerator_seconds"] != 0
            or record["phase2_budget_transfer"] is not False
            or set(record["candidate_dispositions"]) != {"E5","E6-DISC","E6-REPEAT"}
            or any(v["status"] != "not_admitted" or not v["reason"] for v in record["candidate_dispositions"].values())):
        raise ValueError("unsupported Phase 3 treatment activation")
    validate_preparation(root)
    validate_inactive_guardrail(root, record)
    if (record["status"] != "complete_no_justified_treatment_H1_not_applicable"
            or record["phase3_complete"] is not True
            or record["completion_basis"] != "user_supplied_H1_v3_no_candidate_rule"
            or record["completion_scope"] != "conditional_phase_disposition_not_architecture_performance_acceptance"):
        raise ValueError("unsupported Phase 3 completion claim")
    registry = json.loads((root / "config/experiment_registry.yaml").read_text())
    review = registry["phase_3_review"]
    if (registry["current_phase"] != record["status"] or review["status"] != record["status"]
            or review["phase3_complete"] is not True or review["admitted_treatments"]
            or review["parent"] != record["parent_policy"] or review["H1_consumed"] is not False):
        raise ValueError("registry disagrees with Phase 3 closure")
    criteria = json.loads((root / "config/success_criteria.yaml").read_text())["phase_3"]
    if (criteria["status"] != record["status"] or criteria["acceptance_claim"] is not False
            or criteria["H1_executed"] is not False or criteria["admitted_treatments"]):
        raise ValueError("success criteria overstate Phase 3 evidence")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-exit",action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--historical", action="store_true", help="Verify immutable archived completion; grants no current eligibility")
    mode.add_argument("--current", action="store_true", help="Check current applicability (default); rejects later drift or supersession")
    args = parser.parse_args()
    try:
        if args.historical:
            from scripts.phase23_evidence import historical
            historical(ROOT)
            print("PHASE23_HISTORICAL_COMPLETION_PASSED current_eligibility_evaluated=false")
            return 0
        validate(require_exit=args.require_exit)
    except (ValueError,KeyError,OSError,TypeError) as exc:
        print(f"PHASE3_VALIDATION_FAILED scope={'historical' if args.historical else 'current_applicability'} reason={exc}")
        return 1
    label = "PHASE3_EXIT_PASSED" if args.require_exit else "PHASE3_REVIEW_PASSED"
    print(f"{label} scope=current_applicability selected=E1S-R admitted=0 H1=not_applicable_unconsumed phase3_complete=true acceptance_claim=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
