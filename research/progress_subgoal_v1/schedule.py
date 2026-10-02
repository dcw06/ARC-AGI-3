"""Call order, timing and admission for the progress_subgoal_v1 run: v2's module (itself v1's rules), unchanged."""
from research.evidence_comprehension_v2.schedule import (  # noqa: F401  (re-exported, unchanged)
    ADMISSION_CUTOFF_SECONDS, BRIDGE_MARGIN_SECONDS, CANCELLATION_VERIFY_SECONDS, CLEANUP_RESERVE_SECONDS,
    INTERNAL_SECONDS, MAX_CONSECUTIVE_TIMEOUTS, PER_CALL_BOUND_SECONDS, PER_CALL_TIMEOUT_SECONDS, PHASES,
    TEARDOWN_SECONDS, Admission, admit, call_order)
