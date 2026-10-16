"""MolmoPoint sealing/request checks, adapted from the hardened notebook guards; never calls Kaggle.

The approval cell is the sole declared late-bound data slot. Every other notebook
byte and all metadata/runtime bytes remain fixed by the outer review lock.
"""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path

from research.object_identification_v1.mount_check import canonical
from .supervisor import readiness


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def normalized(book):
    book = copy.deepcopy(book)
    for cell in book['cells']:
        if isinstance(cell['source'], list):
            cell['source'] = ''.join(cell['source'])
    return book


def authority_from(book):
    book = normalized(book)
    cell = book['cells'][0]
    if cell['id'] != 'launch-authority' or cell['cell_type'] != 'code':
        raise ValueError('declared authority cell missing')
    tree = ast.parse(cell['source'])
    if (len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign)
            or len(tree.body[0].targets) != 1 or not isinstance(tree.body[0].targets[0], ast.Name)
            or tree.body[0].targets[0].id != 'AUTHORITY'):
        raise ValueError('authority cell must contain one literal assignment')
    value = ast.literal_eval(tree.body[0].value)
    if value is not None and type(value) is not dict:
        raise ValueError('authority must be a dictionary or None')
    if value is not None and len(canonical(value)) > 1_000_000:
        raise ValueError('authority data too large')
    return value


def verify_review(package):
    package = Path(package).resolve()
    raw = (package/'review-lock.json').read_bytes()
    lock = json.loads(raw)
    for name, expected in lock['artifacts'].items():
        path = package/name
        if path.is_symlink() or not path.resolve().is_relative_to(package) or digest(path.read_bytes()) != expected:
            raise ValueError('review artifact differs: '+name)
    return digest(raw)


def verify_authority(package, authority):
    package = Path(package)
    pin = verify_review(package)
    runtime_pin = digest((package/'runtime/runtime-lock.json').read_bytes())
    protocol = json.loads((package/'runtime/protocol.json').read_bytes())
    problems = readiness(protocol, authority or {})
    if not authority or authority.get('review_lock_sha256') != pin or authority.get('runtime_lock_sha256') != runtime_pin:
        problems.append('approval/claim not bound to reviewed notebook and runtime')
    if problems:
        raise ValueError('; '.join(problems))
    blobs = authority.get('evidence_blobs', {})
    for pin, relative in authority.get('retained_evidence', {}).items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or str(path).startswith(('/', '\\')) or '\\' in relative:
            raise ValueError('unsafe authority evidence path')
        raw = base64.b64decode(blobs[pin], validate=True)
        if digest(raw) != pin:
            raise ValueError('authority evidence hash differs')
    return True


def seal(package, authority):
    """Only usable AFTER a real source/compute approval and single-use claim."""
    package = Path(package)
    verify_authority(package, authority)
    book = json.loads((package/'profile.ipynb').read_bytes())
    if authority_from(book) is not None:
        raise ValueError('reviewed authority slot must be empty')
    book['cells'][0]['source'] = ['AUTHORITY = '+repr(authority)+'\n']
    return book


def verify_sealed(package, book, expected_authority):
    package = Path(package)
    actual = authority_from(book)
    if canonical(actual) != canonical(expected_authority):
        raise ValueError('actual launch authority differs')
    verify_authority(package, actual)
    expected = normalized(json.loads((package/'profile.ipynb').read_bytes()))
    candidate = normalized(book)
    candidate['cells'][0]['source'] = 'AUTHORITY = None\n'
    if canonical(candidate) != canonical(expected):
        raise ValueError('notebook changed outside the declared authority data slot')
    return True


def validate_save(body, package, authority):
    package = Path(package)
    spec = json.loads((package/'launch-spec.json').read_bytes())
    def field(name):
        camel = name.split('_')[0]+''.join(part.capitalize() for part in name.split('_')[1:])
        if camel != name and camel in body and name in body:
            raise ValueError('ambiguous save field')
        return body.get(camel, body.get(name))
    for key, expected in spec['save_fields'].items():
        if canonical(field(key)) != canonical(expected):
            raise ValueError('actual save field differs: '+key)
    mode = field('kernel_execution_type')
    if not ((type(mode) is int and mode == 1) or (type(mode) is str and mode in (
            'SAVE_AND_RUN_ALL', 'saveAndRunAll', 'SaveAndRunAll'))):
        raise ValueError('save-and-run execution type required')
    verify_sealed(package, json.loads(field('text')), authority)
    return True


def bootstrap(payload_raw):
    """Generate exact executable bootstrap, without loading code or weights here."""
    return '''if AUTHORITY is None:
    raise SystemExit("APPROVAL REQUIRED: this exact live package has not been authorized; no installation or GPU query started.")
import base64, hashlib, json, pathlib, sys
payload_raw = base64.b64decode(%r, validate=True)
assert hashlib.sha256(payload_raw).hexdigest() == %r
payload = json.loads(payload_raw)
base = pathlib.Path('/kaggle/working/molmopoint-targeted448-runtime')
if base.exists():
    raise FileExistsError('preserve earlier runtime/attempt')
base.mkdir(mode=0o700)
for name, encoded in payload.items():
    relative = pathlib.PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or chr(92) in name:
        raise ValueError('unsafe runtime path')
    target = base/name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(base64.b64decode(encoded, validate=True))
runtime_lock_raw = (base/'runtime-lock.json').read_bytes()
if hashlib.sha256(runtime_lock_raw).hexdigest() != AUTHORITY.get('runtime_lock_sha256'):
    raise ValueError('runtime differs from source approval')
for name, expected in json.loads(runtime_lock_raw)['artifacts'].items():
    target = base/name
    if not target.resolve().is_relative_to(base) or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError('extracted runtime bytes differ')
for pin, relative in AUTHORITY.get('retained_evidence', {}).items():
    path = pathlib.PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or chr(92) in relative:
        raise ValueError('unsafe authority path')
    raw = base64.b64decode(AUTHORITY['evidence_blobs'][pin], validate=True)
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError('authority evidence bytes differ')
    target = base/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
with (base/'live-authority.json').open('x') as stream:
    json.dump(AUTHORITY, stream, sort_keys=True)
sys.path.insert(0, str(base/'reviewed-source'))
from research.molmopoint_identification_v1.supervisor import run
run(base)
''' % (base64.b64encode(payload_raw).decode(), digest(payload_raw))
