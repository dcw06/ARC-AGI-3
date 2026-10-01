"""Evidence-linked memory entries, update rules and mechanical checks (Track 2, evidence_memory_v1).

An entry is one claim about transition evidence, never a free-form note:

  {'id': str, 'kind': 'observation' | 'hypothesis',
   'claim': {'action': {'action_id': int, 'action_data': dict | 'any'}, 'predicate': str, 'value': str},
   'scope': {'kind': 'exact_state', 'level': int, 'state_sha256': str}
          | {'kind': 'segment', 'level': int, 'segment': int}
          | {'kind': 'object_instance', 'level': int, 'cells': [[x, y], ...]}
          | {'kind': 'level', 'level': int}
          | {'kind': 'cross_level'},
   'status': 'tentative' | 'supported' | 'contradicted' | 'retired',
   'evidence': [ref, ...], 'counterevidence': [ref, ...],   ref = a transition record's identity
   'last_reviewed_step': int, 'revision': int, 'supersedes': str | None, 'reason': str}

There is no confidence field and no number other than identifiers, levels, segments, steps and revisions. The
claim is structured so that an observation can be reconstructed mechanically from the records it references; its
readable text is derived (`claim_text`), never stored apart from the structure.

Rules (each one is checked by `check`):
- An observation describes referenced transitions only: scope `exact_state`, specific action arguments, status
  `supported` (or `retired`), no counterevidence, and every referenced record reproduces it.
- A hypothesis is everything else. It is `supported` only when its evidence covers at least two distinct states in
  scope (two records for an exact-state hypothesis), at least two distinct arguments when it claims 'any'
  arguments, it has no counterevidence, and its scope is not `cross_level` (cross-level stays tentative in v1).
- A hypothesis with an in-scope counterexample the writer had seen must list it and be `contradicted` or retired.
- An outcome that was not observed (failed, unknown, missing, indeterminate) never supports or contradicts a claim.
- `segment` scope is state-dependent: once its segment has ended (a seen record reports a reset, level change or
  terminal state), a live segment-scoped entry is stale. A reset or level change never deletes entries; there is no delete operation.

Updates (`Memory`): add, revise, retire, review. Every operation needs a reason and the expected revision, bumps
the revision, and appends a full before/after copy to the audit trail; `replay(audit)` rebuilds the entries.
Counterevidence is append-only; evidence may shrink only together with a change of scope or claim; a kind never
changes (retire and add a new entry with `supersedes`); a retired entry is never revised.
"""
import copy

from research.transition_evidence_v1 import vocabulary as V

VERSION = 'evidence_memory_v1'
OBSERVATION, HYPOTHESIS = 'observation', 'hypothesis'
KINDS = (OBSERVATION, HYPOTHESIS)
TENTATIVE, SUPPORTED, CONTRADICTED, RETIRED = 'tentative', 'supported', 'contradicted', 'retired'
STATUSES = (TENTATIVE, SUPPORTED, CONTRADICTED, RETIRED)
LIVE = (TENTATIVE, SUPPORTED)
EXACT_STATE, SEGMENT, OBJECT_INSTANCE, LEVEL, CROSS_LEVEL = (
    'exact_state', 'segment', 'object_instance', 'level', 'cross_level')
SCOPES = (EXACT_STATE, SEGMENT, OBJECT_INSTANCE, LEVEL, CROSS_LEVEL)
SCOPE_FIELDS = {EXACT_STATE: ('kind', 'level', 'state_sha256'), SEGMENT: ('kind', 'level', 'segment'),
                OBJECT_INSTANCE: ('kind', 'level', 'cells'), LEVEL: ('kind', 'level'), CROSS_LEVEL: ('kind',)}
PREDICATES = {'visual_effect': (V.NO_OBSERVED_CHANGE, V.CHANGED_THEN_RETURNED, V.FINAL_FRAME_DIFFERS),
              'environment_event': (V.LEVEL_COMPLETED, V.TERMINAL_STATE, V.RESET_ACKNOWLEDGED)}
