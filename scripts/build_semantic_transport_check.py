"""Build a sealed CPU-only transport-check proposal locally. Never uploads/runs."""
import argparse
import ast
import base64
import copy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.object_discovery_boundaries_v1.archive_transport import canonical, digest, manifest, inventory
from research.object_discovery_boundaries_v1.transport_check import SCOPE, authority_check

SOURCES = ('research/object_discovery_boundaries_v1/archive_transport.py',
           'research/object_discovery_boundaries_v1/transport_check.py')


def authority_from(book):
    cell = book['cells'][0]
    if cell['cell_type'] != 'code' or cell['id'] != 'launch-authority':
        raise ValueError('declared authority slot missing')
    source = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
    statements = ast.parse(source).body
    if (len(statements) != 1 or not isinstance(statements[0], ast.Assign) or
            len(statements[0].targets) != 1 or not isinstance(statements[0].targets[0], ast.Name) or
            statements[0].targets[0].id != 'AUTHORITY'):
        raise ValueError('authority must be one literal assignment')
    value = ast.literal_eval(statements[0].value)
    if value is not None and type(value) is not dict:
        raise ValueError('authority literal must be None or a dictionary')
    return value


def verify_review(package):
    package = Path(package).resolve()
    raw = (package / 'review-lock.json').read_bytes()
    lock = json.loads(raw)
    for name, pin in lock['artifacts'].items():
        path = package / name
        if path.is_symlink() or not path.resolve().is_relative_to(package) or digest(path.read_bytes()) != pin:
            raise ValueError('review artifact differs: ' + name)
    for name, pin in lock['source_sha256'].items():
        if digest((ROOT / name).read_bytes()) != pin:
            raise ValueError('reviewed checkout source differs: ' + name)
    return digest(raw)


def seal(package, authority):
    package = Path(package)
    pin = verify_review(package)
    protocol = json.loads((package / 'runtime/protocol.json').read_bytes())
    authority_check(protocol, authority)
    if (authority['review_lock_sha256'] != pin or
            authority['runtime_lock_sha256'] != digest((package / 'runtime/runtime-lock.json').read_bytes())):
        raise ValueError('authority does not name this exact package')
    book = json.loads((package / 'profile.ipynb').read_bytes())
    if authority_from(book) is not None:
        raise ValueError('reviewed slot is not empty')
    book['cells'][0]['source'] = ['AUTHORITY = ' + repr(authority) + '\n']
    return book


def verify_sealed(package, book, authority):
    expected = seal(package, authority)
    if canonical(expected) != canonical(book):
        raise ValueError('notebook differs outside the exact authority slot')
    return True


def validate_save(body, package, authority):
    """Validate the actual serialized provider request; never sends it."""
    def field(name):
        parts = name.split('_')
        camel = parts[0] + ''.join(part.title() for part in parts[1:])
        if camel != name and camel in body and name in body:
            raise ValueError('ambiguous save field')
        return body.get(camel, body.get(name))
    spec = json.loads((Path(package) / 'launch-spec.json').read_bytes())
    for name, expected in spec['save_fields'].items():
        if canonical(field(name)) != canonical(expected):
            raise ValueError('actual CPU save field differs: ' + name)
    execution = field('kernel_execution_type')
    if not ((type(execution) is int and execution == 1) or
            (type(execution) is str and execution in ('SAVE_AND_RUN_ALL', 'saveAndRunAll', 'SaveAndRunAll'))):
        raise ValueError('one save-and-run CPU attempt required')
    verify_sealed(package, json.loads(field('text')), authority)
    return True


def bootstrap(payload, payload_pin, runtime_pin):
    return '''if AUTHORITY is None:
    raise SystemExit('APPROVAL REQUIRED: CPU transport check not authorized; no mount read or extraction started.')
import base64, hashlib, json, pathlib, sys
payload_raw = base64.b64decode(%r, validate=True)
assert hashlib.sha256(payload_raw).hexdigest() == %r
payload = json.loads(payload_raw)
base = pathlib.Path('/kaggle/working/semantic-transport-check-runtime')
if base.exists():
    raise FileExistsError('preserve every earlier package and attempt')
if AUTHORITY.get('runtime_lock_sha256') != %r:
    raise ValueError('runtime authority differs')
base.mkdir(mode=0o700)
for name, encoded in payload.items():
    relative = pathlib.PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or chr(92) in name:
        raise ValueError('unsafe runtime path')
    target = base / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(base64.b64decode(encoded, validate=True))
lock_raw = (base / 'runtime-lock.json').read_bytes()
assert hashlib.sha256(lock_raw).hexdigest() == %r
for name, pin in json.loads(lock_raw)['artifacts'].items():
    target = base / name
    if target.is_symlink() or not target.resolve().is_relative_to(base) or hashlib.sha256(target.read_bytes()).hexdigest() != pin:
        raise ValueError('extracted runtime differs')
sys.path.insert(0, str(base / 'reviewed-source'))
from research.object_discovery_boundaries_v1.transport_check import run
run(json.loads((base / 'protocol.json').read_bytes()), AUTHORITY)
''' % (base64.b64encode(payload).decode(), payload_pin, runtime_pin, runtime_pin)


