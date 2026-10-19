"""Deterministic offline package sealing; the review notebook refuses all compute."""
import ast
import base64
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.geometry import canonical
from research.initial_geometry_assistance_v1.game_wheels import GAME_WHEEL_SOURCE
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from .live_runtime import SCOPE, check_authority, verify_inputs
from .source_closure import source_inventory, source_payload
from .live_contract import protocol

EMPTY_LOCK = '0'*64
# Conservative local packaging budget; not a claim about Kaggle's exact limit.
MAX_NOTEBOOK_BYTES = 900_000


def creation_title(kernel_id):
    """Use a creation title whose generated Kaggle slug matches the binding.

    A new notebook can take its slug from new_title even when SaveKernel also
    carries a slug. Restrict this path to a simple ASCII round-trip; post-save
    target verification remains mandatory and is never relaxed to an alias.
    """
    if type(kernel_id) is not str or not re.fullmatch(
            r'daichongwei06/[a-z0-9]+(?:-[a-z0-9]+)*', kernel_id):
        raise ValueError('notebook slug cannot round-trip through its creation title')
    return kernel_id.split('/', 1)[1].replace('-', ' ').title()


def validate_creation_binding(fields):
    if fields.get('new_title') != creation_title(fields.get('slug')):
        raise ValueError('new-notebook creation title generates a different bound slug')


def validate_target_binding(lock, metadata=None):
    fields = lock['save_fields']
    validate_creation_binding(fields)
    if lock.get('kernel_id') != fields['slug']:
        raise ValueError('review and save target identities differ')
    if metadata is not None and (metadata.get('id') != fields['slug'] or
                                 metadata.get('title') != fields['new_title']):
        raise ValueError('metadata and save target/title identities differ')


def check_runtime(runtime):
    """Keep the verified runtime fixed while binding this new private notebook.

    The public contract hashes deployment-independent settings; account/mount
    bindings are included verbatim in the private review lock, never inferred
    from an accelerator request or from public dataset availability.
    """
    contract = deepcopy(runtime)
    if (runtime.get('schema') != 'feedback_probe_private_runtime_v1' or
            not re.fullmatch(r'daichongwei06/[a-z0-9][a-z0-9-]+', runtime.get('kernel_id', '')) or
            not re.fullmatch(r'[0-9a-f]{64}', runtime.get('input_manifest_sha256', ''))):
        raise ValueError('private runtime notebook/input bindings differ')
    model = runtime.get('model', {})
    if (not re.fullmatch(r'daichongwei06/[a-z0-9][a-z0-9-]+/1', model.get('kaggle_source', '')) or
            model.get('mounted_path') != '/kaggle/input/datasets/'+model['kaggle_source'].rsplit('/', 1)[0]):
        raise ValueError('private version-one model attachment/mount differs')
    for name in ('schema', 'kernel_id', 'input_manifest_sha256'):
        contract.pop(name)
    for name in ('kaggle_source', 'mounted_path'):
        contract['model'].pop(name)
    if hashlib.sha256(canonical(contract)).hexdigest() != protocol()['runtime_contract_sha256']:
        raise ValueError('immutable image/model/dependency/installation contract changed')
    return runtime


def normalized(notebook):
    notebook = deepcopy(notebook)
    if (len(notebook['cells']) != 3 or notebook['cells'][0]['id'] != 'launch-authority' or
            any(c.get('outputs') or c.get('execution_count') is not None for c in notebook['cells'] if c['cell_type'] == 'code')):
        raise ValueError('unexpected notebook cells or retained output')
    source = notebook['cells'][0]['source']
    if type(source) is not str or not source.startswith('AUTHORITY = '):
        raise ValueError('authority slot contract')
    ast.literal_eval(source[len('AUTHORITY = '):].strip())
    notebook['cells'][0]['source'] = 'AUTHORITY = None\n'
    body = notebook['cells'][2]['source']
    prefix = 'REVIEW_LOCK_SHA256 = '
    first, rest = body.split('\n', 1)
    if not first.startswith(prefix) or len(ast.literal_eval(first[len(prefix):])) != 64:
        raise ValueError('review-lock slot contract')
    notebook['cells'][2]['source'] = prefix+repr(EMPTY_LOCK)+'\n'+rest
    return notebook


