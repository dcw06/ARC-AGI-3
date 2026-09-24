"""Separate approvals, one-use reservation, exact package, and one-shot upload."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.grounded_action_v1 import authority

PACKAGE = 'notebooks/phase4-grounded-action-v1-run-r6'
CLAIM = 'reports/perception_stage_b_r6_launch_claim.json'
RECEIPT = 'reports/perception_stage_b_r6_launch.json'
PRELAUNCH = 'reports/perception_stage_b_r6_prelaunch.json'
MARKER = '    # STAGE_B_AUTHORITY_SIDECARS: reviewed packaging inserts bound approvals here.\n'


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def path(root, name):
    return authority._path(root, name)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(root, name):
    return sha(path(root, name).read_bytes())


def write_once(root, name, value):
    target = path(root, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    return target


def replace_record(root, name, value):
    target = path(root, name)
    temporary = target.with_name(target.name + '.writing')
    with temporary.open('xb') as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(target)


def review_source(root):
    from scripts.review_grounded_action_v1_launch_notebook import review

    root = Path(root)
    folder = path(root, authority.REVIEW).parent
    if root.resolve() == ROOT.resolve():
        review(folder)
    lock = json.loads(path(root, authority.REVIEW).read_bytes())
    if (lock.get('status') != 'reviewed_launch_source' or
            lock.get('scope') != authority.SCOPE or
            not authority.REQUIRED_SOURCE <= set(lock.get('bindings', {})) or
            lock.get('gpu_launch_authorized') is not False):
        raise PermissionError('review source lock')
    for name, expected in lock['bindings'].items():
        if digest(root, name) != expected:
            raise PermissionError('review source drift: ' + name)
    for name, expected in lock['artifacts'].items():
        if digest(root, str(Path(authority.REVIEW).parent / name)) != expected:
            raise PermissionError('review notebook drift: ' + name)
    return lock


def approved(root):
    review_source(root)
    lock_hash = digest(root, authority.REVIEW)
    source = json.loads(path(root, authority.SOURCE).read_bytes())
    compute = json.loads(path(root, authority.COMPUTE).read_bytes())
    for value, kind in ((source, 'source'), (compute, 'compute')):
        if (value.get('status') != 'approved' or value.get('scope') != authority.SCOPE or
                value.get('approval_kind') != kind or
                value.get('review_lock_sha256') != lock_hash or
                not isinstance(value.get('user_response'), str) or
                not value['user_response'].strip()):
            raise PermissionError(kind + ' approval')
    if compute.get('source_approval_sha256') != digest(root, authority.SOURCE):
        raise PermissionError('compute/source approval binding')
    for name, expected in authority.LIMITS.items():
        if type(compute.get(name)) is not int or compute[name] != expected:
            raise PermissionError('compute limit: ' + name)
    return source, compute


def record_approval(root, kind, user_response, review_sha256):
    if kind not in ('source', 'compute') or not isinstance(user_response, str) or not user_response.strip():
        raise PermissionError('explicit approval response required')
    review_source(root)
    if review_sha256 != digest(root, authority.REVIEW):
        raise PermissionError('review lock approval mismatch')
    value = {'status': 'approved', 'scope': authority.SCOPE,
             'approval_kind': kind, 'user_response': user_response,
             'review_lock_sha256': review_sha256, 'approved_at': now()}
    if kind == 'compute':
        source = json.loads(path(root, authority.SOURCE).read_bytes())
        if (source.get('status') != 'approved' or
                source.get('review_lock_sha256') != review_sha256 or
                source.get('approval_kind') != 'source'):
            raise PermissionError('source approval required first')
        value.update(authority.LIMITS)
        value['source_approval_sha256'] = digest(root, authority.SOURCE)
    return write_once(root, authority.SOURCE if kind == 'source' else authority.COMPUTE, value)


def reserve(root):
    approved(root)
    if any(path(root, name).exists() for name in (authority.EXECUTION, authority.RESERVATION,
                                                  CLAIM, RECEIPT, PACKAGE)):
        raise PermissionError('Stage B attempt already reserved or consumed')
    execution = {'scope': authority.SCOPE, 'attempt_id': 'gab1-' + uuid.uuid4().hex,
                 'review_lock_sha256': digest(root, authority.REVIEW),
                 'source_approval_sha256': digest(root, authority.SOURCE),
                 'compute_authorization_sha256': digest(root, authority.COMPUTE)}
    write_once(root, authority.EXECUTION, execution)
    reservation = {'status': 'reserved', 'attempt_id': execution['attempt_id'],
                   'seconds': authority.LIMITS['authorized_seconds'],
                   'execution_sha256': digest(root, authority.EXECUTION),
                   'reserved_at': now(), 'events': ['reserve']}
    write_once(root, authority.RESERVATION, reservation)
    authority.require(root)
    return execution


def unconsumed(root):
    if any(path(root, name).exists() for name in (CLAIM, RECEIPT)):
        raise PermissionError('Stage B launch already claimed; no retry')
    execution = authority.require(root)
    reservation = json.loads(path(root, authority.RESERVATION).read_bytes())
    return execution, reservation


def materialize(root):
    execution, reservation = unconsumed(root)
    folder = path(root, authority.REVIEW).parent
    notebook = json.loads((folder / 'profile.ipynb').read_bytes())
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    code = notebook['cells'][1]['source']
    if code.count(MARKER) != 1 or metadata.get('enable_gpu') is not False or metadata.get('enable_internet') is not False:
        raise ValueError('review wrapper/settings drift')
    sidecars = {name: path(root, name).read_bytes() for name in
                (authority.REVIEW, authority.SOURCE, authority.COMPUTE,
                 authority.EXECUTION, authority.RESERVATION)}
    encoded = {name: base64.b64encode(raw).decode() for name, raw in sidecars.items()}
    hashes = {name: sha(raw) for name, raw in sidecars.items()}
    injection = (
        f'    authority_payload={encoded!r}\n'
        f'    authority_hashes={hashes!r}\n'
        '    for name,encoded in authority_payload.items():\n'
        '        raw=base64.b64decode(encoded,validate=True)\n'
        '        if hashlib.sha256(raw).hexdigest()!=authority_hashes[name]:\n'
        '            raise ValueError("authority sidecar hash: "+name)\n'
        '        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)\n'
    )
    notebook['cells'][1]['source'] = code.replace(MARKER, MARKER + injection)
    notebook['cells'][0]['source'] = (
        '# Stage B: one separately authorized private development attempt\n'
        'Two episodes, at most two actions each, 12 study calls and one canary. '
        'No automatic retry or scored submission.')
    metadata.update(id='daichongwei06/arc3-grounded-action-v1-r6',
                    title='arc3-grounded-action-v1-r6', enable_gpu=True,
                    machine_shape='NvidiaRtxPro6000')
    artifacts = {'profile.ipynb': encode(notebook), 'kernel-metadata.json': encode(metadata)}
    if len(artifacts['profile.ipynb']) >= 900000:
        raise ValueError('launch notebook size ceiling')
    lock = {'scope': authority.SCOPE, 'attempt_id': execution['attempt_id'],
            'review_lock_sha256': digest(root, authority.REVIEW),
            'sidecars': hashes,
            'artifacts': {name: sha(raw) for name, raw in artifacts.items()},
            'authorized_seconds': authority.LIMITS['authorized_seconds'],
            'automatic_retries': 0}
    artifacts['launch-package-lock.json'] = encode(lock)
    return artifacts


def package(root):
    artifacts = materialize(root)
    folder = path(root, PACKAGE)
    folder.mkdir(parents=True, exist_ok=False)
    for name, raw in artifacts.items():
        with (folder / name).open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    return verify(root)


def verify(root):
    artifacts = materialize(root)
    folder = path(root, PACKAGE)
    if folder.is_symlink() or {p.name for p in folder.iterdir()} != set(artifacts):
        raise PermissionError('launch package inventory')
    for name, raw in artifacts.items():
        candidate = folder / name
        if candidate.is_symlink() or candidate.read_bytes() != raw:
            raise PermissionError('launch package drift: ' + name)
    return json.loads(artifacts['launch-package-lock.json'])


def launch(root, backend):
    lock = verify(root)  # All local checks before provider authentication or quota query.
    quota = backend.quota()
    for name in ('total_time_allowed', 'time_used', 'time_reserved'):
        value = quota.get(name)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise PermissionError('invalid provider GPU quota')
    remaining = quota['total_time_allowed'] - quota['time_used'] - quota['time_reserved']
    if remaining < authority.LIMITS['authorized_seconds']:
        raise PermissionError('insufficient provider GPU quota')
    write_once(root, PRELAUNCH, {'recorded_at': now(), 'gpu_quota_seconds': quota,
                                 'attempt_id': lock['attempt_id']})
    lock = verify(root)
    claim = {'status': 'consumed_before_upload', 'attempt_id': lock['attempt_id'],
             'package_lock_sha256': digest(root, PACKAGE + '/launch-package-lock.json'),
             'recorded_at': now(), 'automatic_retry_authorized': False}
    write_once(root, CLAIM, claim)
    reservation = json.loads(path(root, authority.RESERVATION).read_bytes())
    reservation.update(status='consumed', events=['reserve', 'launch_request_started'])
    replace_record(root, authority.RESERVATION, reservation)
    receipt = {'attempt_id': lock['attempt_id'], 'attempt_consumed': True,
               'provider_timeout_requested_seconds': authority.LIMITS['authorized_seconds'],
               'exact_provider_billed_seconds': None, 'automatic_retry_authorized': False,
               'recorded_at': now()}
    try:
        response = backend.push(path(root, PACKAGE))
        receipt.update(status='provider_response_received', url=response.url,
                       provider_version=response.version_number, error=response.error)
        for name in ('invalid_dataset_sources', 'invalid_competition_sources',
                     'invalid_kernel_sources'):
            receipt[name] = getattr(response, name, None)
    except Exception as exc:
        receipt.update(status='launch_outcome_unknown_no_retry', error=type(exc).__name__)
    receipt['response_received_at'] = now()
    write_once(root, RECEIPT, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('record-source', 'record-compute', 'reserve',
                                               'package', 'verify', 'launch'))
    parser.add_argument('--user-response')
    parser.add_argument('--review-sha256')
    args = parser.parse_args()
    if args.operation.startswith('record-'):
        result = record_approval(ROOT, args.operation.removeprefix('record-'),
                                 args.user_response, args.review_sha256)
        print(result)
    elif args.operation == 'reserve':
        print(json.dumps(reserve(ROOT), sort_keys=True))
    elif args.operation == 'package':
        print(json.dumps(package(ROOT), sort_keys=True))
    elif args.operation == 'verify':
        print(json.dumps(verify(ROOT), sort_keys=True))
    else:
        verify(ROOT)
        from scripts.phase4_integrated_v2_launch import KaggleBackend
        receipt = launch(ROOT, KaggleBackend())
        print(json.dumps(receipt, sort_keys=True))
        if receipt.get('error'):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
