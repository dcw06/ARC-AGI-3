"""CPU-only mounted transport restoration. No dataset code is executed."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import shutil
import signal
import sys
import time

from .archive_transport import canonical, digest, restore

SCOPE = {'gpu': False, 'tpu': False, 'internet': False, 'access': 'account_holder_only',
         'session_timeout_seconds': 1200, 'worker_seconds': 1100,
         'cleanup_reserve_seconds': 120, 'attempts': 1, 'automatic_retries': 0,
         'package_installs': 0, 'model_loads': 0, 'model_forward_calls': 0,
         'game_actions': 0, 'scorecards': 0}


def authority_check(protocol, authority):
    if canonical(protocol.get('scope')) != canonical(SCOPE):
        raise ValueError('CPU transport scope differs')
    if type(authority) is not dict or authority.get('approved') is not True or not authority.get('owner_answer'):
        raise PermissionError('APPROVAL REQUIRED: no CPU run authorized')
    for name in ('review_lock_sha256', 'runtime_lock_sha256'):
        value = authority.get(name)
        if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('review/runtime authority binding missing')
    if (authority.get('protocol_sha256') != digest(canonical(protocol)) or
            canonical(authority.get('scope')) != canonical(SCOPE) or
            authority.get('claim_consumed') is not True or not authority.get('attempt_id')):
        raise ValueError('exact scope, protocol and single-use claim required')


class LifecycleDeadline(TimeoutError):
    """The final deadline must escape work/cleanup failure recording."""


@contextmanager
def alarm(deadline, work_deadline):
    started = time.monotonic()
    previous = signal.getitimer(signal.ITIMER_REAL)
    if previous[0] > 0:
        deadline = min(deadline, started + previous[0])
    work_deadline = min(work_deadline, deadline)
    phase = 'work'

    def final_phase():
        nonlocal phase
        phase = 'final'
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LifecycleDeadline('CPU transport final lifecycle deadline reached')
        signal.setitimer(signal.ITIMER_REAL, remaining)

    def expired(number, unused):
        if phase == 'final' or time.monotonic() >= deadline:
            raise LifecycleDeadline('CPU transport final lifecycle deadline reached')
        # The one-shot work timer is already gone. Arm the separate remaining
        # cleanup budget BEFORE raising the recoverable work/cancellation error.
        final_phase()
        raise TimeoutError('CPU transport work deadline or termination reached')

    handlers = {number: signal.signal(number, expired) for number in
                (signal.SIGALRM, signal.SIGTERM, signal.SIGHUP)}
    signal.setitimer(signal.ITIMER_REAL, max(.001, work_deadline - time.monotonic()))
    try:
        yield final_phase
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for number, handler in handlers.items():
            signal.signal(number, handler)
        if previous[0] or previous[1]:
            signal.setitimer(signal.ITIMER_REAL, max(.001, previous[0] - (time.monotonic() - started)), previous[1])


def write(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)


def run(protocol, authority, *, input_root='/kaggle/input',
        output='/kaggle/working/semantic-transport-cpu-check',
        now=time.monotonic, remove=shutil.rmtree, writer=write, use_alarm=True):
    authority_check(protocol, authority)  # before filesystem writes or mount reads
    if (protocol.get('schema') != 'semantic_transport_cpu_check_v1' or
            type(protocol.get('dataset_version')) is not int or protocol['dataset_version'] != 1 or
            type(protocol.get('dataset_ref')) is not str or
            not re.fullmatch('[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', protocol['dataset_ref'])):
        raise ValueError('explicit version-1 CPU transport protocol required')
    started = now()
    deadline = started + SCOPE['worker_seconds']
    work_deadline = deadline - SCOPE['cleanup_reserve_seconds']
    if use_alarm:
        real_deadline = time.monotonic() + SCOPE['worker_seconds']
        with alarm(real_deadline, real_deadline - SCOPE['cleanup_reserve_seconds']) as final_phase:
            return _run(protocol, authority, input_root, output, started, deadline, work_deadline,
                        now, remove, writer, final_phase)
    return _run(protocol, authority, input_root, output, started, deadline, work_deadline, now, remove, writer)


def _run(protocol, authority, input_root, output, started, deadline, work_deadline, now, remove, writer,
         final_phase=lambda: None):
    def check_work():
        if now() >= work_deadline:
            raise TimeoutError('CPU transport work deadline reached')
    def check_final():
        if now() >= deadline:
            raise LifecycleDeadline('CPU transport cleanup/finalization deadline reached')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / 'transport-restore-tmp'  # own the path before mkdir can be interrupted
    failure = None
    result = {'schema': 'semantic_transport_cpu_result_v1', 'status': 'not_complete',
        'protocol_sha256': digest(canonical(protocol)), 'review_lock_sha256': authority['review_lock_sha256'],
        'attempt_id': authority['attempt_id'], 'dataset_ref': protocol['dataset_ref'], 'dataset_version_requested': 1,
        'provider_attachment_version_verified': False, 'gpu_runtime_validated': False,
        'model_loads': 0, 'model_forward_calls': 0, 'package_installs': 0,
        'game_actions': 0, 'scorecards': 0, 'provider_COMPLETE_and_cell_marker_required': True,
        'host_python': sys.version.split()[0]}
    try:
        check_work()
        owner, slug = protocol['dataset_ref'].split('/')
        root = Path(input_root)
        mounts = [p for p in (root / slug, root / 'datasets' / owner / slug) if p.is_dir()]
        if len(mounts) != 1:
            raise ValueError('expected exactly one bound dataset mount')
        workspace.mkdir(exist_ok=False)
        result['restoration'] = restore(mounts[0], workspace / 'originals',
            protocol['transport_manifest_sha256'], protocol['original_manifest_sha256'], check_work)
        check_work()
        result['restoration']['actual_mount'] = str(mounts[0])
    except LifecycleDeadline:
        raise
    except BaseException as error:
        failure = error
        result.update(error_type=type(error).__name__, error=str(error)[:1000])
    # No finally block: expiration of the hard deadline must not start another
    # cleanup or evidence write. Ordinary work failure still enters this reserve.
    final_phase()
    check_final()
    try:
        if workspace.exists():
            if workspace.is_symlink() or workspace.resolve().parent != output.resolve():
                raise ValueError('temporary workspace escaped expected output')
            remove(workspace)
        result['temporary_workspace_removed'] = not workspace.exists()
        if not result['temporary_workspace_removed']:
            raise ValueError('temporary originals were not removed')
        check_final()
    except LifecycleDeadline:
        raise
    except BaseException as error:
        failure = failure or error
        result['cleanup_error'] = type(error).__name__ + ': ' + str(error)[:1000]
        result['temporary_workspace_removed'] = not workspace.exists()
    check_final()
    if failure is None:
        result['status'] = 'provisional_complete'
    else:
        result['status'] = 'failed'
    result['elapsed_before_receipt_write_seconds'] = now() - started
    raw = canonical(result)
    writer(output / 'result.json', raw)
    check_final()
    if failure is not None:
        raise RuntimeError('CPU transport check failed; preserve evidence') from failure
    witness = canonical({'result_sha256': digest(raw), 'elapsed_after_receipt_write_seconds': now() - started,
                         'provider_COMPLETE_and_cell_marker_required': True})
    writer(output / 'completion-witness.json', witness)
    check_final()
    print('SEMANTIC_TRANSPORT_CHECK_RETURNED ' + digest(witness), flush=True)
    check_final()
    return result
