"""Deterministic qualified compression with complete dispatch and revision provenance.

The existing Track 2 faithful writer/fidelity evaluator is also run, unchanged.
The new store groups exact contexts; it does not assert cross-context mechanics.
"""
import copy
import hashlib

from research.evidence_memory_v1 import schema as ES, writers as W, fidelity as F
from . import schema as S
from .fixtures import conditions


def source_facts(case):
    indexed = ES.index(case['records'])
    return [{'id': ES.record_key(r), 'step': i['step'], 'level': i['level'],
             'segment': i['segment'], 'state': i['state'], 'action': i['action'],
             'conditions': conditions(raw['before']['frames'][-1]),
             'dispatch': i['dispatch'], 'visual': i['visual'], 'events': i['events']}
            for r, raw in zip(case['records'], case['raws']) for i in [indexed[ES.record_key(r)]]]


def write(case):
    groups = {}
    for fact in source_facts(case):
        identity = {k: fact[k] for k in ('action', 'conditions', 'level', 'segment')}
        key = S.compact(identity)
        if key not in groups:
            groups[key] = {'rule_id': 'mem-' + hashlib.sha256(key.encode()).hexdigest()[:12],
                           'statement': {'effect': None}, 'action': copy.deepcopy(fact['action']),
                           'preconditions': copy.deepcopy(fact['conditions']),
                           'scope': {'kind': 'segment', 'level': fact['level'], 'segment': fact['segment']},
                           'epistemic_status': 'hypothesis', 'supporting_record_ids': [],
                           'contradictory_record_ids': [], 'revision_history': [],
                           'applicability_status': 'unobserved', 'observations': []}
        rule = groups[key]
        rule['observations'].append(copy.deepcopy(fact))
        if fact['visual'] is not None:
            if rule['statement']['effect'] is None:
                rule['statement']['effect'] = fact['visual']
            if fact['visual'] == rule['statement']['effect']:
                rule['supporting_record_ids'].append(fact['id'])
                if not rule['contradictory_record_ids']:
                    rule['applicability_status'] = 'supported_in_observed_context'
            else:
                rule['contradictory_record_ids'].append(fact['id'])
                rule['applicability_status'] = 'contradicted'
        rule['revision_history'].append({'record_id': fact['id'], 'step': fact['step'],
                                         'status': rule['applicability_status']})
    store = list(groups.values())
    for rule in store:
        S.validate_rule(rule)
    return store


def flatten(store):
    return sorted((o for rule in store for o in rule['observations']), key=lambda o: o['step'])


def audit(case, store):
    faults = []
    for rule in store:
        try:
            S.validate_rule(rule)
        except (ValueError, KeyError, TypeError) as exc:
            faults.append(str(exc))
    if flatten(store) != source_facts(case):
        faults.append('complete observation ledger differs from source')
    # Compare every qualified claim and revision with deterministic provenance,
    # in addition to checking the observation ledger. A ledger alone is insufficient.
    if store != write(case):
        faults.append('qualification, support, counterevidence or revision differs')
    base = W.run_writer(W.Faithful(), {'records': case['records']})
    expected = {'required_facts': [], 'required_counterexamples': [], 'must_not_hold': [], 'required_live': []}
    receipt = F.evaluate(case['records'], base['memory'], expected)
    if F.faulty(receipt):
        faults.append('existing faithful-writer evaluator rejected source construction')
    return {'faults': faults, 'existing_fidelity': receipt}
