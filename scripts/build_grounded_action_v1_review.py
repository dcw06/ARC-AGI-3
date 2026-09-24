"""Build a GPU-disabled, review-only Stage B source snapshot; no launch cell."""
import base64
import hashlib
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'notebooks/phase4-grounded-action-v1-review-r2'


def inventory():
    names = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / 'research/grounded_action_v1').glob('*.py'))]
    names += [f'scripts/{name}.py' for name in (
        'run_grounded_action_v1_engine_local', 'run_grounded_action_v1_local',
        'replay_grounded_action_v1_local', 'replay_grounded_action_v1_archive',
        'archive_grounded_action_v1_local', 'audit_grounded_action_v1_tokens',
        'inspect_phase4_perception_stage_a_v1')]
    names += ['tests/test_grounded_action_v1_local.py', 'tests/test_grounded_action_v1_engine.py',
              'tests/test_grounded_action_v1_bridge.py',
              'reports/perception_stage_b_v1_case_protocol.json',
              'reports/perception_stage_b_v1_token_audit.json',
              'reports/perception_stage_b_v1_local_archive.json',
              'reports/perception_stage_b_v1_local_review.md',
              'reports/perception_stage_b_v0_protocol.md',
              'reports/perception_stage_b_v2_integration_review.md']
    return sorted(set(names))


def build(output=OUT):
    output = Path(output)
    if output.exists() and {p.name for p in output.iterdir()} != {
            'profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json'}:
        raise ValueError('unexpected review output inventory')
    contents = {name: (ROOT / name).read_bytes() for name in inventory()}
    bindings = {name: hashlib.sha256(raw).hexdigest() for name, raw in contents.items()}
    encoded = base64.b85encode(lzma.compress(json.dumps(
        {name: base64.b64encode(raw).decode() for name, raw in contents.items()},
        sort_keys=True).encode(), preset=6)).decode()
    cell = (
        'import base64, hashlib, json, lzma\n'
        f'bindings = {bindings!r}\n'
        f'payload = json.loads(lzma.decompress(base64.b85decode({encoded!r})))\n'
        'assert set(payload) == set(bindings)\n'
        'for name, raw64 in payload.items():\n'
        '    assert hashlib.sha256(base64.b64decode(raw64)).hexdigest() == bindings[name], name\n'
        "print('Stage B review source verified; GPU and live execution disabled')\n"
    )
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {},
                           'source': '# Stage B grounded action: review-only source snapshot\n'
                                     'CPU archive and token audit are bound below. No model startup, game action, '
                                     'source approval, reservation, or launch entrypoint is included.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': cell}]}
    metadata = {'id': 'daichongwei06/arc3-phase4-grounded-action-v1-review-r2',
                'title': 'ARC3 Grounded Action V1 Review R2', 'code_file': 'profile.ipynb',
                'language': 'python', 'kernel_type': 'notebook', 'is_private': True,
                'enable_gpu': False, 'enable_tpu': False, 'enable_internet': False,
                'competition_sources': [], 'dataset_sources': [], 'model_sources': []}
    output.mkdir(parents=True, exist_ok=True)
    for name, content in (('profile.ipynb', notebook), ('kernel-metadata.json', metadata)):
        (output / name).write_bytes((json.dumps(content, indent=2) + '\n').encode())
    lock = {'status': 'review_only_gpu_disabled_no_live_authority',
            'bindings': bindings,
            'artifacts': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                          for name in ('profile.ipynb', 'kernel-metadata.json')},
            'provider_seconds_authorized': 0, 'gpu_launch_authorized': False}
    (output / 'review-source-lock.json').write_bytes((json.dumps(lock, indent=2) + '\n').encode())
    return lock


if __name__ == '__main__':
    print(json.dumps({'files': len(build()['bindings']), 'output': str(OUT)}))
