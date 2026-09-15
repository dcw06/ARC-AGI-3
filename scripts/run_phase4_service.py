"""Run an offline supervised service probe. Target GPU launch remains disabled."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4_runner import FAULTS, fake_worker, supervise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("fake", "target"), default="fake")
    parser.add_argument("--fault", choices=FAULTS, default="none")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scratch", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--admission-seconds", type=float, default=13, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.backend != "fake" or args.scratch is None:
            parser.error("worker requires an explicit fake scratch directory")
        return fake_worker(args.scratch, args.fault, args.admission_seconds)
    try:
        report = supervise(fault=args.fault, backend=args.backend)
    except PermissionError as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
