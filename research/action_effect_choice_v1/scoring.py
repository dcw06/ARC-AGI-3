"""Full-denominator forecast scoring; reference observations never become input."""
from .interface import parse_choice, EFFECTS
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation

def effect_size(before, after):
    check_observation(before); check_observation(after)
    count = sum(before['grid'][y][x] != after['grid'][y][x] for y in range(64) for x in range(64))
    return 'none' if count == 0 else '1_to_4' if count <= 4 else '5_to_64' if count <= 64 else '65_plus'

def branch_key(before, pair, branches):
    check_observation(before)
    if type(branches) is not dict or set(branches) != {'A', 'B'}: raise ValueError('two reference branches required')
    key = {}
    for label in ('A', 'B'):
        branch = branches[label]
        if (set(branch) != {'before', 'action', 'after'} or digest(branch['before']) != digest(before)
                or digest(branch['action']) != digest(pair[label])):
            raise ValueError('reference branch state or full action differs')
        check_observation(branch['after'])
        key[label] = effect_size(before, branch['after'])
    return key

def score(text, key, *, first, previous_forecast=None, previous_observed=None, previous_effect=None):
    if type(key) is not dict or set(key) != {'A', 'B'} or any(type(v) is not str or v not in EFFECTS[:-1] for v in key.values()):
        raise ValueError('unverified or incomplete candidate outcome key')
    if not first and (previous_forecast not in EFFECTS or previous_observed not in ('yes', 'no') or previous_effect not in EFFECTS[:-1]):
        raise ValueError('previous immutable forecast and observation required')
    if not first and (previous_observed == 'no') != (previous_effect == 'none'):
        raise ValueError('previous visible-change and extent keys contradict each other')
    result = {'valid': False, 'invalid_reason': None, 'prediction': None,
        'forecasts': {label: {'correct': False, 'covered': False} for label in ('A', 'B')},
        'different_effects_available': key['A'] != key['B'],
        'both_forecasts_correct': False, 'previous_observation_correct': None if first else False,
        'previous_check_correct': None if first else False, 'previous_forecast_was_known': None if first else previous_forecast != 'unknown'}
    try: answer = parse_choice(text, first=first)
    except (ValueError, TypeError, RecursionError) as exc:
        result['invalid_reason'] = str(exc); return result
    result.update(valid=True, prediction=answer)
    for label in ('A', 'B'):
        value = answer['candidate_predictions'][label]
        result['forecasts'][label] = {'correct': value == key[label], 'covered': value != 'unknown'}
    result['both_forecasts_correct'] = all(row['correct'] for row in result['forecasts'].values())
    if not first:
        expected = ('unknown' if previous_forecast == 'unknown' else
                    'matched' if previous_forecast == previous_effect else 'mismatched')
        result['previous_observation_correct'] = answer['observed_previous_change'] == previous_observed
        result['previous_check_correct'] = answer['previous_prediction_check'] == expected
    return result
