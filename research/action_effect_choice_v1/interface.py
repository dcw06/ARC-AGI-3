"""Fixed shared actions, matched request contract and repair-free compact output."""
from copy import deepcopy
import json

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import parse_answer as parse_action
from research.recent_feedback_v1.interface import displayed_history, request_for_variant

VARIANTS = ('neutral_choice', 'compare_review')
EFFECTS = ('none', '1_to_4', '5_to_64', '65_plus', 'unknown')
FIELDS = {'candidate_predictions', 'selected_candidate', 'observed_previous_change', 'previous_prediction_check'}
SYSTEM = (
    'You control an unfamiliar pixel game and try to complete its first level. '
    'Choose exactly one supplied legal full action A or B; the host executes its exact action ID and coordinates. '
    'Images are 448 by 448 with no overlays: each native cell is a 7 by 7 block; x increases right and y down. '
    'Initial geometry is historical, can be incomplete, and does not establish current positions or control meanings. '
    'Use only visible evidence and the factual recent summary. Do not invent game rules. '
    'Predict how many visible cells each candidate would change on the next final image, including interface changes. '
    'Change does not imply progress. A repeated action can be justified. Unknown is allowed. '
    'Return ONLY compact JSON with exactly candidate_predictions, selected_candidate, observed_previous_change, '
    'previous_prediction_check. candidate_predictions has exactly A and B, each none (0 changed cells), '
    '1_to_4 (1 through 4), 5_to_64 (5 through 64), 65_plus (65 or more), or unknown. '
    'selected_candidate is A or B. On the first decision both remaining fields must be not_applicable. '
    'On the second decision observed_previous_change is yes, no or unknown for the immediately preceding executed action; '
    'previous_prediction_check is matched, mismatched or unknown for the original changed-cell category. '
    'A previous unknown forecast must be checked as unknown. '
    'Never rewrite the original prediction. Current candidate forecasts refer to the current state. '
    'Do not output explanations, extra coordinates or multiple selected actions.'
)
INSTRUCTIONS = {
    'neutral_choice': 'Choose A or B using the supplied evidence and fill the required fields.',
    'compare_review': (
        'Compare the predicted observable consequences of A and B before choosing. Use the visible evidence to '
        'select an action that can help progress or test an unresolved alternative, while allowing justified repetition. '
        'When a previous decision is supplied, check its original forecast against the observed result before choosing '
        'again. Update your current forecasts only as supported by evidence; do not force a change of action or infer '
        'usefulness from changed pixels. Use unknown when the evidence does not support a prediction.'
    ),
}

def checked_pair(pair, legal):
    if type(pair) is not dict or set(pair) != {'A', 'B'}:
        raise ValueError('exactly two fixed candidates required')
    for action in pair.values():
        if type(action) is not dict: raise ValueError('candidate must be a full action object')
        parse_action(json.dumps(dict(action, predicted_visible_change='unknown')), legal)
        if set(action) != {'action_id', 'action_data'}:
            raise ValueError('candidate contains undeclared fields')
    if digest(pair['A']) == digest(pair['B']):
        raise ValueError('candidate full actions must differ')
    return pair

def candidates(checkpoint, ordinal):
    legal = checkpoint['current']['legal_actions']
    repeat = deepcopy(checkpoint['prefix'][-1]['action'])
    parse_action(json.dumps(dict(repeat, predicted_visible_change='unknown')), legal)
    universe = [{'action_id': action, 'action_data': {}} for action in sorted(legal) if action != 6]
    if 6 in legal:
        points = {tuple(obj['occupied_anchor_xy']) for obj in checkpoint['initial_case']['geometry']['reviewed']
                  if obj['occupied_anchor_xy'] is not None}
        universe += [{'action_id': 6, 'action_data': {'x': x, 'y': y}} for x, y in sorted(points, key=lambda p: (p[1], p[0]))]
    different = [action for action in universe if digest(action) != digest(repeat)]
    alternatives = [action for action in different if action['action_id'] != repeat['action_id']] or different
    if not alternatives:
        raise ValueError('no distinct evidence-derived legal alternative')
    values = [repeat, alternatives[0]]
    if (ordinal // 2) % 2: values.reverse()
    return deepcopy(checked_pair(dict(zip(('A', 'B'), values)), legal))

def make_request(base, pair, variant, previous=None):
    if variant not in VARIANTS: raise ValueError('unknown condition')
    step, _, history = displayed_history(base)
    meta = json.loads(base['messages'][1]['content'][0]['text'])
    checked_pair(pair, meta['current_legal_actions'])
    if previous is not None:
        parse_choice(json.dumps(previous), first=False if previous['observed_previous_change'] != 'not_applicable' else True)
        if not history or digest(history[-1][0]['action']) != digest(pair[previous['selected_candidate']]):
            raise ValueError('previous selected action differs from actual displayed transition')
    result = request_for_variant(base, 'recent_summary')
    result['messages'][0] = {'role': 'system', 'content': SYSTEM}
    result['messages'][1]['content'].append({'type': 'text', 'text': json.dumps({
        'candidate_choice_v1': {'A': pair['A'], 'B': pair['B']},
        'previous_selected_forecast': None if previous is None else {
            'candidate': previous['selected_candidate'],
            'action': pair[previous['selected_candidate']],
            'prediction': previous['candidate_predictions'][previous['selected_candidate']]},
        'decision_instruction': INSTRUCTIONS[variant]}, sort_keys=True, separators=(',', ':'))})
    return result

def parse_choice(text, *, first):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('duplicate output field')
            result[key] = value
        return result
    def nonfinite(_): raise ValueError('non-finite output')
    if type(text) is not str: raise ValueError('non-text output')
    answer = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    if type(answer) is not dict or set(answer) != FIELDS: raise ValueError('choice fields differ')
    predictions = answer['candidate_predictions']
    if type(predictions) is not dict or set(predictions) != {'A', 'B'}:
        raise ValueError('both candidate forecasts required')
    if any(type(value) is not str or value not in EFFECTS for value in predictions.values()):
        raise ValueError('candidate prediction enum')
    if type(answer['selected_candidate']) is not str or answer['selected_candidate'] not in ('A', 'B'):
        raise ValueError('one candidate must be selected')
    for field, allowed in (
        ('observed_previous_change', ('not_applicable',) if first else ('yes', 'no', 'unknown')),
        ('previous_prediction_check', ('not_applicable',) if first else ('matched', 'mismatched', 'unknown'))):
        if type(answer[field]) is not str or answer[field] not in allowed: raise ValueError('invalid '+field)
    return answer
