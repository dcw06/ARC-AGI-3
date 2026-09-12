"""Build the offline target-RTX whole-run E1 four-cell experiment notebook."""

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

from scripts.build_m0_profile_notebook import _install_cell, code_cell, markdown_cell


OUTPUT_DIR = ROOT / "notebooks/e1-four-cell"
MODEL_PATH = "/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/30b-a3b-instruct-fp8/1"
COMPETITION_ROOT = "/kaggle/input/competitions/arc-prize-2026-arc-agi-3"
ENVIRONMENTS_PATH = f"{COMPETITION_ROOT}/environment_files"
WHEELS_PATH = f"{COMPETITION_ROOT}/arc_agi_3_wheels"


def bundled_sources() -> dict[str, str]:
    paths = (
        "agent/__init__.py",
        "agent/action.py",
        "agent/action_journal.py",
        "agent/competition_loop.py",
        "agent/config.py",
        "agent/controller.py",
        "agent/e1_policy.py",
        "agent/evidence.py",
        "agent/feature_manifest.py",
        "agent/framework_adapter.py",
        "agent/representation.py",
        "agent/safe_operations.py",
        "agent/scheduler.py",
        "agent/state.py",
        "agent/watchdog.py",
        "evaluation/__init__.py",
        "evaluation/e1_experiment.py",
        "evaluation/e1_whole_run.py",
        "evaluation/metrics.py",
        "evaluation/m0_profile.py",
        "evaluation/phase1.py",
        "scripts/profile_m0_openai.py",
        "scripts/run_e1_four_cell.py",
        "scripts/run_e1_whole_run.py",
        "config/e1_experiment_protocol.yaml",
        "config/e1_whole_run_protocol.yaml",
        "config/e1_feature_manifests.yaml",
        "config/m0_launch_spec_q3vl30.json",
    )
    return {
        relative: base64.b64encode((ROOT / relative).read_bytes()).decode("ascii")
        for relative in paths
    }


def _arc_install_cell() -> dict:
    return code_cell(
        dedent(
            f"""\
            import pathlib, subprocess, sys

            wheels = pathlib.Path({WHEELS_PATH!r})
            required = {{
                'arc_agi-0.9.8-py3-none-any.whl',
                'arcengine-0.9.3-py3-none-any.whl',
                'requests-2.33.1-py3-none-any.whl',
                'numpy-2.4.4-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
                'pydantic-2.13.2-py3-none-any.whl',
            }}
            missing = sorted(name for name in required if not (wheels / name).is_file())
            if missing:
                raise FileNotFoundError(f'frozen competition wheels missing: {{missing}}')
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '--quiet', '--no-index',
                '--disable-pip-version-check', '--find-links', str(wheels),
                'arc-agi==0.9.8', 'arcengine==0.9.3', 'requests==2.33.1',
                'numpy==2.4.4', 'pydantic==2.13.2', 'python-dotenv==1.2.2',
            ])
            """
        )
    )


def build() -> dict:
    encoded = json.dumps(bundled_sources(), sort_keys=True, separators=(",", ":"))
    packed = base64.b64encode(zlib.compress(encoded.encode(), level=9)).decode("ascii")
    unpack = code_cell(
        "import base64, json, pathlib, shutil, zlib\n"
        "root = pathlib.Path('/tmp/arc3-e1-four-cell/source')\n"
        "shutil.rmtree(root.parent, ignore_errors=True)\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        f"files = json.loads(zlib.decompress(base64.b64decode({packed!r})))\n"
        "for relative, payload in files.items():\n"
        "    target = root / relative\n"
        "    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    target.write_bytes(base64.b64decode(payload))\n"
        "del files, payload\n"
    )
    preflight = code_cell(
        dedent(
            f"""\
            import json, pathlib

            source = pathlib.Path('/tmp/arc3-e1-four-cell/source')
            protocol = json.loads((source / 'config/e1_experiment_protocol.yaml').read_text())
            whole_run = json.loads((source / 'config/e1_whole_run_protocol.yaml').read_text())
            if whole_run.get('status') != 'frozen_pending_execution':
                raise RuntimeError('whole-run protocol is not frozen pending execution')
            blocks = whole_run.get('execution', {{}}).get('blocks', [])
            if (
                len(blocks) != 2
                or blocks[0].get('order') != list(reversed(blocks[1].get('order', [])))
                or whole_run.get('execution', {{}}).get('uncertainty_unit')
                != 'paired_complete_workload_run_block'
            ):
                raise RuntimeError('whole-run block/order/uncertainty contract drifted')
            environments = pathlib.Path({ENVIRONMENTS_PATH!r})
            missing_games = []
            for item in protocol['development_game_seed_pairs']:
                base, version = item['game_id'].split('-', 1)
                root = environments / base / version
                if not (root / f'{{base}}.py').is_file() or not (root / 'metadata.json').is_file():
                    missing_games.append(item['game_id'])
            if missing_games:
                raise FileNotFoundError(f'frozen public games missing: {{missing_games}}')

            model = pathlib.Path({MODEL_PATH!r})
            required_model = {{
                'config.json', 'model.safetensors.index.json', 'tokenizer.json',
                'tokenizer_config.json', 'chat_template.json',
            }}
            missing_model = sorted(name for name in required_model if not (model / name).is_file())
            shards = sorted(model.glob('model-*.safetensors'))
            if missing_model or len(shards) != 4:
                raise RuntimeError(
                    f'frozen model layout mismatch: missing={{missing_model}} shards={{len(shards)}}'
                )
            print('E1_FOUR_CELL_PREFLIGHT_OK games=15 model_shards=4 whole_run_blocks=2')
            """
        )
    )
    run = code_cell(
        dedent(
            f"""\
            import pathlib, subprocess, sys

            source = pathlib.Path('/tmp/arc3-e1-four-cell/source')
            subprocess.check_call([
                sys.executable, str(source / 'scripts/run_e1_whole_run.py'),
                '--model-path', {MODEL_PATH!r},
                '--environments-dir', {ENVIRONMENTS_PATH!r},
                '--launch-spec', str(source / 'config/m0_launch_spec_q3vl30.json'),
                '--source-protocol', str(source / 'config/e1_experiment_protocol.yaml'),
                '--whole-run-protocol', str(source / 'config/e1_whole_run_protocol.yaml'),
                '--feature-registry', str(source / 'config/e1_feature_manifests.yaml'),
                '--expected-artifact-sha256', '052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627',
                '--output', '/kaggle/working/e1-whole-run-four-cell-v1.json',
                '--server-log-dir', '/kaggle/working/e1-whole-run-server-logs',
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
                "# E1 counterbalanced whole-run four-cell experiment\n\n"
                "Private, unscored, internet-disabled execution of two paired complete-workload "
                "blocks. Every treatment run receives a fresh model server, queue, Arcade "
                "sessions, and policy state."
            ),
            unpack,
            preflight,
            _install_cell(),
            _arc_install_cell(),
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
    print(f"[build_e1_four_cell_notebook] wrote {notebook.relative_to(ROOT)}")
    return notebook


if __name__ == "__main__":
    write()
