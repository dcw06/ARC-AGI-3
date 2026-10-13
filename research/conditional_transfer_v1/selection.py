"""Task-blind current-state/recency selection; shared FINAL prompt-token maximum.

Reuse readers._fit's longest priority prefix including its stop-at-first-oversize
behaviour. Changes from old protocol: an explicit prompt ceiling and atomic
qualified rule groups. No query/task/key/family is used in ranking.
"""
from research.evidence_memory_v1 import readers as RD
from . import render as R, schema as S


def select(case, store, arm, ceiling, tokenizer):
    target = case['target']
    memory = arm == 'conditional_memory'
    if arm == 'recent_history':
        order = sorted(R.raw_items(case)[-6:], key=lambda r: -r['step'])
    elif arm == 'retrieved_evidence':
        order = sorted(R.raw_items(case), key=lambda r: (
            not (r['level'] == target['level'] and r['state'] == target['state']), -r['step']))
    elif memory:
        def rank(rule):
            obs = rule['observations']
            exact = any(o['level'] == target['level'] and o['state'] == target['state'] for o in obs)
            segment = rule['scope']['level'] == target['level'] and rule['scope']['segment'] == target['segment']
            return (0 if exact else 1 if segment else 2, -max(o['step'] for o in obs), rule['rule_id'])
        order = sorted(store, key=rank)
    else:
        raise ValueError('unknown arm')
    def size(items):
        return max(tokenizer.chat_prompt_tokens(R.request(case, task, items, memory)['messages'])
                   for task in S.TASKS)
    if size([]) > ceiling:
        raise ValueError('common prompt alone exceeds shared ceiling')
    kept = RD._fit(order, ceiling, size)
    kept = sorted(kept, key=lambda r: min(o['step'] for o in r['observations']) if memory else r['step'])
    return {'items': kept, 'memory': memory, 'max_prompt_tokens': size(kept),
            'dropped_items': len(order)-len(kept), 'eligible_items': len(order)}
