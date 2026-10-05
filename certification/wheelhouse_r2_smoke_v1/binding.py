"""Protocol loading and the live-path gate: unresolved placeholders, reviewed sources, separate source approval,
Record C compute authorization and an unconsumed single-attempt reservation. Import is inert."""
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'certification/wheelhouse_r2_smoke_v1'
PROTOCOL = PACKAGE + '/protocol.json'
SCOPE = 'wheelhouse-r2-smoke-v1'
REVIEW_GLOB = 'notebooks/wheelhouse-r2-smoke-v1-review-r*/review-source-lock.json'
SOURCE = 'reports/wheelhouse_r2_smoke_v1_source_approval.json'
COMPUTE = 'reports/wheelhouse_r2_smoke_v1_compute_authorization.json'
EXECUTION = PACKAGE + '/execution_lock.json'
RESERVATION = PACKAGE + '/reservation.json'
COMPUTE_LIMITS = ('authorized_seconds', 'internal_seconds', 'cleanup_reserve_seconds', 'admission_cutoff_seconds',
                  'maximum_attempts', 'maximum_model_requests', 'automatic_retries')
ATTEMPT = re.compile(r'r2s-[a-zA-Z0-9-]{8,80}')


class LiveRefused(PermissionError):
    """The live path may not run; `reasons` lists every failed condition found."""

    def __init__(self, reasons):
        super().__init__('wheelhouse R2 smoke test live path refused: ' + '; '.join(reasons))
        self.reasons = list(reasons)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(root, name):
    if not isinstance(name, str) or not name or '\\' in name or name.startswith('/'):
        raise ValueError(f'unsafe reference {name!r}')
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError(f'reference escapes root: {name}')
    return path


def read_json(root, name):
    return json.loads(resolve(root, name).read_bytes())


def load_protocol(root=ROOT):
    protocol = read_json(root, PROTOCOL)
    if protocol.get('schema') != 'wheelhouse_r2_smoke_v1_protocol' or protocol.get('scope') != SCOPE:
        raise ValueError('not the wheelhouse R2 smoke v1 protocol')
    return protocol


def unresolved(protocol):
    """Dotted paths of every value still carrying the placeholder prefix."""
    prefix, found = protocol['placeholder_prefix'], []

    def walk(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                if key != 'placeholder_prefix':
                    walk(item, f'{path}.{key}' if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f'{path}[{index}]')
        elif isinstance(value, str) and value.startswith(prefix):
            found.append(path)
    walk(protocol, '')
    return found


def review_lock(root):
    locks = sorted(Path(root).glob(REVIEW_GLOB), key=lambda p: int(p.parent.name.rsplit('-r', 1)[1]))
    if not locks:
        raise ValueError('no review source lock')
    return locks[-1].relative_to(root).as_posix()


def check_sources(root, lock_name):
    lock = read_json(root, lock_name)
    required = {p.relative_to(root).as_posix() for p in (Path(root) / PACKAGE).glob('*.py')} | {PROTOCOL}
    missing = sorted(required - set(lock.get('bindings', {})))
    if missing:
        raise ValueError('reviewed sources incomplete: ' + ', '.join(missing))
    for name, digest in lock['bindings'].items():
        if sha256(resolve(root, name)) != digest:
            raise ValueError('source drift: ' + name)
    return lock


def check_approvals(root, lock_name, protocol):
    lock_sha = sha256(resolve(root, lock_name))
    source, compute = read_json(root, SOURCE), read_json(root, COMPUTE)
    for record, kind in ((source, 'source'), (compute, 'compute')):
        if (record.get('status') != 'approved' or record.get('approval_kind') != kind or record.get('scope') != SCOPE
                or record.get('review_lock_sha256') != lock_sha or not str(record.get('user_response', '')).strip()
                or not record.get('approved_at')):
            raise ValueError(f'{kind} approval missing or not bound to the reviewed lock')
    if compute.get('source_approval_sha256') != sha256(resolve(root, SOURCE)):
        raise ValueError('compute authorization not bound to the source approval')
    if compute.get('protocol_sha256') != sha256(resolve(root, PROTOCOL)):
        raise ValueError('compute authorization not bound to the protocol')
    for name in COMPUTE_LIMITS:
        if type(compute.get(name)) is not int or compute[name] != protocol['limits'][name]:
            raise ValueError('compute limit differs from the protocol: ' + name)
    for name in ('ref', 'version', 'sha256sums_sha256', 'bundle_manifest_sha256'):
        if compute.get('dataset', {}).get(name) != protocol['dataset'][name]:
            raise ValueError('compute authorization not bound to the dataset ' + name)
    return source, compute


def check_reservation(root, lock_name):
    execution, reservation = read_json(root, EXECUTION), read_json(root, RESERVATION)
    bindings = {'review_lock': lock_name, 'review_sha256': sha256(resolve(root, lock_name)),
                'source_approval_sha256': sha256(resolve(root, SOURCE)),
                'compute_approval_sha256': sha256(resolve(root, COMPUTE)), 'scope': SCOPE}
    if any(execution.get(k) != v for k, v in bindings.items()):
        raise ValueError('execution lock not bound to the approvals')
    if not isinstance(execution.get('attempt_id'), str) or not ATTEMPT.fullmatch(execution['attempt_id']):
        raise ValueError('attempt id')
    digest = hashlib.sha256(json.dumps(execution, sort_keys=True, indent=2).encode() + b'\n').hexdigest()
    if (reservation.get('status') != 'reserved' or reservation.get('attempt_id') != execution['attempt_id']
            or reservation.get('execution_sha256') != digest or reservation.get('events') != ['reserve']):
        raise ValueError('reservation missing, consumed or not bound to the execution lock')
    return execution


def require_live(root=None):
    """Every live-path condition, checked before any installation, model or GPU activity. Raises LiveRefused with
    all reasons found; returns (protocol, execution) when the attempt may run."""
    root = ROOT if root is None else Path(root)
    reasons = []
    try:
        protocol = load_protocol(root)
    except (OSError, ValueError, KeyError) as exc:
        raise LiveRefused([f'protocol unreadable: {exc}']) from exc
    pending = unresolved(protocol)
    if pending:
        reasons.append('unresolved placeholders: ' + ', '.join(pending))
    execution = None
    try:
        lock_name = review_lock(root)
        check_sources(root, lock_name)
        check_approvals(root, lock_name, protocol)
        execution = check_reservation(root, lock_name)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reasons.append(f'authorization: {type(exc).__name__}: {exc}')
    if reasons:
        raise LiveRefused(reasons)
    return protocol, execution


def consume(root, working):
    """Mark the reservation consumed in the provider working directory (exclusive create: never twice)."""
    protocol, execution = require_live(root)
    marker = Path(working) / f".{execution['attempt_id']}.consumed.json"
    with marker.open('x', encoding='utf-8') as stream:
        json.dump({'attempt_id': execution['attempt_id'], 'status': 'consumed'}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return protocol, execution, marker
