"""Independently inspect the unpacked Stage B launch review; never use GPU."""
import ast
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'notebooks/phase4-grounded-action-v1-launch-r10'


def review(folder=FOLDER, *, compare_checkout=True):
    folder = Path(folder)
    lock = json.loads((folder / 'review-source-lock.json').read_bytes())
    allowed_scopes = ({'phase4-grounded-action-stage-b-live-r7'} if compare_checkout else
                      {'phase4-grounded-action-stage-b-live-r1',
                       'phase4-grounded-action-stage-b-live-r2',
                       'phase4-grounded-action-stage-b-live-r3',
                       'phase4-grounded-action-stage-b-live-r4',
                       'phase4-grounded-action-stage-b-live-r5',
                       'phase4-grounded-action-stage-b-live-r6',
                       'phase4-grounded-action-stage-b-live-r7'})
    if (lock.get('status') != 'reviewed_launch_source' or
            lock.get('scope') not in allowed_scopes or
            lock.get('authorized_seconds') != 0 or lock.get('gpu_launch_authorized') is not False):
        raise ValueError('review lock state')
    if set(lock['artifacts']) != {'profile.ipynb', 'kernel-metadata.json'}:
        raise ValueError('review artifact inventory')
    for name, digest in lock['artifacts'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise ValueError('review artifact hash: ' + name)
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    if (metadata.get('enable_gpu') is not False or
            metadata.get('enable_tpu') is not False or
            metadata.get('enable_internet') is not False or
            metadata.get('is_private') is not True):
        raise ValueError('review notebook settings')
    book = json.loads((folder / 'profile.ipynb').read_bytes())
    if len(book['cells']) != 2 or book['cells'][1]['execution_count'] is not None or book['cells'][1]['outputs']:
        raise ValueError('review notebook execution state')
    code = book['cells'][1]['source']
    tree = ast.parse(code)
    assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in ast.walk(tree)
                   if isinstance(node, ast.Assign) and len(node.targets) == 1 and
                   isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'bindings'}
    if assignments.get('bindings') != lock['bindings']:
        raise ValueError('notebook source binding')
    decodes = [ast.literal_eval(node.args[0]) for node in ast.walk(tree)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
               node.func.attr == 'b85decode' and len(node.args) == 1]
    if len(decodes) != 1:
        raise ValueError('notebook payload decoder')
    payload = json.loads(lzma.decompress(base64.b85decode(decodes[0])))
    if set(payload) != set(lock['bindings']):
        raise ValueError('unpacked source inventory')
    for name, encoded in payload.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError('source path escapes root')
        raw = base64.b64decode(encoded, validate=True)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != lock['bindings'][name] or (compare_checkout and hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError('unpacked source drift: ' + name)
        if name.endswith('.py'):
            ast.parse(raw.decode())
    if code.count('# STAGE_B_AUTHORITY_SIDECARS:') != 1 or code.count('    require(source)\n') != 1:
        raise ValueError('launch authority placement')
    if code.index('    require(source)') > code.index('    from scripts.phase4_grounded_action_v1_launch import run'):
        raise ValueError('launch import precedes authority')
    with tempfile.TemporaryDirectory(prefix='stage-b-review-exec-') as folder_name:
        temporary = Path(folder_name)
        script = temporary / 'review.py'
        script.write_text(code)
        environment = dict(os.environ, TMPDIR=folder_name, TMP=folder_name, TEMP=folder_name)
        result = subprocess.run([sys.executable, str(script)], cwd=temporary,
                                env=environment, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 or 'PermissionError: Stage B requires reviewed source' not in result.stderr:
            raise ValueError('unapproved review notebook did not stop at authority gate')
        if {p.name for p in temporary.iterdir()} != {'review.py'}:
            raise ValueError('review execution left staged source')
    return {'status': 'launch_source_review_verified_pending_separate_approvals',
            'source_files': len(payload), 'notebook_bytes': (folder / 'profile.ipynb').stat().st_size,
            'review_lock_sha256': hashlib.sha256((folder / 'review-source-lock.json').read_bytes()).hexdigest(),
            'gpu_enabled': False, 'unapproved_execution_rejected': True}


if __name__ == '__main__':
    print(json.dumps(review(), sort_keys=True))
