"""Declared non-model shortcuts. Score categories and provenance separately."""
import copy
from . import schema as S, score as SC

NAMES = ('always_reuse', 'never_reuse', 'always_unknown', 'latest_entry', 'ignore_coordinates',
         'ignore_boundaries', 'repeated_support_is_certainty', 'support_without_corrections')
CONSTANT = {
    'always_reuse': ('match', 'supported', 'not_observed', 'supported_local', 'records', 'retain'),
    'never_reuse': ('mismatch', 'unobserved', 'not_observed', 'not_applicable', 'no_evidence', 'retire'),
    'always_unknown': ('unknown', 'unobserved', 'not_observed', 'unestablished', 'no_evidence', 'retain')}


def read(request, name):
    if name not in NAMES:
        raise ValueError('unknown shortcut')
    payload, facts = SC.parse_request(request)
    facts, rule, target = copy.deepcopy(facts), copy.deepcopy(payload['rule']), copy.deepcopy(payload['target'])
    task = payload['task']
    if name == 'latest_entry':
        facts = sorted(facts, key=lambda f: -f['step'])[:1]
    elif name == 'ignore_coordinates':
        for f in facts:
            if f['action']['action_id'] == rule['action']['action_id']:
                f['action']['action_data'] = copy.deepcopy(rule['action']['action_data'])
        target['action']['action_data'] = copy.deepcopy(rule['action']['action_data'])
    elif name == 'ignore_boundaries':
        for f in facts:
            f['level'], f['segment'] = target['level'], target['segment']
        rule['scope']['level'] = target['level']
        if rule['scope']['kind'] == 'segment':
            rule['scope']['segment'] = target['segment']
    elif name == 'support_without_corrections':
        facts = [f for f in facts if f['action'] != rule['action'] or f['visual'] in (None, rule['effect'])]
    key = SC.judge(facts, rule, target, task)
    output = SC.canonical(key)
    if name in CONSTANT:
        output['answer'] = CONSTANT[name][list(S.TASKS).index(task)]
        output['evidence_ids'] = []
    elif name == 'repeated_support_is_certainty' and task == 'transfer':
        support = [f['id'] for f in facts if f['action'] == rule['action'] and f['visual'] == rule['effect']]
        if len(support) >= 2 and target['action'] == rule['action'] and all(
                target['conditions'].get(k) == v for k, v in rule['preconditions'].items()):
            output = {'answer': 'supported_local', 'evidence_ids': [target['observation_id'], support[0]]}
    return S.compact(output)
