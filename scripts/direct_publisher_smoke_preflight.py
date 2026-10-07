"""Build a CPU-only review snapshot or verify mounted dataset bytes; never launch.

  python scripts/direct_publisher_smoke_preflight.py review-build
  python scripts/direct_publisher_smoke_preflight.py review-check
  python scripts/direct_publisher_smoke_preflight.py verify --dataset-root PATH
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.direct_publisher_smoke_v1.preflight import (PACKAGE, PreflightFailed, load_inputs,
                                                             verify_mounted)


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def build_review():
    proposal, _, _ = load_inputs()
    names = ('__init__.py', 'preflight.py', 'proposal.json', 'trusted_manifest.json', 'trusted_requirements.lock')
    payload = {name: base64.b64encode((PACKAGE / name).read_bytes()).decode() for name in names}
    bindings = {name: hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() for name in names}
    code = '''import base64, hashlib, json, pathlib, shutil, sys, tempfile
# CPU integrity only: no pip, package imports, server, GPU queries or launch.
payload = %r
bindings = %r
source = pathlib.Path(tempfile.mkdtemp(prefix='direct-publisher-preflight-'))
try:
    package = source / 'certification/direct_publisher_smoke_v1'
    package.mkdir(parents=True)
    for name, value in payload.items():
        data = base64.b64decode(value)
        if hashlib.sha256(data).hexdigest() != bindings[name]:
            raise ValueError('embedded source drift: ' + name)
        (package / name).write_bytes(data)
    sys.path.insert(0, str(source))
    from certification.direct_publisher_smoke_v1.preflight import verify_mounted
    roots = [pathlib.Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),
             pathlib.Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3')]
    mounted = [p for p in roots if p.is_dir()]
    if len(mounted) != 1:
        raise ValueError('expected exactly one known dataset mount; do not guess another source')
    receipt = verify_mounted(mounted[0])
    print(json.dumps(receipt, indent=2))
    output = pathlib.Path('/kaggle/working/direct-publisher-byte-integrity.json')
    output.write_text(json.dumps(receipt, indent=2) + '\\n')
finally:
    sys.path.remove(str(source)) if str(source) in sys.path else None
    shutil.rmtree(source)
''' % (payload, bindings)
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {}, 'source':
                           '# Direct-publisher smoke intake: CPU-only review draft\n'
                           'Checks mounted wheel bytes against the trusted inventory. Does not install or run '
                           'a model, establish permission, verify provider version, or authorize a smoke test. '
                           'Requested dataset version: 1. The attachment version needs separate provider evidence.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None,
                           'outputs': [], 'source': code}]}
    metadata = {'id': 'REPLACE_WITH_KAGGLE_OWNER/arc3-direct-publisher-smoke-preflight-review',
                'title': 'ARC3 Direct Publisher Smoke CPU Preflight Review', 'code_file': 'profile.ipynb',
                'language': 'python', 'kernel_type': 'notebook', 'is_private': True,
                'enable_gpu': False, 'enable_tpu': False, 'enable_internet': False,
                'dataset_sources': [proposal['dataset']['ref']], 'model_sources': [], 'competition_sources': []}
    folder = ROOT / 'notebooks/direct-publisher-smoke-v1-preflight-review-r1'
    artifacts = {'profile.ipynb': encode(notebook), 'kernel-metadata.json': encode(metadata)}
    if len(artifacts['profile.ipynb']) >= 900000:
        raise PreflightFailed('review notebook size guard exceeded')
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        (folder / name).write_bytes(data)
    lock = {'status': 'cpu_preflight_review_draft_not_approved_not_launchable',
            'scope': 'direct-publisher-smoke-v1', 'bindings': bindings,
            'artifacts': {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()},
            'gpu_enabled': False, 'requested_dataset_version': 1, 'attachment_version_verified': False}
    (folder / 'review-source-lock.json').write_bytes(encode(lock))
    return {'review_folder': folder.relative_to(ROOT).as_posix(), 'status': lock['status']}


def review_check():
    folder = ROOT / 'notebooks/direct-publisher-smoke-v1-preflight-review-r1'
    lock = json.loads((folder / 'review-source-lock.json').read_bytes())
    for name, digest in lock['artifacts'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise PreflightFailed('review artifact drift: ' + name)
    for name, digest in lock['bindings'].items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != digest:
            raise PreflightFailed('review source drift: ' + name)
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    if any(metadata.get(name) is not False for name in ('enable_gpu', 'enable_tpu', 'enable_internet')):
        raise PreflightFailed('CPU review metadata enables compute or internet')
    if metadata.get('is_private') is not True or metadata.get('model_sources'):
        raise PreflightFailed('CPU review metadata is public or attaches a model')
    code = json.loads((folder / 'profile.ipynb').read_bytes())['cells'][1]['source']
    with tempfile.TemporaryDirectory(prefix='direct-publisher-review-check-') as base:
        base = Path(base)
        scratch, decoys, calls = base / 'tmp', base / 'bin', base / 'effect-calls.log'
        scratch.mkdir()
        decoys.mkdir()
        for name in ('nvidia-smi', 'pip', 'pip3'):
            decoy = decoys / name
            decoy.write_text('#!/bin/sh\necho called >> "' + str(calls) + '"\nexit 1\n')
            decoy.chmod(0o755)
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
        env.update(CUDA_VISIBLE_DEVICES='', TMPDIR=str(scratch), TMP=str(scratch), TEMP=str(scratch),
                   PATH=str(decoys) + os.pathsep + env.get('PATH', ''))
        process = subprocess.run([sys.executable, '-I', '-c', code], cwd=base, env=env,
                                 capture_output=True, text=True, timeout=60)
        receipt = {'schema': 'direct_publisher_cpu_intake_review_check_v1',
                   'evidence_class': 'local_cpu_control_check_not_remote_wheel_or_gpu_evidence',
                   'review_lock_sha256': hashlib.sha256((folder / 'review-source-lock.json').read_bytes()).hexdigest(),
                   'exit_code': process.returncode,
                   'missing_mount_refused': 'expected exactly one known dataset mount' in process.stderr,
                   'pip_or_gpu_query_invoked': calls.exists(),
                   'temporary_files_left': sorted(p.name for p in scratch.iterdir()),
                   'account_attachment_verified': False, 'remote_wheel_bytes_verified': False,
                   'launch_authorized': False}
    receipt['passed'] = (receipt['exit_code'] != 0 and receipt['missing_mount_refused']
                         and not receipt['pip_or_gpu_query_invoked'] and not receipt['temporary_files_left'])
    (ROOT / 'reports/direct_publisher_smoke_v1/review_check.json').write_bytes(encode(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('review-build', 'review-check', 'verify'))
    parser.add_argument('--dataset-root', type=Path)
    args = parser.parse_args()
    if args.command == 'verify' and args.dataset_root is None:
        parser.error('verify requires --dataset-root')
    try:
        if args.command == 'review-build':
            receipt = build_review()
        elif args.command == 'review-check':
            receipt = review_check()
        else:
            receipt = verify_mounted(args.dataset_root)
    except (PreflightFailed, OSError, ValueError, KeyError) as exc:
        print(json.dumps({'integrity_passed': False, 'error': str(exc), 'launch_authorized': False}))
        return 1
    print(json.dumps(receipt, indent=2))
    return 1 if receipt.get('passed') is False else 0


if __name__ == '__main__':
    raise SystemExit(main())
