"""Runtime v2 notebook packaging (hand-written successor of the R4 builder and the verified runtime's notebook.py).

The review notebook embeds exactly the computed payload closure (closure.py), hash-bound, with GPU, TPU and
internet disabled; its single code cell calls `launch.notebook_entry` in live mode, whose first statement is the
runtime v2 gate, so in this checkout it refuses before installation, model or GPU use. Its metadata carries the
verified runtime's immutable image pin, the ARC-AGI-3 competition attachment and the version-pinned input
references (the private model dataset as its REPLACE_WITH_ placeholder; the wheel dataset is attached only once no
placeholder remains, as in the verified runtime's review packaging).

The launch package is the same reviewed notebook with the review lock, decision, evidence, execution, reservation
and claim records injected and the session line set from the execution lock; it can be built only when the gate
passes (`launch_artifacts`). Nothing here submits, uploads or contacts a provider.
"""
import base64
import hashlib
import json
import lzma
from pathlib import Path
import re

from research.stagnation_supervision_runtime_v2 import authority as A
from research.stagnation_supervision_runtime_v2.closure import closure

ROOT = A.ROOT
SIZE_GUARD = 900000
MARKER = '    sys.path.insert(0, str(source))\n'
SESSION_LINE = "SESSION = '1'\n"
IMAGE = re.compile(r'gcr\.io/kaggle-(?:private-byod|gpu-images)/python@sha256:[a-f0-9]{64}')
CELL = '''import base64, hashlib, json, lzma, pathlib, shutil, sys, tempfile, time
started = time.monotonic()  # one clock: extraction, installation, study, cleanup and evidence
MODE = 'live'
SESSION = '1'
source = pathlib.Path(tempfile.mkdtemp(prefix='stagnation-supervision-runtime-v2-source-'))
try:
    payload = json.loads(lzma.decompress(base64.b85decode({packed!r})))
    bindings = {bindings!r}
    if set(payload) != set(bindings):
        raise ValueError('embedded source inventory differs from its bindings')
    for name, value in payload.items():
        data = base64.b64decode(value, validate=True)
        if hashlib.sha256(data).hexdigest() != bindings[name]:
            raise ValueError('embedded source drift: ' + name)
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    sys.path.insert(0, str(source))
    from research.stagnation_supervision_runtime_v2.launch import notebook_entry
    receipt = notebook_entry(source, started, MODE, SESSION)  # the runtime v2 gate runs first and refuses without authority
    print(json.dumps({{k: receipt.get(k) for k in ('study_status', 'error', 'elapsed_seconds', 'installation')}}))
finally:
    shutil.rmtree(source)
'''


def source_names(root=ROOT):
    value = closure(root)
    if value['unresolved_project_imports'] or value['missing_data']:
        raise ValueError('payload closure incomplete: ' + ', '.join(value['unresolved_project_imports'] + value['missing_data']))
    return value['files'], value


def image_metadata(protocol):
    """An immutable Kaggle GPU image; never a mutable tag or latest (the R4/R6 packages had no pin)."""
    pin = protocol.get('kaggle_image')
    if (not isinstance(pin, dict) or not isinstance(pin.get('docker_image'), str)
            or not IMAGE.fullmatch(pin['docker_image']) or pin.get('docker_image_pinning_type') != 'original'):
        raise ValueError('immutable Kaggle GPU image pin required')
    return {k: pin[k] for k in ('docker_image', 'docker_image_pinning_type')}


def input_sources(protocol, pending=False):
    """Version-pinned wheel dataset and dataset-backed model; no Kaggle Model source (R4/R6 used one)."""
    dataset, model = protocol['dataset'], protocol['model']
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', dataset['ref']) or type(dataset['version']) is not int:
        raise ValueError('version-pinned wheel dataset reference required')
    if model.get('source_kind') != 'dataset' or not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*',
                                                                  model['kaggle_source']):
        raise ValueError('version-pinned model dataset reference required')
    if model['kaggle_source'].rsplit('/', 1)[0] == dataset['ref']:
        raise ValueError('model and wheel datasets must be distinct')
    datasets = [] if pending else [f"{dataset['ref']}/{dataset['version']}"]
    return {'dataset_sources': datasets + [model['kaggle_source']], 'model_sources': []}


def competition_sources(protocol):
    if protocol.get('competition', {}).get('ref') != 'arc-prize-2026-arc-agi-3':
        raise ValueError('explicit ARC-AGI-3 competition binding required (game files and wheels)')
    return ['arc-prize-2026-arc-agi-3']


def encode(value):
    return (json.dumps(value, indent=1, sort_keys=True) + '\n').encode()


