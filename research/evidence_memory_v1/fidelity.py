"""Independent fidelity checker for evidence-linked memory (imports nothing).

A second implementation, written without schema.py: it reads transition records (plain dicts from
`transition.history`) and a memory view ({'entries': [...], 'audit': [...]}) and re-derives from the records which
facts the memory should retain and which claims it may hold. Agreement with schema.check on which entries are
faulty is tested, on scripted writers and on targeted mutations of faithful memories; this module scores writers.

Every entry is first validated structurally (exact fields, vocabulary, strict integers with bool excluded, no
non-integer number, no confidence). A malformed entry is reported and not interpreted further. Every non-retired
entry is then checked, whatever its kind, for:
- unsupported: cited evidence that does not exist, was not observed, shows another action or value, or lies
  outside the claimed scope; or no evidence at all;
- invalid_counterevidence: cited counterevidence that does not exist, was not observed, concerns another action
  (arguments per the claim), lies outside the scope, or does not contradict the claim;
- status_rules: the allowed kind/status combinations (an observation is supported and lists no counterevidence;
  a contradicted hypothesis lists counterevidence);
- scope violations, overclaims, ignored counterexamples, stale state-dependent entries.
The memory is held responsible for every record of the trajectory, whether or not an entry was reviewed after it.

It also reports, for one memory at the end of one trajectory: required facts retained; required counterexamples
still cited; contradicted claims still live, revised or never held; required mechanisms lost; size and update
cost; and whether the audit trail is consistent.
"""
import json

LIVE = ('tentative', 'supported')
KINDS = ('observation', 'hypothesis')
STATUSES = ('tentative', 'supported', 'contradicted', 'retired')
VISUAL = ('no_observed_change', 'changed_then_returned', 'final_frame_differs')
VALUES = {'visual_effect': VISUAL, 'environment_event': ('level_completed', 'terminal_state', 'reset_acknowledged')}
SCOPE_KEYS = {'exact_state': {'kind', 'level', 'state_sha256'}, 'segment': {'kind', 'level', 'segment'},
              'object_instance': {'kind', 'level', 'cells'}, 'level': {'kind', 'level'}, 'cross_level': {'kind'}}
FIELDS = {'id', 'kind', 'claim', 'scope', 'status', 'evidence', 'counterevidence', 'last_reviewed_step', 'revision',
          'supersedes', 'reason'}
ENTRY_FAULTS = ('malformed', 'numeric_confidence', 'unsupported', 'invalid_counterevidence', 'status_rules',
                'scope_violations', 'overclaims', 'ignored_counterexamples', 'stale_state_dependent')
ENDING = ('reset_acknowledged', 'level_completed', 'level_count_decreased', 'terminal_state')


def facts(records):
    """{(episode_id, action_index): facts} re-derived from transition_evidence_v2 records, keyed by the identity
    pair each record reports and naming it by its own record_id. The level is context.levels_completed_before.
    The masked view is never read."""
    out = {}
    for r in records:
        rep = r['environment'].get('reported')
        level = r['context']['levels_completed_before']
        visual = r['measurements']['visual_effect']['status']
        ident = r['identity']
        out[(ident['episode_id'], ident['action_index'])] = {
            'record_id': ident['record_id'], 'step': ident['action_index'],
            'level': level['value'] if level.get('status') == 'measured' else None, 'segment': r['segment'],
            'state': r['observations']['before_frames_sha256'][-1], 'action': r['action']['dispatched'],
            'visual': visual if visual in VISUAL else None,
            'events': list(r['environment']['events']) if rep is not None else None}
    return out


def _int(value):
    return type(value) is int  # bool excluded


def _text(value):
    return isinstance(value, str) and bool(value)


def _ref(ref):
    """The lookup key of a stored reference: its identity pair, compared with the pair each record reports."""
    return ref['episode_id'], ref['action_index']


