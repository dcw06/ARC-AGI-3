# Derived by scripts/build_evidence_memory_v1_sessions.py from research/control_interface_action_selection_v2/runtime_controls.py at 5a21dd3 (origin/wheelhouse-replacement-audit); edit the derivation.
"""Track 2 Stage 1 preconditions layered over the unchanged verified lifecycle (bindings in
research/evidence_memory_v1/successor/plan.py)."""
import hashlib
import json
from pathlib import Path
import re
from research.evidence_memory_v1.successor import plan as PL

PACKAGE = 'research/evidence_memory_v1_session_a'


def validate_protocol(root, protocol):
    """Frozen set, token audit, protocol v2 limits, the counted request plan and prefix caching."""
    PL.validate_experiment(root, protocol, PACKAGE)


def live_frozen_set_reasons(root, protocol):
    """Only the withheld set built from the committed seed may run live."""
    return PL.live_frozen_set_reasons(root, protocol, PACKAGE)


def verify_cache_disabled(log):
    with Path(log).open('rb') as stream:
        stream.seek(max(0, Path(log).stat().st_size - 2097152))
        text = stream.read().decode('utf-8', errors='replace')
    values = re.findall(r"enable_prefix_caching(?:['\"])?\s*[:=]\s*(True|False)", text)
    if not values or any(value != 'False' for value in values):
        raise ValueError('server log does not confirm prefix caching disabled')
    return {'disabled': True, 'confirmation': 'all retained startup configuration entries say enable_prefix_caching=False',
            'matches': len(values)}
