"""Exact SDK request boundary for one authorized save; no implicit retries."""
from datetime import datetime, timezone
import ast
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

from research.initial_geometry_assistance_v1.geometry import canonical
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from .live_package import check_notebook, check_runtime, validate_target_binding
from .live_runtime import check_authority
from .source_closure import source_inventory, verify_source_inventory, safe_member
from research.initial_geometry_assistance_v1.game_wheels import GAME_WHEEL_SOURCE

MAX_SAVE_BODY_BYTES = 1_000_000  # Conservative local budget, not a provider-limit assertion.


def check_request_size(raw):
    if len(raw) > MAX_SAVE_BODY_BYTES:
        raise ValueError('SaveKernel request exceeds conservative local size budget')
    return len(raw)


def verify_review(review, source):
    review, source = Path(review), Path(source)
    lock = json.loads((review/'review-lock.json').read_bytes())
    pin = sha(review/'review-lock.json')
    validate_target_binding(lock, json.loads((review/'kernel-metadata.json').read_bytes()))
    for name, expected in lock['review_sources'].items():
        if sha(source/name) != expected:
            raise ValueError('reviewed source changed: '+name)
    verify_source_inventory(source, lock['review_sources'])
    for field, roots in (('review_sources', 'review_source_entrypoints'),
                         ('execution_sources', 'execution_source_entrypoints')):
        if source_inventory(source, lock[roots]) != lock[field]:
            raise ValueError('review/execution entrypoint closure differs')
    if hashlib.sha256(canonical(lock['execution_sources'])).hexdigest() != lock['source_inventory_sha256']:
        raise ValueError('execution source inventory digest differs')
    if sha(review/'kernel-metadata.json') != lock['review_metadata_sha256']:
        raise ValueError('metadata changed')
    if sha(review/'runtime.json') != lock['runtime_sha256']:
        raise ValueError('runtime changed')
    check_runtime(json.loads((review/'runtime.json').read_bytes()))
    for name, expected in lock['scope_evidence_sha256'].items():
        if sha(review/'scope-review'/name) != expected:
            raise ValueError('scoped-use evidence changed')
    notebook = json.loads((review/'review.ipynb').read_bytes())
    check_notebook(notebook, lock, pin, live=False)
    assignments = [node for node in ast.walk(ast.parse(notebook['cells'][2]['source']))
                   if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_raw' for t in node.targets)]
    if len(assignments) != 1:
        raise ValueError('embedded payload assignment differs')
    call = assignments[0].value
    if not isinstance(call, ast.Call) or len(call.args) != 1:
        raise ValueError('embedded payload expression differs')
    payload = base64.b64decode(ast.literal_eval(call.args[0]), validate=True)
    if len(payload) != lock['payload_bytes'] or hashlib.sha256(payload).hexdigest() != lock['payload_sha256']:
        raise ValueError('embedded payload differs from reviewed bytes')
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(lock['payload_files']) | {'payload-manifest.json'}:
            raise ValueError('embedded payload inventory differs')
        if json.loads(archive.read('payload-manifest.json')) != lock['payload_files']:
            raise ValueError('embedded payload manifest differs')
        for name, expected in lock['payload_files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('embedded payload member differs: '+name)
        if json.loads(archive.read('source-manifest.json')) != lock['execution_sources']:
            raise ValueError('embedded source manifest differs')
        if archive.read('runtime.json') != (review/'runtime.json').read_bytes():
            raise ValueError('embedded runtime differs')
        if any(name.startswith(('tests/', 'scripts/rehearse_')) or 'private-reference-keys' in name for name in names):
            raise ValueError('evaluation answers or scripted server in inference payload')
    return lock, pin


def preflight(review, source, provider, output):
    """Read-only provider checks, retained separately from any reservation/claim."""
    review, output = Path(review), Path(output)
    lock, pin = verify_review(review, source)
    runtime = json.loads((review/'runtime.json').read_bytes())
    checks, observations, error = {}, {}, None
    try:
        checks['account'] = provider.account() == 'daichongwei06'
        if not checks['account']:
            raise ValueError('authenticated account differs')
        observations['quota'] = provider.quota()
        quota = observations['quota']
        available = quota['total_time_allowed']-quota['time_used']-quota['time_reserved']
        checks['quota'] = math.isfinite(available) and available >= 3600
        if not checks['quota']:
            raise ValueError('GPU quota insufficient')
        checks['target_absent'] = lock['kernel_id'] not in provider.own_kernels('daichongwei06')
        if not checks['target_absent']:
            raise ValueError('target already exists; preserve every prior version')
        wheel_facts, wheels = provider.dataset(runtime['dataset']['ref'], 1)
        model_ref = runtime['model']['kaggle_source'].rsplit('/', 1)[0]
        model_facts, model = provider.dataset(model_ref, 1, private=True)
        observations.update(wheel_facts=wheel_facts, model_facts=model_facts, wheels=wheels, model=model)
        checks['dataset_versions'] = (wheel_facts['ref'] == runtime['dataset']['ref'] and wheel_facts['version'] == 1 and
                                     model_facts['ref'] == model_ref and model_facts['version'] == 1)
        checks['model_private_account_only'] = (model_facts.get('private') is True and model_facts.get('ready') is True and
                                                model_facts.get('collaborators') == 0)
        trusted = json.loads((Path(source)/'certification/direct_publisher_smoke_v1/trusted_manifest.json').read_bytes())
        expected_wheels = {row['filename']: row['size'] for row in trusted['artifacts']}
        prior_model = json.loads((review/'scope-review/model-dataset-inventory.json').read_bytes())
        expected_model = {row['path']: row['bytes'] for row in prior_model['files']}
        metadata_names = set(runtime['dataset']['publisher_metadata_sha256'])
        checks['inventories'] = (len(expected_wheels) == 174 and
                                {k: v for k, v in wheels.items() if k not in metadata_names} == expected_wheels and
                                set(wheels) == set(expected_wheels) | metadata_names and model == expected_model)
        if not all(checks.values()):
            raise ValueError('dataset identities, privacy or inventories differ')
        if runtime.get('game_wheel_source') != GAME_WHEEL_SOURCE:
            raise ValueError('mounted game wheel binding differs')
        listing = provider.competition_files(GAME_WHEEL_SOURCE['competition'])
        prefix = GAME_WHEEL_SOURCE['directory']+'/'
        expected_game = {prefix+name: info['bytes'] for name, info in lock['game_wheels'].items()}
        observed_game = {name: size for name, size in listing.items() if name.startswith(prefix)}
        checks['competition_game_wheels'] = len(expected_game) == 31 and observed_game == expected_game
        observations['competition_game_wheels'] = observed_game
        if not checks['competition_game_wheels']:
            raise ValueError('competition wheel filename/size inventory differs; bytes still require runtime verification')
        verify_review(review, source)
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
    record = {'schema': 'ls20_memory_evidence_readonly_preflight_v1', 'review_lock_sha256': pin,
              'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
              'observations': observations, 'provider_writes': 0, 'error': error,
              'actual_GPU_allocation_verified': False,
              'qualification': 'Quota and requested shape do not prove actual allocation. The notebook refuses any accelerator other than exactly one RTX PRO 6000.'}
    write_new(output, record)
    return record


def serialize(lock, notebook):
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest
    from kagglesdk.kernels.types.kernels_enums import KernelExecutionType
    request = ApiSaveKernelRequest()
    for key, value in lock['save_fields'].items():
        setattr(request, key, value)
    request.text = json.dumps(notebook)
    request.kernel_execution_type = KernelExecutionType.SAVE_AND_RUN_ALL
    import requests
    raw = requests.Request('POST', 'https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel',
                           json=ApiSaveKernelRequest.to_dict(request)).prepare().body
    check_request_size(raw)
    return request, json.loads(request.to_json())


def validate_send(body, lock, notebook, pin, *, live=True):
    validate_target_binding(lock)
    aliases = {key: key for key in [*lock['save_fields'], 'text', 'kernel_execution_type']}
    aliases.update({key.split('_')[0]+''.join(p.title() for p in key.split('_')[1:]): key for key in list(aliases)})
    normalized = {}
    for key, value in body.items():
        if key not in aliases or aliases[key] in normalized:
            raise ValueError('unexpected/ambiguous SDK field')
        normalized[aliases[key]] = value
    for key, expected in lock['save_fields'].items():
        value = normalized.get(key)
        if expected == [] and value is None:
            value = []
        if canonical(value) != canonical(expected):
            raise ValueError('serialized provider setting differs: '+key)
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest
    from kagglesdk.kernels.types.kernels_enums import KernelExecutionType
    check = ApiSaveKernelRequest()
    check.kernel_execution_type = KernelExecutionType.SAVE_AND_RUN_ALL
    encoded = json.loads(check.to_json())
    expected_mode = encoded.get('kernelExecutionType', encoded.get('kernel_execution_type'))
    if normalized.get('kernel_execution_type') != expected_mode:
        raise ValueError('not an explicit save-and-run request')
    if json.loads(normalized['text']) != notebook:
        raise ValueError('serialized source differs')
    check_notebook(notebook, lock, pin, live=live)


def validate_saved(snapshot, lock, pin, version):
    """Check provider-echoed source/settings, without inventing absent echoes."""
    from copy import deepcopy
    metadata = snapshot['metadata']
    expected = lock['save_fields']
    if (metadata.get('ref', '').strip('/').removeprefix('code/') != expected['slug'] or
            type(version) is not int or type(metadata.get('current_version_number')) is not int or
            metadata['current_version_number'] != version):
        raise ValueError('provider version/target differs')
    for name in ('is_private', 'enable_gpu', 'enable_tpu', 'enable_internet', 'machine_shape', 'docker_image'):
        if canonical(metadata.get(name)) != canonical(expected[name]):
            raise ValueError('provider saved setting differs: '+name)
    version_labels_echoed = True
    for name in ('dataset_data_sources', 'competition_data_sources', 'kernel_data_sources', 'model_data_sources'):
        actual, wanted = metadata.get(name) or [], expected[name]
        if actual != wanted:
            if name != 'dataset_data_sources' or sorted(actual) != sorted(ref.rsplit('/', 1)[0] for ref in wanted):
                raise ValueError('provider attachments differ: '+name)
            version_labels_echoed = False
    book = json.loads(snapshot['source']) if isinstance(snapshot['source'], str) else deepcopy(snapshot['source'])
    for cell in book['cells']:
        if isinstance(cell['source'], list):
            cell['source'] = ''.join(cell['source'])
        if cell['cell_type'] == 'code':
            cell['execution_count'], cell['outputs'] = None, []
    authority = check_notebook(book, lock, pin, live=True)
    timeout = metadata.get('session_timeout_seconds')
    if timeout is not None and (type(timeout) is not int or timeout != 3600):
        raise ValueError('provider timeout differs')
    return {'authority': authority, 'provider_dataset_version_labels_echoed': version_labels_echoed,
            'provider_timeout_echoed': timeout is not None, 'requested_session_timeout_seconds': 3600,
            'actual_GPU_allocation_verified': False}


class Boundary:
    """Use with the retained Backend's allowlisted, no-retry HTTP adapter.

    Approval files, reservation and a fresh read-only preflight are external
    inputs. They are not fabricated by package construction or a dry check.
    """
    def __init__(self, review, source, launch, preflight):
        self.review, self.source, self.launch = map(Path, (review, source, launch))
        self.lock, self.pin = verify_review(review, source)
        self.book = json.loads((self.launch/'launch.ipynb').read_bytes())
        self.authority = check_notebook(self.book, self.lock, self.pin, live=True)
        self.preflight = Path(preflight)
        self.http_events, self.sent = [], False

    def before_send(self, body, raw):
        _, pin = verify_review(self.review, self.source)
        if pin != self.pin or self.sent:
            raise ValueError('package drift or provider write already attempted')
        record = json.loads(self.preflight.read_bytes())
        age = (datetime.now(timezone.utc)-datetime.fromisoformat(record['checked_at_utc'])).total_seconds()
        required = ('account', 'target_absent', 'quota', 'dataset_versions', 'inventories', 'model_private_account_only',
                    'competition_game_wheels')
        if (record.get('review_lock_sha256') != pin or not 0 <= age < 300 or
                record.get('provider_writes') != 0 or not all(record.get('checks', {}).get(k) is True for k in required)):
            raise ValueError('fresh exact-scope preflight missing')
        receipt = json.loads((self.launch/'launch-receipt.json').read_bytes())
        if receipt['notebook_sha256'] != sha(self.launch/'launch.ipynb') or receipt['authority'] != self.authority:
            raise ValueError('consumed launch claim differs')
        registry = self.review.parent/'single-use-reservations'
        consumed = registry/(self.authority['reservation']+'.json')
        if json.loads(consumed.read_bytes()) != self.authority:
            raise ValueError('single-use reservation receipt differs')
        validate_send(body, self.lock, self.book, pin)
        check_request_size(raw)
        # Exclusive write BEFORE forwarding. A network failure consumes this send.
        write_new(registry/(self.authority['reservation']+'-sent.json'), {
            'review_lock_sha256': pin, 'notebook_sha256': sha(self.launch/'launch.ipynb'),
            'preflight_sha256': sha(self.preflight), 'request_sha256': __import__('hashlib').sha256(raw).hexdigest()})
        self.sent = True
