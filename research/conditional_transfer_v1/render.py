"""Common ASCII requests. Only this projection crosses the reader boundary."""
import copy
from research.evidence_memory_v1 import stage1
from . import schema as S
from .writer import source_facts

SYSTEM = (
    'Judge supplied evidence only. A rule remains a hypothesis; matching conditions do not prove transfer. '
    'Require exact action including coordinates and named preconditions. Target trials must match current '
    'state, level and segment. Only acknowledged effects count; failed/unknown is not no-change. '
    'A differing effect within original scope or the matching target is a counter; counters remain active. '
    'Transfer: mismatch=not_applicable; missing conditions=unestablished; relevant counter=contradicted; '
    'matching acknowledged target support=supported_local; otherwise unestablished. '
    'Update: original-scope counter=retire; only outside-scope target counter=narrow; otherwise retain. '
    'Contradiction absent means not_observed, not proof of absence. Evidence task lists all original-scope '
    'or current-context qualified records including unknown receipts. Other tasks cite sufficient records: '
    'conditions and transfer cite target observation; supported/contradicted cite a deciding trial; '
    'unobserved cites unknown receipt if present; update cites counter or original support if present. '
    'Return only the strict JSON answer and evidence_ids, at most 8 distinct visible references.')


def raw_items(case):
    return [{**copy.deepcopy(f), 'before_frames': raw['before']['frames'],
             'returned_frames': raw['outcome'].get('after', {}).get('frames'),
             'available_actions': raw['before']['available_actions']}
            for f, raw in zip(source_facts(case), case['raws'])]


def request(case, task, items, memory=False):
    payload = {'rule': case['proposed_rule'], 'target': case['target'], 'task': task,
               'answer_categories': list(S.TASKS[task]),
               'evidence': {'kind': 'memory' if memory else 'raw',
                            'rules' if memory else 'records': items}}
    return {'model': stage1.MODEL, 'temperature': 0, 'seed': 0, 'max_tokens': S.OUTPUT_CAP,
            'chat_template_kwargs': {'enable_thinking': False},
            'messages': [{'role': 'system', 'content': SYSTEM},
                         {'role': 'user', 'content': S.compact(payload)}],
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': S.VERSION + '_' + task, 'strict': True, 'schema': S.answer_schema(task)}}}


def allowed_ids(request_object):
    from .score import parse_request
    p, facts = parse_request(request_object)
    return {p['target']['observation_id']} | {f['id'] for f in facts}
