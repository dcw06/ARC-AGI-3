"""Targeted mutations of faithful memories, for testing both checkers (Track 2, evidence_memory_v1).

Each mutation picks one non-retired entry of a faithful memory and corrupts it in one specific way. The audit trail
is rewritten so that it stays consistent (the last 'after' row of that entry becomes the mutated entry), so only
the entry checks can catch the fault. A mutation returns None when the memory has no suitable target.

This module produces inputs only; it is not a checker. It uses schema.index to find records to cite.
"""
import copy

from research.evidence_memory_v1 import schema as S

MISSING_INDEX = 10 ** 6


def _ref(info):
    return copy.deepcopy(info['ref'])


def _targets(entries, kind=None, statuses=S.LIVE + (S.CONTRADICTED,), scopes=None):
    return [e for e in entries if e['status'] in statuses and (kind is None or e['kind'] == kind)
            and (scopes is None or e['scope']['kind'] in scopes)]


def _first(targets):
    return targets[0] if targets else None


def _with(entry, **changes):
    out = copy.deepcopy(entry)
    out.update(copy.deepcopy(changes))
    return out


def _record(idx, entry, *, same_action, in_scope, verdict):
    """A record relative to the entry's claim and scope; verdict is 'agrees', 'conflicts' or 'undetermined'."""
    for info in sorted(idx.values(), key=lambda i: i['step']):
        if (S.subject_matches(info, entry['claim']['action']) == same_action and
                S.in_scope(info, entry['scope']) == in_scope and S.outcome(info, entry['claim']) == verdict):
            return info
    return None


def _counter(idx, entries, *, same_action, in_scope, verdict, statuses=S.LIVE + (S.CONTRADICTED,)):
    for e in _targets(entries, S.HYPOTHESIS, statuses):
        info = _record(idx, e, same_action=same_action, in_scope=in_scope, verdict=verdict)
        if info is not None and S.key(info['ref']) not in {S.key(r) for r in e['counterevidence']}:
            return _with(e, status=S.CONTRADICTED, counterevidence=e['counterevidence'] + [_ref(info)])
    return None