def structure(entry):
    """[why] for an entry whose structure is not exactly the schema's; [] when it can be interpreted."""
    if not isinstance(entry, dict) or set(entry) != FIELDS:
        return ['fields differ from the schema']
    why = []
    if entry['kind'] not in KINDS:
        why.append('kind outside the vocabulary')
    if entry['status'] not in STATUSES:
        why.append('status outside the vocabulary')
    if not _text(entry['id']) or not _text(entry['reason']):
        why.append('id and reason must be non-empty text')
    if not (_int(entry['last_reviewed_step']) and _int(entry['revision'])):
        why.append('last_reviewed_step and revision must be integers')
    if entry['supersedes'] is not None and not _text(entry['supersedes']):
        why.append('supersedes must be null or an id')
    claim = entry['claim']
    action = claim.get('action') if isinstance(claim, dict) else None
    if (not isinstance(claim, dict) or set(claim) != {'action', 'predicate', 'value'}
            or claim['predicate'] not in VALUES or claim['value'] not in VALUES[claim['predicate']]
            or not isinstance(action, dict) or set(action) != {'action_id', 'action_data'}
            or not _int(action['action_id'])
            or not (action['action_data'] == 'any' or isinstance(action['action_data'], dict) and all(
                isinstance(k, str) and _int(v) for k, v in action['action_data'].items()))):
        why.append('claim is not {action: {action_id, action_data}, predicate, value} in the vocabulary')
    scope = entry['scope']
    kind = scope.get('kind') if isinstance(scope, dict) else None
    if (kind not in SCOPE_KEYS or set(scope) != SCOPE_KEYS[kind]
            or ('level' in scope and not _int(scope['level']))
            or ('segment' in scope and not _int(scope['segment']))
            or ('state_sha256' in scope and not _text(scope['state_sha256']))
            or ('cells' in scope and not (isinstance(scope['cells'], list) and all(
                isinstance(c, list) and len(c) == 2 and all(_int(v) for v in c) for c in scope['cells'])))):
        why.append('scope is not one of the scope forms')
    for name in ('evidence', 'counterevidence'):
        refs = entry[name]
        if not isinstance(refs, list) or not all(
                isinstance(r, dict) and set(r) == {'episode_id', 'action_index'} and _int(r['action_index'])
                and isinstance(r['episode_id'], str) for r in refs):
            why.append(f'{name} is not a list of record identities')
        elif len({_ref(r) for r in refs}) != len(refs):
            why.append(f'{name} repeats a reference')
    return why


def _same_action(subject, action):
    return subject['action_id'] == action['action_id'] and subject['action_data'] in ('any', action['action_data'])


def _within(f, scope):
    if scope['kind'] == 'cross_level':
        return True
    if f['level'] != scope['level']:
        return False
    if scope['kind'] == 'exact_state':
        return f['state'] == scope['state_sha256']
    if scope['kind'] == 'segment':
        return f['segment'] == scope['segment']
    if scope['kind'] == 'object_instance':
        return [f['action']['action_data'].get('x'), f['action']['action_data'].get('y')] in scope['cells']
    return scope['kind'] == 'level'


def _shows(f, claim):
    """True / False when the record decides the claim's value, None when it was not observed."""
    if claim['predicate'] == 'visual_effect':
        return None if f['visual'] is None else f['visual'] == claim['value']
    return None if f['events'] is None else claim['value'] in f['events']


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


def verify_counter(entry, known):
    """[issue] for each counterevidence reference that is not an observed, in-scope conflict of the same action."""
    issues = []
    claim, scope = entry['claim'], entry['scope']
    for ref in entry['counterevidence']:
        f = known.get(_ref(ref))
        if f is None:
            issues.append(f'counterevidence {_ref(ref)} is not a record')
        elif _shows(f, claim) is None:
            issues.append(f'counterevidence {_ref(ref)} has no observed outcome')
        elif not _same_action(claim['action'], f['action']):
            issues.append(f'counterevidence {_ref(ref)} concerns another action')
        elif not _within(f, scope):
            issues.append(f'counterevidence {_ref(ref)} lies outside the claimed scope')
        elif _shows(f, claim):
            issues.append(f'counterevidence {_ref(ref)} agrees with the claim')
    return issues


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
    return trail == {e['id']: e for e in entries if isinstance(e, dict) and 'id' in e}


