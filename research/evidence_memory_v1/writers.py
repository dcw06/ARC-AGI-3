"""Scripted memory writers and the writer harness (Track 2, evidence_memory_v1). No model is called.

A writer sees the records so far (the newest last) and the current memory view, and returns text: the output a
model would produce, `{"operations": [...]}`. The harness parses it and applies each operation to the audited
store. Every writer call is charged (calls, input characters, output characters). Unparseable outputs and rejected
operations are retained in the log, never dropped.

Scripted writers (fake model outputs, for validating the checker and harness, not for estimating model quality):
- faithful: exact-state observations, level-scoped hypotheses once an action has been seen in two states, and a
  segment-scoped "tried here without change" working set retired when the segment ends;
- lossy: faithful, but retires the oldest observations beyond a fixed number of entries;
- overclaiming: records unobserved outcomes as "no change", generalises repeated no-change to any arguments,
  and never records counterexamples;
- scope_violating: writes mechanisms as cross-level, and never retires state-dependent entries;
- invalid: faithful, but every third output is prose and every fifth carries a numeric confidence.

`gate=True` is a separate treatment: every add or revise is checked mechanically (schema.check) before it is
stored; a failing operation is rejected and logged.
"""
import copy
import json

from research.evidence_memory_v1 import render as R, schema as S


def action_key(action):
    data = action['action_data']
    if data == S.ANY:
        return f"a{action['action_id']}-any"
    return f"a{action['action_id']}" + ''.join(f'-{k}{data[k]}' for k in sorted(data))


def new_entry(entry_id, kind, claim, scope, status, evidence, counter, step, reason):
    return {'id': entry_id, 'kind': kind, 'claim': claim, 'scope': scope, 'status': status, 'evidence': evidence,
            'counterevidence': counter, 'last_reviewed_step': step, 'revision': 1, 'supersedes': None,
            'reason': reason}


def status_for(scope, infos, counter):
    if counter:
        return S.CONTRADICTED
    states = {(i['level'], i['state']) for i in infos}
    enough = len(infos) >= 2 if scope['kind'] == S.EXACT_STATE else len(states) >= 2
    return S.SUPPORTED if enough and scope['kind'] != S.CROSS_LEVEL else S.TENTATIVE