def check_notebook(notebook, lock, lock_sha, *, live):
    if hashlib.sha256(canonical(normalized(notebook))).hexdigest() != lock['notebook_template_sha256']:
        raise ValueError('notebook changed outside its authority data slot')
    first = notebook['cells'][2]['source'].split('\n', 1)[0]
    if ast.literal_eval(first.split(' = ', 1)[1]) != lock_sha:
        raise ValueError('notebook bound to another review lock')
    value = ast.literal_eval(notebook['cells'][0]['source'].split(' = ', 1)[1].strip())
    if live:
        check_authority(value, lock_sha)
    elif value is not None:
        raise ValueError('review notebook must remain GPU-refusing')
    return value


def build(root, inputs, input_pin, game, game_pin, runtime, output, *, scope_review):
    root, inputs, game, output = map(Path, (root, inputs, game, output))
    verify_inputs(inputs, input_pin)
    check_runtime(runtime)
    verify_game_environment(game, game_pin)
    manifest = json.loads((inputs/'manifest.json').read_bytes())
    if runtime['input_manifest_sha256'] != input_pin or runtime['game_receipt_sha256'] != game_pin:
        raise ValueError('runtime input/environment pins differ')
    if runtime.get('game_wheel_source') != GAME_WHEEL_SOURCE:
        raise ValueError('runtime must bind the frozen mounted competition wheels')
    execution_roots = [
        'research/feedback_probe_v1/live_runtime.py', 'research/feedback_probe_v1/live_worker.py',
        'research/initial_geometry_assistance_v1/engine_bridge.py', 'agent/framework_adapter.py',
        'research/feedback_probe_v1/protocol.json', 'research/feedback_probe_v1/live_protocol.json',
        'certification/direct_publisher_smoke_v1/proposal.json',
        'certification/direct_publisher_smoke_v1/trusted_manifest.json',
        'certification/direct_publisher_smoke_v1/trusted_requirements.lock']
    execution_sources = source_inventory(root, execution_roots)
    review_roots = execution_roots + [
        'research/feedback_probe_v1/live_package.py', 'research/feedback_probe_v1/live_operator.py',
        'research/feedback_probe_v1/live_evaluation.py',
        'research/feedback_probe_v1/protocol.json', 'research/feedback_probe_v1/live_protocol.json',
        'research/feedback_probe_v1/runtime_template.json',
        'scripts/build_feedback_probe_live_v1.py', 'scripts/rehearse_feedback_probe_live_v1.py']
    review_roots.extend(p.relative_to(root).as_posix() for p in (root/'tests').glob('test_feedback_probe_*v1.py'))
    sources = source_inventory(root, review_roots)
    files = source_payload(root, execution_sources)
    files['source-manifest.json'] = canonical(execution_sources)
    for name in [*manifest['files'], 'manifest.json']:
        files['inputs/'+name] = (inputs/name).read_bytes()
    game_receipt = json.loads((game/'receipt.json').read_bytes())
    for name in [*game_receipt['verified_members'], 'receipt.json', 'game_requirements.lock']:
        if not name.startswith('wheels/'):
            files['game/'+name] = (game/name).read_bytes()
    files['runtime.json'] = canonical(runtime)
    payload_members = {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())}
    files['payload-manifest.json'] = canonical(payload_members)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            archive.writestr(info, raw)
    payload = stream.getvalue()
    payload_pin = hashlib.sha256(payload).hexdigest()
    encoded = base64.b64encode(payload).decode('ascii')
    bootstrap = '''REVIEW_LOCK_SHA256 = LOCK_VALUE
import time
_started = time.monotonic()
if AUTHORITY is None:
    raise SystemExit('APPROVAL REQUIRED: no live authority; no installation, GPU use or game action')
import base64, hashlib, io, json, os, pathlib, shutil, signal, subprocess, sys, tempfile, zipfile
# Separate stdlib process bounds extraction/initial imports too. It never uses
# a GPU and is handed to the owned-process supervisor before model setup.
_old_handlers, _pending = {}, []
for _sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    _old_handlers[_sig] = signal.signal(_sig, lambda s, f: _pending.append((s, f)))
try:
    _guard = subprocess.Popen([sys.executable, '-c',
        'import os,signal,sys,time; time.sleep(max(0,float(sys.argv[2])-time.monotonic())); os.kill(int(sys.argv[1]),signal.SIGKILL)',
        str(os.getpid()), str(_started+3300)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, env={'PATH': os.defpath})
finally:
    for _sig, _handler in _old_handlers.items():
        signal.signal(_sig, _handler)
_source = None
try:
    if _pending:
        raise KeyboardInterrupt('interrupted during watchdog creation')
    _raw = base64.b64decode(PAYLOAD_VALUE, validate=True)
    if hashlib.sha256(_raw).hexdigest() != PAYLOAD_PIN:
        raise ValueError('embedded payload changed')
    _source = pathlib.Path(tempfile.mkdtemp(prefix='feedback-probe-source-'))
    with zipfile.ZipFile(io.BytesIO(_raw)) as _archive:
        _names = _archive.namelist()
        _pins = json.loads(_archive.read('payload-manifest.json'))
        if set(_names) != set(_pins) | {'payload-manifest.json'} or len(_names) != len(set(_names)):
            raise ValueError('payload inventory changed')
        for _name in _names:
            _p = pathlib.PurePosixPath(_name)
            if _p.is_absolute() or '..' in _p.parts:
                raise ValueError('unsafe payload member')
            _data = _archive.read(_name)
            if _name in _pins and hashlib.sha256(_data).hexdigest() != _pins[_name]:
                raise ValueError('payload member changed')
            _target = _source / _name
            _target.parent.mkdir(parents=True, exist_ok=True)
            with _target.open('xb') as _f:
                _f.write(_data)
    sys.path.insert(0, str(_source))
    from research.feedback_probe_v1.live_runtime import check_authority, run
    check_authority(AUTHORITY, REVIEW_LOCK_SHA256)
    run(_source, AUTHORITY, REVIEW_LOCK_SHA256, started=_started, bootstrap_guard=_guard)
finally:
    # The runtime normally consumes this guard and removes the source. Cover
    # import/setup failures as well; a failed cleanup cannot emit a success.
    if _guard.poll() is None:
        _guard.terminate()
        try:
            _guard.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _guard.kill()
            _guard.wait(timeout=2)
    if _source is not None and _source.exists():
        shutil.rmtree(_source)
    if time.monotonic() >= _started+3300:
        raise TimeoutError('bootstrap lifecycle exceeded final deadline')
'''.replace('LOCK_VALUE', repr(EMPTY_LOCK)).replace('PAYLOAD_VALUE', repr(encoded)).replace('PAYLOAD_PIN', repr(payload_pin))
    notebook = {'nbformat': 4, 'nbformat_minor': 5,
                'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
                'cells': [{'cell_type': 'code', 'id': 'launch-authority', 'metadata': {}, 'source': 'AUTHORITY = None\n',
                           'outputs': [], 'execution_count': None},
                          {'cell_type': 'markdown', 'id': 'scope', 'metadata': {},
                           'source': 'Private paired feedback-probe gameplay study. Review only: refuses before setup without fresh lock-bound authority.'},
                          {'cell_type': 'code', 'id': 'bounded-runner', 'metadata': {}, 'source': bootstrap,
                           'outputs': [], 'execution_count': None}]}
    metadata = {'id': runtime['kernel_id'], 'title': creation_title(runtime['kernel_id']), 'code_file': 'review.ipynb',
                'language': 'python', 'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': False,
                'enable_tpu': False, 'enable_internet': False, 'machine_shape': 'NvidiaRtxPro6000',
                'docker_image': runtime['kaggle_image']['docker_image'], 'docker_image_pinning_type': 'original',
                'dataset_sources': [runtime['dataset']['ref']+'/'+str(runtime['dataset']['version']), runtime['model']['kaggle_source']],
                'competition_sources': ['arc-prize-2026-arc-agi-3'], 'model_sources': []}
    lock = {'schema': 'feedback_probe_live_review_lock_v1', 'scope': SCOPE, 'kernel_id': runtime['kernel_id'],
            'input_manifest_sha256': input_pin, 'game_receipt_sha256': game_pin,
            'game_wheels': {name.split('/', 1)[1]: info for name, info in game_receipt['verified_members'].items()
                            if name.startswith('wheels/')},
            'runtime_sha256': hashlib.sha256(canonical(runtime)).hexdigest(), 'payload_sha256': payload_pin,
            'payload_bytes': len(payload), 'payload_files': payload_members,
            'notebook_template_sha256': hashlib.sha256(canonical(normalized(notebook))).hexdigest(),
            'review_metadata_sha256': hashlib.sha256(canonical(metadata)).hexdigest(),
            'review_sources': sources, 'review_source_entrypoints': sorted(review_roots),
            'execution_sources': execution_sources, 'execution_source_entrypoints': sorted(execution_roots),
            'source_inventory_sha256': hashlib.sha256(canonical(execution_sources)).hexdigest(),
            'session_timeout_seconds': 3600,
            'provider_overhead_may_extend_total_beyond_one_hour': True}
    save_fields = {'slug': metadata['id'], 'new_title': metadata['title'], 'language': 'python',
                   'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': True, 'enable_tpu': False,
                   'enable_internet': False, 'machine_shape': 'NvidiaRtxPro6000',
                   'docker_image': metadata['docker_image'], 'docker_image_pinning_type': 'original',
                   'dataset_data_sources': metadata['dataset_sources'], 'competition_data_sources': metadata['competition_sources'],
                   'kernel_data_sources': [], 'model_data_sources': [], 'session_timeout_seconds': 3600}
    validate_creation_binding(save_fields)
    lock['save_fields'] = save_fields
    validate_target_binding(lock, metadata)
    scope_review = Path(scope_review)
    scope_files = {p.relative_to(scope_review).as_posix(): p.read_bytes() for p in scope_review.rglob('*') if p.is_file()}
    if not scope_files or any(p.is_symlink() for p in scope_review.rglob('*')):
        raise ValueError('private scoped-use review evidence missing/unsafe')
    lock['scope_evidence_sha256'] = {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(scope_files.items())}
    lock_pin = hashlib.sha256(canonical(lock)).hexdigest()
    notebook['cells'][2]['source'] = notebook['cells'][2]['source'].replace(repr(EMPTY_LOCK), repr(lock_pin), 1)
    check_notebook(notebook, lock, lock_pin, live=False)
    if len(canonical(notebook)) > MAX_NOTEBOOK_BYTES:
        raise ValueError('notebook exceeds conservative local source-size budget')
    output.mkdir(exist_ok=False)
    write_new(output/'review-lock.json', lock)
    write_new(output/'review.ipynb', notebook)
    write_new(output/'kernel-metadata.json', metadata)
    write_new(output/'runtime.json', runtime)
    for name, raw in scope_files.items():
        target = output/'scope-review'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
    return {'review_lock_sha256': lock_pin, 'notebook_sha256': sha(output/'review.ipynb'),
            'payload_bytes': len(payload), 'payload_files': len(payload_members), 'GPU_launched': False}


