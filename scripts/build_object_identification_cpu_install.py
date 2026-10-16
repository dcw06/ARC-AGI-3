"""Build a private CPU installation review packet locally; never submits jobs."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(previous, output, notebook_id):
    previous, output = Path(previous), Path(output)
    if not re.fullmatch(r'[a-z0-9_-]+/[a-z0-9-]+', notebook_id):
        raise ValueError('expected owner/notebook-slug')
    if output.exists():
        raise FileExistsError('preserve every prior review package')
    lock = json.loads((previous/'review-lock.json').read_bytes())
    for name, digest in lock['artifacts'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or sha((previous/path).read_bytes()) != digest:
            raise ValueError('previous byte-review artifact mismatch')
    manifest = json.loads((previous/'manifest.json').read_bytes())
    if (manifest['schema'] != 'internvl_cpu_dataset_bytes_v1'
            or [d['kind'] for d in manifest['datasets']] != ['model', 'inputs', 'publisher_wheels']
            or [len(d['files']) for d in manifest['datasets']] != [27, 12, 177]):
        raise ValueError('expected reviewed 216-file byte manifest')
    manifest.update(schema='internvl_cpu_install_check_v1', worker_budget_seconds=1700,
                    cleanup_reserve_seconds=120,
                    historical_byte_review_lock_sha256=sha((previous/'review-lock.json').read_bytes()))
    source_names = [
        'research/object_identification_v1/install_check.py',
        'research/object_identification_v1/runtime.py',
        'research/object_identification_v1/runtime_source_pin.json',
        'research/object_identification_v1/runtime_requirements_extra.lock',
        'research/object_identification_v1/mount_check.py',
        'certification/direct_publisher_smoke_v1/install.py',
        'certification/direct_publisher_smoke_v1/server.py',
        'certification/direct_publisher_smoke_v1/trusted_requirements.lock',
    ]
    files = {'reviewed-source/'+name: (ROOT/name).read_bytes() for name in source_names}
    for package in ('research', 'research/object_identification_v1', 'certification',
                    'certification/direct_publisher_smoke_v1'):
        files['reviewed-source/'+package+'/__init__.py'] = b''
    payload = {name: base64.b64encode(raw).decode() for name, raw in files.items()}
    hashes = {name: sha(raw) for name, raw in files.items()}
    code = '''# Reviewed CPU installation check. No pretrained weights or GPU execution.
import base64, hashlib, json, pathlib, sys
base = pathlib.Path('/kaggle/working/internvl-cpu-install-verification-v1')
if base.exists():
    raise FileExistsError('preserve previous installation attempt')
base.mkdir(mode=0o700)
payload = %r
hashes = %r
for name, encoded in payload.items():
    raw = base64.b64decode(encoded, validate=True)
    assert hashlib.sha256(raw).hexdigest() == hashes[name], name
    target = base/name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
manifest_raw = base64.b64decode(%r, validate=True)
assert hashlib.sha256(manifest_raw).hexdigest() == %r
sys.path.insert(0, str(base/'reviewed-source'))
from research.object_identification_v1.install_check import run
run(json.loads(manifest_raw), output=base/'result.json')
''' % (payload, hashes, base64.b64encode(canonical(manifest)).decode(), sha(canonical(manifest)))
    notebook = {'nbformat': 4, 'nbformat_minor': 5,
                'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
                'cells': [{'cell_type': 'markdown', 'id': 'scope', 'metadata': {}, 'source': [
                    '# Private CPU installation compatibility check\n',
                    'GPU/TPU/internet off. Fresh offline 175-wheel environment, pip check, exact versions,\n',
                    'pinned tokenizer/classes and tiny random-weight CPU forward. No pretrained loading,\n',
                    'study requests, game actions or scorecards. Not GPU compatibility or cap proof.\n']},
                    {'cell_type': 'code', 'id': 'install-check', 'metadata': {},
                     'execution_count': None, 'outputs': [], 'source': code.splitlines(keepends=True)}]}
    metadata = json.loads((previous/'kernel-metadata.json').read_bytes())
    metadata.update(id=notebook_id, title='ARC3 InternVL CPU Installation Verification V1',
                    is_private=True, enable_gpu=False, enable_tpu=False, enable_internet=False)
    if (metadata['dataset_sources'] != [d['ref']+'/'+str(d['version']) for d in manifest['datasets']]
            or metadata.get('model_sources') or metadata.get('kernel_sources')):
        raise ValueError('dataset attachments differ from reviewed byte manifest')
    if (not metadata.get('docker_image', '').endswith(
            '@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461')
            or metadata.get('docker_image_pinning_type') != 'original'):
        raise ValueError('immutable image differs from completed CPU byte check')
    scope = {'status': 'prepared_not_uploaded_or_authorized', 'account': notebook_id.split('/')[0],
             'access': 'account_holder_only', 'gpu': False, 'tpu': False, 'internet': False,
             'attempts_proposed': 1, 'automatic_retries': 0,
             'session_timeout_seconds_proposed': 1800, 'worker_budget_seconds': 1700,
             'cleanup_reserve_seconds': 120, 'model_requests': 0, 'game_actions': 0,
             'scorecards': 0, 'pretrained_weights_loaded': False,
             'package_installs': '175 pinned wheels into one temporary isolated environment',
             'provider_full_gpu_job_cap_verified': False}
    guide = '''# CPU installation review

One proposed private account-only saved CPU run; GPU, TPU and internet off.
Requested session runtime timeout: 1,800 seconds. Worker: 1,700 seconds,
including a 120-second cleanup reserve. One attempt, no automatic retries.
This is a NEW compute scope, separate from the consumed byte-only attempt.
No upload, reservation, submission or approval is supplied by this builder.

The worker rehashes all 216 mounted files before any installation. Host pip
manages a fresh venv created without pip; both wheel mounts are supplied via
--find-links, with --no-index, --require-hashes and binary-only installation.
The 174 original pins are unchanged; separately pinned timm 1.0.20 makes 175.
No host site-packages are inherited. All 175 distributions and pip check must
match, then the exact pinned InternVL classes/tokenizer are imported offline.
The only forward uses a tiny random 46,416-parameter model and synthetic input
on CPU. Six real images are preprocessed on CPU, never fed into that model.
No pretrained tensors are loaded. No model requests, game actions or scorecards.

Subprocess ownership/descendant termination uses the existing reviewed smoke
installer. Temporary venv/cache removal and evidence writes count toward the
worker deadline. Source extraction is retained as reviewed evidence, not an
unremoved temporary environment. All raw logs/receipts stay private.

A result file is PROVISIONAL: independent collection must verify the exact saved
source, immutable image, private/offline CPU settings, provider COMPLETE status,
result and completion-witness hashes, and the matching final cell-output marker.
ERROR, interrupted/late finalization, missing witness or stale evidence fail.
Do not infer success from the provisional result's status alone. Requested dataset
version labels may be omitted by the pull API; verify the locked mounted bytes.

This checks installation and CPU execution of CUDA-linked wheels on the pinned
image. It does not validate pretrained answers, full checkpoint loading, GPU
kernels or enforcement of the separate entire-GPU-job one-hour cap. That cap
remains unresolved. This packet supplies no GPU authority.
'''
    files.update({'manifest.json': canonical(manifest), 'kernel-metadata.json': canonical(metadata),
                  'profile.ipynb': canonical(notebook), 'scope.json': canonical(scope),
                  'review.md': guide.encode()})
    packet_lock = {'schema': 'internvl_cpu_install_review_lock_v1',
                   'artifacts': {name: sha(raw) for name, raw in sorted(files.items())},
                   'source_sha256': {name: sha((ROOT/name).read_bytes()) for name in source_names},
                   'builder_sha256': sha(Path(__file__).read_bytes()),
                   'manifest_sha256': sha(canonical(manifest)), 'scope': scope}
    files['review-lock.json'] = canonical(packet_lock)
    output.mkdir(mode=0o700)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'prepared': str(output), 'review_lock_sha256': sha(files['review-lock.json']),
            'provider_writes': 0, 'compute_jobs': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-byte-review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--notebook-id', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.previous_byte_review, args.output, args.notebook_id), indent=2))
