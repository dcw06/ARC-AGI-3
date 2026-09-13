"""Build a separate offline capture revision. Never overwrites the live V1 lock."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_phase2_diagnostic_notebook import build as build_v1
from scripts.build_m0_profile_notebook import code_cell, markdown_cell


def build(attempt_id=None):
    notebook, lock = build_v1()
    active = json.loads((ROOT / "notebooks/phase2-cd82/execution-lock.json").read_text())
    if lock != active:
        raise ValueError("frozen V1 source drift; do not overwrite running evidence provenance")
    extras = {name: (ROOT / name).read_bytes() for name in
        ("evaluation/phase2_sequences.py", "scripts/run_phase2_diagnostics_v2.py")}
    extension = {"version":2,"policy_delta":"none", "sources":{k:hashlib.sha256(v).hexdigest() for k,v in extras.items()},
                 "parent_lock_sha256": hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
    extension["execution_authorized"] = False
    extension["attempt_id"] = attempt_id
    if attempt_id is not None:
        from evaluation.phase2_budget import read_ledger
        ledger = read_ledger(ROOT / "config/phase2_compute_ledger.json")
        attempt = ledger["attempts"].get(attempt_id)
        if (attempt_id == "cd82-v1-user-reported" or not ledger["inventory_confirmed"]
                or ledger["over_budget"] or attempt is None or attempt["reconciled"]
                or attempt["charged_seconds"] < 7200):
            raise ValueError("V2 requires its own funded reservation after provider-inventory reconciliation")
        extension["execution_authorized"] = True
    encoded = {k:base64.b64encode(v).decode() for k,v in extras.items()}
    inject = (f"extra_sources = {encoded!r}\n"
        "for name,payload in extra_sources.items():\n"
        "    target = source / name\n    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    target.write_bytes(base64.b64decode(payload))\n"
        f"extension = {extension!r}\n"
        "(source / 'config/phase2_capture_extension.json').write_text(json.dumps(extension))\n"
        "(output / 'capture-extension.json').write_text(json.dumps(extension))\n")
    cells = [cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code"]
    cells[0] = cells[0].replace("phase2-cd82'", "phase2-cd82-v2'").replace("output.mkdir(exist_ok=False)", "output.mkdir(exist_ok=True)")
    cells[-1] = cells[-1].replace("run_phase2_diagnostics.py", "run_phase2_diagnostics_v2.py")
    # Outer supervisor owns cost recording; inner V1 finalizer would undercount setup.
    cells[-1] = cells[-1].split("try:\n")[0] + "subprocess.run(command, check=True)\n"
    program = cells[0] + "\n" + inject + "\n" + "\n".join(cells[1:])
    compile(program, "phase2-v2-driver", "exec")
    supervisor = (ROOT / "scripts/phase2_supervisor.py").read_text()
    payload = base64.b64encode(zlib.compress(program.encode())).decode()
    launch = ("import base64, pathlib, tempfile, zlib, sys\n"
        f"if not {extension['execution_authorized']!r}: raise RuntimeError('V2 has no funded execution reservation')\n"
        f"program = zlib.decompress(base64.b64decode({payload!r})).decode()\n"
        "driver = pathlib.Path(tempfile.mkdtemp(prefix='arc3-p2-v2-')) / 'driver.py'\n"
        "driver.write_text(program)\n" + supervisor + "\n"
        "supervise([sys.executable, str(driver)], '/kaggle/working/phase2-cd82-v2', 7200)\n")
    return {"nbformat":4,"nbformat_minor":4,"metadata":notebook["metadata"],"cells":[
        markdown_cell("# Phase 2 capture V2\nEvaluator-only full sequences; supervised setup and execution. No treatment activation."),
        code_cell(launch)]}, extension


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-id")
    args = parser.parse_args()
    notebook, extension = build(args.attempt_id)
    target = ROOT / "notebooks/phase2-cd82-v2"
    target.mkdir(parents=True, exist_ok=True)
    (target / "profile.ipynb").write_text(json.dumps(notebook,indent=1)+"\n")
    (target / "capture-extension.json").write_text(json.dumps(extension,indent=2)+"\n")
    print("Built separate V2 capture notebook; not uploaded or launched")