ANY = 'any'
SEGMENT_ENDING = (V.RESET_ACKNOWLEDGED, V.LEVEL_COMPLETED, V.LEVEL_COUNT_DECREASED, V.TERMINAL_STATE)
ENTRY_FIELDS = ('id', 'kind', 'claim', 'scope', 'status', 'evidence', 'counterevidence', 'last_reviewed_step',
                'revision', 'supersedes', 'reason')
REVISABLE = ('claim', 'scope', 'status', 'evidence', 'counterevidence', 'last_reviewed_step', 'reason')


# ---- evidence index over transition records (transition_evidence_v1, consumed read-only)

def ref_of(record):
    return {'episode_id': record['identity']['episode_id'], 'action_index': record['identity']['action_index']}


def key(ref):
    return f"{ref['episode_id']}#{ref['action_index']}"


def index(records):
    """{ref key: facts} for records from transition.history. The level of a transition without an environment
    observation (failed, unknown) is carried forward from the last report and marked as derived."""
    out, level = {}, 0
    for record in records:
        reported = record['environment'].get('reported')
        if reported:
            level = reported['levels_completed_before']
        visual = record['measurements']['visual_effect']['status']
        acknowledged = record['dispatch']['status'] == V.ACKNOWLEDGED
        out[key(ref_of(record))] = {
            'ref': ref_of(record), 'step': record['identity']['action_index'], 'level': level,
            'level_derived': not reported, 'segment': record['segment'],
            'state': record['observations']['before_frames_sha256'][-1],
            'action': record['action']['dispatched'], 'dispatch': record['dispatch']['status'],
            'visual': None if visual == V.INDETERMINATE else visual,
            'events': record['environment']['events'] if acknowledged and reported else None,
            'ends_segment': bool(set(record['environment']['events']) & set(SEGMENT_ENDING))}
        if reported:
            level = reported['levels_completed_after']
    return out


def seen(idx, step):
    return {k: v for k, v in idx.items() if v['step'] <= step}


def subject_matches(info, action):
    return (info['action']['action_id'] == action['action_id'] and
            (action['action_data'] == ANY or info['action']['action_data'] == action['action_data']))


def in_scope(info, scope):
    kind = scope['kind']
    if kind == CROSS_LEVEL:
        return True
    if info['level'] != scope['level']:
        return False
    if kind == EXACT_STATE:
        return info['state'] == scope['state_sha256']
    if kind == SEGMENT:
        return info['segment'] == scope['segment']
    if kind == OBJECT_INSTANCE:
        data = info['action']['action_data']
        return [data.get('x'), data.get('y')] in scope['cells']
    return True  # LEVEL


def outcome(info, claim):
    """'agrees', 'conflicts' or 'undetermined' (nothing was observed that could decide)."""
    if claim['predicate'] == 'visual_effect':
        if info['visual'] is None:
            return 'undetermined'
        return 'agrees' if info['visual'] == claim['value'] else 'conflicts'
    if info['events'] is None:
        return 'undetermined'
    return 'agrees' if claim['value'] in info['events'] else 'conflicts'


def claim_text(entry):
    action = entry['claim']['action']
    data = action['action_data']
    args = 'any arguments' if data == ANY else ','.join(f'{k}={data[k]}' for k in sorted(data)) or 'no arguments'
    scope = entry['scope']
    where = {EXACT_STATE: lambda: f"in exact state {scope['state_sha256'][:8]} (level {scope['level']})",
             SEGMENT: lambda: f"in segment {scope['segment']} only (level {scope['level']})",
             OBJECT_INSTANCE: lambda: f"at cells {scope['cells']} (level {scope['level']})",
             LEVEL: lambda: f"anywhere in level {scope['level']}",
             CROSS_LEVEL: lambda: 'in every level (tentative)'}[scope['kind']]()
    return f"ACTION{action['action_id']}({args}) -> {entry['claim']['predicate']}={entry['claim']['value']} {where}"


