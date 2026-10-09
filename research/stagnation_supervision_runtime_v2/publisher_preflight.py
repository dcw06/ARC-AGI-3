# Derived from certification/direct_publisher_smoke_v1/preflight.py at 5a21dd3 by scripts/derive_stagnation_supervision_runtime_v2.py; edit the derivation, not this file.
"""Verify mounted bytes without installing packages, importing them or using a GPU.

This checks integrity only. It cannot establish account attachment, licence
permission, runtime compatibility or compute authorization.
"""
import hashlib
import json
from pathlib import Path
import re
import time

PACKAGE = Path(__file__).resolve().parent
PIN = re.compile(r'([A-Za-z0-9_.-]+)==([^\s]+)(?: --hash=sha256:([a-f0-9]{64}))?')


class PreflightFailed(ValueError):
    pass


def normalize(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def pins(text, require_hashes):
    rows = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = PIN.fullmatch(line)
        if not match or (require_hashes and not match[3]):
            raise PreflightFailed('requirements line is not an exact permitted pin')
        name, version, digest = match.groups()
        name = normalize(name)
        if name in rows:
            raise PreflightFailed('duplicate requirement: ' + name)
        rows[name] = (version, digest)
    return rows


def digest_file(path, check):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            check()
            chunk = stream.read(8 * 1024 * 1024)
            check()
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_inputs(package=PACKAGE):
    package = Path(package)
    proposal = json.loads((package / 'proposal.json').read_bytes())
    manifest = json.loads((package / 'trusted_manifest.json').read_bytes())
    lock = (package / 'trusted_requirements.lock').read_bytes()
    canonical = json.dumps(manifest['artifacts'], sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(canonical).hexdigest() != proposal['trusted_artifacts_sha256']:
        raise PreflightFailed('trusted artifact inventory differs from its binding')
    if hashlib.sha256(lock).hexdigest() != proposal['trusted_requirements_sha256']:
        raise PreflightFailed('trusted hash-pinned requirements differ from their binding')
    rows = manifest['artifacts']
    names = [row['filename'] for row in rows]
    if len(rows) != proposal['wheel_count'] or len(set(names)) != len(rows):
        raise PreflightFailed('wrong trusted wheel count or duplicate filename')
    for name in names:
        if not name.endswith('.whl') or Path(name).name != name or '/' in name or '\\' in name:
            raise PreflightFailed('unsafe trusted filename')
    lock_pins = pins(lock.decode('utf-8'), require_hashes=True)
    expected_pins = {}
    for row in rows:
        name, version = row['filename'].split('-')[:2]
        name = normalize(name)
        if name in expected_pins:
            raise PreflightFailed('multiple trusted wheels for one distribution')
        expected_pins[name] = (version, row['sha256'])
    if lock_pins != expected_pins:
        raise PreflightFailed('trusted lock and wheel inventory disagree')
    return proposal, rows, lock_pins


def verify_mounted(dataset_root, *, package=PACKAGE, now=time.monotonic):
    started = now()
    proposal, artifacts, trusted_pins = load_inputs(package)
    deadline = started + proposal['integrity_budget_seconds']

    def check():
        current = now()
        if current >= deadline:
            raise PreflightFailed('integrity deadline exceeded')
        return current

    root = Path(dataset_root)
    if not root.is_dir():
        raise PreflightFailed('dataset root is not mounted')
    expected = {row['filename'] for row in artifacts} | set(proposal['publisher_metadata_sha256'])
    present = set()
    for path in root.rglob('*'):
        check()
        if path.is_symlink():
            raise PreflightFailed('symlink in dataset inventory')
        if path.is_file():
            present.add(path.relative_to(root).as_posix())
    if present != expected:
        raise PreflightFailed('dataset file inventory differs: missing=%s extra=%s' %
                              (sorted(expected - present)[:5], sorted(present - expected)[:5]))
    for name, digest in proposal['publisher_metadata_sha256'].items():
        if digest_file(root / name, check) != digest:
            raise PreflightFailed('publisher metadata differs: ' + name)
    publisher_pins = pins((root / 'requirements.lock').read_text(encoding='utf-8'), require_hashes=False)
    if {n: v for n, (v, _) in publisher_pins.items()} != {n: v for n, (v, _) in trusted_pins.items()}:
        raise PreflightFailed('publisher package/version pins differ')
    for row in artifacts:
        check()
        path = root / row['filename']
        if path.stat().st_size != row['size']:
            raise PreflightFailed('wheel size differs: ' + row['filename'])
        if digest_file(path, check) != row['sha256']:
            raise PreflightFailed('wheel byte hash differs: ' + row['filename'])
    finished = check()  # explicit check after all reads; an overrun never passes
    return {'integrity_passed': True, 'wheel_bytes_verified': len(artifacts),
            'trusted_artifacts_sha256': proposal['trusted_artifacts_sha256'],
            'installation_requirements_sha256': proposal['trusted_requirements_sha256'],
            'dataset_ref': proposal['dataset']['ref'], 'requested_version': proposal['dataset']['version'],
            'account_attachment_verified': False, 'provider_attachment_version_verified': False,
            'permissions_assessed': False, 'gpu_compatibility_established': False,
            'launch_authorized': False, 'elapsed_seconds': round(finished - started, 3)}
