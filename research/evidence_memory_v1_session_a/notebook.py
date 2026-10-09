# Derived by scripts/build_evidence_memory_v1_sessions.py from research/control_interface_action_selection_v2/notebook.py at 5a21dd3 (origin/wheelhouse-replacement-audit); edit the derivation.
"""Notebook packaging. The review notebook embeds every package source (hash-bound) and runs with GPU disabled; it
stops at the live gate before installation or GPU use. The launch package is the same reviewed notebook with the
approval, execution-lock and reservation sidecars injected, and it can only be built when the live gate passes."""
import base64
import hashlib
import json
import lzma
from pathlib import Path
import re

from research.evidence_memory_v1_session_a.binding import (CLAIM, COMPUTE, EXECUTION, PACKAGE, PROTOCOL, RESERVATION,
                                                          ROOT, SOURCE, ACCOUNT, PERMISSION, BYTES, evidence_names, load_protocol, require_live, review_lock,
                                                          sha256, unresolved)

MODEL_SOURCE = 'qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1'
COMPETITION_SOURCE = 'arc-prize-2026-arc-agi-3'
KERNEL_ID = 'REPLACE_WITH_KAGGLE_OWNER/arc3-evidence-memory-v1-session-a'
SIZE_GUARD = 900000
MARKER = '    sys.path.insert(0, str(source))\n'
IMAGE = re.compile(r'gcr\.io/kaggle-(?:private-byod|gpu-images)/python@sha256:[a-f0-9]{64}')
CELL = '''import base64, hashlib, json, lzma, pathlib, shutil, sys, tempfile, time
started = time.monotonic()  # one clock: installation start through cleanup
source = pathlib.Path(tempfile.mkdtemp(prefix='evidence-memory-session-a-source-'))
working = pathlib.Path('/kaggle/working')
try:
    payload = json.loads(lzma.decompress(base64.b85decode({packed!r})))
    bindings = {bindings!r}
    if set(payload) != set(bindings):
        raise ValueError('embedded source inventory differs from its bindings')
    for name, value in payload.items():
        data = base64.b64decode(value)
        if hashlib.sha256(data).hexdigest() != bindings[name]:
            raise ValueError('embedded source drift: ' + name)
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    sys.path.insert(0, str(source))
    from research.evidence_memory_v1_session_a.binding import consume
    consume(source, working)  # the live gate: refuses here, before any installation, model or GPU use
    from research.evidence_memory_v1_session_a.run import live_main
    def remove_source():
        shutil.rmtree(source)
        if source.exists():
            raise RuntimeError('embedded source removal was not verified')
    result = live_main(source, working / 'evidence-memory-v1-session-a', started, pathlib.Path('/tmp'),
                       on_source_cleanup=remove_source)
    print(json.dumps({{k: result[k] for k in ('passed', 'failed_stage', 'error', 'evidence_class')}}))
    if not result['passed']:
        raise SystemExit('session lifecycle failed; evidence in /kaggle/working/evidence-memory-v1-session-a')
finally:
    if source.exists():
        shutil.rmtree(source)
'''