# ---- mechanical checks

def _numbers_are_integers(value):
    if isinstance(value, float):
        return False
    if isinstance(value, dict):
        return all(_numbers_are_integers(v) for v in value.values())
    if isinstance(value, list):
        return all(_numbers_are_integers(v) for v in value)
    return True


def shape_problems(entry):
    """Structure only (no evidence needed). An empty list means the entry can be stored."""
    if not isinstance(entry, dict) or tuple(sorted(entry)) != tuple(sorted(ENTRY_FIELDS)):
        extra = sorted(set(entry) - set(ENTRY_FIELDS)) if isinstance(entry, dict) else []
        return ['shape: fields must be exactly ' + ', '.join(ENTRY_FIELDS) + (f'; unexpected {extra}' if extra else '')]
    problems = []
    if not _numbers_are_integers(entry):
        problems.append('numeric_confidence: a non-integer number is not allowed anywhere in an entry')
    if entry['kind'] not in KINDS or entry['status'] not in STATUSES:
        problems.append('vocabulary: kind or status')
    claim, scope = entry['claim'], entry['scope']
    action = claim.get('action') if isinstance(claim, dict) else None
    if (not isinstance(claim, dict) or sorted(claim) != ['action', 'predicate', 'value'] or
            claim['predicate'] not in PREDICATES or claim['value'] not in PREDICATES[claim['predicate']] or
            not isinstance(action, dict) or sorted(action) != ['action_data', 'action_id'] or
            type(action['action_id']) is not int or
            not (action['action_data'] == ANY or isinstance(action['action_data'], dict) and all(
                isinstance(k, str) and type(v) is int for k, v in action['action_data'].items()))):
        problems.append('vocabulary: claim')
    kind = scope.get('kind') if isinstance(scope, dict) else None
    if kind not in SCOPES or tuple(sorted(scope)) != tuple(sorted(SCOPE_FIELDS[kind])):
        problems.append('vocabulary: scope')
    elif (any(type(scope[f]) is not int for f in ('level', 'segment') if f in scope) or
          ('state_sha256' in scope and not (isinstance(scope['state_sha256'], str) and scope['state_sha256'])) or
          ('cells' in scope and not (isinstance(scope['cells'], list) and all(
              isinstance(c, list) and len(c) == 2 and all(type(v) is int for v in c) for c in scope['cells'])))):
        problems.append('vocabulary: scope field types')
    for name in ('evidence', 'counterevidence'):
        refs = entry[name]
        if not isinstance(refs, list) or any(not isinstance(r, dict) or sorted(r) != ['action_index', 'episode_id']
                                             or type(r['action_index']) is not int
                                             or not isinstance(r['episode_id'], str) for r in refs):
            problems.append(f'shape: {name} must be a list of record identities')
        elif len({key(r) for r in refs}) != len(refs):
            problems.append(f'shape: duplicate {name} reference')
    if not isinstance(entry['id'], str) or not entry['id'] or not isinstance(entry['reason'], str) or not entry['reason']:
        problems.append('shape: a non-empty id and reason are required')
    if entry['supersedes'] is not None and not (isinstance(entry['supersedes'], str) and entry['supersedes']):
        problems.append('shape: supersedes is null or an entry id')
    if type(entry['last_reviewed_step']) is not int or type(entry['revision']) is not int:
        problems.append('shape: last_reviewed_step and revision are integers')
    return problems


