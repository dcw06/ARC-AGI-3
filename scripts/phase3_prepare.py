"""Validate inactive preparation or summarize externally supplied paired records."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase3 import paired_report, validate_preparation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, help="JSON list of complete-workload records")
    args = parser.parse_args()
    validate_preparation(ROOT)
    if args.records:
        print(json.dumps(paired_report(json.loads(args.records.read_text())), indent=2))
    else:
        print("PHASE3_PREPARATION_VALID inactive=true execution_closed=false")


if __name__ == "__main__":
    main()
