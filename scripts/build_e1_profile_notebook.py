"""Build the offline Q3VL-30B mixed E1 target-RTX profile notebook."""

from __future__ import annotations

import base64
import json
import sys
import zlib
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.e1_profile import build_e1_workload_fixtures
from scripts.build_m0_profile_notebook import _install_cell, code_cell, markdown_cell


OUTPUT_DIR = ROOT / "notebooks/e1-q3vl30"
MODEL_PATH = "/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/30b-a3b-instruct-fp8/1"


def bundled_sources() -> dict[str, str]:
    paths = (
        "evaluation/__init__.py",
        "evaluation/e1_profile.py",
        "evaluation/m0_profile.py",
        "evaluation/metrics.py",
        "scripts/profile_m0_openai.py",
        "scripts/profile_e1_openai.py",
        "config/m0_launch_spec_q3vl30.json",
    )
    files = {
        relative: base64.b64encode((ROOT / relative).read_bytes()).decode("ascii")
        for relative in paths
    }
    workloads = build_e1_workload_fixtures(str(ROOT / "config/e1_feature_manifests.yaml"))
    workload_bytes = (json.dumps(workloads, indent=2) + "\n").encode()
    files["config/e1_profile_workloads.json"] = base64.b64encode(workload_bytes).decode("ascii")
    return files


def build() -> dict:
    encoded = json.dumps(bundled_sources(), sort_keys=True, separators=(",", ":"))
    packed = base64.b64encode(zlib.compress(encoded.encode(), level=9)).decode("ascii")
    unpack = code_cell(
        "import base64, json, pathlib, shutil, zlib\n"
        "root = pathlib.Path('/tmp/arc3-e1/source')\n"
        "shutil.rmtree(root.parent, ignore_errors=True)\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        f"files = json.loads(zlib.decompress(base64.b64decode({packed!r})))\n"
        "for relative, payload in files.items():\n"
        "    target = root / relative\n"
        "    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    target.write_bytes(base64.b64decode(payload))\n"
        "del files, payload\n"
    )
    run = code_cell(
        dedent(
            f"""\
            import pathlib, subprocess, sys

            model_path = pathlib.Path({MODEL_PATH!r})
            if not model_path.is_dir():
                raise FileNotFoundError('the frozen Q3VL-30B FP8 model is not attached')
            required = {{
                'config.json', 'model.safetensors.index.json', 'tokenizer.json',
                'tokenizer_config.json', 'chat_template.json',
            }}
            missing = sorted(name for name in required if not (model_path / name).is_file())
            shards = sorted(model_path.glob('model-*.safetensors'))
            all_safetensors = sorted(model_path.glob('*.safetensors'))
            if missing or len(shards) != 4 or len(all_safetensors) != 4:
                raise RuntimeError(
                    f'frozen model layout mismatch: missing={{missing}} '
                    f'model_shards={{len(shards)}} all_safetensors={{len(all_safetensors)}}'
                )

            subprocess.check_call([
                sys.executable, '/tmp/arc3-e1/source/scripts/profile_e1_openai.py',
                '--model-path', str(model_path),
                '--launch-spec', '/tmp/arc3-e1/source/config/m0_launch_spec_q3vl30.json',
                '--workloads', '/tmp/arc3-e1/source/config/e1_profile_workloads.json',
                '--output', '/kaggle/working/e1-q3vl30-mixed-profile.json',
                '--trials-per-cell', '8',
                '--concurrency', '8',
                '--max-new-tokens', '128',
            ])
            """
        )
    )
    return {
        "metadata": {
            "kernelspec": {"language": "python", "display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
            "kaggle": {
                "accelerator": "nvidiaRtxPro6000",
                "isInternetEnabled": False,
                "isGpuEnabled": True,
                "language": "python",
                "sourceType": "notebook",
            },
        },
        "nbformat_minor": 4,
        "nbformat": 4,
        "cells": [
            markdown_cell(
                "# E1 Q3VL-30B mixed target-RTX profile\n\n"
                "Unscored measurement notebook. It runs E1S-R canary first, then the four "
                "frozen E1 request shapes, cancellation recovery, resource sampling, and "
                "the headroom-adjusted C_admit projection. It fails on non-target hardware."
            ),
            _install_cell(),
            unpack,
            run,
        ],
    }


def write() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    notebook = OUTPUT_DIR / "profile.ipynb"
    metadata = OUTPUT_DIR / "kernel-metadata.json"
    if not metadata.is_file():
        raise SystemExit(f"missing tracked metadata: {metadata.relative_to(ROOT)}")
    notebook.write_text(json.dumps(build(), indent=1) + "\n")
    print(f"[build_e1_profile_notebook] wrote {notebook.relative_to(ROOT)}")
    return notebook


if __name__ == "__main__":
    write()
