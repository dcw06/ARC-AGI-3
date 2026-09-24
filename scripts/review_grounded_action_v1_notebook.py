"""Independently inspect unpacked review notebook and source bindings."""
import ast
import base64
import hashlib
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'notebooks/phase4-grounded-action-v1-review-r1'


def review(folder=FOLDER):
    folder = Path(folder)
    lock = json.loads((folder / 'review-source-lock.json').read_bytes())
    if (lock['status'] != 'review_only_gpu_disabled_no_live_authority' or
            lock['provider_seconds_authorized'] != 0 or lock['gpu_launch_authorized'] is not False):
        raise ValueError('review authority')
    for name, expected in lock['artifacts'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError('review artifact hash: ' + name)
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    if any(metadata.get(k) for k in ('enable_gpu', 'enable_tpu', 'enable_internet')) or not metadata['is_private']:
        raise ValueError('review notebook settings')
    book = json.loads((folder / 'profile.ipynb').read_bytes())
    if len(book['cells']) != 2 or book['cells'][1]['execution_count'] is not None or book['cells'][1]['outputs']:
        raise ValueError('review notebook execution state')
    source = book['cells'][1]['source']
    tree = ast.parse(source)
    assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and len(node.targets) == 1 and
                   isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('bindings',)}
    if assignments.get('bindings') != lock['bindings']:
        raise ValueError('unpacked source binding')
    encoded = [ast.literal_eval(node.args[0]) for node in ast.walk(tree)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
               node.func.attr == 'b85decode' and len(node.args) == 1]
    if len(encoded) != 1:
        raise ValueError('review payload decoder')
    payload = json.loads(lzma.decompress(base64.b85decode(encoded[0])))
    if set(payload) != set(lock['bindings']):
        raise ValueError('unpacked inventory')
    for name, b64 in payload.items():
        raw = base64.b64decode(b64)
        if (hashlib.sha256(raw).hexdigest() != lock['bindings'][name] or
                hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != lock['bindings'][name]):
            raise ValueError('unpacked source drift: ' + name)
        if name.endswith('.py'):
            ast.parse(raw.decode())
    if any(token in source for token in ('kaggle kernels push', 'enable_gpu=True', 'consume_runtime(')):
        raise ValueError('review cell contains launch path')
    return {'status': 'review_snapshot_verified_no_launch_authority', 'source_files': len(payload),
            'gpu_enabled': False}


if __name__ == '__main__':
    print(json.dumps(review(), sort_keys=True))
