"""Durable launch-side accounting: the claim and the receipt live in the repository, not in the provider session.

  claim    created exclusively (never overwritten) once every approval and the reservation are valid; immutable and
           embedded in the launch package, which the notebook gate requires
  receipt  created exclusively as `submitting` BEFORE the provider push, then replaced by `submitted` (with the
           provider's kernel ref and version) or `submission_uncertain` (the push raised or its outcome is unknown)

Any receipt, whatever its status, means the attempt is spent: the tooling refuses every further launch of it.
An uncertain submission is reconciled by hand against the provider's version history and is never relaunched; a
new attempt needs a new authorization and reservation."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from certification.wheelhouse_r2_smoke_v1.binding import (CLAIM, EXECUTION, RECEIPT, LiveRefused, require_live,
                                                          reservation_digest, resolve, sha256)
from certification.wheelhouse_r2_smoke_v1.notebook import launch_artifacts


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
    _replace(root, RECEIPT, dict(record, status='submitted', finished_at=now(), provider=outcome))
    return outcome
