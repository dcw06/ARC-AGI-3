"""Runtime v2 launch-side accounting (hand-written successor of the verified runtime's launch.py).

  claim    created exclusively once every live condition except the claim holds; immutable; embedded in the package
  package  the reviewed notebook plus authority sidecars, written only when the full gate (with claim) passes
  receipt  created exclusively as `submitting` BEFORE the provider push, after fresh provider read receipts were
           validated, then replaced by exactly one of `submitted`, `submission_rejected` (any provider error or any
           nonempty invalid*Sources/invalid_*_sources field, including the R6 failure mode of HTTP 200 with
           invalidDatasetSources) or `submission_uncertain`. Any receipt spends the attempt; nothing retries.
The provider backend is injected by a separately authorized operator; this module contains none, loads no
credentials and makes no network call. In this checkout `claim`, `write_package` and `submit` all refuse at the gate.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from research.stagnation_supervision_runtime_v2 import authority as A
from research.stagnation_supervision_runtime_v2.notebook import launch_artifacts

REJECTED = ('invalidDatasetSources', 'invalidModelSources', 'invalidCompetitionSources', 'invalidKernelSources',
            'invalid_dataset_sources', 'invalid_model_sources', 'invalid_competition_sources', 'invalid_kernel_sources')


class LaunchRefused(PermissionError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def _exclusive(root, name, value):
    path = A.resolve(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def _replace(root, name, value):
    path = A.resolve(root, name)
    temporary = path.with_name(path.name + '.writing')
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def spent(root):
    if A.resolve(root, A.RECEIPT).exists():
        status = json.loads(A.resolve(root, A.RECEIPT).read_text(encoding='utf-8')).get('status')
        return f'a launch receipt exists (status {status!r}); the attempt is spent'
    return None


def claim(root):
    reason = spent(root)
    if reason:
        raise LaunchRefused(reason)
    try:
        _, execution = A.require_live(root, need_claim=False)
    except A.LiveRefused as exc:
        raise LaunchRefused(str(exc)) from exc
    try:
        _exclusive(root, A.CLAIM, {'status': 'claimed', 'attempt_id': execution['attempt_id'], 'scope': A.SCOPE,
                                   'execution_sha256': A.sha256(A.resolve(root, A.EXECUTION)),
                                   'reservation_sha256': A.sha256(A.resolve(root, A.RESERVATION)), 'claimed_at': now()})
    except FileExistsError as exc:
        raise LaunchRefused('a launch claim already exists; an attempt is claimed once') from exc
    return execution['attempt_id']


def write_package(root, folder):
    reason = spent(root)
    if reason:
        raise LaunchRefused(reason)
    try:
        artifacts = launch_artifacts(root)
    except A.LiveRefused as exc:
        raise LaunchRefused(str(exc)) from exc
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        (folder / name).write_bytes(data)
    return json.loads(artifacts['launch-package-lock.json'])


def submit(root, folder, backend, provider_records, *, clock=None):
    """Validate fresh provider receipts, write the `submitting` receipt, push once, classify, never retry."""
    from research.stagnation_supervision_runtime_v2.provider_preflight import validate
    reason = spent(root)
    if reason:
        raise LaunchRefused(reason)
    try:
        expected = launch_artifacts(root)
        protocol = A.load_protocol(root)
    except A.LiveRefused as exc:
        raise LaunchRefused(str(exc)) from exc
    folder = Path(folder)
    if {p.name for p in folder.iterdir()} != set(expected) or any((folder / n).read_bytes() != d for n, d in expected.items()):
        raise LaunchRefused('the written launch package differs from the authorized package')
    receipts = validate(folder, provider_records, protocol, root, clock)  # before any receipt or push
    package_lock = json.loads(expected['launch-package-lock.json'])
    record = {'attempt_id': package_lock['attempt_id'], 'session': package_lock['session'], 'scope': A.SCOPE,
              'package_lock_sha256': A.sha256(folder / 'launch-package-lock.json'), 'started_at': now(),
              'provider_preflight': receipts, 'status': 'submitting'}
    try:
        _exclusive(root, A.RECEIPT, record)
    except FileExistsError as exc:
        raise LaunchRefused('a launch receipt exists; the attempt is spent') from exc
    try:
        outcome = backend.push(folder)
    except BaseException as exc:  # noqa: B036 - any failure leaves the submission uncertain, never retried
        _replace(root, A.RECEIPT, dict(record, status='submission_uncertain', finished_at=now(),
                                       error=f'{type(exc).__name__}: {str(exc)[:300]}',
                                       reconciliation='check the provider version history by hand; never relaunch'))
        raise
    status, findings = classify_response(outcome, json.loads((folder / 'kernel-metadata.json').read_bytes())['id'])
    final = dict(record, status=status, finished_at=now(), provider_response=_jsonable(outcome), findings=findings)
    if status != 'submitted':
        final['reconciliation'] = 'check the provider version history by hand; never relaunch'
    _replace(root, A.RECEIPT, final)
    return final


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)[:1000]


def normalised_ref(ref):
    if not isinstance(ref, str) or not ref.strip():
        return None
    parts = [p for p in ref.strip().split('://', 1)[-1].split('/') if p]
    if parts and '.' in parts[0]:
        parts = parts[1:]
    if parts and parts[0] == 'code':
        parts = parts[1:]
    return '/'.join(parts[:2]) if len(parts) >= 2 else None


def classify_response(outcome, expected):
    """Only an unambiguous confirmation of the authorized kernel with no error and no invalid source is `submitted`."""
    if not isinstance(outcome, dict):
        return 'submission_uncertain', [f'no confirmation mapping (got {type(outcome).__name__})']
    rejected = []
    if outcome.get('error'):
        rejected.append(f"provider error: {str(outcome['error'])[:200]}")
    for key in sorted(outcome):
        value = outcome[key]
        if key in REJECTED or key.lower().startswith('invalid'):
            if value is not None and (not isinstance(value, list) or value):
                rejected.append(f'{key}: {_jsonable(value)}')
    if rejected:
        return 'submission_rejected', rejected
    findings = []
    ref = normalised_ref(outcome.get('ref') or outcome.get('url'))
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
