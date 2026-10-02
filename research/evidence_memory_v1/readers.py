"""Decision readers, context packages and context pressure (Track 2, evidence_memory_v1). No model is called.

Packages compared under one character budget (the budget is the rendered length of the frozen recent window):
- recent_raw: the last WINDOW transition records (the baseline; WINDOW is frozen before any comparison);
- state_keyed_raw: a control. Raw records whose (level, state) equals the current one, then the most recent
  others, in the same budget. It separates "retrieval by current state" from "structured memory";
- memory: non-retired entries ranked by how specifically their scope covers the current state (exact state,
  segment, object instance, level, cross-level, then the rest), then by last review, in the same budget. The memory package is writer + store + selection + rendering together: a comparison of packages, not of
  formatting.

Selection is keyed on the current state at the end of the trajectory, never on the question.

Readers return text, as a model would: recall `{"values": [...]}`, decision `{"choice": action}`. The oracle
readers answer exactly from what their package contains; they measure information availability, not model
ability. Scripted readers (faithful, status-blind, invalid) validate the reader harness with known behaviour.
"""
import json

from research.evidence_memory_v1 import fidelity as F, render as R, schema as S, trajectories as TR, writers as W

WINDOW = 6  # frozen: the recent-raw-history baseline window, in transitions


def current_state(trajectory):
    """(level, frame SHA-256) after the last transition, as its record reports them."""
    last = trajectory['records'][-1]
    frames = last['measurements']['frames']
    if last['dispatch']['status'] != 'acknowledged' or not frames or not frames[-1]['valid']:
        raise ValueError('the current state is unobserved after the last transition')
    return last['environment']['reported']['levels_completed_after'], frames[-1]['sha256']


def _fit(lines, budget):
    kept, used = [], 0
    for item, line in lines:
        if used + len(line) + 1 > budget + 1:
            break
        kept.append((item, line))
        used += len(line) + 1
    return kept


def rank(entry, level, state, segment):
    """Selection rank by how specifically the entry's scope covers the current state (0 = exact state);
    5 = does not cover it."""
    scope = entry['scope']
    if scope['kind'] == S.CROSS_LEVEL:
        return 4
    if scope.get('level') != level:
        return 5
    return {S.EXACT_STATE: 0 if scope.get('state_sha256') == state else 5,
            S.SEGMENT: 1 if scope.get('segment') == segment else 5, S.OBJECT_INSTANCE: 2, S.LEVEL: 3}[scope['kind']]


def packages(trajectory, memory_view, window=WINDOW):
    records = trajectory['records']
    idx = S.index(records)
    level, state = current_state(trajectory)
    segment = records[-1]['segment'] + bool(set(records[-1]['environment']['events']) & {
        'reset_acknowledged', 'level_completed', 'level_count_decreased', 'terminal_state'})
    recent = records[-window:]
    budget = len(R.records_text(recent, idx))
    line = lambda r: R.record_line(r, idx[S.record_key(r)])
    order = sorted(records, key=lambda r: (not (idx[S.record_key(r)]['level'] == level and
                                                idx[S.record_key(r)]['state'] == state), -r['identity']['action_index']))
    keyed = sorted((r for r, _ in _fit([(r, line(r)) for r in order], budget)), key=lambda r: r['identity']['action_index'])
    entries = sorted((e for e in memory_view['entries'] if e['status'] != S.RETIRED),
                     key=lambda e: (rank(e, level, state, segment), -e['last_reviewed_step'], e['id']))
    kept = [e for e, _ in _fit([(e, R.entry_line(e)) for e in entries], budget)]
    return {'budget_chars': budget, 'current': {'level': level, 'state': state},
            'recent_raw': {'records': recent, 'chars': budget},
            'state_keyed_raw': {'records': keyed, 'chars': len(R.records_text(keyed, idx))},
            'memory': {'entries': kept, 'chars': len(R.memory_text(kept)), 'dropped': len(entries) - len(kept),
                       'unbounded_chars': len(R.memory_text(entries))}}


def _memory_values(entries, question, action):
    return sorted({e['claim']['value'] for e in entries if e['kind'] == S.OBSERVATION and e['status'] == S.SUPPORTED
                   and e['scope']['kind'] == S.EXACT_STATE and e['scope']['level'] == question['level']
                   and e['scope']['state_sha256'] == question['state'] and e['claim']['action'] == action})


def _answer(values_of, question):
    if question['kind'] == 'recall':
        return {'values': values_of(question['action']) or ['no_evidence']}
    changed = [c for c in question['candidates'] if 'final_frame_differs' in values_of(c)]
    pool = changed or [c for c in question['candidates'] if 'no_observed_change' not in values_of(c)]
    return {'choice': pool[0] if pool else None}


def oracle_raw(records):
    def read(question):
        values = lambda a: [v for v in F.gold(records, {**question, 'kind': 'recall', 'action': a}) if v != 'no_evidence']
        return json.dumps(_answer(values, question))
    return read


def oracle_memory(entries):
    return lambda question: json.dumps(_answer(lambda a: _memory_values(entries, question, a), question))


