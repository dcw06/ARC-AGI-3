"""Freeze a runnable, GPU-disabled Stage B target notebook for source review."""
import base64
import hashlib
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'notebooks/phase4-grounded-action-v1-launch-r2'


def inventory():
    names = set()
    for directory in ('agent', 'certification', 'evaluation',
                      'research/grounded_action_v1'):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*.py'))
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'config').iterdir()
                 if p.is_file() and p.suffix in ('.json', '.yaml'))
    names.update(('scripts/run_grounded_action_v1_engine_local.py',
                  'scripts/phase4_grounded_action_v1_launch.py',
                  'reports/perception_stage_b_v1_case_protocol.json',
                  'reports/phase4_v2_offline_package.json',
                  'reports/phase4_transient_v2_protocol.json',
                  'reports/m0_profiles/m0-q3vl30-instruct.json',
                  'reports/integrated_case_v1/initial_observation.json',
                  'reports/integrated_case_v1/geometry_reference.json',
                  'certification/phase4_integrated_v2/tokenizer_manifest.json'))
    if any(not (ROOT / name).is_file() or (ROOT / name).is_symlink() for name in names):
        raise ValueError('missing or linked launch source')
    return sorted(names)


def build(output=OUT):
    output = Path(output)
    if output.exists():
        raise FileExistsError('launch review is immutable; create a new revision')
    payload = {name: (ROOT / name).read_bytes() for name in inventory()}
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()}
    packed = base64.b85encode(lzma.compress(json.dumps({
        name: base64.b64encode(raw).decode() for name, raw in payload.items()
    }, sort_keys=True).encode(), preset=6)).decode()
    code = (
        'import base64,hashlib,json,lzma,pathlib,shutil,sys,tempfile,time\n'
        'started=time.monotonic()\n'
        "source=pathlib.Path(tempfile.mkdtemp(prefix='stage-b-launch-source-'))\n"
        'try:\n'
        f'    bindings={hashes!r}\n'
        f'    payload=json.loads(lzma.decompress(base64.b85decode({packed!r})))\n'
        '    if set(payload)!=set(bindings): raise ValueError("source inventory")\n'
        '    for name,encoded in payload.items():\n'
        '        raw=base64.b64decode(encoded,validate=True)\n'
        '        if hashlib.sha256(raw).hexdigest()!=bindings[name]: raise ValueError("source hash: "+name)\n'
        '        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)\n'
        '    # STAGE_B_AUTHORITY_SIDECARS: reviewed packaging inserts bound approvals here.\n'
        '    sys.path.insert(0,str(source))\n'
        '    from research.grounded_action_v1.authority import require\n'
        '    require(source)\n'
        '    from scripts.phase4_grounded_action_v1_launch import run\n'
        "    run('/kaggle/working/phase4-grounded-action-v1',pathlib.Path('/kaggle/working'),"
        'started=started,root=source)\n'
        'finally:\n'
        '    shutil.rmtree(source)\n'
    )
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3',
                                            'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {},
                           'source': '# Stage B target launch review\n'
                                     'GPU disabled; the runnable cell requires separately '
                                     'bound source approval, compute authorization, and reservation.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None,
                           'outputs': [], 'source': code}]}
    metadata = {'id': 'daichongwei06/arc3-phase4-grounded-action-v1-launch-review-r2',
                'title': 'ARC3 Grounded Action Launch Review R2',
                'code_file': 'profile.ipynb', 'language': 'python', 'kernel_type': 'notebook',
                'is_private': True, 'enable_gpu': False, 'enable_tpu': False,
                'enable_internet': False,
                'competition_sources': ['arc-prize-2026-arc-agi-3'],
                'dataset_sources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
                'model_sources': ['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    output.mkdir(parents=True)
    for name, value in (('profile.ipynb', notebook), ('kernel-metadata.json', metadata)):
        (output / name).write_bytes((json.dumps(value, indent=2) + '\n').encode())
    lock = {'status': 'reviewed_launch_source',
            'scope': 'phase4-grounded-action-stage-b-live-r1',
            'bindings': hashes,
            'artifacts': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                          for name in ('profile.ipynb', 'kernel-metadata.json')},
            'authorized_seconds': 0, 'gpu_launch_authorized': False}
    (output / 'review-source-lock.json').write_bytes((json.dumps(lock, indent=2) + '\n').encode())
    return lock


if __name__ == '__main__':
    result = build()
    print(json.dumps({'files': len(result['bindings']), 'output': str(OUT)}))
