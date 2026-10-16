"""MolmoPoint operator guards, adapted from the hardened deployment lifecycle; never imported by the immutable GPU notebook."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid

from . import deployment as D
from research.object_identification_v1.mount_check import canonical


def require(condition, message):
    if not condition:
        raise ValueError(message)


def put(path, value):
    """Exclusive, durable records. A partial record is a refusal, never reusable."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def load(path):
    return json.loads(Path(path).read_bytes())


def stamp():
    return datetime.now(timezone.utc).isoformat()


def validate_request(body, package, authority):
    """Closed field set; only SDK omission of an expected empty source list is normalized."""
    spec = load(Path(package)/'launch-spec.json')['save_fields']
    expected = set(spec) | {'text', 'kernel_execution_type'}
    aliases = {name: name for name in expected}
    aliases.update({name.split('_')[0]+''.join(p.capitalize() for p in name.split('_')[1:]): name
                    for name in expected})
    require(type(body) is dict and not set(body)-set(aliases), 'unexpected save fields/target ID')
    normalized = {}
    for key, value in body.items():
        name = aliases[key]
        require(name not in normalized, 'ambiguous save field: '+name)
        normalized[name] = value
    for name in ('dataset_data_sources', 'competition_data_sources', 'kernel_data_sources', 'model_data_sources'):
        if spec.get(name) == [] and normalized.get(name) is None:
            normalized[name] = []
    return D.validate_save(normalized, package, authority)


def inventory_check(item, actual):
    expected = {row['name']: row['bytes'] for row in item['files']}
    require(len(expected) == len(item['files']), 'duplicate expected inventory name')
    missing, extra = sorted(set(expected)-set(actual)), sorted(set(actual)-set(expected))
    changed = [name for name, size in expected.items() if size is not None and actual.get(name) != size]
    unspecified = [name for name, size in expected.items() if size is None]
    require(not unspecified or (item['kind'] == 'wheelhouse' and set(unspecified) <= {
        'README.md', 'SHA256SUMS', 'requirements.lock'}), 'unexpected unspecified inventory size')
    for row in item['files']:
        require(bool(re.fullmatch('[a-f0-9]{64}', row['sha256'])), 'inventory hash missing')
    for name, size in actual.items():
        require(type(size) is int and size >= 0, 'invalid provider size: '+name)
    return {'missing': missing, 'extra': extra, 'size_mismatches': changed,
            'unspecified_sizes_bound_by_SHA256': {name: actual.get(name) for name in unspecified},
            'passed': not (missing or extra or changed)}


CHECKS = ('account', 'quota', 'target_absent', 'dataset_identity_versions', 'private_access', 'inventories')


def validate_preflight(raw, pin, reservation_id, target, *, expected_sha256=None, now=None):
    if expected_sha256 is not None:
        require(D.digest(raw) == expected_sha256, 'preflight bytes differ from consumed claim')
    record = json.loads(raw)
    require(record.get('schema') == 'molmopoint_preflight_v1' and record.get('status') == 'passed', 'preflight not passed')
    require(record.get('review_lock_sha256') == pin, 'preflight names different review lock')
    require(record.get('reservation_id') == reservation_id and record.get('target') == target, 'preflight identity differs')
    require(all(record.get('checks', {}).get(name) is True for name in CHECKS), 'preflight checks incomplete')
    require(record.get('provider_writes') == 0, 'preflight contains provider writes')
    checked = datetime.fromisoformat(record['checked_at_utc'])
    require(checked.tzinfo is not None, 'preflight timestamp has no timezone')
    age = ((now or datetime.now(timezone.utc))-checked).total_seconds()
    require(0 <= age < 300, 'preflight stale or from future')
    return record


