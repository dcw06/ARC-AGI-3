"""The two v3 interventions, each an addition to its reference observation and nothing else.

A1, computed control metadata. One added observation field, computed by a deterministic tool from
legal_actions and the control rules (never from the history). It precomputes the relationship the target
question tests, which legal actions take coordinates; the remaining task is extracting it. Success
therefore shows improved interface usability, not that the model learned the intersection.

B1, tool-computed history eligibility. Two fields are added to every normalized history entry (v2's
history_candidate), computed by a deterministic tool from the shown entries. The rule is v2's frozen,
conservative one. An entry is `eligible` if it was acknowledged, its final returned frame equals the frame
before it, and no later shown entry changed the final frame or had an unknown outcome. `not eligible` means
only that the rule does not count the entry; it never asserts that the current frame differs. tool_reason
names the first applicable condition, in this order:
  1. the dispatch was not delivered;
  2. its own outcome is unknown;
  3. its own final returned frame differed from the frame before it;
  4. the earliest later shown entry that changed the final frame or had an unknown outcome.
The tool does not select, deduplicate or list actions. Results in this condition are tool-assisted.
"""
import copy

from research.evidence_comprehension_v2 import representation as R2

CONTROL_FIELD = 'computed_control_metadata'
COORDINATES = 'x and y, integers 0 to 63'
EMPTY = 'empty {}'
TOOL_RULE, TOOL_REASON = 'tool_history_rule', 'tool_reason'
ELIGIBLE, NOT_ELIGIBLE = 'eligible', 'not eligible'
TOOL_DESCRIPTION = (
    'tool_history_rule and tool_reason are computed by a deterministic tool from the shown entries, not by the '
    'model. "eligible" means the entry meets a conservative rule for an action already dispatched on the frame '
    'that is still current that left it unchanged: acknowledged, final returned frame the same as the frame '
    'before it, and no later shown entry changed the final frame or had an unknown outcome. "not eligible" means '
    'only that this rule does not count the entry; it does not establish that the current frame differs. '
    'tool_reason names the first applicable condition in this order: not delivered; own outcome unknown; own '
    'final frame differed; the earliest later entry that changed the final frame or had an unknown outcome.')


def control_metadata(legal_actions):
    return {'computed_by': 'deterministic tool from legal_actions and the control rules, not the model; '
                           'the history is not used',
            'legal_actions_with_action_data': [{'action_id': k, 'action_data': COORDINATES if k == 6 else EMPTY}
                                               for k in sorted(legal_actions)]}


def with_control_metadata(observation):
    return {**copy.deepcopy(observation), CONTROL_FIELD: control_metadata(observation['legal_actions'])}


def _final_changed(entry):
    return entry['status'] == 'acknowledged' and entry['final_frame_changed']


def eligibility(entries):
    """[(rule, reason)] per baseline entry, oldest first."""
    result = []
    for i, entry in enumerate(entries):
        if entry['status'] == 'dispatch_failed':
            result.append((NOT_ELIGIBLE, 'not delivered: the dispatch failed'))
        elif entry['status'] == 'outcome_unknown':
            result.append((NOT_ELIGIBLE, 'its own outcome is unknown'))
        elif entry['final_frame_changed']:
            result.append((NOT_ELIGIBLE, 'its own final returned frame differed from the frame before it'))
        else:
            later = next((e for e in entries[i + 1:] if _final_changed(e) or e['status'] == 'outcome_unknown'), None)
            if later is None:
                result.append((ELIGIBLE, 'acknowledged; final returned frame same as the frame before it; no later '
                                         'shown entry changed the final frame or had an unknown outcome'))
            elif later['status'] == 'outcome_unknown':
                result.append((NOT_ELIGIBLE, f'later step {later["step"]} had an unknown outcome'))
            else:
                result.append((NOT_ELIGIBLE, f'later step {later["step"]} changed the final frame'))
    return result


def with_tool_eligibility(observation):
    """v2's normalized history candidate plus the two tool fields per entry and their description."""
    base = R2.candidate_observation(observation)
    field = base['action_effect_history']
    rows = eligibility(observation['action_effect_history']['entries'])
    field = {**field, 'tool_fields': TOOL_DESCRIPTION,
             'entries': [{**entry, TOOL_RULE: rule, TOOL_REASON: reason}
                         for entry, (rule, reason) in zip(field['entries'], rows)]}
    return {**base, 'action_effect_history': field}


def strip_tool_fields(observation):
    value = copy.deepcopy(observation)
    field = value['action_effect_history']
    field.pop('tool_fields', None)
    for entry in field['entries']:
        entry.pop(TOOL_RULE, None)
        entry.pop(TOOL_REASON, None)
    return value
