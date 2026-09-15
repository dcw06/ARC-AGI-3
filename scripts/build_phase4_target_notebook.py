"""Build review-only or reserved private target notebook; never uploads anything."""
import argparse
import base64
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4_execution import LOCK, PROTOCOL, LEDGER, verify_lock, authority, source_names
from scripts.build_m0_profile_notebook import code_cell, markdown_cell, _install_cell
from scripts.build_e1_four_cell_notebook import _arc_install_cell


def build(root=ROOT, reserved=False):
    lock = verify_lock(root)
    if set(lock["sources"]) != set(source_names(root)):
        raise ValueError("execution inventory differs from complete package inventory")
    if reserved:
        authority(root)
    names = [*lock["sources"], LOCK, LEDGER]
    packed = base64.b64encode(zlib.compress(json.dumps({name:
        base64.b64encode((root / name).read_bytes()).decode() for name in names}).encode())).decode()
    install = _install_cell()["source"] + "\n" + _arc_install_cell()["source"]
    source = f'''import base64, json, pathlib, tempfile, time, sys, subprocess, os, signal
started = time.monotonic()
source = pathlib.Path(tempfile.mkdtemp(prefix='p4-source-'))
for name, payload in json.loads(zlib.decompress(base64.b64decode({packed!r}))).items():
    target = source / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(payload))
output = pathlib.Path('/kaggle/working/phase4-prescreen')
output.mkdir(exist_ok=False)
receipt = {{'scope':'all_accelerator_time_including_setup_and_failures','charged_or_reserved_seconds':28800,'provider_reconciliation_required':True,'status':'failed'}}
try:
    # Gate BEFORE dependency installation or model start. A review notebook
    # contains zero authorization and fails here if run accidentally.
    check = "import sys; sys.path.insert(0, sys.argv[1]); from evaluation.phase4_execution import authority; authority()"
    subprocess.run([sys.executable, '-S', '-c', check, str(source)], check=True, timeout=30)
    for name in {(Path(LOCK).name, Path(PROTOCOL).name, Path(LEDGER).name)!r}:
        (output/name).write_bytes((source/'config'/name).read_bytes())
    install = subprocess.Popen([sys.executable, '-c', {install!r}], start_new_session=True)
    try:
        install.wait(timeout=max(1, 900-(time.monotonic()-started)))
        if install.returncode:
            raise RuntimeError('offline dependency setup failed')
    finally:
        try: os.killpg(install.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        install.wait(timeout=5)
    # The supervisor enforces the full lifecycle measured from this cell.
    subprocess.run([sys.executable, str(source/'scripts/run_phase4_target.py'), '--output', str(output), '--started', str(started)], check=True)
    receipt['status'] = 'target_command_completed'
finally:
    receipt['elapsed_since_first_cell_seconds'] = time.monotonic()-started
    (output/'notebook-cost.json').write_text(json.dumps(receipt, sort_keys=True))
    import shutil
    shutil.rmtree(source)
'''
    source = "import zlib\n" + source
    notebook = {"nbformat": 4, "nbformat_minor": 4,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
        "cells": [markdown_cell("# Phase 4 private fixture prescreen\n"
                    + ("Reserved build; one attempt only." if reserved else "REVIEW ONLY: zero authorized compute; do not launch.")
                    + "\nNot full-game lifecycle certification. H1 is not accessed."), code_cell(source)]}
    metadata = {"id": "daichongwei06/arc3-phase4-fixture-prescreen-v2",
        "title": "ARC3 Phase4 Fixture Prescreen v2", "code_file": "profile.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True,
        "enable_gpu": True, "machine_shape": "NvidiaRtxPro6000", "enable_tpu": False,
        "enable_internet": False, "dataset_sources": ["driessmit1/arc3-vllm-h100-wheelhouse-v3"],
        "model_sources": ["qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1"],
        "competition_sources": ["arc-prize-2026-arc-agi-3"], "kernel_sources": []}
    return notebook, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reserved", action="store_true")
    args = parser.parse_args()
    notebook, metadata = build(reserved=args.reserved)
    destination = ROOT / "notebooks/phase4-prescreen-v2"
    destination.mkdir(exist_ok=True, parents=True)
    for name, value in (("profile.ipynb", notebook), ("kernel-metadata.json", metadata)):
        (destination / name).write_text(json.dumps(value, indent=1) + "\n")
    print("Built private " + ("reserved" if args.reserved else "REVIEW-ONLY") + " Phase 4 notebook; nothing uploaded")