class Records:
    """One stable consumption registry across every operation/preflight revision."""
    def __init__(self, control_root):
        self.root = Path(control_root).resolve()
        require(not Path(control_root).is_symlink(), 'control root is a symlink')
        self.registry = self.root/'gpu-reservation-registry-v2'
        self.registry.mkdir(exist_ok=True, parents=True)
        require(not self.registry.is_symlink(), 'reservation registry is a symlink')

    def slot(self, reservation_id):
        require(type(reservation_id) is str and bool(re.fullmatch('[A-Za-z0-9_-]{1,128}', reservation_id)), 'unsafe reservation ID')
        return self.registry/reservation_id

    def ensure_unspent(self, reservation):
        require(reservation.get('consumed') is False, 'reservation is consumed')
        rid = reservation['reservation_id']
        require(not self.slot(rid).exists(), 'reservation already consumed or ownership uncertain')
        # Legacy v1 receipts were per operation. Never forget them when moving to v2.
        for pattern in ('gpu-execution-attempt*/launch-claim.json', 'gpu-execution-attempt*/reservation-consumption.json'):
            for path in self.root.glob(pattern):
                record = load(path)
                if record.get('attempt_id', record.get('reservation_id')) == rid:
                    raise ValueError('reservation consumed in a retained legacy operation')

    def consume(self, reservation, claim):
        self.ensure_unspent(reservation)
        require(claim.get('attempt_id') == reservation['reservation_id'] and claim.get('consumed') is True,
                'claim does not consume this reservation')
        require(claim.get('review_lock_sha256') == reservation['review_lock_sha256'], 'claim lock differs')
        slot = self.slot(reservation['reservation_id'])
        slot.mkdir()  # Atomic, shared lock. Keep even if interruption prevents writing claim.json.
        put(slot/'claim.json', claim)

    def verify_claim(self, claim):
        slot = self.slot(claim['attempt_id'])
        require(not slot.is_symlink() and canonical(load(slot/'claim.json')) == canonical(claim), 'global claim differs')
        require(claim.get('consumed') is True, 'claim not consumed')

    def consume_send(self, claim, record):
        self.verify_claim(claim)
        put(self.slot(claim['attempt_id'])/'send.json', record)  # Exclusive before forwarding, even on timeout.

    def revision(self, kind):
        require(kind in ('preflights', 'executions'), 'unknown revision kind')
        path = self.root/'gpu-operations-v2'/kind/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8])
        path.mkdir(parents=True)
        return path


def validate_boundary(package, authority, preflight_raw, records, *, body=None):
    pin = D.verify_review(package)
    D.verify_authority(package, authority)
    claim = authority['launch_claim']
    target = load(Path(package)/'kernel-metadata.json')['id']
    validate_preflight(preflight_raw, pin, claim['attempt_id'], target, expected_sha256=claim['preflight_sha256'])
    records.verify_claim(claim)
    if body is not None:
        validate_request(body, package, authority)
    return True


def validate_saved(snapshot, book, package, authority, version):
    """Check only provider-echoed facts; never invent timeout/version-label echoes."""
    metadata = snapshot['metadata']
    expected = load(Path(package)/'launch-spec.json')['save_fields']
    require(metadata.get('ref', '').strip('/').removeprefix('code/') == expected['slug'], 'saved target differs')
    require(type(version) is int and type(metadata.get('current_version_number')) is int
            and version == metadata['current_version_number'], 'saved version differs')
    for name in ('is_private', 'enable_gpu', 'enable_tpu', 'enable_internet', 'machine_shape', 'docker_image'):
        require(canonical(metadata.get(name)) == canonical(expected[name]), 'saved setting differs: '+name)
    exact_labels = True
    for name in ('dataset_data_sources', 'competition_data_sources', 'kernel_data_sources', 'model_data_sources'):
        actual, wanted = metadata.get(name) or [], expected[name]
        if canonical(actual) != canonical(wanted):
            # API strips numeric dataset version labels. Names/owners still must match exactly.
            def identity(ref):
                parts = ref.split('/')
                return '/'.join(parts[:2]) if len(parts) == 3 and parts[-1].isdigit() else ref
            require(name == 'dataset_data_sources' and len(actual) == len(wanted)
                    and sorted(actual) == sorted(identity(ref) for ref in wanted), 'saved attachments differ: '+name)
            exact_labels = False
    saved = json.loads(snapshot['source'])
    def without_outputs(value):
        value = D.normalized(value)
        for cell in value['cells']:
            if cell['cell_type'] == 'code':
                cell['outputs'], cell['execution_count'] = [], None
        return value
    require(canonical(without_outputs(saved)) == canonical(without_outputs(book)), 'saved program/authority differs')
    D.verify_sealed(package, book, authority)
    timeout_echo = metadata.get('session_timeout_seconds')
    if timeout_echo is not None:
        require(type(timeout_echo) is int and timeout_echo == expected['session_timeout_seconds'], 'saved timeout differs')
    return {'saved_source_and_available_settings_verified': True, 'saved_version': version,
            'provider_dataset_version_labels_echoed': exact_labels,
            'provider_session_timeout_echoed': timeout_echo is not None,
            'requested_session_timeout_seconds': expected['session_timeout_seconds'],
            'actual_GPU_allocation_verified': False}
