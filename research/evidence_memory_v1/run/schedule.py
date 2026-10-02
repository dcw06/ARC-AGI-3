"""Call order, timing and admission for the Stage 1 run: v2's module (itself v1's rules), unchanged.

The order is the frozen schedule: pass 1 (every probe, group-interleaved by stage1.build), then pass 2 (the
preselected repeat groups). Admission is v1's per-call rule: a call starts only if its whole bound ends before the
cutoff, so the cleanup reserve is never entered; a truncated session keeps complete groups first by construction.
"""
from research.evidence_comprehension_v2.schedule import (  # noqa: F401  (re-exported, unchanged)
    ADMISSION_CUTOFF_SECONDS, BRIDGE_MARGIN_SECONDS, CANCELLATION_VERIFY_SECONDS, CLEANUP_RESERVE_SECONDS,
    INTERNAL_SECONDS, MAX_CONSECUTIVE_TIMEOUTS, PER_CALL_BOUND_SECONDS, PER_CALL_TIMEOUT_SECONDS, PHASES,
    TEARDOWN_SECONDS, Admission, admit, call_order)
