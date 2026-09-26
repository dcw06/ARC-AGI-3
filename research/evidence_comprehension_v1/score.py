"""Scoring of comprehension answers against frozen keys, with heuristic reference baselines.

Lists of action ids and lists of actions are compared as sets (the question's ordering is not
scored); a duplicate item is recorded but does not change correctness. An output that is not a
JSON object with exactly one `answer` field of the family's shape is invalid and scored wrong.
"""
import json
import math

from research.evidence_comprehension_v1.probes import ANSWER_SCHEMAS, OUTCOMES, action_of, outcome_class


def canonical_action(value):
    if (not isinstance(value, dict) or set(value) != {'action_id', 'action_data'} or type(value['action_id']) is not int
            or not isinstance(value['action_data'], dict) or set(value['action_data']) - {'x', 'y'}
            or any(type(v) is not int for v in value['action_data'].values())):
        raise ValueError('action shape')
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def parse(family, content):
    value = json.loads(content)
    if not isinstance(value, dict) or set(value) != {'answer'}:
        raise ValueError('answer object')
    answer = value['answer']
    if family in ('available_actions', 'coordinate_actions'):
        if not isinstance(answer, list) or any(type(i) is not int for i in answer):
            raise ValueError('id list')
    elif family == 'tried_unchanged':
        if not isinstance(answer, list):
            raise ValueError('action list')
        for item in answer:
            canonical_action(item)
    elif family == 'recall_action':
        if answer != 'not_shown':
            canonical_action(answer)
    elif answer not in ANSWER_SCHEMAS[family]['enum']:
        raise ValueError('label')
    return answer


def correct(family, answer, key):
    if family in ('available_actions', 'coordinate_actions'):
        return set(answer) == set(key)
    if family == 'tried_unchanged':
        return {canonical_action(a) for a in answer} == {canonical_action(a) for a in key}
    return answer == key


def score(probe, content):
    try:
        answer = parse(probe['family'], content)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return {'probe_id': probe['probe_id'], 'valid': False, 'correct': False, 'error': str(exc)[:80]}
    duplicate = isinstance(answer, list) and len({json.dumps(a, sort_keys=True) for a in answer}) != len(answer)
    return {'probe_id': probe['probe_id'], 'valid': True, 'correct': correct(probe['family'], answer, probe['key']),
            'duplicate_items': duplicate, 'answer': answer}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


def summarize(probes, results):
    """Accuracy by condition x family and by stratum. `results` maps probe_id -> score row."""
    groups = {}
    for probe in probes:
        row = results.get(probe['probe_id'])
        labels = [f"{probe['condition']}/{probe['family']}"] + [f"{probe['condition']}/{probe['family']}/{s}"
                                                                  for s in probe['strata']]
        for label in labels:
            g = groups.setdefault(label, {'n': 0, 'correct': 0, 'invalid': 0, 'missing': 0})
            g['n'] += 1
            if row is None:
                g['missing'] += 1
                continue
            g['correct'] += row['correct']
            g['invalid'] += not row['valid']
    for g in groups.values():
        answered = g['n']
        g['accuracy'] = round(g['correct'] / answered, 4) if answered else None
        g['wilson95'] = wilson(g['correct'], answered)
    return dict(sorted(groups.items()))


# ------------------------------------------------------------------ heuristic reference answers

def heuristic_answers(probe, observation):
    """Shortcut answers a model could give without reading the evidence correctly."""
    entries = observation['action_effect_history']['entries']
    family, arg = probe['family'], probe['arg']
    if family == 'available_actions':
        return {'all_seven': [1, 2, 3, 4, 5, 6, 7],
                'ids_in_history': sorted({e['action_id'] for e in entries} or {1})}
    if family == 'coordinate_actions':
        return {'always_six': [6]}
    if family == 'recall_action':
        return {'latest_entry': action_of(entries[-1]) if entries else 'not_shown'}
    if family == 'outcome_class':
        latest = outcome_class(entries[-1]) if entries else 'not_shown'
        return {'latest_entry_outcome': latest, 'always_no_change': 'acknowledged_no_change'}
    if family == 'observed_effect':
        same_type = [e for e in entries if e['action_id'] == arg['action_id']]
        return {'always_not_observed': 'not_observed',
                'ignore_coordinates': outcome_class(same_type[-1]) if same_type else 'not_observed'}
    if family == 'tried_unchanged':
        unchanged = []
        for e in entries:
            if outcome_class(e) in ('acknowledged_no_change', 'changed_then_returned') and action_of(e) not in unchanged:
                unchanged.append(action_of(e))
        return {'every_unchanged_entry': unchanged, 'empty': []}
    raise ValueError(family)


def heuristic_baselines(probes, observations):
    table = {}
    for probe in probes:
        for name, answer in heuristic_answers(probe, observations[probe['context_id']]).items():
            label = f"{probe['condition']}/{probe['family']}/{name}"
            t = table.setdefault(label, {'n': 0, 'correct': 0})
            t['n'] += 1
            t['correct'] += correct(probe['family'], answer, probe['key'])
    return {k: {**v, 'accuracy': round(v['correct'] / v['n'], 4)} for k, v in sorted(table.items())}


__all__ = ['score', 'summarize', 'heuristic_baselines', 'parse', 'correct', 'wilson', 'OUTCOMES']
