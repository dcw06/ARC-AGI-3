"""Rehearsal slow-fault latencies derived from the frozen schedule (hand-written; CPU rehearsal only, never live).

The connected deadline rehearsal must stop at the admission cutoff inside a chosen pass. A uniform per-call latency
can place the cutoff inside the short repeat pass only within a window about 5% wide, narrower than the per-call
overhead varies between hosts. So the two faults work differently:
- slow_withheld_pass_1: a uniform latency, so slow that pass 1 alone outlasts the cutoff even with zero overhead;
- slow_withheld_pass_2: no added latency in pass 1, then a latency on every repeat call (from questionnaire call
  pass_1 + 1) so slow that the repeat pass alone outlasts the cutoff even with zero overhead.

Both values come from the frozen schedule (`slow_latencies`). `margins` states the conditions they satisfy under
stated, generous bounds on the host:
- the pass-1 end, under STARTUP_MAX_SECONDS before the first question and OVERHEAD_MAX_SECONDS per call, stays
  LOW_MARGIN_SECONDS before the last admissible start (cutoff minus the per-call bound);
- a slowed pass, at zero overhead, exceeds the cutoff by HIGH_FACTOR;
- a slowed call plus the overhead bound stays TIMEOUT_MARGIN_SECONDS under the rehearsal call timeout.
"""
import json
import math
from pathlib import Path

FROZEN_PATH = Path(__file__).with_name('probes.json')
REHEARSAL_INTERNAL_SECONDS = 600  # the connected test's CUTOFF_REHEARSAL_SECONDS
CLEANUP_RESERVE_SECONDS = 300
CALL_TIMEOUT_SECONDS, TEARDOWN_SECONDS, VERIFY_SECONDS, BRIDGE_MARGIN_SECONDS = 2.0, 1, 3.0, 4  # rehearsal timing
STARTUP_MAX_SECONDS = 30.0  # first question after the first-cell start (supervisor, worker, fake host, canary)
OVERHEAD_MAX_SECONDS = 0.08  # per call beyond the injected latency (transport, metrics check, evidence write)
HIGH_FACTOR = 1.25
LOW_MARGIN_SECONDS = 30.0
TIMEOUT_MARGIN_SECONDS = 0.5
REPEAT_FAULT = 'slow_withheld_pass_2'


def _round_up(value, step=0.01):
    return round(math.ceil(value / step - 1e-9) * step, 2)


def passes(frozen=None):
    frozen = frozen or json.loads(FROZEN_PATH.read_bytes())
    sizes = {block['pass']: len(block['probe_ids']) for block in frozen['schedule']}
    return sizes['pass_1'], sizes['pass_2']


def cutoff(internal_seconds=REHEARSAL_INTERNAL_SECONDS):
    return internal_seconds - CLEANUP_RESERVE_SECONDS


def bound():
    return CALL_TIMEOUT_SECONDS + TEARDOWN_SECONDS + VERIFY_SECONDS + BRIDGE_MARGIN_SECONDS


def slow_latencies(frozen=None, internal_seconds=REHEARSAL_INTERNAL_SECONDS):
    n1, n2 = passes(frozen)
    target = HIGH_FACTOR * cutoff(internal_seconds)
    return {'slow_withheld_pass_1': _round_up(target / n1), REPEAT_FAULT: _round_up(target / n2)}


def margins(frozen=None, internal_seconds=REHEARSAL_INTERNAL_SECONDS):
    """Every quantity the placement relies on, in seconds, and whether each condition holds."""
    n1, n2 = passes(frozen)
    latency = slow_latencies(frozen, internal_seconds)
    last_start = cutoff(internal_seconds) - bound()
    pass_1_end_max = STARTUP_MAX_SECONDS + n1 * OVERHEAD_MAX_SECONDS  # pass 1 without injected latency
    slowed_pass_1_min = n1 * latency['slow_withheld_pass_1']
    slowed_repeat_min = n2 * latency[REPEAT_FAULT]
    slowest_call = max(latency.values()) + OVERHEAD_MAX_SECONDS
    return {
        'pass_1_calls': n1, 'repeat_calls': n2, 'cutoff': cutoff(internal_seconds), 'per_call_bound': bound(),
        'last_admissible_start': last_start, 'latency': latency,
        'pass_2_fault': {'pass_1_end_max': round(pass_1_end_max, 3), 'low_side_margin': round(last_start - pass_1_end_max, 3),
                         'repeat_min_seconds': round(slowed_repeat_min, 3),
                         'high_side_margin': round(slowed_repeat_min - cutoff(internal_seconds), 3)},
        'pass_1_fault': {'pass_1_min_seconds': round(slowed_pass_1_min, 3),
                         'high_side_margin': round(slowed_pass_1_min - cutoff(internal_seconds), 3)},
        'slowest_call': round(slowest_call, 3), 'timeout_margin': round(CALL_TIMEOUT_SECONDS - slowest_call, 3),
        'holds': {'pass_1_ends_before_last_start': last_start - pass_1_end_max >= LOW_MARGIN_SECONDS,
                  'repeat_outlasts_cutoff': slowed_repeat_min >= HIGH_FACTOR * cutoff(internal_seconds) - 1e-9,
                  'pass_1_outlasts_cutoff': slowed_pass_1_min >= HIGH_FACTOR * cutoff(internal_seconds) - 1e-9,
                  'slowed_call_under_timeout': CALL_TIMEOUT_SECONDS - slowest_call >= TIMEOUT_MARGIN_SECONDS},
    }