def build(protocol_path, transport_path, provider_path, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('preserve every earlier review packet')
    protocol_raw = Path(protocol_path).read_bytes()
    protocol = json.loads(protocol_raw)
    if protocol.get('schema') != 'semantic_transport_cpu_check_v1' or canonical(protocol['scope']) != canonical(SCOPE):
        raise ValueError('only the fixed CPU transport-check scope can be built')
    if type(protocol.get('dataset_version')) is not int or protocol['dataset_version'] != 1:
        raise ValueError('dataset version 1 required')
    if not re.fullmatch('[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', protocol['dataset_ref']):
        raise ValueError('invalid private dataset binding')
    if (not re.fullmatch('[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', protocol['notebook_ref']) or
            protocol['notebook_ref'].split('/')[0] != protocol['dataset_ref'].split('/')[0]):
        raise ValueError('account binding differs')
    if not re.fullmatch(r'gcr\.io/kaggle-private-byod/python@sha256:[0-9a-f]{64}', protocol['docker_image']):
        raise ValueError('immutable Kaggle image required')
    transport_raw = Path(transport_path).read_bytes()
    data = manifest(transport_raw, protocol['transport_manifest_sha256'], protocol['original_manifest_sha256'])
    expected = inventory(data, len(transport_raw))
    provider_raw = Path(provider_path).read_bytes()
    provider = json.loads(provider_raw)
    if (provider.get('verified') is not True or provider.get('ref') != protocol['dataset_ref'] or
            provider.get('private') is not True or provider.get('collaborators') != 0 or
            provider.get('version') != 1 or provider.get('manifest_sha256') != protocol['transport_manifest_sha256'] or
            provider.get('all_21_remote_file_hashes_match') is not True or
            provider.get('all_12_reconstructed_original_hashes_match') is not True):
        raise ValueError('exact private downloaded-byte evidence required')
    files = {row['name']: {'bytes': row['bytes'], 'sha256': row['sha256']}
             for row in provider['files'] if row.get('pass') is True}
    expected_files = {'transport-manifest.json': {'bytes': len(transport_raw), 'sha256': protocol['transport_manifest_sha256']},
        **{chunk['name']: {'bytes': chunk['stored_bytes'], 'sha256': chunk['sha256']}
           for row in data['originals'] for chunk in row['chunks']}}
    if files != expected_files or len(provider['files']) != len(expected):
        raise ValueError('provider file inventory differs')
    originals = {row['name']: {'bytes': row['bytes'], 'sha256': row['sha256']}
                 for row in provider['originals'] if row.get('pass') is True}
    if (originals != {row['name']: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in data['originals']} or
            len(provider['originals']) != len(data['originals'])):
        raise ValueError('reconstructed original evidence differs')
    runtime = {'protocol.json': canonical(protocol), 'transport-manifest.json': transport_raw}
    for name in SOURCES:
        runtime['reviewed-source/' + name] = (ROOT / name).read_bytes()
    for name in ('research/__init__.py', 'research/object_discovery_boundaries_v1/__init__.py'):
        path = ROOT / name
        runtime['reviewed-source/' + name] = path.read_bytes() if path.exists() else b''
    runtime['runtime-lock.json'] = canonical({'artifacts': {name: digest(raw) for name, raw in sorted(runtime.items())}})
    runtime_pin = digest(runtime['runtime-lock.json'])
    payload = canonical({name: base64.b64encode(raw).decode() for name, raw in sorted(runtime.items())})
    book = {'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
        'cells': [
            {'id': 'launch-authority', 'cell_type': 'code', 'metadata': {}, 'execution_count': None,
             'outputs': [], 'source': ['AUTHORITY = None\n']},
            {'id': 'scope', 'cell_type': 'markdown', 'metadata': {}, 'source': [
                '# Private CPU-only Semantic-SAM transport verification\n',
                'Restore and hash original files only; execute no dataset contents.\n',
                'No GPU/TPU/internet, package installs, model loading or inference.\n']},
            {'id': 'verify', 'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
             'source': bootstrap(payload, digest(payload), runtime_pin).splitlines(keepends=True)}]}
    metadata = {'id': protocol['notebook_ref'], 'title': 'ARC3 Semantic SAM CPU Transport Check V1',
        'code_file': 'profile.ipynb', 'language': 'python', 'kernel_type': 'notebook',
        'is_private': True, 'enable_gpu': False, 'enable_tpu': False, 'enable_internet': False,
        'dataset_sources': [protocol['dataset_ref'] + '/1'], 'model_sources': [],
        'kernel_sources': [], 'competition_sources': [], 'docker_image': protocol['docker_image'],
        'docker_image_pinning_type': 'original'}
    save_fields = {'slug': metadata['id'], 'new_title': metadata['title'], 'language': 'python',
        'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': False, 'enable_tpu': False,
        'enable_internet': False, 'machine_shape': None, 'session_timeout_seconds': 1200,
        'docker_image': metadata['docker_image'], 'docker_image_pinning_type': 'original',
        'dataset_data_sources': metadata['dataset_sources'], 'competition_data_sources': [],
        'kernel_data_sources': [], 'model_data_sources': []}
    guide = '''# CPU transport-check review — no launch performed

One proposed private, account-only saved CPU run. GPU, TPU and internet off.
Requested session timeout 1,200 seconds; worker 1,100 seconds, with a 120-second
cleanup reserve. One attempt, no automatic retries. Provider setup/release time
is not certified by the worker deadline. This is not GPU authorization.

Read the 21 version-1 mounted files, verify their independently pinned manifest,
and reconstruct the 12 original files into one temporary directory. Validate
every part and original hash, and cross-check the restored original manifest.
Then remove all reconstructed copies. No archives are extracted or executed;
no dependency install, pretrained-weight load, model import/forward, game action
or scorecard occurs. Approximate peak temporary storage: 10.577 GB.

CPU results are provisional. Independent collection must require provider
COMPLETE, exact saved notebook and immutable image, private/offline CPU settings,
the reviewed attachment, a result/witness hash pair and the matching final cell
marker. A missing marker, ERROR, interrupted write, late finalization or cleanup
failure is not a pass. Requested version labels are not evidence of the actual
attachment version; retain saved-run attachment evidence and mounted hashes.

Only the first AUTHORITY assignment may change after actual approval, with a
fresh single-use claim bound to this package. Missing authority refuses before
mount reads and filesystem extraction. No authority or claim is supplied here.

The original upload and all earlier attempts remain unchanged. The next GPU
smoke must bind this dataset, reviewed decoder, exact image and scoped use in
its own final package; this CPU result alone cannot qualify CUDA inference.
'''
    artifacts = {'runtime/' + name: raw for name, raw in runtime.items()}
    artifacts.update({'runtime-payload.json': payload, 'profile.ipynb': canonical(book),
        'kernel-metadata.json': canonical(metadata), 'scope.json': canonical(SCOPE),
        'launch-spec.json': canonical({'save_fields': save_fields, 'kernel_execution_type': 'SAVE_AND_RUN_ALL'}),
        'review.md': guide.encode(), 'evidence/provider-verification.json': provider_raw})
    source_names = (*SOURCES, 'scripts/build_semantic_transport_check.py')
    lock = {'schema': 'semantic_transport_cpu_review_v1',
        'artifacts': {name: digest(raw) for name, raw in sorted(artifacts.items())},
        'source_sha256': {name: digest((ROOT / name).read_bytes()) for name in source_names},
        'scope': SCOPE, 'runtime_lock_sha256': runtime_pin}
    output.mkdir(parents=True)
    for name, raw in artifacts.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (output / 'review-lock.json').write_bytes(canonical(lock))
    return {'review_lock_sha256': verify_review(output), 'runtime_lock_sha256': runtime_pin,
            'provider_writes': 0, 'gpu_jobs': 0, 'output': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'transport-manifest', 'provider-evidence', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.protocol, args.transport_manifest, args.provider_evidence, args.output), indent=2))
