"""Scripted readers of the actual prompt text and component-level diagnostics.

The existing evaluator remains authoritative for factual recall and writer fidelity.
The additional hypothesis-status task is a development diagnostic, not a change to
the Stage 1 endpoint. Readers see text and questions only, never evaluator keys.
"""
import json
import re

from research.evidence_memory_v1 import fidelity as F, protocol as P, readers as RD, render as R, schema as S
from research.evidence_memory_v1 import stage1

STATUSES = ('hypothesis_only', 'contradicted', 'no_evidence')


def _action(text):
    match = re.search(r'ACTION(\d+)\(([^)]*)\)', text)
    if not match:
        raise ValueError('action missing from rendered evidence')
    data = match[2]
    if data in ('', 'no arguments'):
        data = {}
    elif data == 'any arguments' or data == 'any':
        data = 'any'
    else:
        data = {k: int(v) for k, v in (p.split('=') for p in data.split(','))}
    return {'action_id': int(match[1]), 'action_data': data}


def parse(text):
    """Read only the existing human-readable renderings (no hidden record objects)."""
    entries = []
    for line in text.splitlines():
        if line.startswith('step '):
            parts = line.split(' | ')
            if len(parts) != 8:
                raise ValueError('unexpected raw record format')
            entries.append({'kind': 'observation', 'status': 'supported',
                            'step': int(parts[0][5:]), 'level': int(parts[1][6:]),
                            'state': parts[3][6:], 'action': _action(parts[4]),
                            'value': parts[6][7:] if parts[5] == 'dispatch acknowledged' else None,
                            'scope': 'exact_state'})
        elif line.startswith('['):
            match = re.search(r'\] (observation|hypothesis)/(\w+) ', line)
            value = re.search(r'visual_effect=(\w+)', line)
            level = re.search(r'level (\d+)', line)
            state = re.search(r'in exact state ([a-f0-9]+)', line)
            if not match or not value or not level:
                raise ValueError('unexpected memory entry format')
            entries.append({'kind': match[1], 'status': match[2], 'level': int(level[1]),
                            'state': state[1] if state else None, 'action': _action(line),
                            'value': value[1], 'scope': 'exact_state' if state else
                            'level' if 'anywhere in level' in line else 'other'})
        else:
            raise ValueError('unexpected evidence line')
    return entries


def text_truth(text, question):
    entries = parse(text)
    matching = [e for e in entries if e['action'] == question['action'] and e['level'] == question['level']]
    if question['kind'] == 'recall':
        values = sorted({e['value'] for e in matching if e['kind'] == 'observation'
                         and e['status'] == 'supported' and e['value'] in RD.RECALL_VALUES
                         and e['scope'] == 'exact_state' and question['state'].startswith(e['state'])})
        return {'values': values or ['no_evidence']}
    observations = [e for e in matching if e['kind'] == 'observation' and e['value'] in P.VALUES]
    hypotheses = [e for e in matching if e['kind'] == 'hypothesis' and e['scope'] == 'level']
    if any(e['value'] != question['value'] for e in observations) or any(
            e['value'] == question['value'] and e['status'] == 'contradicted' for e in hypotheses):
        return {'status': 'contradicted'}
    if any(e['value'] == question['value'] for e in observations + hypotheses):
        # Repeated observations do not prove an everywhere-in-level mechanism.
        return {'status': 'hypothesis_only'}
    return {'status': 'no_evidence'}


def hypothesis_gold(records, question):
    """Independent supplemental key: rederive support and counterexamples from records."""
    observed = [i for i in F.facts(records).values() if i['action'] == question['action']
                and i['level'] == question['level'] and i['visual'] is not None]
    if any(i['visual'] != question['value'] for i in observed):
        return {'status': 'contradicted'}
    return {'status': 'hypothesis_only' if observed else 'no_evidence'}


def score(output, question, truth, package):
    if question['kind'] == 'recall':
        return P.score(output, question, truth['values'], package['values'])
    try:
        answer = json.loads(output, object_pairs_hook=RD._object, parse_constant=RD._reject_constant)
        valid = isinstance(answer, dict) and set(answer) == {'status'} and answer['status'] in STATUSES
    except (ValueError, TypeError):
        answer, valid = None, False
    return {'valid': valid, 'correct_truth': valid and answer == truth,
            'correct_package': valid and answer == package,
            'unsupported': valid and answer['status'] != 'no_evidence' and answer != package,
            'abstained': valid and answer['status'] == 'no_evidence', 'output': output}


def attribution(truth, full_store, selected, output, question, writer_faults=False):
    """Independent flags, not a guessed single cause inferred from answer correctness.

    Store loss/error: full writer output lacks or distorts the full-history answer.
    Selection loss: selected evidence differs from its complete source store.
    Reader error: output contradicts the evidence it was actually given.
    Several stages may fail simultaneously; an unrelated writer fault is separate.
    """
    scored = score(output, question, truth, selected)
    return {**scored, 'writer_store_loss_or_distortion': full_store != truth,
            'writer_integrity_fault_present': bool(writer_faults),
            'selection_loss_or_distortion': selected != full_store,
            'reader_error': not scored['correct_package']}


def messages(text, question):
    if question['kind'] == 'recall':
        return P.reader_messages(text, question)
    task = ('For the proposed hypothesis that ' + R.action_text(question['action']) +
            ' produces visual_effect=' + question['value'] + ' anywhere in level ' + str(question['level']) +
            ', classify the supplied evidence. A differing observed effect or an explicit contradiction means '
            'contradicted. Consistent observations or a hypothesis without a counterexample mean hypothesis_only, '
            'never an established mechanism. If neither exists, use no_evidence. '
            'Return only {"status": "hypothesis_only"}, {"status": "contradicted"}, or {"status": "no_evidence"}.')
    return [{'role': 'system', 'content': P.SYSTEM},
            {'role': 'user', 'content': 'Evidence:\n' + (text or '(none)') + '\n\n' + task}]


def request(text, question):
    if question['kind'] == 'recall':
        return stage1.build_request({'evidence': text}, {'kind': 'recall', 'question': question})
    return {'model': stage1.MODEL, 'messages': messages(text, question), 'temperature': 0, 'seed': 0,
            'max_tokens': P.MAX_TOKENS, 'chat_template_kwargs': {'enable_thinking': False},
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'evidence_memory_stress_hypothesis_status', 'strict': True,
                'schema': {'type': 'object', 'additionalProperties': False, 'required': ['status'],
                           'properties': {'status': {'type': 'string', 'enum': list(STATUSES)}}}}}}
