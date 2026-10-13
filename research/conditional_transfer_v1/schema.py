"""Conditional knowledge and strict answers. Record IDs follow transition_evidence_v2."""
import json

from research.evidence_memory_v1 import readers as RD

VERSION = 'conditional_transfer_v1'
TASKS = {
    'conditions': ('match', 'mismatch', 'unknown'),
    'target_support': ('supported', 'contradicted', 'unobserved'),
    'contradiction': ('present', 'not_observed'),
    'transfer': ('supported_local', 'unestablished', 'not_applicable', 'contradicted'),
    'evidence': ('records', 'no_evidence'),
    'update': ('retain', 'narrow', 'retire'),
}
ARMS = ('recent_history', 'retrieved_evidence', 'conditional_memory')
CEILINGS = (1024, 1536)
PRIMARY_CEILING = 1536
OUTPUT_CAP = 256


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def answer_schema(task):
    # No uniqueItems: the exact old runtime refused that decoding keyword.
    # Duplicates are still rejected by the scorer rather than repaired.
    return {'type': 'object', 'additionalProperties': False, 'required': ['answer', 'evidence_ids'],
            'properties': {'answer': {'type': 'string', 'enum': list(TASKS[task])},
                           'evidence_ids': {'type': 'array', 'maxItems': 8, 'items': {'type': 'string'}}}}


def validate_response(text, task, allowed_ids):
    if not isinstance(text, str):
        raise ValueError('response must be text')
    value = json.loads(text, object_pairs_hook=RD._object, parse_constant=RD._reject_constant)
    if not isinstance(value, dict) or set(value) != {'answer', 'evidence_ids'}:
        raise ValueError('answer fields differ from the schema')
    if not isinstance(value['answer'], str) or value['answer'] not in TASKS[task]:
        raise ValueError('answer is outside the task vocabulary')
    refs = value['evidence_ids']
    if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
        raise ValueError('evidence_ids must be strings')
    if len(refs) > 8 or len(set(refs)) != len(refs) or any(r not in allowed_ids for r in refs):
        raise ValueError('duplicate or unresolved evidence reference')
    return value


def validate_rule(rule):
    required = {'rule_id', 'statement', 'supporting_record_ids', 'action', 'preconditions', 'scope',
                'epistemic_status', 'contradictory_record_ids', 'revision_history',
                'applicability_status', 'observations'}
    if set(rule) != required:
        raise ValueError('conditional-rule fields differ from schema')
    if not isinstance(rule['rule_id'], str) or not rule['rule_id']:
        raise ValueError('rule identifier required')
    if not isinstance(rule['preconditions'], dict) or any(
            k not in ('mode', 'layout', 'appearance') or type(v) is not int
            for k, v in rule['preconditions'].items()):
        raise ValueError('observable integer preconditions required')
    if not isinstance(rule['statement'], dict) or set(rule['statement']) != {'effect'} or rule['statement']['effect'] not in (
            None, 'no_observed_change', 'changed_then_returned', 'final_frame_differs'):
        raise ValueError('unsupported statement')
    if rule['epistemic_status'] not in ('hypothesis', 'observation'):
        raise ValueError('unknown epistemic status')
    if rule['applicability_status'] not in ('candidate', 'supported_in_observed_context', 'contradicted', 'unobserved'):
        raise ValueError('unknown applicability status')
    action = rule['action']
    if set(action) != {'action_id', 'action_data'} or type(action['action_id']) is not int:
        raise ValueError('malformed action')
    if not isinstance(action['action_data'], dict) or any(type(v) is not int for v in action['action_data'].values()):
        raise ValueError('exact integer arguments required; no wildcard coordinates')
    if rule['scope']['kind'] not in ('state', 'level', 'segment'):
        raise ValueError('unsupported scope')
    scope = rule['scope']
    shape = {'level': {'kind', 'level'}, 'segment': {'kind', 'level', 'segment'}, 'state': {'kind', 'level', 'state'}}
    if set(scope) != shape[scope['kind']] or type(scope['level']) is not int or scope['level'] < 0:
        raise ValueError('scope shape or level is invalid')
    if scope['kind'] == 'segment' and (type(scope['segment']) is not int or scope['segment'] < 0):
        raise ValueError('segment must be a nonnegative integer')
    if scope['kind'] == 'state' and (not isinstance(scope['state'], str) or len(scope['state']) != 64 or
                                    any(c not in '0123456789abcdef' for c in scope['state'])):
        raise ValueError('exact state hash required')
    ids = [o['id'] for o in rule['observations']]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate observation')
    for field in ('supporting_record_ids', 'contradictory_record_ids'):
        if len(set(rule[field])) != len(rule[field]) or not set(rule[field]) <= set(ids):
            raise ValueError('unresolved rule reference')
    if any(o['action'] != action or o['conditions'] != rule['preconditions'] for o in rule['observations']):
        raise ValueError('rule broadens action or observable conditions')
    if rule['epistemic_status'] == 'observation' and len(rule['observations']) != 1:
        raise ValueError('multiple trials cannot silently become a universal observation')
    effect = rule['statement']['effect']
    by_id = {o['id']: o for o in rule['observations']}
    if any(by_id[r]['visual'] != effect or effect is None for r in rule['supporting_record_ids']):
        raise ValueError('support does not acknowledge the stated effect')
    if any(by_id[r]['visual'] is None or by_id[r]['visual'] == effect for r in rule['contradictory_record_ids']):
        raise ValueError('unknown or agreeing effect cannot be counterevidence')
    for observation in rule['observations']:
        if type(observation['step']) is not int or observation['level'] != scope['level']:
            raise ValueError('observation context differs from rule scope')
        if scope['kind'] == 'segment' and observation['segment'] != scope['segment']:
            raise ValueError('observation crosses segment scope')
        if scope['kind'] == 'state' and observation['state'] != scope['state']:
            raise ValueError('observation crosses exact state scope')
        if observation['dispatch'] != 'acknowledged' and observation['visual'] is not None:
            raise ValueError('unobserved dispatch cannot provide a visual fact')
    if [r['record_id'] for r in rule['revision_history']] != ids:
        raise ValueError('each observation requires its ordered revision receipt')
