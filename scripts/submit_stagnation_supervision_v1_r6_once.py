"""One-use local submission boundary. Transport is supplied explicitly; no retry or implicit network."""
import json
import os
from pathlib import Path
import tempfile
from scripts import prepare_stagnation_supervision_v1_authorization_r6 as P

LEDGER = P.ROOT / 'reports/stagnation_supervision_v1_r5_session1_authority'


def durable_new(path, value):
    data = P.raw(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)


def submit_once(package, transport, *, ledger=LEDGER):
    """Validate, claim durably, invoke transport at most once; errors remain consumed/unknown.

    The caller must provide a reviewed single-request provider adapter. This module
    does not implement or authorize provider retries. No transport is called by review.
    """
    ledger, package = Path(ledger), Path(package)
    if ledger.is_symlink() or not ledger.is_dir():
        raise ValueError('canonical reservation ledger required')
    state = json.loads((ledger / 'compute-ledger.json').read_bytes())
    if state['consumed'] is not False or state['provider_submission_started'] is not False:
        raise PermissionError('reservation already attempted')
    expected_attempt = 'ssv1-r5-session1-reservation-001'
    if state['attempt_id'] != expected_attempt or state['authorized_seconds'] != 5400 or state['session'] != '1':
        raise PermissionError('wrong preserved reservation')
    # Authority paths are fixed, not chosen by a package manifest.
    from scripts.review_stagnation_supervision_v1_authorization_r6 import verify, extract
    _, _, payload, source = verify(P.OUT)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); extract(root / 'source', payload, source)
        gate = P.authority(root / 'source')
        names = {gate.SOURCE, gate.COMPUTE, gate.EXECUTION, gate.RESERVATION, gate.SUCCESSOR_SOURCE, gate.LAUNCH}
        sidecars = {n: (ledger / n).read_bytes() for n in names}
        rebuilt = root / 'verified-package'
        P.assemble_approved(P.OUT, sidecars, '1', rebuilt)
        if {p.name for p in package.iterdir()} != {p.name for p in rebuilt.iterdir()}:
            raise ValueError('submission package inventory')
        for p in rebuilt.iterdir():
            if (package / p.name).is_symlink() or (package / p.name).read_bytes() != p.read_bytes():
                raise ValueError('submission artifact drift')
        binding = json.loads((rebuilt / 'package-binding.json').read_bytes())
        if binding['attempt_id'] != expected_attempt:
            raise ValueError('attempt binding')
        claim = {'attempt_id': expected_attempt, 'status': 'submission_claimed_no_retry',
                 'source_review_sha256': binding['source_review_sha256'],
                 'package_binding_sha256': P.sha((rebuilt / 'package-binding.json').read_bytes()),
                 'launch_approval_sha256': P.sha(sidecars[gate.LAUNCH]),
                 'reservation_sha256': gate.RESERVED_HASHES[gate.RESERVATION]}
        # Exclusive claim is authoritative even if a crash prevents a result receipt.
        durable_new(ledger / 'submission-claim.json', claim)
        try:
            transport(rebuilt)
        except BaseException as exc:
            result = {**claim, 'status': 'submission_outcome_unknown_no_retry',
                      'exception_type': type(exc).__name__, 'consumed': True}
            durable_new(ledger / 'submission-result.json', result)
            raise
        result = {**claim, 'status': 'transport_returned_pending_provider_reconciliation', 'consumed': True}
        durable_new(ledger / 'submission-result.json', result)
        return result