def check(entry, idx, as_of=None):
    """Problems of one entry against the records seen by `as_of` (default: the entry's `last_reviewed_step`, which
    is what the gate uses; an end-of-trajectory audit passes the final step). Each problem starts
    with a stable code: shape, numeric_confidence, vocabulary, dangling_reference, unknown_outcome_as_evidence,
    observation_not_reconstructable, evidence_mismatch, scope_violation, counterevidence_mismatch, status_rule,
    overgeneralization, contradiction_unaddressed, counterexample_ignored, stale_state_dependent."""
    problems = shape_problems(entry)
    if problems:
        return problems
    as_of = entry['last_reviewed_step'] if as_of is None else as_of
    known = seen(idx, as_of)
    claim, scope, kind, status = entry['claim'], entry['scope'], entry['kind'], entry['status']
    evidence = []
    for ref in entry['evidence']:
        info = known.get(key(ref))
        if info is None:
            problems.append(f'dangling_reference: evidence {key(ref)} is not a record seen by step '
                            f"{as_of}")
            continue
        verdict = outcome(info, claim)
        if verdict == 'undetermined':
            problems.append(f'unknown_outcome_as_evidence: {key(ref)} has no observed outcome ({info["dispatch"]})')
        elif not subject_matches(info, claim['action']) or verdict == 'conflicts':
            code = 'observation_not_reconstructable' if kind == OBSERVATION else 'evidence_mismatch'
            problems.append(f'{code}: {key(ref)} does not show this action with this value')
        elif not in_scope(info, scope):
            code = 'observation_not_reconstructable' if kind == OBSERVATION else 'scope_violation'
            problems.append(f'{code}: evidence {key(ref)} lies outside the claimed scope')
        else:
            evidence.append(info)
    for ref in entry['counterevidence']:
        info = known.get(key(ref))
        if info is None:
            problems.append(f'dangling_reference: counterevidence {key(ref)}')
        elif not (subject_matches(info, claim['action']) and in_scope(info, scope) and
                  outcome(info, claim) == 'conflicts'):
            problems.append(f'counterevidence_mismatch: {key(ref)} is not an in-scope observed conflict')
    if not entry['evidence']:
        problems.append('status_rule: an entry needs at least one evidence reference')
    if kind == OBSERVATION:
        if scope['kind'] != EXACT_STATE:
            problems.append('scope_violation: an observation is limited to the exact observed state')
        if claim['action']['action_data'] == ANY:
            problems.append('scope_violation: an observation names the exact action arguments')
        if status not in (SUPPORTED, RETIRED) or entry['counterevidence']:
            problems.append('status_rule: an observation is supported (or retired) and has no counterevidence')
        return problems
    states = {(i['level'], i['state']) for i in evidence}
    if status == SUPPORTED:
        if scope['kind'] == CROSS_LEVEL:
            problems.append('scope_violation: a cross-level mechanism stays tentative in v1')
        if scope['kind'] == EXACT_STATE and len(evidence) < 2:
            problems.append('overgeneralization: supported from fewer than two records')
        if scope['kind'] != EXACT_STATE and len(states) < 2:
            problems.append('overgeneralization: supported beyond the exact state from a single state')
        if claim['action']['action_data'] == ANY and len({repr(sorted(i['action']['action_data'].items()))
                                                          for i in evidence}) < 2:
            problems.append('overgeneralization: any arguments supported from a single argument value')
    if status in LIVE and entry['counterevidence']:
        problems.append('contradiction_unaddressed: counterevidence listed but the status is ' + status)
    if status == CONTRADICTED and not entry['counterevidence']:
        problems.append('status_rule: contradicted without counterevidence')
    if status in LIVE:
        listed = {key(r) for r in entry['counterevidence']}
        for k, info in sorted(known.items(), key=lambda kv: kv[1]['step']):
            if (k not in listed and subject_matches(info, claim['action']) and in_scope(info, scope) and
                    outcome(info, claim) == 'conflicts'):
                problems.append(f'counterexample_ignored: {k} conflicts in scope')
        if scope['kind'] == SEGMENT and any(i['segment'] > scope['segment'] or
                                            i['segment'] == scope['segment'] and i['ends_segment'] for i in known.values()):
            problems.append('stale_state_dependent: the segment ended; a segment-scoped entry must be retired')
    return problems


# ---- the audited store

class OperationError(ValueError):
    pass


