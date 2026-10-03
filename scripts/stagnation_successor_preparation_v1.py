"""Successor preparation boundary. No approval generation, reservation, GPU flag or submission."""
from pathlib import Path
from scripts.stagnation_provider_preflight_v1 import validate_provider_preflight
from scripts.stagnation_supervision_launch_preflight_v1 import consume_explicit_approvals


def review_inputs(folder,provider_records,source_approval,launch_approval,*,source_hash,reservation_hash,now=None):
    # Provider-specific replay happens before any authority handling. Caller cannot
    # bypass it with a claimed accessible=true normalized record.
    rows=validate_provider_preflight(folder,provider_records,now)
    approvals=consume_explicit_approvals(source_approval,launch_approval,
                                       source_hash=source_hash,reservation_hash=reservation_hash)
    return {'preflight':rows,'approvals':approvals,'launch_authorized_by_this_helper':False}


def refuse_live():
    raise PermissionError('R7 preparation-only package: wheelhouse access and replacement approvals unresolved')
