"""Replay and group local Phase 2 diagnostics without entering policy context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.diagnostics import DiagnosticReplayError, grouped_failure_report, load_bundles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="A diagnostic bundle or directory of bundles")
    parser.add_argument("--json", action="store_true", help="Emit the complete machine-readable report")
    parser.add_argument("--require-failure", action="store_true")
    args = parser.parse_args()
    try:
        report = grouped_failure_report(load_bundles(args.path))
    except (OSError, DiagnosticReplayError) as exc:
        print(f"PHASE2_DIAGNOSTIC_REPLAY_FAILED reason={type(exc).__name__}:{exc}")
        return 1
    if args.require_failure and report["reproduced_failures"] < 1:
        print("PHASE2_DIAGNOSTIC_REPLAY_FAILED reason=no_reproduced_failure")
        return 1
    if args.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print(
            "PHASE2_DIAGNOSTIC_REPLAY_PASSED "
            f"bundles={report['bundle_count']} transitions={report['transition_count']} "
            f"failures={report['reproduced_failures']}"
        )
        for row in report["groups"]:
            print(
                f"game={row['game_id']} treatment={row['treatment_id']} "
                f"category={row['category']} count={row['count']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