def entry_faults(entry, known, ended):
    """[(fault class, why)] for one entry. Retired entries are checked for structure only."""
    why = structure(entry)
    if why:
        return [('malformed', w) for w in why]
    out = []
    if _has_float(entry):  # the fields are fixed, so a confidence can only arrive as a non-integer number
        out.append(('numeric_confidence', 'a non-integer number'))
    if entry['status'] == 'retired':
        return out
    good, issues = verify(entry, known)
    out += [('unsupported', w) for w in issues]
    out += [('invalid_counterevidence', w) for w in verify_counter(entry, known)]
    kind, status, scope, claim = entry['kind'], entry['status'], entry['scope'], entry['claim']
    if kind == 'observation':
        if status != 'supported':
            out.append(('status_rules', f'an observation cannot be {status}'))
        if entry['counterevidence']:
            out.append(('status_rules', 'an observation lists no counterevidence'))
        if scope['kind'] != 'exact_state' or claim['action']['action_data'] == 'any':
            out.append(('scope_violations', 'an observation beyond one exact state and action'))
    elif status == 'contradicted' and not entry['counterevidence']:
        out.append(('status_rules', 'contradicted without counterevidence'))
    if kind == 'hypothesis' and status == 'supported':
        states = {(f['level'], f['state']) for f in good}
        args = {json.dumps(f['action']['action_data'], sort_keys=True) for f in good}
        if scope['kind'] == 'cross_level':
            out.append(('scope_violations', 'cross-level mechanism marked supported'))
        if (len(good) < 2) if scope['kind'] == 'exact_state' else (len(states) < 2):
            out.append(('overclaims', 'supported beyond what its evidence covers'))
        if claim['action']['action_data'] == 'any' and len(args) < 2:
            out.append(('overclaims', 'any arguments supported from one argument'))
    if kind == 'hypothesis' and status in LIVE:
        listed = {_ref(r) for r in entry['counterevidence']}
        conflicts = {k for k, f in known.items() if _same_action(claim['action'], f['action'])
                     and _within(f, scope) and _shows(f, claim) is False}
        if listed or conflicts - listed:
            names = sorted(known[k]['record_id'] if k in known else repr(k) for k in conflicts | listed)
            out.append(('ignored_counterexamples', f'live with conflicting records {names}'))
    if status in LIVE and scope['kind'] == 'segment' and scope['segment'] in ended:
        out.append(('stale_state_dependent', 'the segment ended'))
    return out


def evaluate(records, memory, expected):
    known = facts(records)
    entries = memory['entries']
    ended = {f['segment'] for f in known.values() if f['events'] and set(f['events']) & set(ENDING)}
    ended |= {f['segment'] - 1 for f in known.values()}
    report = {k: [] for k in ENTRY_FAULTS}
    valid = []
    for e in entries:
        faults = entry_faults(e, known, ended)
        for key, why in faults:
            report[key].append({'id': e.get('id') if isinstance(e, dict) else None, 'why': why})
        if not any(key == 'malformed' for key, _ in faults):
            valid.append(e)
    current = [e for e in valid if e['status'] != 'retired']
    live = [e for e in valid if e['status'] in LIVE]
    clean = {e['id'] for e in current} - {x['id'] for k in ENTRY_FAULTS for x in report[k]}

    def retained_fact(fact):
        return any(e['id'] in clean and e['kind'] == 'observation' and e['scope']['kind'] == 'exact_state'
                   and e['scope']['level'] == fact['level'] and e['scope']['state_sha256'] == fact['state']
                   and e['claim'] == {'action': fact['action'], 'predicate': fact['predicate'], 'value': fact['value']}
                   for e in current)
    cited = {known[_ref(r)]['record_id'] for e in current for r in e['evidence'] + e['counterevidence']
             if _ref(r) in known}

    def holds(pattern, entry):
        return (entry['claim']['action'] == pattern['action'] and entry['claim']['predicate'] == pattern['predicate']
                and entry['claim']['value'] == pattern['value'] and entry['scope']['kind'] in pattern['scope_kinds']
                and entry['scope'].get('level', pattern['level']) == pattern['level'])
    violations, revised, never = [], 0, 0
    for pattern in expected['must_not_hold']:
        matching = [e for e in valid if holds(pattern, e)]
        bad = [e['id'] for e in matching if e['status'] in LIVE]
        violations += bad
        revised += bool(matching) and not bad
        never += not matching
    lost_live = [p for p in expected['required_live'] if not any(
        e['status'] in LIVE and e['kind'] == 'hypothesis' and e['scope']['kind'] == p['scope_kind'] and
        e['scope'].get('level') == p['level'] and e['claim'] == {k: p[k] for k in ('action', 'predicate', 'value')}
        for e in valid)]
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
        report[k] for k in ENTRY_FAULTS)) and report['audit_consistent']
    return report


def faulty(report):
    """Ids of entries with any entry-level fault."""
    return {x['id'] for k in ENTRY_FAULTS for x in report[k]}
