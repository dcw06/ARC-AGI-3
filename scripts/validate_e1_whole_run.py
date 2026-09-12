"""Validate and summarize the counterbalanced shared-resource E1 record."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.e1_whole_run import validate_whole_run_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "record",
        nargs="?",
        type=Path,
        default=ROOT / "reports/runs/e1-four-cell/e1-whole-run-four-cell-v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "config/e1_whole_run_protocol.yaml",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = args.record.read_bytes()
        record = json.loads(payload)
        protocol = json.loads(args.protocol.read_text())
        validate_whole_run_record(record, protocol)
        log_root = args.record.parent / "e1-whole-run-server-logs"
        for block in record["blocks"]:
            for cell in block["cells"].values():
                runtime = cell["fresh_runtime"]
                log_payload = (log_root / runtime["server_log"]).read_bytes()
                if hashlib.sha256(log_payload).hexdigest() != runtime["server_log_sha256"]:
                    raise ValueError("whole-run server log digest mismatch")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"E1_WHOLE_RUN_INVALID reason={type(exc).__name__}:{exc}")
        return 1

    print(f"E1_WHOLE_RUN_VALID sha256={hashlib.sha256(payload).hexdigest()}")
    print(
        "UNIT paired_complete_workload_run_block "
        f"blocks={len(record['blocks'])} elapsed={record['runtime']['elapsed_seconds']:.6f}"
    )
    for name, contrast in record["analysis"]["factorial_contrasts"].items():
        print(
            f"CONTRAST name={name} effect={contrast['mean_effect']:.8f} "
            f"nonzero_blocks={contrast['nonzero_blocks']} "
            f"p={contrast['two_sided_p_value']} status={contrast['status']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
