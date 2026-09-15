"""Build, restore and verify an immutable Phase 2–3 historical evidence package.

The pinned archive contains project code and development evidence, not model
weights or environment source. Archived validators run in an isolated Python
process using the installed project dependencies, with their own source root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = "config/phase23_evidence_package.json"
ARCHIVE = "evidence/phase23-closure-v1.zip"
MAX_BYTES = 64 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    paths = {p.relative_to(root).as_posix() for folder in ("agent", "evaluation", "scripts")
             for p in (root / folder).glob("*.py")}
    paths.update(p.relative_to(root).as_posix() for p in (root / "config").iterdir()
                 if p.suffix in {".yaml", ".json"} and p.name != Path(DESCRIPTOR).name)
    paths.update({"notebooks/phase2-cd82/execution-lock.json",
                  "reports/phase2_cd82_evidence_review.md",
                  "reports/phase2_runtime_owner_confirmation.json"})
    closure = json.loads((root / "config/phase2_closure.json").read_text())
    paths.update(str(Path(closure["execution_directory"]) / ref["path"]) for ref in closure["runs"])
    return sorted(paths)


def build(root=ROOT):
    # Building a new snapshot is explicit, never a side effect of validation.
    sys.path.insert(0, str(root))
    from scripts.validate_phase3 import validate
    validate(root, require_exit=True)
    archive = root / ARCHIVE
    descriptor = root / DESCRIPTOR
    if archive.exists() or descriptor.exists():
        raise ValueError("immutable package already exists; use a new version for a new closure")
    files = {}
    payloads = {}
    for name in inventory(root):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("package source escapes root")
        data = path.read_bytes()
        files[name] = {"sha256": digest(data), "bytes": len(data)}
        payloads[name] = data
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for name, data in payloads.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, data)
    value = {"schema_version": 1, "package_id": "phase23-closure-v1",
             "scope": "historical_completion_only_no_current_execution_authority",
             "archive": ARCHIVE, "archive_sha256": digest(archive.read_bytes()),
             "files": files}
    with descriptor.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return value


def restore(archive, descriptor, destination):
    value = json.loads(Path(descriptor).read_text())
    payload = Path(archive).read_bytes()
    if len(payload) > MAX_BYTES or digest(payload) != value["archive_sha256"]:
        raise ValueError("historical archive checksum or size mismatch")
    destination = Path(destination)
    if destination.exists():
        raise ValueError("restore requires a new destination; existing files are never overwritten")
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        if len(names) != len(set(names)) or set(names) != set(value["files"]):
            raise ValueError("historical archive inventory mismatch")
        if sum(item.file_size for item in source.infolist()) > MAX_BYTES:
            raise ValueError("historical archive expanded size exceeds ceiling")
        verified = {}
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("invalid archive path")
            data = source.read(name)
            ref = value["files"][name]
            if digest(data) != ref["sha256"] or len(data) != ref["bytes"]:
                raise ValueError("historical file checksum mismatch")
            verified[name] = data
    destination.mkdir(parents=True)
    for name, data in verified.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return destination


def validate_snapshot(snapshot):
    snapshot = Path(snapshot).resolve()
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["MPLCONFIGDIR"] = str(snapshot / ".cache/matplotlib")
    environment["XDG_CACHE_HOME"] = str(snapshot / ".cache")
    result = subprocess.run(
        [sys.executable, "-I", str(snapshot / "scripts/validate_phase3.py"), "--require-exit", "--current"],
        cwd=snapshot, env=environment, capture_output=True, text=True, timeout=120,
    )
    if result.returncode:
        raise ValueError("archived closure validation failed: " + result.stdout + result.stderr)
    return {"historical_completion": True, "current_eligibility_evaluated": False,
            "archived_validator_output": result.stdout.strip()}


def historical(root=ROOT, archive=None, descriptor=None):
    descriptor = Path(descriptor) if descriptor else root / DESCRIPTOR
    value = json.loads(descriptor.read_text())
    archive = Path(archive) if archive else root / value["archive"]
    with tempfile.TemporaryDirectory(prefix="phase23-history-") as temporary:
        snapshot = restore(archive, descriptor, Path(temporary) / "snapshot")
        return validate_snapshot(snapshot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify", "restore"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--descriptor", type=Path, default=ROOT / DESCRIPTOR)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.action == "build":
        result = build()
        print("EVIDENCE_PACKAGE_CREATED " + result["archive_sha256"])
    elif args.action == "verify":
        print(json.dumps(historical(ROOT, args.archive, args.descriptor), sort_keys=True))
    else:
        if args.destination is None:
            parser.error("restore requires --destination")
        value = json.loads(args.descriptor.read_text())
        restored = restore(args.archive or ROOT / value["archive"], args.descriptor, args.destination)
        print(json.dumps(validate_snapshot(restored), sort_keys=True))


if __name__ == "__main__":
    main()
