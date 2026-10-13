"""Visible-evidence task semantics and strict reader scoring, without response repair."""
import json
from . import schema as S


def judge(facts, rule, target, task):
    """Return category plus sufficient reference alternatives, not a hidden mechanic.

    Counters stay active even if later support appears. A counter inside the
    originally declared scope retires that rule. A target counter outside the
    original scope narrows reuse while retaining the original local evidence.
    """
    def matches(f):
        return f['action'] == rule['action'] and all(f['conditions'].get(k) == v
                                                   for k, v in rule['preconditions'].items())
    def scoped(f):
        scope = rule['scope']
        return f['level'] == scope['level'] and (scope['kind'] == 'level' or
                (scope['kind'] == 'state' and f['state'] == scope['state']) or
                (scope['kind'] == 'segment' and f['segment'] == scope['segment']))
    def here(f):
        return all(f[k] == target[k] for k in ('level', 'segment', 'state'))
    matching = [f for f in facts if matches(f)]
    source = [f for f in matching if scoped(f)]
    local = [f for f in matching if here(f)]
    supports = lambda fs: [f['id'] for f in fs if f['visual'] == rule['effect']]
    counters = lambda fs: [f['id'] for f in fs if f['visual'] is not None and f['visual'] != rule['effect']]
    old_bad, local_bad, local_good = counters(source), counters(local), supports(local)
    missing = [f['id'] for f in local if f['visual'] is None]
    relevant = [f['id'] for f in matching if scoped(f) or here(f)]
    target_ref = [target['observation_id']]
    cond = ('unknown' if any(k not in target['conditions'] for k in rule['preconditions']) else
            'match' if target['action'] == rule['action'] and all(
                target['conditions'][k] == v for k, v in rule['preconditions'].items()) else 'mismatch')
    # A different target action is never confirmed by a trial of the old action.
    if cond != 'match':
        local_bad, local_good, missing = [], [], []
    bad = sorted(set(old_bad + local_bad))
    groups = []
    if task == 'conditions':
        answer, groups = cond, [target_ref]
    elif task == 'target_support':
        answer = 'contradicted' if local_bad else 'supported' if local_good else 'unobserved'
        groups = [local_bad or local_good or missing] if local_bad or local_good or missing else []
    elif task == 'contradiction':
        answer, groups = ('present', [bad]) if bad else ('not_observed', [])
    elif task == 'transfer':
        answer = ('not_applicable' if cond == 'mismatch' else 'unestablished' if cond == 'unknown' else
                  'contradicted' if bad else 'supported_local' if local_good else 'unestablished')
        groups = [target_ref]
        if answer == 'contradicted':
            groups.append(bad)
        elif answer == 'supported_local':
            groups.append(local_good)
        elif answer == 'unestablished' and missing:
            groups.append(missing)
    elif task == 'evidence':
        answer, groups = ('records' if relevant else 'no_evidence'), [[r] for r in relevant]
    elif task == 'update':
        answer = 'retire' if old_bad else 'narrow' if local_bad else 'retain'
        ids = old_bad if old_bad else local_bad if local_bad else supports(source)
        groups = [ids] if ids else []
    else:
        raise ValueError('unknown task')
    eligible = sorted({r for group in groups for r in group})
    return {'answer': answer, 'required_groups': groups, 'eligible_ids': eligible}


def canonical(key):
    return {'answer': key['answer'], 'evidence_ids': sorted({group[0] for group in key['required_groups']})}


def score(output, task, key, allowed_ids):
    try:
        value = S.validate_response(output, task, allowed_ids)
    except (ValueError, TypeError, KeyError):
        return {'valid': False, 'category_correct': False, 'correct': False,
                'reference_precision': 0.0, 'reference_coverage': 0.0, 'output': output}
    refs = set(value['evidence_ids'])
    precision = len(refs & set(key['eligible_ids'])) / len(refs) if refs else float(not key['required_groups'])
    coverage = (sum(bool(refs & set(g)) for g in key['required_groups']) / len(key['required_groups'])
                if key['required_groups'] else 1.0)
    category = value['answer'] == key['answer']
    return {'valid': True, 'category_correct': category,
            'correct': category and precision == 1 and coverage == 1,
            'reference_precision': precision, 'reference_coverage': coverage, 'output': output}


def parse_request(request):
    payload = json.loads(request['messages'][1]['content'])
    evidence = payload['evidence']
    facts = (evidence['records'] if evidence['kind'] == 'raw' else
             [o for r in evidence['rules'] for o in r['observations']])
    return payload, facts


def scripted_reader(request):
    payload, facts = parse_request(request)
    return S.compact(canonical(judge(facts, payload['rule'], payload['target'], payload['task'])))
