"""Build the offline, multi-file Plan 8 Kaggle submission notebook."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from textwrap import dedent

ACCELERATOR = "rtx6000"

_ACCELERATORS = {
    "cpu": {"name": "none", "gpu": False},
    "t4": {"name": "nvidiaTeslaT4", "gpu": True},
    "p100": {"name": "nvidiaTeslaP100", "gpu": True},
    "rtx6000": {"name": "nvidiaRtx6000", "gpu": True},
}

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agent"
NOTEBOOK_PATH = ROOT / "notebooks" / "submission.ipynb"
METADATA_PATH = ROOT / "notebooks" / "kernel-metadata.json"


def code_cell(source: str) -> dict:
    return {"cell_type": "code", "metadata": {"trusted": True}, "outputs": [], "execution_count": None, "source": source}


def markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def bundled_sources() -> dict[str, str]:
    required = {
        "agent/__init__.py", "agent/action.py", "agent/action_journal.py",
        "agent/competition_loop.py", "agent/controller.py",
        "agent/framework_adapter.py", "agent/production_main.py",
        "agent/output_policy.py", "agent/scheduler.py", "agent/state.py", "agent/watchdog.py",
    }
    files: dict[str, str] = {}
    for relative in sorted(required):
        path = ROOT / relative
        if path.exists():
            files[relative] = base64.b64encode(path.read_bytes()).decode("ascii")
    missing = required - files.keys()
    if missing:
        raise SystemExit(f"submission bundle is missing: {sorted(missing)}")
    return files


def build() -> dict:
    if ACCELERATOR not in _ACCELERATORS:
        raise SystemExit(f"unknown accelerator: {ACCELERATOR}")
    accel = _ACCELERATORS[ACCELERATOR]
    encoded = json.dumps(bundled_sources(), sort_keys=True, separators=(",", ":"))

    install_cell = code_cell(
        "import os\n"
        "os.environ['PIP_CACHE_DIR'] = '/tmp/arc3-agent/pip-cache'\n"
        "!pip install --quiet --disable-pip-version-check --no-index --find-links "
        "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels "
        "arc-agi==0.9.9 arcengine==0.9.3 python-dotenv\n"
    )

    bundle_cell = code_cell(
        "import base64, json, pathlib, shutil\n"
        "bundle_root = pathlib.Path('/tmp/arc3-agent/source')\n"
        "shutil.rmtree(bundle_root.parent, ignore_errors=True)\n"
        "bundle_root.mkdir(parents=True, exist_ok=True)\n"
        f"files = json.loads({encoded!r})\n"
        "for relative, payload in files.items():\n"
        "    target = bundle_root / relative\n"
        "    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    target.write_bytes(base64.b64decode(payload))\n"
        "del files, payload\n"
    )

    run_cell = code_cell(
        dedent(
            """\
            import os, subprocess, sys, time
            import requests
            from agent.output_policy import enforce_retained_allowlist

            sys.tracebacklimit = 0

            if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
                enforce_retained_allowlist('/kaggle/working', remove_allowed=True)
                deadline = time.monotonic() + 600
                while True:
                    try:
                        response = requests.get('http://gateway:8001/api/games', timeout=5)
                        if response.ok:
                            break
                    except requests.RequestException:
                        pass
                    if time.monotonic() >= deadline:
                        raise RuntimeError('gateway readiness timeout')
                    time.sleep(5)

                env = os.environ.copy()
                env.update({
                    'ARC_BASE_URL': 'http://gateway:8001',
                    'ARC_API_KEY': 'test-key-123',
                    'PYTHONPATH': '/tmp/arc3-agent/source',
                    'PYTHONPYCACHEPREFIX': '/tmp/arc3-agent/pycache',
                    'MPLCONFIGDIR': '/tmp/arc3-agent/matplotlib',
                    'XDG_CACHE_HOME': '/tmp/arc3-agent/cache',
                })
                completed = None
                try:
                    completed = subprocess.run(
                        [sys.executable, '-m', 'agent.production_main'],
                        cwd='/tmp/arc3-agent', env=env, check=False,
                    )
                finally:
                    enforce_retained_allowlist('/kaggle/working')
                assert completed is not None
                if completed.returncode:
                    raise RuntimeError(f'agent exited with lifecycle code {completed.returncode}')
            """
        )
    )

    dummy_cell = code_cell(
        dedent(
            """\
            import os
            if not os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
                import pandas as pd
                pd.DataFrame(
                    data=[['1_0', '1', True, 1]],
                    columns=['row_id', 'game_id', 'end_of_game', 'score'],
                ).to_parquet('/kaggle/working/submission.parquet', index=False)
            """
        )
    )

    return {
        "metadata": {
            "kernelspec": {"language": "python", "display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python", "mimetype": "text/x-python", "file_extension": ".py", "pygments_lexer": "ipython3"},
            "kaggle": {"accelerator": accel["name"], "isInternetEnabled": False, "isGpuEnabled": accel["gpu"], "language": "python", "sourceType": "notebook"},
        },
        "nbformat_minor": 4,
        "nbformat": 4,
        "cells": [
            markdown_cell("# ARC Prize 2026 — ARC-AGI-3 Plan 8 submission\n\nGenerated; edit repository sources, not this notebook."),
            install_cell, bundle_cell, run_cell, dummy_cell,
        ],
    }


def main() -> None:
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(json.dumps(build(), indent=1) + "\n")
    meta = json.loads(METADATA_PATH.read_text())
    meta["enable_gpu"] = _ACCELERATORS[ACCELERATOR]["gpu"]
    METADATA_PATH.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"[build_notebook] wrote {NOTEBOOK_PATH.relative_to(ROOT)} ({ACCELERATOR})")


if __name__ == "__main__":
    main()
