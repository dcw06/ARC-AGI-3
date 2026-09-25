"""Freeze a runnable, GPU-disabled review notebook for the action-effect-history comparison."""
import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'r2'
OUT = ROOT / f'notebooks/action-effect-history-v1-review-{REVISION}'
MARKER = '    # AEH_AUTHORITY_SIDECARS: reviewed packaging inserts bound approvals here.\n'
MODE_LINE = "MODE='live'\n"
REVIEW_DOCUMENTS = ('reports/action_effect_history_v1_protocol.md', 'reports/action_effect_history_v1_budget.json',
                    'reports/action_effect_history_v1_token_audit.json',
                    'reports/action_effect_history_v1_control_inventory.json',
                    'reports/action_effect_history_v1_environment_check.json',
                    'reports/action_effect_history_v1_rehearsal_results.json',
                    'reports/action_effect_history_v1_review.md',
                    'scripts/action_effect_history_v1_package.py', 'scripts/review_action_effect_history_v1_notebook.py',
                    'scripts/build_action_effect_history_v1_review.py', 'scripts/check_action_effect_history_v1.py',
                    'scripts/rehearse_action_effect_history_v1.py', 'tests/test_action_effect_v1.py',
                    'tests/test_action_effect_history_v1_contract.py', 'tests/test_action_effect_history_v1_runner.py',
                    'tests/test_action_effect_history_v1_connected.py', 'tests/test_action_effect_history_v1_snapshot.py',
                    'tests/test_action_effect_history_v1_negative.py')


def inventory():
    names = set()
    for directory in ('agent', 'certification', 'evaluation', 'research/action_effect_history_v1',
                      'research/action_effect_v1', 'research/grounded_action_v1'):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*.py'))
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'config').iterdir()
                 if p.is_file() and p.suffix in ('.json', '.yaml'))
    names.update(('research/action_effect_history_v1/protocol.json', 'research/action_effect_v1/fixtures.json',
                  'scripts/action_effect_history_v1_launch.py', 'scripts/run_grounded_action_v1_engine_local.py',
                  'scripts/evaluate_action_effect_history_v1.py',
                  'reports/phase4_v2_offline_package.json', 'reports/phase4_torch_wheel_inspection.json',
                  'reports/phase4_transient_v2_protocol.json', 'reports/m0_profiles/m0-q3vl30-instruct.json',
                  'reports/perception_stage_b_v1_case_protocol.json',
                  'reports/integrated_case_v1/initial_observation.json',
                  'reports/integrated_case_v1/geometry_reference.json',
                  'certification/phase4_integrated_v2/tokenizer_manifest.json'))
    names = {n for n in names if '__pycache__' not in n}
    missing = [n for n in names if not (ROOT / n).is_file() or (ROOT / n).is_symlink()]
    if missing:
        raise ValueError('missing or linked review source: ' + ', '.join(sorted(missing)[:5]))
    return sorted(names)


def cell(hashes, packed):
    return ('import base64,hashlib,json,lzma,pathlib,shutil,sys,tempfile,time\n'
            'started=time.monotonic()\n'
            + MODE_LINE +
            "source=pathlib.Path(tempfile.mkdtemp(prefix='action-effect-history-source-'))\n"
            'try:\n'
            f'    bindings={hashes!r}\n'
            f'    payload=json.loads(lzma.decompress(base64.b85decode({packed!r})))\n'
            '    if set(payload)!=set(bindings): raise ValueError("source inventory")\n'
            '    for name,encoded in payload.items():\n'
            '        raw=base64.b64decode(encoded,validate=True)\n'
            '        if hashlib.sha256(raw).hexdigest()!=bindings[name]: raise ValueError("source hash: "+name)\n'
            '        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)\n'
            + MARKER +
            '    sys.path.insert(0,str(source))\n'
            '    from scripts.action_effect_history_v1_launch import notebook_entry\n'
            '    notebook_entry(source,started,MODE)\n'
            'finally:\n'
            '    shutil.rmtree(source)\n')


def build(output=OUT):
    output = Path(output)
    if output.exists():
        raise FileExistsError('review revisions are immutable; create a new revision')
    payload = {name: (ROOT / name).read_bytes() for name in inventory()}
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()}
    packed = base64.b85encode(lzma.compress(json.dumps({n: base64.b64encode(r).decode() for n, r in payload.items()},
                                                       sort_keys=True).encode(), preset=6)).decode()
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {},
                           'source': '# Action-effect history v1: review snapshot\n'
                                     'GPU disabled. The runnable cell requires separately bound source approval, '
                                     'compute authorization and one fresh reservation. Twelve episodes, at most 12 '
                                     'actions each, 144 policy calls and one canary.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
                           'source': cell(hashes, packed)}]}
    metadata = {'id': 'daichongwei06/arc3-action-effect-history-v1-review-' + REVISION,
                'title': 'ARC3 Action Effect History V1 Review ' + REVISION.upper(), 'code_file': 'profile.ipynb',
                'language': 'python', 'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': False,
                'enable_tpu': False, 'enable_internet': False, 'competition_sources': ['arc-prize-2026-arc-agi-3'],
                'dataset_sources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
                'model_sources': ['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    encoded = (json.dumps(notebook, indent=2) + '\n').encode()
    if len(encoded) >= 900000:
        raise ValueError('review notebook exceeds the upload size guard: %d bytes' % len(encoded))
    output.mkdir(parents=True)
    (output / 'profile.ipynb').write_bytes(encoded)
    (output / 'kernel-metadata.json').write_bytes((json.dumps(metadata, indent=2) + '\n').encode())
    lock = {'status': 'reviewed_launch_source', 'scope': 'action-effect-history-v1', 'revision': REVISION,
            'bindings': hashes, 'artifacts': {n: hashlib.sha256((output / n).read_bytes()).hexdigest()
                                              for n in ('profile.ipynb', 'kernel-metadata.json')},
            'review_documents': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in REVIEW_DOCUMENTS},
            'authorized_seconds': 0, 'gpu_launch_authorized': False}
    (output / 'review-source-lock.json').write_bytes((json.dumps(lock, indent=2) + '\n').encode())
    return lock


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    lock = build(args.output)
    print(json.dumps({'files': len(lock['bindings']), 'notebook_bytes': (args.output / 'profile.ipynb').stat().st_size}))