class Faithful:
    name = 'faithful'
    record_conflicts = True

    def __call__(self, records, view):
        return json.dumps({'operations': self.operations(records, view)})

    def operations(self, records, view):
        idx = S.index(records)
        info = idx[S.key(S.ref_of(records[-1]))]
        entries = {e['id']: e for e in view['entries'] if e['status'] != S.RETIRED}
        ops = self.on_boundary(entries, info)
        for op in ops:
            entries.pop(op['id'], None)
        if info['visual'] is None:
            return ops + self.on_unobserved(info)
        ops += self.observe(entries, info)
        ops += self.hypothesize(entries, idx, info)
        return ops

    def on_boundary(self, entries, info):
        return [{'op': 'retire', 'id': e['id'], 'expected_revision': e['revision'],
                 'reason': 'the segment ended (reset, level change or terminal); this conclusion depended on its state'}
                for e in entries.values() if e['scope']['kind'] == S.SEGMENT and (
                    e['scope']['segment'] < info['segment'] or info['ends_segment'])]

    def on_unobserved(self, info):
        return []  # an unobserved outcome supports no factual claim

    def observe(self, entries, info):
        claim = {'action': info['action'], 'predicate': 'visual_effect', 'value': info['visual']}
        scope = {'kind': S.EXACT_STATE, 'level': info['level'], 'state_sha256': info['state']}
        for e in entries.values():
            if e['kind'] == S.OBSERVATION and e['claim'] == claim and e['scope'] == scope:
                return [{'op': 'revise', 'id': e['id'], 'expected_revision': e['revision'], 'reason': 'repeated',
                         'changes': {'evidence': e['evidence'] + [info['ref']], 'last_reviewed_step': info['step']}}]
        return [{'op': 'add', 'reason': 'observed', 'entry': new_entry(
            f"obs-{info['step']}", S.OBSERVATION, claim, scope, S.SUPPORTED, [info['ref']], [], info['step'],
            'reconstructed from the cited transition')}]

    def fold(self, entry, idx, info):
        agrees = S.outcome(info, entry['claim']) == 'agrees'
        if not agrees and not self.record_conflicts:
            return []
        evidence = entry['evidence'] + ([info['ref']] if agrees else [])
        counter = entry['counterevidence'] + ([] if agrees else [info['ref']])
        status = status_for(entry['scope'], [idx[S.key(r)] for r in evidence], counter)
        reason = 'consistent observation' if agrees else f"step {info['step']} contradicts it in scope"
        return [{'op': 'revise', 'id': entry['id'], 'expected_revision': entry['revision'], 'reason': reason,
                 'changes': {'evidence': evidence, 'counterevidence': counter, 'status': status,
                             'last_reviewed_step': info['step'], 'reason': reason}}]

    def mechanism_scope(self, info):
        return {'kind': S.LEVEL, 'level': info['level']}

    def propose(self, hid, idx, info, scope, reason, value=None):
        """A new hypothesis from every seen in-scope record of this action, conflicts included."""
        same = sorted((i for i in idx.values() if S.subject_matches(i, info['action']) and S.in_scope(i, scope)
                       and i['visual'] is not None), key=lambda i: i['step'])
        claim = {'action': info['action'], 'predicate': 'visual_effect', 'value': value or same[0]['visual']}
        ev = [i for i in same if S.outcome(i, claim) == 'agrees']
        ce = [i['ref'] for i in same if S.outcome(i, claim) == 'conflicts'] if self.record_conflicts else []
        return {'op': 'add', 'reason': reason, 'entry': new_entry(
            hid, S.HYPOTHESIS, claim, scope, status_for(scope, ev, ce), [i['ref'] for i in ev], ce, info['step'], reason)}

    def hypothesize(self, entries, idx, info):
        ops = []
        scope = self.mechanism_scope(info)
        hid = f"hyp-{scope['kind']}-L{scope.get('level', 'x')}-{action_key(info['action'])}"
        if hid in entries:
            ops += self.fold(entries[hid], idx, info)
        elif len({i['state'] for i in idx.values() if S.subject_matches(i, info['action']) and S.in_scope(i, scope)
                  and i['visual'] is not None}) >= 2:
            ops.append(self.propose(hid, idx, info, scope, 'the same action seen in more than one state'))
        sid = f"seg-{info['segment']}-{action_key(info['action'])}"
        if sid in entries:
            ops += self.fold(entries[sid], idx, info)
        elif info['visual'] == 'no_observed_change' and not info['ends_segment']:  # the "tried here" working set
            scope = {'kind': S.SEGMENT, 'level': info['level'], 'segment': info['segment']}
            ops.append(self.propose(sid, idx, info, scope, 'state-dependent: holds for this segment only',
                                    'no_observed_change'))
        return ops


class Lossy(Faithful):
    name = 'lossy'
    cap = 4

    def operations(self, records, view):
        ops = super().operations(records, view)
        observations = sorted((e for e in view['entries'] if e['kind'] == S.OBSERVATION and e['status'] != S.RETIRED),
                              key=lambda e: e['last_reviewed_step'])
        touched = {op.get('id') for op in ops}
        excess = len(observations) + sum(op['op'] == 'add' and op['entry']['kind'] == S.OBSERVATION for op in ops) - self.cap
        for e in [e for e in observations if e['id'] not in touched][:max(excess, 0)]:
            ops.append({'op': 'retire', 'id': e['id'], 'expected_revision': e['revision'],
                        'reason': 'dropped to keep memory short'})
        return ops


class Overclaiming(Faithful):
    name = 'overclaiming'
    record_conflicts = False

    def on_unobserved(self, info):
        return [{'op': 'add', 'reason': 'nothing happened', 'entry': new_entry(
            f"obs-{info['step']}", S.OBSERVATION,
            {'action': info['action'], 'predicate': 'visual_effect', 'value': 'no_observed_change'},
            {'kind': S.EXACT_STATE, 'level': info['level'], 'state_sha256': info['state']}, S.SUPPORTED,
            [info['ref']], [], info['step'], 'nothing happened')}]

    def hypothesize(self, entries, idx, info):
        ops = super().hypothesize(entries, idx, info)
        broad = {'action_id': info['action']['action_id'], 'action_data': S.ANY}
        hid = f"hyp-any-L{info['level']}-{action_key(broad)}"
        same = [i for i in idx.values() if i['level'] == info['level'] and S.subject_matches(i, broad)
                and i['visual'] == 'no_observed_change']
        if hid not in entries and info['visual'] == 'no_observed_change' and len(same) >= 2:
            ops.append({'op': 'add', 'reason': 'it never works', 'entry': new_entry(
                hid, S.HYPOTHESIS, {'action': broad, 'predicate': 'visual_effect', 'value': 'no_observed_change'},
                {'kind': S.LEVEL, 'level': info['level']}, S.SUPPORTED, [i['ref'] for i in same], [], info['step'],
                'repeated attempts failed')})
        return ops


