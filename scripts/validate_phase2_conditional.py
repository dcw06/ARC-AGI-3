"""Validate the fail-closed no-implementation outcome for Chunks 2.3/2.4."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.phase2_contract import Phase2ContractError
from evaluation.phase2_selection import validate_conditional_implementation


def main() -> int:
    try:
        closure = validate_conditional_implementation(ROOT)
    except Phase2ContractError as exc:
        print(f"PHASE2_CONDITIONAL_FAILED reason={exc}")
        return 1
    print(
        "PHASE2_CONDITIONAL_PASSED scope=conditional_implementation no_unselected_features=true phase_completion_not_evaluated=true closure_record=config/phase2_closure.json "
        f"status={closure['status']} selected={closure['selected_treatment']} "
        "e2_variants=0 memory_stores=0 retrieval_schemas=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
