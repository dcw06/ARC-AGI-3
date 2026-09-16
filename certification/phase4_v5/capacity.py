"""Prospective development-pilot arithmetic, not a certificate or launch gate.

Inputs must come from an independently accepted, complete workload record.
The minimum-window rate is an empirical guard, NOT a confidence bound.
"""
import math

SERVICE_SECONDS = 19800
HEADROOM_FRACTION = 0.20
RATE_MARGIN_FRACTION = 0.20
WINDOWS = 8


def estimate(start_seconds, end_seconds, requests):
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)

    if (not finite(start_seconds) or not finite(end_seconds)
            or not 0 <= start_seconds < end_seconds):
        raise ValueError('invalid global workload interval')
    if not isinstance(requests, list) or not 1 <= len(requests) <= 8800:
        raise ValueError('missing or excessive request inventory')
    seen = set()
    counts = [0] * WINDOWS
    width = (end_seconds - start_seconds) / WINDOWS
    for request in requests:
        identity = request.get('request_id')
        submitted = request.get('submitted_seconds')
        started = request.get('service_started_seconds')
        completed = request.get('completed_seconds')
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError('missing/duplicate request identity')
        seen.add(identity)
        if (not all(finite(t) for t in (submitted, started, completed))
                or not start_seconds <= submitted <= started <= completed <= end_seconds):
            raise ValueError('invalid request timeline')
        if request.get('error') is not None or request.get('outcome') != 'completed':
            raise ValueError('failed/canceled/unfinished nominal request')
        # Half-open windows, except the last includes the workload endpoint.
        index = min(WINDOWS - 1, int((completed - start_seconds) / width))
        counts[index] += 1
    rates = [count / width for count in counts]
    mean_rate = len(requests) / (end_seconds - start_seconds)
    guard_rate = min(rates) * (1 - RATE_MARGIN_FRACTION)
    effective_seconds = SERVICE_SECONDS * (1 - HEADROOM_FRACTION)
    nominal = math.floor(SERVICE_SECONDS * mean_rate)
    candidate = min(nominal, math.floor(effective_seconds * guard_rate))
    return {
        'scope': 'development_repeated_games_pilot_projection_only',
        'window_completed_requests': counts,
        'window_seconds': width,
        'nominal_requests_per_wall_second': mean_rate,
        'conservative_requests_per_wall_second': guard_rate,
        'conservative_rule': '0.8_times_minimum_of_8_equal_wall_time_windows',
        'bound_kind': 'empirical_margin_not_statistical_or_deterministic_bound',
        'service_budget_seconds': SERVICE_SECONDS,
        'service_headroom_fraction': HEADROOM_FRACTION,
        'service_headroom_seconds': SERVICE_SECONDS - effective_seconds,
        'effective_service_seconds': effective_seconds,
        'C_nominal': nominal,
        'C_admit_candidate': candidate,
        'C_admit': None,
        'subsequent_admission_authorized': False,
        'phase4_complete': False,
    }
