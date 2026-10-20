"""Explicit study phase and native enum constraints; no reply repair or keys."""
import json

from research.action_effect_choice_v1.interface import (
    EFFECTS, FIELDS, INSTRUCTIONS, VARIANTS, candidates, checked_pair, parse_choice,
    make_request as original_request,
)
from research.recent_feedback_v1.interface import displayed_history

SYSTEM = (
    'You control an unfamiliar pixel game and try to complete its first level. '
    'Choose exactly one supplied legal full action A or B; the host executes its exact action ID and coordinates. '
    'Images are 448 by 448 with no overlays: each native cell is a 7 by 7 block; x increases right and y down. '
    'Initial geometry is historical, can be incomplete, and does not establish current positions or control meanings. '
    'Use only visible evidence and the factual recent summary. Do not invent game rules. '
    'Predict the next changed-cell category for both actions, including interface changes. '
    'Change does not imply progress. Repetition can be justified. Unknown is allowed. '
    'Read study_phase.study_decision_index: it is 0 for the FIRST decision in this study condition and 1 for the SECOND. '
    'The separate game_action_count includes restored history and does not identify the study decision. '
    'At index 0, every displayed earlier action is restored history, not an earlier decision in this study condition. '
    'Set BOTH observed_previous_change and previous_prediction_check to the exact string "not_applicable" at index 0, '
    'even when the displayed restored history shows a change or contains an earlier prediction. '
    'At index 1, review only the immediately preceding study action and its original supplied forecast. '
    'Use yes, no or unknown for observed_previous_change, and matched, mismatched or unknown for previous_prediction_check. '
    'An original unknown forecast should be checked as unknown; never rewrite the original forecast. '
    'Current candidate forecasts concern the current state. '
    'Return ONLY the four required JSON fields: candidate_predictions, selected_candidate, observed_previous_change, '
    'previous_prediction_check. candidate_predictions has exactly A and B. Each is a STRING: '
    '"none" for zero changed cells, "1_to_4" for 1 through 4, "5_to_64" for 5 through 64, '
    '"65_plus" for 65 or more, or "unknown". Never return the number 0 or string "0". '
    'selected_candidate is the string A or B. Follow the supplied output schema. '
    'Do not output explanations, extra coordinates or multiple actions.'
)


def checked_phase(index):
    if type(index) is not int or index not in (0, 1):
        raise ValueError('study_decision_index must be integer 0 or 1')
    return index


def response_schema(index):
    checked_phase(index)
    enum = lambda values: {'type': 'string', 'enum': list(values)}
    return {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'candidate_predictions': {'type': 'object', 'additionalProperties': False,
                'properties': {label: enum(EFFECTS) for label in ('A', 'B')}, 'required': ['A', 'B']},
            'selected_candidate': enum(('A', 'B')),
            'observed_previous_change': enum(('not_applicable',) if index == 0 else ('yes', 'no', 'unknown')),
            'previous_prediction_check': enum(('not_applicable',) if index == 0 else ('matched', 'mismatched', 'unknown')),
        },
        'required': ['candidate_predictions', 'selected_candidate', 'observed_previous_change', 'previous_prediction_check'],
    }


def make_request(base, pair, variant, previous=None, *, study_decision_index, restored_prefix_length):
    index = checked_phase(study_decision_index)
    if type(restored_prefix_length) is not int or not 2 <= restored_prefix_length <= 20:
        raise ValueError('restored_prefix_length differs from a retained checkpoint')
    step, _, _ = displayed_history(base)
    if step != restored_prefix_length+index:
        raise ValueError('study index and restored game history disagree')
    if index == 0:
        if previous is not None: raise ValueError('first study decision cannot have an earlier study answer')
    else:
        if type(previous) is not dict: raise ValueError('second study decision requires its original first answer')
        parse_choice(json.dumps(previous), first=True)
    # Preserve the prior evidence, pair validation and action/forecast binding.
    result = original_request(base, pair, variant, previous)
    extension = json.loads(result['messages'][1]['content'][-1]['text'])
    extension['study_phase'] = {
        'schema': 'action_effect_choice_study_phase_v2',
        'study_decision_index': index, 'study_decisions_allowed': 2,
        'restored_history_action_count': restored_prefix_length, 'game_action_count': step,
        'previous_study_decision_exists': index == 1,
        'retrospective_scope': ('not_applicable_to_restored_history' if index == 0 else 'previous_study_action_only'),
        'required_retrospective_fields': (dict(observed_previous_change='not_applicable', previous_prediction_check='not_applicable')
                                         if index == 0 else None),
    }
    if index == 1:
        extension['previous_selected_forecast']['study_decision_index'] = 0
    result['messages'][0] = {'role': 'system', 'content': SYSTEM}
    result['messages'][1]['content'][-1] = {'type': 'text', 'text': json.dumps(extension, sort_keys=True, separators=(',', ':'))}
    result['response_format'] = {'type': 'json_schema', 'json_schema': {
        'name': 'action_effect_choice_v2_decision_'+str(index), 'strict': True, 'schema': response_schema(index)}}
    return result
