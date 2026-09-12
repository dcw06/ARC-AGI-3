"""Build deterministic offline Kaggle RTX notebooks for the frozen M0 set."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]

PROFILE_SPECS: dict[str, dict] = {
    "q38": {
        "candidate_id": "M0-Q38-27B-FP8",
        "model_id": "Qwen/Qwen3.8-27B-FP8",
        "revision": "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a",
        "reasoning": "low",
        "launch_spec": "config/m0_launch_spec_q38.json",
        "output_dir": "notebooks/m0-q38",
        "output_name": "m0-q38-low.json",
        "label": "Qwen3.8 27B FP8 / low reasoning",
        "model_paths": [
            "/kaggle/input/models/foysalemonshanto/qwen3-8-27b-fp8-repacked-v1/pytorch/hf-fp8/1",
        ],
        "required_files": [
            "config.json",
            "model.safetensors.index.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "outside.safetensors",
            "mtp.safetensors",
            "chat_template.jinja",
        ],
        "shard_glob": "model-layers-*.safetensors",
        "shard_count": 16,
        "safetensor_count": 18,
    },
    "q3vl30": {
        "candidate_id": "M0-Q3VL-30B-A3B-FP8",
        "model_id": "Qwen/Qwen3-VL-30B-A3B-Instruct-FP8",
        "revision": "d9748a51ae66354c4dad665aab2c71f26cf2c8cd",
        "reasoning": "instruct_non_thinking",
        "launch_spec": "config/m0_launch_spec_q3vl30.json",
        "output_dir": "notebooks/m0-q3vl30",
        "output_name": "m0-q3vl30-instruct.json",
        "label": "Qwen3-VL 30B-A3B FP8 / instruct",
        "model_paths": [
            "/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/30b-a3b-instruct-fp8/1",
        ],
        "required_files": [
            "config.json",
            "model.safetensors.index.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "chat_template.json",
        ],
        "shard_glob": "model-*.safetensors",
        "shard_count": 4,
        "safetensor_count": 4,
    },
    "q3vl8": {
        "candidate_id": "M0-Q3VL-8B-FP8",
        "model_id": "Qwen/Qwen3-VL-8B-Instruct-FP8",
        "revision": "9cdc6310a8cb770ce18efaf4e9935334512aee45",
        "reasoning": "instruct_non_thinking",
        "launch_spec": "config/m0_launch_spec_q3vl8.json",
        "output_dir": "notebooks/m0-q3vl8",
        "output_name": "m0-q3vl8-instruct.json",
        "label": "Qwen3-VL 8B FP8 / instruct",
        "model_paths": [
            "/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/8b-instruct-fp8/1",
        ],
        "required_files": [
            "config.json",
            "model.safetensors.index.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "chat_template.json",
        ],
        "shard_glob": "model-*.safetensors",
        "shard_count": 2,
        "safetensor_count": 2,
    },
}


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {"trusted": True},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def bundled_sources(candidate: str = "q38") -> dict[str, str]:
    spec = PROFILE_SPECS[candidate]
    relative_paths = (
        "evaluation/__init__.py",
        "evaluation/metrics.py",
        "evaluation/m0_profile.py",
        "scripts/profile_m0_openai.py",
        spec["launch_spec"],
    )
    return {
        relative: base64.b64encode((ROOT / relative).read_bytes()).decode("ascii")
        for relative in relative_paths
    }


def _install_cell() -> dict:
    return code_cell(
        dedent(
            """\
            import hashlib, pathlib, subprocess, sys

            candidates = [
                pathlib.Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),
                pathlib.Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3'),
            ]
            wheelhouse = next((path for path in candidates if path.is_dir()), None)
            if wheelhouse is None:
                raise FileNotFoundError('the frozen vLLM wheelhouse is not attached')
            checksum_manifest = wheelhouse / 'SHA256SUMS'
            expected_manifest_sha256 = '44029b360a9c0073e4b0add10703fc3386dc06bf1314f5913a0dad9564144cbb'
            index_manifest = wheelhouse / 'wheelhouse-manifest.json'
            expected_index_sha256 = 'bc016164d15664c52911fcd11f4e26e72a483e248f3cc9b59ae02b3fce09cc6a'
            if not checksum_manifest.is_file():
                raise FileNotFoundError('the wheelhouse SHA256SUMS manifest is missing')
            if not index_manifest.is_file():
                raise FileNotFoundError('the wheelhouse index manifest is missing')
            observed_manifest_sha256 = hashlib.sha256(checksum_manifest.read_bytes()).hexdigest()
            if observed_manifest_sha256 != expected_manifest_sha256:
                raise RuntimeError('the wheelhouse SHA256SUMS manifest does not match the frozen digest')
            observed_index_sha256 = hashlib.sha256(index_manifest.read_bytes()).hexdigest()
            if observed_index_sha256 != expected_index_sha256:
                raise RuntimeError('the wheelhouse index manifest does not match the frozen digest')
            manifest_lines = [line for line in checksum_manifest.read_text().splitlines() if line]
            if len(manifest_lines) != 179:
                raise RuntimeError(f'expected 179 wheelhouse checksums, found {len(manifest_lines)}')
            expected_files = {
                line.split(maxsplit=1)[1].lstrip('*').removeprefix('./'): line.split()[0]
                for line in manifest_lines
            }
            actual_files = {
                path.relative_to(wheelhouse).as_posix()
                for path in wheelhouse.rglob('*')
                if path.is_file() and path not in {checksum_manifest, index_manifest}
            }
            # Kaggle consumes dataset-metadata.json during publication, so it is
            # present in the creator's signed list but absent from the mounted v1.
            missing_files = set(expected_files) - actual_files
            extra_files = actual_files - set(expected_files)
            if not missing_files.issubset({'dataset-metadata.json'}) or extra_files:
                raise RuntimeError(
                    f'wheelhouse inventory mismatch: missing={sorted(missing_files)} '
                    f'extra={sorted(extra_files)}'
                )
            if len(actual_files) not in {178, 179}:
                raise RuntimeError(f'expected 178 or 179 mounted payloads, found {len(actual_files)}')
            for relative in sorted(actual_files):
                digest = hashlib.sha256()
                with (wheelhouse / relative).open('rb') as stream:
                    for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                        digest.update(chunk)
                if digest.hexdigest() != expected_files[relative]:
                    raise RuntimeError(f'wheelhouse checksum mismatch: {relative}')
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '--quiet', '--no-index',
                '--no-warn-conflicts', '--disable-pip-version-check', '--find-links',
                str(wheelhouse), 'vllm==0.19.0', 'torch==2.10.0',
                'transformers==4.57.6',
            ])
            """
        )
    )


def build(candidate: str = "q38") -> dict:
    spec = PROFILE_SPECS[candidate]
    encoded = json.dumps(bundled_sources(candidate), sort_keys=True, separators=(",", ":"))
    unpack = code_cell(
        "import base64, json, pathlib, shutil\n"
        "root = pathlib.Path('/tmp/arc3-m0/source')\n"
        "shutil.rmtree(root.parent, ignore_errors=True)\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        f"files = json.loads({encoded!r})\n"
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

            model_candidates = [pathlib.Path(path) for path in {spec['model_paths']!r}]
            model_path = next((path for path in model_candidates if path.is_dir()), None)
            if model_path is None:
                raise FileNotFoundError('the frozen {spec['label']} model is not attached')
            required_files = set({spec['required_files']!r})
            missing_files = sorted(name for name in required_files if not (model_path / name).is_file())
            model_shards = sorted(model_path.glob({spec['shard_glob']!r}))
            all_shards = sorted(model_path.glob('*.safetensors'))
            if (
                missing_files
                or len(model_shards) != {spec['shard_count']}
                or len(all_shards) != {spec['safetensor_count']}
            ):
                raise RuntimeError(
                    'frozen model layout mismatch: '
                    f'missing={{missing_files}} model_shards={{len(model_shards)}} '
                    f'all_shards={{len(all_shards)}}'
                )
            subprocess.check_call([
                sys.executable, '/tmp/arc3-m0/source/scripts/profile_m0_openai.py',
                '--candidate-id', {spec['candidate_id']!r},
                '--model-id', {spec['model_id']!r},
                '--model-revision', {spec['revision']!r},
                '--model-path', str(model_path),
                '--engine', 'vllm==0.19.0',
                '--reasoning-setting', {spec['reasoning']!r},
                '--launch-spec', '/tmp/arc3-m0/source/{spec['launch_spec']}',
                '--output', '/kaggle/working/{spec['output_name']}',
                # Production is bounded at 80 actions for each of 110 games.
                # Treat every legal action as requiring a model call for the
                # conservative M0 projection, even though later admission may
                # use deterministic or cached decisions instead.
                '--projected-requests', '8800',
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
                f"# M0 target-RTX profile: {spec['label']}\n\n"
                "This is a measurement notebook, not a competition submission. "
                "It fails unless Kaggle assigns the target RTX Pro 6000."
            ),
            _install_cell(),
            unpack,
            run,
        ],
    }


def write(candidate: str) -> Path:
    spec = PROFILE_SPECS[candidate]
    output_dir = ROOT / spec["output_dir"]
    notebook_path = output_dir / "profile.ipynb"
    metadata_path = output_dir / "kernel-metadata.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    notebook_path.write_text(json.dumps(build(candidate), indent=1) + "\n")
    if not metadata_path.exists():
        raise SystemExit(f"missing tracked metadata: {metadata_path.relative_to(ROOT)}")
    print(f"[build_m0_profile_notebook] wrote {notebook_path.relative_to(ROOT)}")
    return notebook_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=sorted(PROFILE_SPECS), default="q38")
    args = parser.parse_args()
    write(args.candidate)


if __name__ == "__main__":
    main()