class Memory:
    """Entries plus an append-only audit trail. Nothing is ever deleted or overwritten without a trail."""

    def __init__(self):
        self.entries, self.audit = {}, []

    def _log(self, op, entry_id, step, reason, before, after):
        self.audit.append({'seq': len(self.audit), 'op': op, 'id': entry_id, 'step': step, 'reason': reason,
                           'before': copy.deepcopy(before), 'after': copy.deepcopy(after)})

    def _current(self, entry_id, expected_revision):
        entry = self.entries.get(entry_id)
        if entry is None:
            raise OperationError(f'no entry {entry_id}')
        if entry['status'] == RETIRED:
            raise OperationError(f'{entry_id} is retired; add a new entry that supersedes it')
        if expected_revision != entry['revision']:
            raise OperationError(f'{entry_id}: expected revision {expected_revision}, found {entry["revision"]}')
        return entry

    @staticmethod
    def _reason(reason):
        if not isinstance(reason, str) or not reason:
            raise OperationError('every operation needs a reason')

    def add(self, entry, step, reason):
        self._reason(reason)
        problems = shape_problems(entry)
        if problems:
            raise OperationError('; '.join(problems))
        if entry['id'] in self.entries:
            raise OperationError(f'{entry["id"]} exists; revise it instead of overwriting')
        if entry['revision'] != 1 or entry['status'] == RETIRED:
            raise OperationError('a new entry starts at revision 1 and is not retired')
        if entry['supersedes'] is not None and entry['supersedes'] not in self.entries:
            raise OperationError('supersedes an unknown entry')
        self.entries[entry['id']] = copy.deepcopy(entry)
        self._log('add', entry['id'], step, reason, None, entry)

    def revise(self, entry_id, expected_revision, changes, step, reason):
        self._reason(reason)
        before = self._current(entry_id, expected_revision)
        if not changes or set(changes) - set(REVISABLE):
            raise OperationError('revise changes only ' + ', '.join(REVISABLE))
        after = {**copy.deepcopy(before), **copy.deepcopy(changes), 'revision': before['revision'] + 1}
        problems = shape_problems(after)
        if problems:
            raise OperationError('; '.join(problems))
        if after['status'] == RETIRED:
            raise OperationError('use retire to retire an entry')
        if not {key(r) for r in before['counterevidence']} <= {key(r) for r in after['counterevidence']}:
            raise OperationError('counterevidence is append-only')
        narrowing = after['scope'] != before['scope'] or after['claim'] != before['claim']
        if not narrowing and not {key(r) for r in before['evidence']} <= {key(r) for r in after['evidence']}:
            raise OperationError('evidence may be dropped only with a change of scope or claim')
        if after['last_reviewed_step'] < before['last_reviewed_step']:
            raise OperationError('last_reviewed_step never decreases')
        self.entries[entry_id] = after
        self._log('revise', entry_id, step, reason, before, after)

    def retire(self, entry_id, expected_revision, step, reason):
        self._reason(reason)
        before = self._current(entry_id, expected_revision)
        after = {**copy.deepcopy(before), 'status': RETIRED, 'reason': reason, 'revision': before['revision'] + 1,
                 'last_reviewed_step': max(step, before['last_reviewed_step'])}
        self.entries[entry_id] = after
        self._log('retire', entry_id, step, reason, before, after)

    def review(self, entry_id, expected_revision, step, reason):
        """Record that the entry was re-examined at `step` and left unchanged."""
        self.revise(entry_id, expected_revision, {'last_reviewed_step': step}, step, reason)
        self.audit[-1]['op'] = 'review'

    def view(self):
        return {'version': VERSION, 'entries': [copy.deepcopy(self.entries[k]) for k in sorted(self.entries)],
                'audit': copy.deepcopy(self.audit)}


def replay(audit):
    """Rebuild the entries from the audit trail alone; each step must start from the logged 'before'."""
    entries = {}
    for row in audit:
        if entries.get(row['id']) != row['before']:
            raise OperationError(f'audit row {row["seq"]} does not continue the trail of {row["id"]}')
        entries[row['id']] = copy.deepcopy(row['after'])
    return [entries[k] for k in sorted(entries)]
