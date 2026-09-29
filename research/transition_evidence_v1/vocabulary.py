"""Transition evidence vocabulary, version 1 (Workstream 3).

Separate dimensions, never one outcome label. Every value describes the retained evidence only: nothing here
describes hidden game state, assigns a cause, or judges an action good or bad.

A measurement that cannot be taken is never null. It is one of:
  {'status': 'measured', 'value': ...}      a value computed from retained frames (0 and False are real values)
  {'status': 'unavailable', 'reason': ...}  the evidence needed for this measurement does not exist
  {'status': 'absent', 'reason': ...}       an older record format did not retain this field
"""
VERSION = 'transition_evidence_v1'

# Dispatch: what happened to the request.
ACKNOWLEDGED, FAILED, OUTCOME_UNKNOWN = 'acknowledged', 'failed', 'outcome_unknown'
DISPATCH = (ACKNOWLEDGED, FAILED, OUTCOME_UNKNOWN)

# Observation availability, under the interface contract "an acknowledged action returns at least one valid frame".
COMPLETE, PARTIAL, MISSING, NOT_APPLICABLE = 'complete', 'partial', 'missing', 'not_applicable'
AVAILABILITY = (COMPLETE, PARTIAL, MISSING, NOT_APPLICABLE)

# Frame comparability, per returned frame against a stated reference.
COMPARABLE, DIMENSIONS_DIFFER, UNAVAILABLE = 'comparable', 'dimensions_differ', 'unavailable'
COMPARABILITY = (COMPARABLE, DIMENSIONS_DIFFER, UNAVAILABLE)

# Visual effect over the available returned frames, against the pre-action frame.
NO_OBSERVED_CHANGE = 'no_observed_change'        # no available returned frame differs (says nothing of hidden state)
CHANGED_THEN_RETURNED = 'changed_then_returned'  # some frame differed; the final frame equals the pre-action frame
FINAL_FRAME_DIFFERS = 'final_frame_differs'      # the final returned frame differs (including in dimensions)
INDETERMINATE = 'indeterminate'                  # the evidence cannot decide (failed, unknown, missing or partial)
VISUAL = (NO_OBSERVED_CHANGE, CHANGED_THEN_RETURNED, FINAL_FRAME_DIFFERS, INDETERMINATE)

# Environment events reported by the environment (never inferred from pixels).
LEVEL_COMPLETED = 'level_completed'              # levels_completed increased
LEVEL_COUNT_DECREASED = 'level_count_decreased'  # reported, not interpreted
TERMINAL_STATE = 'terminal_state'                # state is not NOT_FINISHED; not proof of death or of its cause
RESET_ACKNOWLEDGED = 'reset_acknowledged'        # full_reset reported; not proof that progress was lost
NONE_REPORTED = 'none_reported'
NOT_OBSERVED = 'not_observed'                    # no environment observation after the action exists
ENVIRONMENT_EVENTS = (LEVEL_COMPLETED, LEVEL_COUNT_DECREASED, TERMINAL_STATE, RESET_ACKNOWLEDGED, NONE_REPORTED,
                      NOT_OBSERVED)

# Progress interpretation in the deterministic layer: only an allowed environment signal confirms progress.
CONFIRMED, UNKNOWN = 'confirmed', 'unknown'
PROGRESS = (CONFIRMED, UNKNOWN)
ALLOWED_PROGRESS_SIGNALS = ('levels_completed_increased', 'state_WIN')
# 'hypothesis' is never produced here: model interpretations live in a separate hypothesis record.

# Continuity between consecutive transitions of one segment.
FIRST_IN_SEGMENT = 'first_in_segment'
MATCHES_PREVIOUS = 'matches_previous_final'        # before-frame equals the last observed frame of the prior transition
DIFFERS_FROM_PREVIOUS = 'differs_from_previous_final'  # a change between observations (e.g. automatic animation)
GAP_UNKNOWN_OUTCOME = 'gap_after_unknown_outcome'  # prior action may have executed; its result was never observed
GAP_MISSING_OBSERVATION = 'gap_after_missing_observation'
CONTINUITY = (FIRST_IN_SEGMENT, MATCHES_PREVIOUS, DIFFERS_FROM_PREVIOUS, GAP_UNKNOWN_OUTCOME, GAP_MISSING_OBSERVATION)


def measured(value):
    return {'status': 'measured', 'value': value}


def unavailable(reason):
    if not isinstance(reason, str) or not reason:
        raise ValueError('an unavailable measurement needs a reason')
    return {'status': 'unavailable', 'reason': reason}


def absent(reason):
    if not isinstance(reason, str) or not reason:
        raise ValueError('an absent field needs a reason')
    return {'status': 'absent', 'reason': reason}
