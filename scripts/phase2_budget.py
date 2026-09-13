"""Report or append evidence-backed Phase 2 compute-accounting events."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase2_budget import append_event, read_ledger
from evaluation.phase2_reproduction import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["status", "reserve", "discover", "reconcile", "confirm-inventory"])
    parser.add_argument("--attempt-id")
    parser.add_argument("--seconds", type=float)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    ledger = ROOT / "config/phase2_compute_ledger.json"
    if args.operation == "status":
        result = read_ledger(ledger)
    else:
        kind = "inventory_confirmed" if args.operation == "confirm-inventory" else args.operation
        event = {"kind":kind}
        if kind != "inventory_confirmed":
            if not args.attempt_id or args.seconds is None:
                parser.error("attempt ID and seconds required")
            event.update(attempt_id=args.attempt_id, seconds=args.seconds)
        if kind not in {"reserve", "discover"}:
            if args.evidence is None or not args.evidence.is_file():
                parser.error("retained provider/runtime evidence required")
            event.update(evidence_path=str(args.evidence.resolve()), evidence_sha256=sha(args.evidence))
            evidence = json.loads(args.evidence.read_text())
            if kind == "reconcile":
                if (evidence.get("attempt_id") != args.attempt_id
                        or evidence.get("charged_accelerator_seconds") != args.seconds
                        or evidence.get("scope") != "all_accelerator_time_including_setup_and_failures"):
                    parser.error("evidence must bind attempt and seconds and include all setup/failed work")
            elif set(evidence.get("attempt_ids", [])) != set(read_ledger(ledger)["attempts"]):
                parser.error("provider attempt inventory does not match the ledger; record missing attempts first")
        result = append_event(ledger, event)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