class ScopeViolating(Faithful):
    name = 'scope_violating'

    def on_boundary(self, entries, info):
        return []

    def mechanism_scope(self, info):
        return {'kind': S.CROSS_LEVEL}

    def hypothesize(self, entries, idx, info):
        ops = super().hypothesize(entries, idx, info)
        for op in ops:
            if op['op'] == 'add' and op['entry']['scope']['kind'] == S.CROSS_LEVEL and not op['entry']['counterevidence']:
                op['entry']['status'] = S.SUPPORTED
        return ops


class Invalid(Faithful):
    name = 'invalid'

    def __init__(self):
        self.calls = 0

    def __call__(self, records, view):
        self.calls += 1
        if self.calls % 3 == 0:
            return 'I think the last action probably did nothing, so I will remember that.'
        ops = self.operations(records, view)
        if self.calls % 5 == 0:
            for op in ops:
                if op['op'] == 'add':
                    op['entry']['confidence'] = 0.9
        return json.dumps({'operations': ops})


WRITERS = {w.name: w for w in (Faithful, Lossy, Overclaiming, ScopeViolating, Invalid)}


def _apply(memory, op, step):
    kind = op['op']
    if kind == 'add':
        memory.add(op['entry'], step, op['reason'])
        return op['entry']['id']
    if kind == 'revise':
        memory.revise(op['id'], op['expected_revision'], op['changes'], step, op['reason'])
    elif kind == 'retire':
        memory.retire(op['id'], op['expected_revision'], step, op['reason'])
    elif kind == 'review':
        memory.review(op['id'], op['expected_revision'], step, op['reason'])
    else:
        raise S.OperationError(f'unknown operation {kind!r}')
    return op['id']


def run_writer(writer, trajectory, gate=False):
    """Run one writer over a trajectory, one charged call per transition."""
    records = trajectory['records']
    idx = S.index(records)
    memory, log = S.Memory(), []
    charge = {'writer_calls': 0, 'input_chars': 0, 'output_chars': 0}
    for step in range(len(records)):
        seen = records[:step + 1]
        view = memory.view()
        prompt = R.record_line(seen[-1], idx[S.key(S.ref_of(seen[-1]))]) + '\n' + R.memory_text(view['entries'])
        output = writer(seen, view)
        charge['writer_calls'] += 1
        charge['input_chars'] += len(prompt)
        charge['output_chars'] += len(output)
        try:
            ops = json.loads(output)['operations']
            if not isinstance(ops, list):
                raise TypeError('operations is not a list')
        except (ValueError, KeyError, TypeError) as exc:
            log.append({'step': step, 'kind': 'invalid_output', 'output': output, 'error': f'{type(exc).__name__}: {exc}'})
            continue
        for op in ops:
            trial = copy.deepcopy(memory) if gate else memory
            try:
                entry_id = _apply(trial, op, step)
                if gate and op['op'] in ('add', 'revise'):
                    entry = trial.entries[entry_id]
                    problems = S.check(entry, S.seen(idx, step))
                    if entry['last_reviewed_step'] > step:
                        problems.append('dangling_reference: reviewed at a step not yet seen')
                    if problems:
                        raise S.OperationError('gate: ' + '; '.join(problems))
                memory = trial
            except (S.OperationError, KeyError, TypeError) as exc:
                log.append({'step': step, 'kind': 'rejected_operation', 'operation': op, 'error': str(exc)})
    return {'writer': writer.name, 'gate': gate, 'memory': memory.view(), 'log': log, 'charge': charge}