def source_names(root=ROOT):
    names = sorted(p.relative_to(root).as_posix() for p in (Path(root) / PACKAGE).glob('*.py'))
    names += sorted(p.relative_to(root).as_posix() for p in (Path(root) / 'certification/direct_publisher_smoke_v1').glob('*.py'))
    names += [PACKAGE + '/probes.json', PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json']
    from research.evidence_memory_v1.successor.plan import STUDY_SOURCES
    names += list(STUDY_SOURCES)
    names += ['certification/direct_publisher_smoke_v1/' + n for n in ('proposal.json', 'trusted_manifest.json', 'trusted_requirements.lock')]
    return names + [PROTOCOL, PACKAGE + '/proposal.json', PACKAGE + '/trusted_manifest.json', PACKAGE + '/trusted_requirements.lock']


def image_metadata(protocol):
    """Require an immutable Kaggle GPU image; never fall back to latest."""
    pin = protocol.get('kaggle_image')
    if not isinstance(pin, dict):
        raise ValueError('immutable Kaggle GPU image pin required')
    image = pin.get('docker_image')
    if (not isinstance(image, str) or not IMAGE.fullmatch(image)
            or pin.get('docker_image_pinning_type') != 'original'):
        raise ValueError('immutable Kaggle GPU image pin required')
    return {key: pin[key] for key in ('docker_image', 'docker_image_pinning_type')}


def input_sources(protocol, pending=False):
    """Pin datasets explicitly and attach a model through exactly one source kind."""
    dataset = protocol['dataset']
    ref = dataset['ref']
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', ref):
        raise ValueError('invalid wheel dataset reference')
    version = dataset['version']
    if type(version) is not int or version < 1:
        raise ValueError('dataset version must be a positive integer')
    datasets = [] if pending else [f'{ref}/{version}']
    model = protocol['model']
    source = model['kaggle_source']
    kind = model.get('source_kind', 'model')
    if kind == 'model':
        if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*', source):
            raise ValueError('version-pinned Kaggle Model reference required')
        return {'dataset_sources': datasets, 'model_sources': [source]}
    if kind != 'dataset':
        raise ValueError('unsupported model source kind')
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*', source):
        raise ValueError('version-pinned model dataset reference required')
    if source.rsplit('/', 1)[0] == ref:
        raise ValueError('model and wheel datasets must be distinct')
    return {'dataset_sources': datasets + [source], 'model_sources': []}


def competition_sources(protocol):
    """This ARC-AGI-3 smoke package must retain its reviewed competition binding."""
    if protocol.get('competition', {}).get('ref') != COMPETITION_SOURCE:
        raise ValueError('explicit ARC-AGI-3 competition binding required')
    return [COMPETITION_SOURCE]


def review_notebook(root=ROOT):
    protocol = load_protocol(root)
    image = image_metadata(protocol)
    names = source_names(root)
    bindings = {name: sha256(Path(root) / name) for name in names}
    payload = {name: base64.b64encode((Path(root) / name).read_bytes()).decode() for name in names}
    packed = base64.b85encode(lzma.compress(json.dumps(payload, sort_keys=True).encode(), preset=6)).decode()
    pending = unresolved(load_protocol(root))
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {}, 'source':
                           '# Track 2 evidence memory v1, Stage 1 session A (GPU-disabled package)\n'
                           'One attempt: offline install from the verified flat publisher mount with our trusted '
                           'hash-pinned requirements, pinned model startup, at most 194044 counted '
                           'model requests (startup, study metrics and cancellation probes included), cancellation, cleanup and '
                           'retained evidence. 2896 scheduled study calls; zero game actions; technical evaluation only per session. This notebook refuses to run unless the dataset/account and direct-use evidence, '
                           'binding, source approval, Record C compute authorization and an unconsumed reservation '
                           'are all present and match.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
                           'source': CELL.format(packed=packed, bindings=bindings)}]}
    metadata = {'id': KERNEL_ID + '-review', 'title': 'ARC3 Evidence Memory V1 Session A Review', 'code_file': 'profile.ipynb',
                'language': 'python', 'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': False,
                'enable_tpu': False, 'enable_internet': False,
                'competition_sources': competition_sources(protocol),
                **input_sources(protocol, pending=bool(pending)), **image}
    return notebook, metadata, bindings, pending


def encode(value):
    return (json.dumps(value, indent=1, sort_keys=True) + '\n').encode()


def build_review(output, root=ROOT):
    notebook, metadata, bindings, pending = review_notebook(root)
    artifacts = {'profile.ipynb': encode(notebook), 'kernel-metadata.json': encode(metadata)}
    if len(artifacts['profile.ipynb']) >= SIZE_GUARD:
        raise ValueError('notebook exceeds the upload size guard')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        (output / name).write_bytes(data)
    lock = {'status': 'review_snapshot_not_approved_not_compute_authority', 'scope': 'evidence-memory-v1-session-a',
            'bindings': bindings, 'artifacts': {n: hashlib.sha256(d).hexdigest() for n, d in artifacts.items()},
            'unresolved_placeholders': pending, 'gpu_enabled': False}
    (output / 'review-source-lock.json').write_bytes(encode(lock))
    return lock


def launch_artifacts(root=ROOT):
    """The launch package (built in memory). Refuses unless the live gate passes for `root`."""
    protocol, execution = require_live(root)
    lock_name = review_lock(root)
    folder = (Path(root) / lock_name).parent
    lock = json.loads((Path(root) / lock_name).read_bytes())
    for name, digest in lock['artifacts'].items():
        if sha256(folder / name) != digest:
            raise ValueError('reviewed artifact drift: ' + name)
    sidecars = {name: (Path(root) / name).read_bytes() for name in (lock_name, SOURCE, COMPUTE, EXECUTION,
                                                                    RESERVATION, CLAIM, *evidence_names(root))}
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
    if code.count(MARKER) != 1:
        raise ValueError('review notebook marker')
    notebook['cells'][1]['source'] = code.replace(MARKER, injection + MARKER)
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    if metadata.get('enable_gpu') is not False or metadata.get('is_private') is not True:
        raise ValueError('review metadata')
    if any(metadata.get(key) != value for key, value in image_metadata(protocol).items()):
        raise ValueError('review image pin differs from the protocol')
    sources = input_sources(protocol)
    sources['competition_sources'] = competition_sources(protocol)
    if any(metadata.get(key) != value for key, value in sources.items()):
        raise ValueError('review input bindings differ from the protocol')
    metadata.update(id=protocol['kernel_id'], title=protocol['kernel_id'].split('/')[1], enable_gpu=True,
                    machine_shape='NvidiaRtxPro6000', **sources)
    artifacts = {'profile.ipynb': encode(notebook), 'kernel-metadata.json': encode(metadata)}
    if len(artifacts['profile.ipynb']) >= SIZE_GUARD:
        raise ValueError('notebook exceeds the upload size guard')
    artifacts['launch-package-lock.json'] = encode({
        'attempt_id': execution['attempt_id'], 'review_lock_sha256': sha256(Path(root) / lock_name),
        'dataset': protocol['dataset'], 'sidecars': hashes,
        'artifacts': {n: hashlib.sha256(d).hexdigest() for n, d in artifacts.items()}})
    return artifacts
