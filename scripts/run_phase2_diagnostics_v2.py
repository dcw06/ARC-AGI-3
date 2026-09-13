"""Explicit V2 capture entry point; delegates policy execution to frozen V1."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase2_reproduction import sha
from agent.diagnostics import canonical_sha256
from evaluation.phase2_sequences import SequenceRecorder
from scripts import run_e1_four_cell, run_phase2_diagnostics


def main():
    extension = json.loads((ROOT / "config/phase2_capture_extension.json").read_text())
    if extension["version"] != 2 or extension["policy_delta"] != "none" or not extension.get("execution_authorized"):
        raise ValueError("invalid capture extension")
    parent = json.loads((ROOT / "config/phase2_diagnostic_execution_lock.json").read_text())
    if canonical_sha256(parent) != extension["parent_lock_sha256"]:
        raise ValueError("capture extension parent mismatch")
    for path, digest in extension["sources"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("capture extension source drift")
    run_e1_four_cell.TransitionDiagnosticRecorder = SequenceRecorder
    # Both fresh child processes re-enter this explicit extension entry point.
    run_phase2_diagnostics.__file__ = __file__
    return run_phase2_diagnostics.main()


if __name__ == "__main__":
    raise SystemExit(main())
