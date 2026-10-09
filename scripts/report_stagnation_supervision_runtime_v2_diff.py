"""Generate the machine-readable runtime-only diff between the R4/R6/R7 payloads and the runtime v2 payload.

Deterministic, read-only over committed files; writes reports/stagnation_supervision_runtime_v2_runtime_diff.json.
    python -m scripts.report_stagnation_supervision_runtime_v2_diff [--check]
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'reports/stagnation_supervision_runtime_v2_runtime_diff.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    return json.loads((ROOT / name).read_bytes())


def build():
    from research.stagnation_supervision_runtime_v2.closure import closure
    from research.stagnation_supervision_runtime_v2.notebook import review_notebook
    r4 = load('notebooks/stagnation-supervision-v1-review-r4/review-source-lock.json')['bindings']
    r6 = load('notebooks/stagnation-supervision-v1-authorization-r6/source-review.json')['bindings']
    r7 = load('notebooks/stagnation-supervision-v1-preparation-r7/review-source-lock.json')['bindings']
    inventory = closure(ROOT)
    successor = {n: sha(ROOT / n) for n in inventory['files']}
    shared = sorted(set(successor) & set(r4))
    dropped = sorted(set(r4) - set(successor))
    added = sorted(set(successor) - set(r4))
    derivation = load('research/stagnation_supervision_runtime_v2/derivation.json')
    protocol = load('research/stagnation_supervision_runtime_v2/protocol.json')
    _, review_metadata, _, _, _ = review_notebook(ROOT, 1)
    r6_metadata = load('notebooks/stagnation-supervision-v1-r6-session1-launch/kernel-metadata.json')
    launch_template = {**{k: v for k, v in review_metadata.items() if k not in ('id', 'title')},
                       'enable_gpu': True, 'machine_shape': protocol['machine_shape'],
                       'dataset_sources': [f"{protocol['dataset']['ref']}/{protocol['dataset']['version']}",
                                           protocol['model']['kaggle_source']],
                       'id': protocol['kernel_ids']['1'], 'title': protocol['kernel_ids']['1'].split('/')[1]}
    metadata_diff = {k: {'r6_launch': r6_metadata.get(k), 'runtime_v2_launch': launch_template.get(k)}
                     for k in sorted(set(r6_metadata) | set(launch_template))
                     if r6_metadata.get(k) != launch_template.get(k)}
    metadata_diff['machine_shape']['r6_launch'] = 'NvidiaRtxPro6000 (set in the SaveKernel request, not the metadata)'
    replaced = {row['derived']: {'from': row['source_path'], 'source_commit': row['source_commit'],
                                 'replacements': len(row['replacements']), 'kind': row['kind']}
                for row in derivation['files']}
    return {
        'schema': 'stagnation_supervision_runtime_v2_runtime_diff_v1',
        'scope': 'runtime only; every science, prompt, scoring, stop-rule and lifecycle file shared with R4 is byte-identical',
        'payloads': {'r4_review': len(r4), 'r6_authorization': len(r6), 'r7_preparation': len(r7),
                     'runtime_v2_review': len(successor)},
        'r6_vs_r4': {'changed': sorted(n for n in set(r6) & set(r4) if r6[n] != r4[n]),
                     'added': sorted(set(r6) - set(r4)), 'removed': sorted(set(r4) - set(r6))},
        'r7_vs_r4': {'changed': sorted(n for n in set(r7) & set(r4) if r7[n] != r4[n]),
                     'added': sorted(set(r7) - set(r4)), 'removed': sorted(set(r4) - set(r7))},
        'runtime_v2_vs_r4': {
            'shared_files': len(shared),
            'shared_files_changed': sorted(n for n in shared if successor[n] != r4[n]),
            'added': added,
            'dropped_count_by_directory': dict(sorted(collections.Counter(
                '/'.join(n.split('/')[:2]) if n.count('/') else n.split('.')[0] for n in dropped).items())),
            'dropped': dropped,
            'dropped_reason': ('outside the computed closure of the runtime v2 entry points (R4 embedded every agent/, '
                               'certification/, evaluation/ and config/ file) or excluded as another scope\'s authority '
                               'records, credential handling or superseded tooling (closure.EXCLUDED)')},
        'replaced_runtime_modules': {
            'research/stagnation_supervision_v1/closed_loop/supervisor.py': 'research/stagnation_supervision_runtime_v2/supervisor.py',
            'research/stagnation_supervision_v1/closed_loop/worker.py': 'research/stagnation_supervision_runtime_v2/worker.py',
            'research/stagnation_supervision_v1/closed_loop/host.py': 'research/stagnation_supervision_runtime_v2/host.py',
            'research/stagnation_supervision_v1/closed_loop/monitor.py': 'research/stagnation_supervision_runtime_v2/monitor.py',
            'research/stagnation_supervision_v1/closed_loop/resources.py': 'research/stagnation_supervision_runtime_v2/resources.py',
            'research/stagnation_supervision_v1/closed_loop/target_evaluate.py': 'research/stagnation_supervision_runtime_v2/target_evaluate.py',
            'research/stagnation_supervision_v1/closed_loop/authority.py': 'research/stagnation_supervision_runtime_v2/authority.py (hand-written gate)',
            'scripts/stagnation_supervision_v1_launch.py': 'research/stagnation_supervision_runtime_v2/launch.py',
            'certification/phase4_integrated_v2/prepare.py': 'research/stagnation_supervision_runtime_v2/prepare.py (hand-written)'},
        'derived_files': replaced,
        'kernel_metadata_r6_launch_vs_runtime_v2_launch': metadata_diff,
        'model': {'r6': {'source': 'Kaggle Model qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1',
                         'mount': '/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/30b-a3b-instruct-fp8/1',
                         'tree_sha256': '052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627',
                         'files': 81, 'bytes': 64526033084},
                  'runtime_v2': {'source': protocol['model']['kaggle_source'], 'mount': protocol['model']['mounted_path'],
                                 'tree_sha256': protocol['model']['tree_sha256'], 'files': protocol['model']['file_count'],
                                 'bytes': protocol['model']['bytes']},
                  'unchanged': ['model id and revision d9748a51', 'six tokenizer/chat-template/config files (byte-identical)',
                                'required files and four-shard layout', 'effective vLLM argv and environment']},
        'installation': {'r6': {'wheel_mount': 'first existing of datasets/driessmit1/... or arc3-vllm-h100-wheelhouse-v3',
                                'wheel_verification': 'SHA256SUMS 44029b36... (179 entries) and wheelhouse-manifest.json bc016164...',
                                'model_install': 'pins vllm/torch/transformers/numpy resolved from --find-links, no hashes',
                                'game_install': '31 competition wheels, R4 pins (unchanged)'},
                         'runtime_v2': {'wheel_mount': 'publisher_host.dataset_mount: exactly one of the two layouts',
                                        'wheel_verification': ('174 trusted wheels plus README.md, SHA256SUMS 805388ef..., '
                                                               'requirements.lock bb3e30ac... (version 1 flat mount)'),
                                        'model_install': 'trusted 174-pin lock ba80d350... with --require-hashes, pip check, imports',
                                        'game_install': '31 competition wheels, R4 pins (unchanged)'}},
        'notebook_interpreter': {'r4_r6_r7': 'first cell imported the supervisor module (agent -> arcengine) before installation',
                                 'runtime_v2': 'first cell imports only standard-library-closed modules; game packages stay in the game venv'},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    value = build()
    text = json.dumps(value, indent=1, sort_keys=True) + '\n'
    if args.check:
        if OUT.read_text(encoding='utf-8') != text:
            raise SystemExit('runtime diff differs from the retained report')
    else:
        OUT.write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps({k: value[k] for k in ('payloads',)}, indent=1))
    print('shared changed:', value['runtime_v2_vs_r4']['shared_files_changed'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
