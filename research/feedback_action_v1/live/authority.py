"""Authority interface of the derived launch harness (hand-written adapter; import is inert).

The harness derived from action-effect history v1 calls `require`, `consume_runtime`, `verify_runtime_claim` and
`rehearsal_gate`. The live decision itself is the successor gate `binding.require_live`, derived from the verified
runtime's gate: unresolved placeholders, reviewed sources, separate source approval and compute authorization,
account/permission/byte evidence, an unconsumed single-attempt reservation for one session, and the launch claim.
Nothing here creates an approval, authorization, reservation or claim. Every caller runs inside the runtime payload,
which never carries the review documents; the repository-side gates verified them when the launch package was
built, so these calls skip them (`review_documents=False`).
"""
import json
import os
from pathlib import Path


def require(root=None):
    """The live gate; returns the execution lock (attempt id and session) or raises PermissionError."""
    from .binding import require_live
    _protocol, execution = require_live(root, review_documents=False)  # inside the runtime payload
    return execution


def consume_runtime(working, root=None):
    """Mark the attempt consumed in this provider session (exclusive create) before installation; never retried."""
    from .binding import ROOT, consume
    _protocol, _execution, marker = consume(ROOT if root is None else Path(root), working)
    return marker


def verify_runtime_claim(working, root=None):
    """The supervisor's check that the first cell consumed exactly this attempt."""
    execution = require(root)
    marker = Path(working) / f".{execution['attempt_id']}.consumed.json"
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 4096:
        raise PermissionError('runtime claim missing')
    record = json.loads(marker.read_bytes())
    if record.get('attempt_id') != execution['attempt_id'] or record.get('status') != 'consumed':
        raise PermissionError('runtime claim mismatch')
    return marker


def rehearsal_gate():
    """CPU rehearsal only: explicit opt-in, no visible GPU, never a live authority."""
    if os.environ.get('FA1_REHEARSAL') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES', '') != '':
        raise PermissionError('rehearsal mode requires FA1_REHEARSAL=1 and no visible GPU')
    return {'mode': 'rehearsal', 'attempt_id': None, 'session': None}