def launch_build(review, authority, output):
    """One local launch claim, consumed before a provider write; never retries."""
    review, output = Path(review), Path(output)
    from .live_operator import verify_review
    lock, lock_sha = verify_review(review, Path(__file__).resolve().parents[2])
    check_authority(authority, lock_sha)
    notebook = json.loads((review/'review.ipynb').read_bytes())
    check_notebook(notebook, lock, lock_sha, live=False)
    metadata = json.loads((review/'kernel-metadata.json').read_bytes())
    if sha(review/'kernel-metadata.json') != lock['review_metadata_sha256']:
        raise ValueError('launch settings changed since review')
    # Exclusive claim: failures consume it; an operator cannot rebuild to retry.
    registry = review.parent/'single-use-reservations'
    registry.mkdir(exist_ok=True)
    write_new(registry/(authority['reservation']+'.json'), authority)
    notebook['cells'][0]['source'] = 'AUTHORITY = '+repr(authority)+'\n'
    check_notebook(notebook, lock, lock_sha, live=True)
    metadata.update(enable_gpu=True, code_file='launch.ipynb')
    output.mkdir(exist_ok=False)
    write_new(output/'launch.ipynb', notebook)
    write_new(output/'kernel-metadata.json', metadata)
    write_new(output/'launch-receipt.json', {'review_lock_sha256': lock_sha, 'authority': authority,
                                           'notebook_sha256': sha(output/'launch.ipynb'),
                                           'metadata_sha256': sha(output/'kernel-metadata.json'),
                                           'requested_session_timeout_seconds': 3600, 'provider_writes': 0})
    return output