def review_notebook(root=ROOT, revision=1):
    protocol = A.load_protocol(root)
    names, inventory = source_names(root)
    bindings = {n: A.sha256(Path(root) / n) for n in names}
    payload = {n: base64.b64encode((Path(root) / n).read_bytes()).decode() for n in names}
    packed = base64.b85encode(lzma.compress(json.dumps(payload, sort_keys=True).encode(), preset=9)).decode()
    pending = A.unresolved(protocol)
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {}, 'source':
                           f'# Track 3 stagnation supervision v1: runtime v2 review r{revision}\n'
                           'GPU disabled; the live gate refuses in this snapshot. Protocol v2 science unchanged: '
                           'ar25, wa30, ls20 (retained with its display-driven-novelty limitation) and s5i5; 40 '
                           'actions; continuation, periodic and triggered arms; no restart; frozen trigger. Runtime '
                           'bound to the verified GPU runtime: pinned CPython 3.12 image, version-1 publisher wheels '
                           'installed from the trusted hash-pinned lock, dataset-backed model snapshot (private '
                           'binding still a placeholder) and the competition game files and wheels. Two separately '
                           'authorized sessions; this cell selects session 1 and never launches session 2. The '
                           'consumed R6 attempt cannot be reused.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
                           'source': CELL.format(packed=packed, bindings=bindings)}]}
    owner_slug = protocol['kernel_ids']['1'].rsplit('-session-1', 1)[0]
    metadata = {'id': f'{owner_slug}-review-r{revision}', 'title': f'ARC3 SSV1 Runtime V2 Review R{revision}',
                'code_file': 'profile.ipynb', 'language': 'python', 'kernel_type': 'notebook', 'is_private': True,
                'enable_gpu': False, 'enable_tpu': False, 'enable_internet': False,
                'competition_sources': competition_sources(protocol), **input_sources(protocol, pending=bool(pending)),
                **image_metadata(protocol)}
    return notebook, metadata, bindings, pending, inventory


def build_review(output, root=ROOT, revision=1):
    notebook, metadata, bindings, pending, inventory = review_notebook(root, revision)
    artifacts = {'profile.ipynb': encode(notebook), 'kernel-metadata.json': encode(metadata)}
    if len(artifacts['profile.ipynb']) >= SIZE_GUARD:
        raise ValueError('notebook exceeds the upload size guard')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)  # review revisions are immutable
    for name, data in artifacts.items():
        (output / name).write_bytes(data)
    lock = {'status': 'review_snapshot_not_approved_not_compute_authority', 'scope': A.SCOPE, 'revision': f'r{revision}',
            'bindings': bindings, 'artifacts': {n: hashlib.sha256(d).hexdigest() for n, d in artifacts.items()},
            'unresolved_placeholders': pending, 'gpu_enabled': False, 'authorized_seconds': 0,
            'gpu_launch_authorized': False,
            'closure': {'method': 'research/stagnation_supervision_runtime_v2/closure.py', 'code_files': len(inventory['code']),
                        'data_files': len(inventory['data']), 'third_party': inventory['third_party'],
                        'excluded_reachable': inventory['excluded_reachable']}}
    (output / 'review-source-lock.json').write_bytes(encode(lock))
    return lock


def launch_artifacts(root=ROOT):
    """The launch package, built in memory; refuses unless every live condition holds for `root`."""
    protocol, execution = A.require_live(root)
    lock_name = A.review_lock(root)
    folder = (Path(root) / lock_name).parent
    lock = json.loads((Path(root) / lock_name).read_bytes())
    for name, digest in lock['artifacts'].items():
        if A.sha256(folder / name) != digest:
            raise ValueError('reviewed artifact drift: ' + name)
    names = (lock_name, A.SOURCE, A.COMPUTE, A.LAUNCH, A.EXECUTION, A.RESERVATION, A.CLAIM, *A.evidence_names(root))
    sidecars = {n: (Path(root) / n).read_bytes() for n in names}
    hashes = {n: hashlib.sha256(d).hexdigest() for n, d in sidecars.items()}
    injection = (f'    sidecars = {{n: base64.b64decode(v) for n, v in '
                 f'{ {n: base64.b64encode(d).decode() for n, d in sidecars.items()}!r}.items()}}\n'
                 f'    for name, data in sidecars.items():\n'
                 f'        if hashlib.sha256(data).hexdigest() != {hashes!r}[name]:\n'
                 f"            raise ValueError('authority sidecar drift: ' + name)\n"
                 f'        (source / name).parent.mkdir(parents=True, exist_ok=True)\n'
                 f'        (source / name).write_bytes(data)\n')
    notebook = json.loads((folder / 'profile.ipynb').read_bytes())
    code = notebook['cells'][1]['source']
    if code.count(MARKER) != 1 or code.count(SESSION_LINE) != 1:
        raise ValueError('review notebook marker')
    session = execution['session']
    code = code.replace(MARKER, injection + MARKER).replace(SESSION_LINE, f"SESSION = '{session}'\n")
    notebook['cells'][1]['source'] = code
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    if metadata.get('enable_gpu') is not False or metadata.get('is_private') is not True:
        raise ValueError('review metadata')
    if any(metadata.get(k) != v for k, v in image_metadata(protocol).items()):
        raise ValueError('review image pin differs from the protocol')
    sources = {**input_sources(protocol), 'competition_sources': competition_sources(protocol)}
    kernel = protocol['kernel_ids'][session]
    metadata.update(id=kernel, title=kernel.split('/')[1], enable_gpu=True, machine_shape=protocol['machine_shape'],
                    **sources)
    artifacts = {'profile.ipynb': encode(notebook), 'kernel-metadata.json': encode(metadata)}
    if len(artifacts['profile.ipynb']) >= SIZE_GUARD:
        raise ValueError('notebook exceeds the upload size guard')
    artifacts['launch-package-lock.json'] = encode({
        'attempt_id': execution['attempt_id'], 'session': session, 'review_lock_sha256': A.sha256(Path(root) / lock_name),
        'dataset': protocol['dataset'], 'model_source': protocol['model']['kaggle_source'], 'sidecars': hashes,
        'artifacts': {n: hashlib.sha256(d).hexdigest() for n, d in artifacts.items()}})
    return artifacts