def status_blind(entries):
    """Uses any entry about the action in the current level as a fact, whatever its kind, status or scope."""
    def values(question, action):
        exact = _memory_values(entries, question, action)
        if exact:
            return exact
        return sorted({e['claim']['value'] for e in entries if e['claim']['action']['action_id'] == action['action_id']
                       and e['claim']['action']['action_data'] in (S.ANY, action['action_data'])
                       and e['scope'].get('level', question['level']) == question['level']})
    return lambda question: json.dumps(_answer(lambda a: values(question, a), question))


def invalid(entries):
    return lambda question: 'Probably the first one.'


READERS = {'faithful': oracle_memory, 'status_blind': status_blind, 'invalid': invalid}


RECALL_VALUES = ('no_observed_change', 'changed_then_returned', 'final_frame_differs', 'no_evidence')


class ResponseError(ValueError):
    pass


def _object(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ResponseError('a key is repeated')
    return dict(pairs)


def _reject_constant(name):
    raise ResponseError(f'{name} is not allowed')


def _action(value):
    """Strict action: exactly {action_id: int, action_data: {str: int}}; bool and float are not integers."""
    if not isinstance(value, dict) or set(value) != {'action_id', 'action_data'}:
        raise ResponseError('an action has exactly action_id and action_data')
    if type(value['action_id']) is not int:
        raise ResponseError('action_id must be an integer')
    data = value['action_data']
    if not isinstance(data, dict) or not all(isinstance(k, str) and type(v) is int for k, v in data.items()):
        raise ResponseError('action_data maps names to integers')
    return value


def validate_response(output, question):
    """The parsed answer when `output` matches the response schema exactly; raises ResponseError otherwise.
    recall: {"values": [one or more distinct allowed values]}, with "no_evidence" only on its own.
    decision: {"choice": one of the question's candidate actions}."""
    if not isinstance(output, str):
        raise ResponseError('the output is not text')
    try:
        answer = json.loads(output, object_pairs_hook=_object, parse_constant=_reject_constant)
    except ResponseError:
        raise
    except ValueError as exc:
        raise ResponseError(f'not JSON: {exc}') from None
    if question['kind'] == 'recall':
        if not isinstance(answer, dict) or set(answer) != {'values'}:
            raise ResponseError('a recall answer is exactly {"values": [...]}')
        values = answer['values']
        if not isinstance(values, list) or not values:
            raise ResponseError('values is a non-empty list')
        if not all(isinstance(v, str) and v in RECALL_VALUES for v in values) or len(set(values)) != len(values):
            raise ResponseError('values are distinct allowed values')
        if 'no_evidence' in values and len(values) > 1:
            raise ResponseError('no_evidence stands alone')
        return answer
    if not isinstance(answer, dict) or set(answer) != {'choice'}:
        raise ResponseError('a decision answer is exactly {"choice": action}')
    if _action(answer['choice']) not in question['candidates']:
        raise ResponseError('the choice is not one of the candidates')
    return answer


def score(output, question, gold):
    """Schema first: a response that does not match exactly is invalid (retained, never scored correct)."""
    try:
        answer = validate_response(output, question)
    except ResponseError as exc:
        return {'valid': False, 'correct': False, 'output': output, 'error': str(exc)}
    if question['kind'] == 'recall':
        return {'valid': True, 'correct': sorted(answer['values']) == sorted(gold)}
    return {'valid': True, 'correct': answer['choice'] in gold}


def ask(trajectory, read):
    rows = []
    for n, question in enumerate(trajectory['evaluator_only']['expected']['questions']):
        q = {k: v for k, v in question.items() if k != 'expected_answer'}  # the reader never sees the answer
        gold = F.gold(trajectory['records'], q)
        rows.append({'trajectory': trajectory['id'], 'question': n, 'kind': q['kind'], **score(read(q), q, gold)})
    return rows


def relevant_in_window(trajectory, window=WINDOW):
    expected = trajectory['evaluator_only']['expected']
    return min(expected['relevant_steps']) > expected['final_step'] - window


def pressure(delays=(0, 2, 4, 6, 8, 12, 16), count=2, window=WINDOW, families=None):
    """Information availability by delay: oracle accuracy per package at one character budget. A forgetting problem
    exists only where recent_raw loses answers that the full history supports."""
    rows = []
    for delay in delays:
        for family in families or TR.FAMILIES:
            for i in range(count):
                t = TR.build(family, i, delay)
                memory = W.run_writer(W.Faithful(), t)['memory']
                p = packages(t, memory, window)
                row = {'delay': delay, 'family': family, 'trajectory': t['id'], 'relevant_in_window': relevant_in_window(t, window),
                       'budget_chars': p['budget_chars'], 'memory_unbounded_chars': p['memory']['unbounded_chars'],
                       'memory_dropped_entries': p['memory']['dropped']}
                for name, read in (('full_history', oracle_raw(t['records'])), ('recent_raw', oracle_raw(p['recent_raw']['records'])),
                                   ('state_keyed_raw', oracle_raw(p['state_keyed_raw']['records'])),
                                   ('memory', oracle_memory(p['memory']['entries'])),
                                   ('memory_unbounded', oracle_memory(memory['entries']))):
                    answers = ask(t, read)
                    row[name] = sum(a['correct'] for a in answers) / len(answers)
                rows.append(row)
    return rows
