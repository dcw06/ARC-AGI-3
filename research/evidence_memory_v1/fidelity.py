"""Independent fidelity checker for evidence-linked memory (imports nothing).

A second implementation, written without schema.py: it reads transition records (plain dicts from
`transition.history`) and a memory view ({'entries': [...], 'audit': [...]}) and re-derives from the records which
facts the memory should retain and which claims it may hold. Agreement with schema.check on the problem classes is
tested; this module is what scores writers.

It reports, for one memory at the end of one trajectory:
- facts: required exact-state observations retained by a non-retired observation whose cited records show them;
- unsupported: non-retired entries citing a record that does not exist, was not observed, shows another action
  or value, or lies outside the claimed scope;
- counterexamples: required counterexample records still cited by a non-retired entry;
The memory is held responsible for every record of the trajectory, whether or not an entry was reviewed after it.

- revision: claims the trajectory contradicts that are still live (violations), revised, or never held;
- required_live: level-scoped mechanisms that must survive a reset or a level change;
- scope violations, overclaims, ignored counterexamples, stale state-dependent entries, numeric confidence;
- size (entries, characters) and update cost (operations), and whether the audit trail is consistent.
"""
import json

LIVE = ('tentative', 'supported')
VISUAL = ('no_observed_change', 'changed_then_returned', 'final_frame_differs')
FIELDS = {'id', 'kind', 'claim', 'scope', 'status', 'evidence', 'counterevidence', 'last_reviewed_step', 'revision',
          'supersedes', 'reason'}


def facts(records):
    """{'episode#index': facts} re-derived from records; level carried over unobserved transitions."""
    out, level = {}, 0
    for r in records:
        rep = r['environment'].get('reported')
        if rep is not None:
            level = rep['levels_completed_before']
        visual = r['measurements']['visual_effect']['status']
        ident = r['identity']
        out[f"{ident['episode_id']}#{ident['action_index']}"] = {
            'step': ident['action_index'], 'level': level, 'segment': r['segment'],
            'state': r['observations']['before_frames_sha256'][-1], 'action': r['action']['dispatched'],
            'visual': visual if visual in VISUAL else None,
            'events': list(r['environment']['events']) if rep is not None else None}
        if rep is not None:
            level = rep['levels_completed_after']
    return out


def _same_action(subject, action):
    return subject['action_id'] == action['action_id'] and subject['action_data'] in ('any', action['action_data'])


def _within(f, scope):
    if scope.get('kind') == 'cross_level':
        return True
    if f['level'] != scope.get('level'):
        return False
    if scope['kind'] == 'exact_state':
        return f['state'] == scope.get('state_sha256')
    if scope['kind'] == 'segment':
        return f['segment'] == scope.get('segment')
    if scope['kind'] == 'object_instance':
        return [f['action']['action_data'].get('x'), f['action']['action_data'].get('y')] in scope.get('cells', [])
    return scope['kind'] == 'level'


def _shows(f, claim):
    """True / False when the record decides the claim's value, None when it was not observed."""
    if claim['predicate'] == 'visual_effect':
        return None if f['visual'] is None else f['visual'] == claim['value']
    return None if f['events'] is None else claim['value'] in f['events']


def _ref(ref):
    return f"{ref['episode_id']}#{ref['action_index']}"


def _has_float(value):
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_has_float(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_float(v) for v in value)
    return False


def verify(entry, known):
    """(supporting facts, [issue]) for one entry's evidence."""
    issues, good = [], []
    claim, scope = entry['claim'], entry['scope']
    for ref in entry['evidence']:
        f = known.get(_ref(ref))
        if f is None:
            issues.append(f'cites {_ref(ref)}, which is not a record')
        elif _shows(f, claim) is None:
            issues.append(f'cites {_ref(ref)}, whose outcome was not observed')
        elif not _same_action(claim['action'], f['action']) or not _shows(f, claim):
            issues.append(f'cites {_ref(ref)}, which shows a different action or value')
        elif not _within(f, scope):
            issues.append(f'cites {_ref(ref)}, outside the claimed scope')
        else:
            good.append(f)
    if not entry['evidence']:
        issues.append('cites no evidence')
    return good, issues


def gold(records, question):
    """The answer the full record history supports (independent of any memory)."""
    known = [f for f in facts(records).values() if f['level'] == question['level'] and f['state'] == question['state']]

    def values(action):
        return sorted({f['visual'] for f in known if f['action'] == action and f['visual'] is not None})
    if question['kind'] == 'recall':
        return values(question['action']) or ['no_evidence']
    changed = [c for c in question['candidates'] if 'final_frame_differs' in values(c)]
    return changed or [c for c in question['candidates'] if 'no_observed_change' not in values(c)]


def _audit_consistent(entries, audit):
    trail = {}
    for row in audit:
        if trail.get(row['id']) != row['before'] or (row['before'] is None) != (row['op'] == 'add'):
            return False
        trail[row['id']] = row['after']
    return trail == {e['id']: e for e in entries}


