"""Execute only a source-locked and budget-reserved private fixture prescreen."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4_target import run_target, worker


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--started", type=float, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scratch", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 <= args.started <= time.monotonic():
        parser.error("invalid first-cell monotonic timestamp")
    if args.worker:
        if args.scratch is None:
            parser.error("scratch required")
        worker(args.output, args.scratch, args.started)
    else:
        result = run_target(args.output, args.started)
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(0 if result["status"] == "passed_fixture_prescreen_only" else 1)
