"""Call order, per-call timeouts and admission control for evidence comprehension v1 (no model, no GPU).

Gate-first ordering *prioritizes* gate completion; it cannot guarantee it. Slower startup, inference or
storage, or a failure, can interrupt the gate itself, and the result is then reported `incomplete`.

Cleanup protection does not depend on any throughput estimate:
- a call is admitted only if its whole timeout ends at or before the admission cutoff (the internal
  limit minus the cleanup reserve), so an admitted call can never run into the cleanup reserve;
- a call still running at its timeout is cancelled and recorded as `timed_out`, with no score row
  (its answer is missing, never scored);
- two consecutive timeouts stop admission as a technical failure;
- the supervisor's process-group teardown at the internal limit remains the backstop.
"""
from research.evidence_comprehension_v1.probes import GATE_CONDITION

INTERNAL_SECONDS = 3300
CLEANUP_RESERVE_SECONDS = 300
ADMISSION_CUTOFF_SECONDS = INTERNAL_SECONDS - CLEANUP_RESERVE_SECONDS
# Worst single request under the slow assumed rates (26,294 prompt tokens at 2,500/s plus 320 completion
# tokens at 40/s) is about 19 s; the timeout allows more than three times that.
PER_CALL_TIMEOUT_SECONDS = 60
MAX_CONSECUTIVE_TIMEOUTS = 2
PHASES = ('gate_pass_1', 'gate_pass_2', 'descriptive_pass_1', 'descriptive_pass_2')


def call_order(probes):
    """[(phase, pass_id, probe_id)]: gate pass 1, gate pass 2 reversed, then descriptive pass 1, pass 2 reversed."""
    gate = [p['probe_id'] for p in probes if p['condition'] == GATE_CONDITION]
    rest = [p['probe_id'] for p in probes if p['condition'] != GATE_CONDITION]
    return ([('gate_pass_1', 'pass_1', i) for i in gate] + [('gate_pass_2', 'pass_2', i) for i in reversed(gate)]
            + [('descriptive_pass_1', 'pass_1', i) for i in rest]
            + [('descriptive_pass_2', 'pass_2', i) for i in reversed(rest)])


def admit(elapsed_seconds, cutoff_seconds=ADMISSION_CUTOFF_SECONDS, timeout_seconds=PER_CALL_TIMEOUT_SECONDS):
    """A call may start only if it would end, even at its full timeout, by the admission cutoff."""
    if not all(isinstance(v, (int, float)) for v in (elapsed_seconds, cutoff_seconds, timeout_seconds)):
        raise TypeError('numeric times required')
    return elapsed_seconds + timeout_seconds <= cutoff_seconds


class Admission:
    """Stateful admission: the deadline rule plus the consecutive-timeout stop. Records why admission ended."""

    def __init__(self, cutoff_seconds=ADMISSION_CUTOFF_SECONDS, timeout_seconds=PER_CALL_TIMEOUT_SECONDS):
        self.cutoff, self.timeout = cutoff_seconds, timeout_seconds
        self.consecutive_timeouts = 0
        self.stopped = None

    def may_start(self, elapsed_seconds):
        if self.stopped is None and not admit(elapsed_seconds, self.cutoff, self.timeout):
            self.stopped = 'admission_cutoff'
        return self.stopped is None

    def record(self, status):
        if status not in ('answered', 'timed_out', 'transport_failure'):
            raise ValueError('call status')
        self.consecutive_timeouts = self.consecutive_timeouts + 1 if status == 'timed_out' else 0
        if status == 'transport_failure' and self.stopped is None:
            self.stopped = 'transport_failure'
        if self.consecutive_timeouts >= MAX_CONSECUTIVE_TIMEOUTS and self.stopped is None:
            self.stopped = 'consecutive_timeouts'