def evaluate(records, memory, expected):
    known = facts(records)
    entries = memory['entries']
    current = [e for e in entries if e.get('status') != 'retired']
    live = [e for e in entries if e.get('status') in LIVE]
    ended = {f['segment'] for f in known.values() if f['events'] and set(f['events']) & {
        'reset_acknowledged', 'level_completed', 'level_count_decreased', 'terminal_state'}}
    ended |= {f['segment'] - 1 for f in known.values()}
    report = {'unsupported': [], 'scope_violations': [], 'overclaims': [], 'ignored_counterexamples': [],
              'stale_state_dependent': [], 'numeric_confidence': [], 'malformed': []}
    verified = {}
    for e in entries:
        if set(e) != FIELDS:
            report['malformed'].append({'id': e.get('id'), 'why': 'fields differ from the schema'})
            continue
        if _has_float(e) or 'confidence' in json.dumps(e):
            report['numeric_confidence'].append(e['id'])
        good, issues = verify(e, known)
        verified[e['id']] = good
        if e['status'] == 'retired':
            continue
        report['unsupported'] += [{'id': e['id'], 'why': why} for why in issues]
        if e['kind'] == 'observation' and (e['scope']['kind'] != 'exact_state' or
                                           e['claim']['action']['action_data'] == 'any'):
            report['scope_violations'].append({'id': e['id'], 'why': 'an observation beyond one exact state and action'})
        if e['status'] == 'supported' and e['kind'] == 'hypothesis':
            states = {(f['level'], f['state']) for f in good}
            args = {json.dumps(f['action']['action_data'], sort_keys=True) for f in good}
            if e['scope']['kind'] == 'cross_level':
                report['scope_violations'].append({'id': e['id'], 'why': 'cross-level mechanism marked supported'})
            if (len(good) < 2) if e['scope']['kind'] == 'exact_state' else (len(states) < 2):
                report['overclaims'].append({'id': e['id'], 'why': 'supported beyond what its evidence covers'})
            if e['claim']['action']['action_data'] == 'any' and len(args) < 2:
                report['overclaims'].append({'id': e['id'], 'why': 'any arguments supported from one argument'})
        if e['status'] in LIVE:
            listed = {_ref(r) for r in e['counterevidence']}
            conflicts = [k for k, f in known.items() if _same_action(e['claim']['action'], f['action']) and _within(f, e['scope']) and
                         _shows(f, e['claim']) is False]
            if e['kind'] == 'hypothesis' and (listed or set(conflicts) - listed):
                report['ignored_counterexamples'].append({'id': e['id'], 'records': sorted(set(conflicts) | listed)})
            if e['scope']['kind'] == 'segment' and e['scope'].get('segment') in ended:
                report['stale_state_dependent'].append(e['id'])

    def retained_fact(fact):
        return any(e['kind'] == 'observation' and e['status'] == 'supported' and e['scope']['kind'] == 'exact_state'
                   and e['scope'].get('level') == fact['level'] and e['scope'].get('state_sha256') == fact['state']
                   and e['claim'] == {'action': fact['action'], 'predicate': fact['predicate'], 'value': fact['value']}
                   and verified.get(e['id']) for e in current)
    cited = {_ref(r) for e in current for r in e['evidence'] + e['counterevidence']}

    def holds(pattern, entry):
        return (entry['claim']['action'] == pattern['action'] and entry['claim']['predicate'] == pattern['predicate']
                and entry['claim']['value'] == pattern['value'] and entry['scope']['kind'] in pattern['scope_kinds']
                and entry['scope'].get('level', pattern['level']) == pattern['level'])
    violations, revised, never = [], 0, 0
    for pattern in expected['must_not_hold']:
        matching = [e for e in entries if 'claim' in e and 'scope' in e and holds(pattern, e)]
        bad = [e['id'] for e in matching if e['status'] in LIVE]
        violations += bad
        revised += bool(matching) and not bad
        never += not matching
    lost_live = [p for p in expected['required_live'] if not any(
        e['status'] in LIVE and e['kind'] == 'hypothesis' and e['scope']['kind'] == p['scope_kind'] and
        e['scope'].get('level') == p['level'] and e['claim'] == {k: p[k] for k in ('action', 'predicate', 'value')}
        for e in entries if set(e) == FIELDS)]
    missing = [f for f in expected['required_facts'] if not retained_fact(f)]
    report.update({
        'size': {'entries': len(entries), 'non_retired': len(current), 'live': len(live),
                 'chars': len(json.dumps(entries, sort_keys=True, separators=(',', ':')))},
        'update_cost': {'operations': len(memory['audit']),
                        'by_op': {op: sum(r['op'] == op for r in memory['audit'])
                                  for op in ('add', 'revise', 'retire', 'review')}},
        'facts': {'required': len(expected['required_facts']), 'retained': len(expected['required_facts']) - len(missing),
                  'missing': missing},
        'counterexamples': {'required': len(expected['required_counterexamples']),
                            'missing': [k for k in expected['required_counterexamples'] if k not in cited]},
        'revision': {'patterns': len(expected['must_not_hold']), 'still_live': violations, 'revised': revised,
                     'never_held': never},
        'required_live': {'required': len(expected['required_live']), 'lost': lost_live},
        'audit_consistent': _audit_consistent(entries, memory['audit'])})
    report['faithful'] = not (missing or report['counterexamples']['missing'] or violations or lost_live or any(
        report[k] for k in ('unsupported', 'scope_violations', 'overclaims', 'ignored_counterexamples',
                            'stale_state_dependent', 'numeric_confidence', 'malformed'))) and report['audit_consistent']
    return report
