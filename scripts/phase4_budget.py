"""Reserve an already approved Phase 4 budget; never creates spending approval."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4_execution import reserve

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempt_id")
    args = parser.parse_args()
    print(json.dumps(reserve(ROOT, args.attempt_id), sort_keys=True))
