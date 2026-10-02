"""Compute gate (hand-written): GPU-disabled. No review lock, source approval, compute authorization or reservation
exists for stagnation supervision, so live mode always refuses, before any model, game or GPU access."""
import os

SCOPE = 'stagnation-supervision-v1'


def require():
    raise PermissionError('stagnation-supervision-v1: no reviewed source lock, compute authorization or reservation; '
                          'live mode is disabled')


def rehearsal_gate():
    """CPU rehearsal only: refuses if a GPU is visible to this process."""
    visible = os.environ.get('CUDA_VISIBLE_DEVICES')
    if visible not in (None, ''):
        raise PermissionError('rehearsal must not see a GPU (CUDA_VISIBLE_DEVICES is set)')
    return {'scope': SCOPE, 'mode': 'rehearsal', 'gpu': False}
