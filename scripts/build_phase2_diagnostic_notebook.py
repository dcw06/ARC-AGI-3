"""Freeze and package the two-run cd82 diagnostic notebook."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.e1_policy import e1_system_prompt
from agent.feature_manifest import load_e1_feature_manifests
from evaluation.phase2_contract import validate_contract
from scripts.build_e1_four_cell_notebook import bundled_sources, _arc_install_cell, MODEL_PATH, ENVIRONMENTS_PATH
from scripts.build_m0_profile_notebook import _install_cell, code_cell, markdown_cell


def build():
    validate_contract(ROOT)
    files = bundled_sources()
    for relative in ("scripts/run_phase2_diagnostics.py", "evaluation/phase2_reproduction.py",
        "config/operational_primary.yaml", "config/phase2_diagnostic_schema.json", "config/phase2_contract.yaml"):
        files[relative] = base64.b64encode((ROOT / relative).read_bytes()).decode()
    manifest = load_e1_feature_manifests(ROOT / "config/e1_feature_manifests.yaml")["E1S-R"]
    lock = {"schema_version":1,"protocol_id":"phase2.cd82.parent-diagnostic.v1",
        "sources":{name:hashlib.sha256(base64.b64decode(content)).hexdigest() for name,content in sorted(files.items())},
        "prompt_sha256":hashlib.sha256(e1_system_prompt(manifest).encode()).hexdigest(),
        "model_artifact_sha256":json.loads((ROOT / "config/operational_primary.yaml").read_text())["primary"]["model_artifact"]["tree_sha256"],
        "per_run_seconds":3000,"maximum_diagnostic_accelerator_hours":2,
        "game_id":"cd82-fb555c5d","environment_seed":104759,"request_seed":104759,
        "runs":2,"actions_per_run":80,"requests_per_run":80,
        "attribution_default":"unsupported_other","automatic_admission":False,
        "signature_rule":"ordered_pre_post_action_category_dispatch_excluding_run_ids_and_model_wording_v1"}
    files["config/phase2_diagnostic_execution_lock.json"] = base64.b64encode(json.dumps(lock,sort_keys=True,indent=2).encode()).decode()
    packed = base64.b64encode(zlib.compress(json.dumps(files).encode())).decode()
    unpack = code_cell("import base64, json, pathlib, tempfile, zlib, time\nnotebook_started = time.monotonic()\n"
        "source = pathlib.Path(tempfile.mkdtemp(prefix='arc3-p2-'))\n"
        f"files = json.loads(zlib.decompress(base64.b64decode({packed!r})))\n"
        "for name, payload in files.items():\n    target = source / name\n    target.parent.mkdir(parents=True, exist_ok=True)\n    target.write_bytes(base64.b64decode(payload))\n"
        "output = pathlib.Path('/kaggle/working/phase2-cd82')\noutput.mkdir(exist_ok=False)\n"
        "(output / 'execution-lock.json').write_bytes((source / 'config/phase2_diagnostic_execution_lock.json').read_bytes())\n")
    run = code_cell("import subprocess, sys, json\n"
        f"command = [sys.executable, str(source / 'scripts/run_phase2_diagnostics.py'), '--model-path', {MODEL_PATH!r}, '--environments-dir', {ENVIRONMENTS_PATH!r}, '--output-dir', str(output), '--lock', str(output / 'execution-lock.json')]\n"
        "try:\n    subprocess.run(command, check=True, timeout=max(1, 7200-(time.monotonic()-notebook_started)))\n"
        "finally:\n    (output / 'notebook-cost.json').write_text(json.dumps({'elapsed_seconds':time.monotonic()-notebook_started,'budget_seconds':7200}))\n")
    notebook = {"nbformat":4,"nbformat_minor":4,"metadata":{"kernelspec":{"name":"python3","display_name":"Python 3","language":"python"}},
        "cells":[markdown_cell("# Phase 2 cd82 parent diagnostics\nTwo fresh E1S-R runs, seed 104759. Private and unscored; no automatic treatment admission."),unpack,_install_cell(),_arc_install_cell(),run]}
    return notebook, lock


if __name__ == "__main__":
    notebook, lock = build()
    target = ROOT / "notebooks/phase2-cd82"
    target.mkdir(parents=True,exist_ok=True)
    (target / "profile.ipynb").write_text(json.dumps(notebook,indent=1)+"\n")
    (target / "execution-lock.json").write_text(json.dumps(lock,sort_keys=True,indent=2)+"\n")
    print("Built notebooks/phase2-cd82/profile.ipynb")
