"""Validate the evidence-backed Phase 2 treatment-selection decision."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.phase2_contract import Phase2ContractError
from evaluation.phase2_selection import validate_treatment_selection


def main() -> int:
    try:
        selection = validate_treatment_selection(ROOT)
    except Phase2ContractError as exc:
        print(f"PHASE2_SELECTION_FAILED reason={exc}")
        return 1
    decision = selection["decision"]
    print(
        "PHASE2_SELECTION_PASSED historical_disposition_only=true phase2_complete=false "
        f"conclusion={decision['conclusion']} selected={decision['selected_treatment']} "
        f"activated={len(decision['activated_treatments'])} allocated_hours={decision['allocated_accelerator_hours']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
