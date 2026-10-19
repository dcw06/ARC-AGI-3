"""Strict scoring of evidence recognition, without inferring game semantics."""
from __future__ import annotations

from .interface import parse_recognition


FIELDS = (
    'historical_step',
    'historical_action',
    'visible_change',
    'current_matches_before',
    'legal_actions',
)


def _expected_key(key):
    """Reject an ambiguous or malformed answer key before scoring any response."""
    if type(key) is not dict or set(key) != set(FIELDS):
        raise ValueError('recognition key must contain exactly the five frozen fields')
    if type(key['historical_step']) is not int or key['historical_step'] < 0:
        raise ValueError('recognition key historical_step must be a nonnegative integer')

    action = key['historical_action']
    if type(action) is not dict or set(action) != {'action_id', 'action_data'}:
        raise ValueError('recognition key must contain a complete historical action')
    action_id = action['action_id']
    if type(action_id) is not int or not 1 <= action_id <= 7:
        raise ValueError('recognition key action_id must be an integer from 1 through 7')
    data = action['action_data']
    if type(data) is not dict:
        raise ValueError('recognition key action_data must be an object')
    if action_id == 6:
        if set(data) != {'x', 'y'} or any(
            type(data[axis]) is not int or not 0 <= data[axis] < 64
            for axis in ('x', 'y')
        ):
            raise ValueError('recognition key click requires integer x/y coordinates from 0 through 63')
    elif data:
        raise ValueError('recognition key non-click action_data must be empty')

    for name in ('visible_change', 'current_matches_before'):
        if type(key[name]) is not str or key[name] not in ('yes', 'no'):
            raise ValueError(f'recognition key {name} must be yes or no, without abstention')
    legal = key['legal_actions']
    if type(legal) is not list or any(type(item) is not int or not 1 <= item <= 7 for item in legal):
        raise ValueError('recognition key legal_actions must be an integer action list')
    if len(set(legal)) != len(legal):
        raise ValueError('recognition key legal_actions must contain no duplicates')
    return key


def _abstained(name, value):
    if name in ('historical_action', 'legal_actions'):
        return value is None
    if name in ('visible_change', 'current_matches_before'):
        return value == 'unknown'
    return False


def score_recognition(text, key):
    """Score every field on its full denominator; retain invalid responses.

    A valid abstention is uncovered and incorrect, rather than a forced guess.
    An invalid response is separately identified and cannot count as either a
    correct field or a valid abstention. No accuracy conditional on coverage is
    returned, so an unanswered field cannot acquire a zero-coverage success.
    Invalid keys are preparation errors and raise before the response is read.
    """
    _expected_key(key)
    result = {
        'schema': 'feedback_probe_recognition_score_v1',
        'raw_text': text,
        'valid': False,
        'invalid_reason': None,
        'prediction': None,
        'fields': {
            name: {'correct': False, 'covered': False, 'abstained': False}
            for name in FIELDS
        },
        'all_fields_correct': False,
    }
    try:
        prediction = parse_recognition(text)
    except (ValueError, TypeError, RecursionError) as exc:
        result['invalid_reason'] = str(exc)
        return result

    result['valid'] = True
    result['prediction'] = prediction
    for name in FIELDS:
        abstained = _abstained(name, prediction[name])
        if abstained:
            correct = False
        elif name == 'legal_actions':
            correct = set(prediction[name]) == set(key[name])
        else:
            correct = prediction[name] == key[name]
        result['fields'][name] = {
            'correct': correct,
            'covered': not abstained,
            'abstained': abstained,
        }
    result['all_fields_correct'] = all(result['fields'][name]['correct'] for name in FIELDS)
    return result