def observation_self_counterevidence(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    return e and _with(e, counterevidence=[e['evidence'][0]])


def counterevidence_nonexistent(idx, entries):
    e = _first(_targets(entries, S.HYPOTHESIS))
    ghost = {'episode_id': e['evidence'][0]['episode_id'], 'action_index': MISSING_INDEX} if e else None
    return e and _with(e, status=S.CONTRADICTED, counterevidence=e['counterevidence'] + [ghost])


def counterevidence_out_of_scope(idx, entries):
    return _counter(idx, entries, same_action=True, in_scope=False, verdict='conflicts')


def counterevidence_different_action(idx, entries):
    return _counter(idx, entries, same_action=False, in_scope=True, verdict='conflicts')


def counterevidence_agrees(idx, entries):
    return _counter(idx, entries, same_action=True, in_scope=True, verdict='agrees')


def counterevidence_unobserved(idx, entries):
    unobserved = [i for i in sorted(idx.values(), key=lambda i: i['step']) if i['visual'] is None]
    e = _first(_targets(entries, S.HYPOTHESIS))
    return e and unobserved and _with(e, status=S.CONTRADICTED, counterevidence=e['counterevidence'] + [_ref(unobserved[0])])


def observation_tentative(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    return e and _with(e, status=S.TENTATIVE)


def observation_contradicted(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    return e and _with(e, status=S.CONTRADICTED)


def hypothesis_contradicted_without_counterevidence(idx, entries):
    e = _first(_targets(entries, S.HYPOTHESIS))
    return e and _with(e, status=S.CONTRADICTED, counterevidence=[])


def hypothesis_live_despite_counterevidence(idx, entries):
    e = _first(_targets(entries, S.HYPOTHESIS, (S.CONTRADICTED,)))
    return e and _with(e, status=S.SUPPORTED)


def hypothesis_supported_from_one_state(idx, entries):
    e = _first([h for h in _targets(entries, S.HYPOTHESIS) if h['scope']['kind'] != S.EXACT_STATE])
    return e and _with(e, status=S.SUPPORTED, evidence=e['evidence'][:1], counterevidence=[])


def hypothesis_cross_level_supported(idx, entries):
    e = _first(_targets(entries, S.HYPOTHESIS, (S.SUPPORTED,)))
    return e and _with(e, scope={'kind': S.CROSS_LEVEL})


def kind_outside_vocabulary(idx, entries):
    e = _first(_targets(entries))
    return e and _with(e, kind='prediction')


def status_outside_vocabulary(idx, entries):
    e = _first(_targets(entries))
    return e and _with(e, status='confirmed')


def observation_value_flipped(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    if not e:
        return None
    other = next(v for v in S.PREDICATES['visual_effect'] if v != e['claim']['value'])
    return _with(e, claim={**e['claim'], 'value': other})


def observation_scope_widened(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    return e and _with(e, scope={'kind': S.LEVEL, 'level': e['scope']['level']})


def observation_other_state(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    other = e and next((i['state'] for i in idx.values() if i['state'] != e['scope']['state_sha256']), None)
    return other and _with(e, scope={**e['scope'], 'state_sha256': other})


def evidence_nonexistent(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    return e and _with(e, evidence=[{'episode_id': e['evidence'][0]['episode_id'], 'action_index': MISSING_INDEX}])


def evidence_empty(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    return e and _with(e, evidence=[])


def evidence_unobserved(idx, entries):
    unobserved = [i for i in sorted(idx.values(), key=lambda i: i['step']) if i['visual'] is None]
    e = _first(_targets(entries, S.OBSERVATION))
    return e and unobserved and _with(e, evidence=e['evidence'] + [_ref(unobserved[0])])


def evidence_duplicated(idx, entries):
    e = _first(_targets(entries, S.OBSERVATION))
    return e and _with(e, evidence=e['evidence'] + e['evidence'][:1])


def confidence_field(idx, entries):
    e = _first(_targets(entries))
    if not e:
        return None
    out = copy.deepcopy(e)
    out['confidence'] = 0.9
    return out


def float_step(idx, entries):
    e = _first(_targets(entries))
    return e and _with(e, last_reviewed_step=float(e['last_reviewed_step']))


def bool_action_id(idx, entries):
    e = _first(_targets(entries))
    return e and _with(e, claim={**e['claim'], 'action': {**e['claim']['action'], 'action_id': True}})


def float_argument(idx, entries):
    e = _first([o for o in _targets(entries) if o['claim']['action']['action_data'] not in ({}, S.ANY)])
    if not e:
        return None
    data = {k: float(v) for k, v in e['claim']['action']['action_data'].items()}
    return _with(e, claim={**e['claim'], 'action': {**e['claim']['action'], 'action_data': data}})


def empty_reason(idx, entries):
    e = _first(_targets(entries))
    return e and _with(e, reason='')


def stale_segment_revived(idx, entries):
    e = _first(_targets(entries, S.HYPOTHESIS, (S.RETIRED,), (S.SEGMENT,)))
    return e and _with(e, status=S.TENTATIVE)


MUTATIONS = {f.__name__: f for f in (
    observation_self_counterevidence, counterevidence_nonexistent, counterevidence_out_of_scope,
    counterevidence_different_action, counterevidence_agrees, counterevidence_unobserved,
    observation_tentative, observation_contradicted, hypothesis_contradicted_without_counterevidence,
    hypothesis_live_despite_counterevidence, hypothesis_supported_from_one_state, hypothesis_cross_level_supported,
    kind_outside_vocabulary, status_outside_vocabulary, observation_value_flipped, observation_scope_widened,
    observation_other_state, evidence_nonexistent, evidence_empty, evidence_unobserved, evidence_duplicated,
    confidence_field, float_step, bool_action_id, float_argument, empty_reason, stale_segment_revived)}


def apply(memory, mutated):
    """The memory with `mutated` replacing the entry of the same id, the audit trail kept consistent."""
    out = copy.deepcopy(memory)
    out['entries'] = [copy.deepcopy(mutated) if e['id'] == mutated['id'] else e for e in out['entries']]
    last = max(i for i, row in enumerate(out['audit']) if row['id'] == mutated['id'])
    out['audit'][last]['after'] = copy.deepcopy(mutated)
    return out


def schema_faulty(entries, idx):
    """Entry ids schema.py flags at the end of a trajectory: structure for retired entries, every check otherwise."""
    final = max(i['step'] for i in idx.values())
    return {e.get('id') for e in entries if (S.shape_problems(e) if e.get('status') == S.RETIRED
                                             else S.check(e, idx, final))}
