"""Versioned source lock and one-attempt, full-cost Phase 4 reservation gate."""
import fcntl
import json
import os
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

LOCK = "config/phase4_execution_lock_v2.json"
PROTOCOL = "config/phase4_execution_protocol_v2.json"
LEDGER = "config/phase4_compute_ledger.json"


def source_names(root=ROOT):
    """Shared inventory; bootstrap must import only the standard library."""
    names = {p.relative_to(root).as_posix() for folder in ("agent", "evaluation")
             for p in (root / folder).glob("*.py")}
    names.update(p.relative_to(root).as_posix() for p in (root / "config").iterdir()
                 if p.suffix in {".json", ".yaml"}
                 and not p.name.startswith("phase4_execution_lock_")
                 and p.relative_to(root).as_posix() != LEDGER)
    names.update({"scripts/run_phase4_target.py", "scripts/build_phase4_target_notebook.py",
                  "scripts/build_m0_profile_notebook.py", "scripts/build_e1_four_cell_notebook.py",
                  "scripts/phase4_budget.py", "scripts/evaluate_phase4_prescreen.py"})
    return sorted(names)


def verify_lock(root=ROOT):
    lock = json.loads((root / LOCK).read_text())
    if lock.get("schema_version") != 1 or lock.get("protocol_id") != "P4-fixture-prescreen-v2":
        raise ValueError("invalid execution lock")
    required = {PROTOCOL, "evaluation/phase4_target.py", "evaluation/phase4_execution.py",
                "evaluation/phase4_preflight.py", "evaluation/phase4_runner.py",
                "scripts/run_phase4_target.py", "scripts/build_phase4_target_notebook.py"}
    if not required <= set(lock["sources"]) or set(lock["sources"]) != set(source_names(root)):
        raise ValueError("missing required execution bindings")
    for name, digest in lock["sources"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path) != digest:
            raise ValueError("execution source drift: " + name)
    return lock


def authority(root=ROOT):
    verify_lock(root)
    ledger = json.loads((root / LEDGER).read_text())
    events = ledger.get("events", [])
    if (ledger.get("authorized_seconds") != 28800 or not ledger.get("approval_reference")
            or len(events) != 1):
        raise PermissionError("Phase 4 requires explicit 28800-second approval and one reservation")
    event = events[0]
    if (event.get("kind") != "reserve" or event.get("seconds") != 28800
            or event.get("execution_lock_sha256") != sha(root / LOCK)
            or not isinstance(event.get("attempt_id"), str) or not event["attempt_id"]):
        raise PermissionError("invalid or unbound Phase 4 reservation")
    return event


def reserve(root, attempt_id):
    """No approval is created here. Existing explicit approval is prerequisite."""
    verify_lock(root)
    if not attempt_id or not all(c.isalnum() or c in "-_" for c in attempt_id):
        raise ValueError("invalid attempt id")
    path = root / LEDGER
    with path.with_suffix(".lck").open("a") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        ledger = json.loads(path.read_text())
        if (ledger.get("authorized_seconds") != 28800 or not ledger.get("approval_reference")
                or ledger.get("events")):
            raise PermissionError("approval absent or single attempt already reserved")
        ledger["events"] = [{"kind": "reserve", "attempt_id": attempt_id, "seconds": 28800,
                              "execution_lock_sha256": sha(root / LOCK)}]
        temporary = path.with_suffix(".tmp")
        with temporary.open("x") as stream:
            json.dump(ledger, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    return authority(root)
