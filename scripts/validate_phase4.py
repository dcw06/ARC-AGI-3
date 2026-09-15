"""Validate local Phase 4 preparation; never authorize target execution."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4 import validate_contract, run_synthetic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", action="store_true")
    args = parser.parse_args()
    validate_contract(ROOT)
    if args.load:
        report = run_synthetic(ROOT)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["local_load_passed"] else 1
    print("PHASE4_PREPARATION_PASSED target_gpu_certified=false phase4_complete=false GPU_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
