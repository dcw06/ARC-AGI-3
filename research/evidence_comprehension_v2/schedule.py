"""Call order for evidence comprehension v2; timing and admission are v1's reviewed rules, unchanged.

The order is the frozen schedule in probes.json: withheld pass 1, withheld pass 2 (exactly reversed), then
development pass 1 and transfer pass 1. Withheld-first ordering prioritizes the decision partition; it cannot
guarantee it, and an interrupted withheld partition is reported `incomplete`.

Per-call bound, admission cutoff, consecutive-timeout stop and cleanup reserve are imported from
research/evidence_comprehension_v1/schedule.py without change.
"""
from research.evidence_comprehension_v1.schedule import (  # noqa: F401  (re-exported, unchanged)
    ADMISSION_CUTOFF_SECONDS, BRIDGE_MARGIN_SECONDS, CANCELLATION_VERIFY_SECONDS, CLEANUP_RESERVE_SECONDS,
    INTERNAL_SECONDS, MAX_CONSECUTIVE_TIMEOUTS, PER_CALL_BOUND_SECONDS, PER_CALL_TIMEOUT_SECONDS, TEARDOWN_SECONDS,
    Admission, admit)

PHASES = ('withheld_pass_1', 'withheld_pass_2', 'development_pass_1', 'transfer_pass_1')


def call_order(frozen):
    """[(phase, pass_id, probe_id)] exactly as the frozen schedule lists them."""
    order = []
    for block in frozen['schedule']:
        phase = f"{block['partition']}_{block['pass']}"
        if phase not in PHASES:
            raise ValueError('unknown schedule phase: ' + phase)
        order += [(phase, block['pass'], probe_id) for probe_id in block['probe_ids']]
    if [p for p in PHASES if any(o[0] == p for o in order)] != list(dict.fromkeys(o[0] for o in order)):
        raise ValueError('schedule phases out of order')
    return order
