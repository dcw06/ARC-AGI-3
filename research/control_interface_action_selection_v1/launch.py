# Derived by scripts/build_control_interface_action_selection_v1.py; edit the derivation.
"""Durable launch-side accounting: the claim and the receipt live in the repository, not in the provider session.

  claim    created exclusively (never overwritten) once every approval and the reservation are valid; immutable and
           embedded in the launch package, which the notebook gate requires
  receipt  created exclusively as `submitting` BEFORE the provider push, then replaced by exactly one of:
           `submitted`             the response names the authorized kernel, a valid version and no provider error
                                   or invalid source;
           `submission_rejected`   the provider explicitly reported an error or invalid sources;
           `submission_uncertain`  the push raised, or the confirmation is missing, malformed or ambiguous (for
                                   example another kernel reference or no version)

Any receipt, whatever its status, means the attempt is spent: the tooling refuses every further launch of it.
An uncertain submission is reconciled by hand against the provider's version history and is never relaunched; a
new attempt needs a new authorization and reservation."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from research.control_interface_action_selection_v1.binding import (CLAIM, EXECUTION, RECEIPT, LiveRefused, require_live,
                                                          reservation_digest, resolve, sha256)
from research.control_interface_action_selection_v1.notebook import launch_artifacts


class LaunchRefused(PermissionError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def _exclusive(root, name, value):
    path = resolve(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def _replace(root, name, value):
    path = resolve(root, name)
    temporary = path.with_name(path.name + '.writing')
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def spent(root):
    """Why the attempt can no longer be launched (None if it can)."""
    if resolve(root, RECEIPT).exists():
        status = json.loads(resolve(root, RECEIPT).read_text(encoding='utf-8')).get('status')
        return f'a launch receipt exists (status {status!r}); the attempt is spent'
    return None


def claim(root):
    """Create the immutable claim; refuses if one exists or the attempt is spent."""
    reason = spent(root)
    if reason:
        raise LaunchRefused(reason)
    protocol, execution = require_live(root, need_claim=False)
    try:
        _exclusive(root, CLAIM, {'status': 'claimed', 'attempt_id': execution['attempt_id'],
                                 'execution_sha256': sha256(resolve(root, EXECUTION)),
                                 'reservation_sha256': reservation_digest(root), 'claimed_at': now()})
    except FileExistsError as exc:
        raise LaunchRefused('a launch claim already exists; an attempt is claimed once') from exc
    return execution['attempt_id']


def write_package(root, folder):
    """Write the launch package (requires the claim: the gate checks it)."""
    reason = spent(root)
    if reason:
        raise LaunchRefused(reason)
    artifacts = launch_artifacts(root)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        (folder / name).write_bytes(data)
    return json.loads(artifacts['launch-package-lock.json'])


def submit(root, folder, backend):
    """Push the written package once. The receipt is created as `submitting` before the push, so an interrupted
    push leaves an uncertain, spent attempt rather than a reusable one."""
    reason = spent(root)
    if reason:
        raise LaunchRefused(reason)
    try:
        expected = launch_artifacts(root)
    except LiveRefused as exc:
        raise LaunchRefused(str(exc)) from exc
    folder = Path(folder)
    if {p.name for p in folder.iterdir()} != set(expected) or any(
            (folder / n).read_bytes() != d for n, d in expected.items()):
        raise LaunchRefused('the written launch package differs from the authorized package')
    package_lock = json.loads(expected['launch-package-lock.json'])
    record = {'attempt_id': package_lock['attempt_id'], 'package_lock_sha256': sha256(folder / 'launch-package-lock.json'),
              'started_at': now(), 'status': 'submitting'}
    try:
        _exclusive(root, RECEIPT, record)
    except FileExistsError as exc:
        raise LaunchRefused('a launch receipt exists; the attempt is spent') from exc
    try:
        outcome = backend.push(folder)
    except BaseException as exc:  # noqa: B036 - any failure leaves the submission uncertain, never retried
        _replace(root, RECEIPT, dict(record, status='submission_uncertain', finished_at=now(),
                                     error=f'{type(exc).__name__}: {str(exc)[:300]}',
                                     reconciliation='check the provider version history by hand; never relaunch'))
        raise
    status, findings = classify_response(outcome, expected_kernel(folder))
    final = dict(record, status=status, finished_at=now(), provider_response=_jsonable(outcome), findings=findings)
    if status != 'submitted':
        final['reconciliation'] = 'check the provider version history by hand; never relaunch'
    _replace(root, RECEIPT, final)
    return final


def expected_kernel(folder):
    return json.loads((Path(folder) / 'kernel-metadata.json').read_text(encoding='utf-8'))['id']


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)[:1000]


def normalised_ref(ref):
    """'/code/owner/slug', 'code/owner/slug', a kernel URL or 'owner/slug' -> 'owner/slug'."""
    if not isinstance(ref, str) or not ref.strip():
        return None
    ref = ref.strip().split('://', 1)[-1]
    parts = [p for p in ref.split('/') if p]
    if parts and '.' in parts[0]:  # a host name
        parts = parts[1:]
    if parts and parts[0] == 'code':
        parts = parts[1:]
    return '/'.join(parts[:2]) if len(parts) >= 2 else None


def classify_response(outcome, expected):
    """(status, findings) for a provider push response. Only an unambiguous confirmation of the authorized kernel
    is `submitted`; explicit provider errors or invalid sources are `submission_rejected`; everything else is
    `submission_uncertain`. No outcome permits an automatic retry."""
    if not isinstance(outcome, dict):
        return 'submission_uncertain', [f'no confirmation mapping (got {type(outcome).__name__})']
    rejected = []
    if outcome.get('error'):
        rejected.append(f"provider error: {str(outcome['error'])[:200]}")
    for key, value in sorted(outcome.items()):
        if key.lower().startswith('invalid') and value:
            rejected.append(f'{key}: {_jsonable(value)}')
    if rejected:
        return 'submission_rejected', rejected
    findings = []
    ref = normalised_ref(outcome.get('ref'))
    if ref is None:
        findings.append('no kernel reference in the response')
    elif ref != expected:
        findings.append(f'kernel reference {ref!r} is not the authorized {expected!r}')
    version = outcome.get('versionNumber')
    if type(version) is not int or version < 1:
        findings.append(f'no valid version number (got {version!r})')
    if findings:
        return 'submission_uncertain', findings
    return 'submitted', [f'confirmed {ref} version {version}']
