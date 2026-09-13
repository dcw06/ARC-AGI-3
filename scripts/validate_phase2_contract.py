"""Validate the frozen Phase 2 contract and any proposed admission artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.phase2_contract import (
    Phase2ContractError,
    file_sha256,
    validate_contract,
    validate_failure_record,
    validate_treatment_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failure", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.manifest is not None and args.failure is None:
        print("PHASE2_CONTRACT_FAILED reason=manifest_requires_failure_record")
        return 1
    try:
        contract = validate_contract(ROOT)
        contract_path = ROOT / "config/phase2_contract.yaml"
        contract_sha256 = file_sha256(contract_path)
        failure = None
        if args.failure is not None:
            failure = json.loads(args.failure.read_text())
            validate_failure_record(
                failure,
                contract,
                contract_sha256=contract_sha256,
                require_admitted=args.manifest is not None,
            )
        if args.manifest is not None and failure is not None:
            manifest = json.loads(args.manifest.read_text())
            validate_treatment_manifest(
                manifest,
                failure,
                contract,
                contract_sha256=contract_sha256,
            )
    except (OSError, json.JSONDecodeError, Phase2ContractError) as exc:
        print(f"PHASE2_CONTRACT_FAILED reason={type(exc).__name__}:{exc}")
        return 1

    print(
        "PHASE2_CONTRACT_PASSED "
        f"sha256={contract_sha256} cap=2 activated=0 mode=strictly_sequential"
    )
    if args.failure is not None:
        print("PHASE2_FAILURE_RECORD_PASSED")
    if args.manifest is not None:
        print("PHASE2_TREATMENT_MANIFEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
