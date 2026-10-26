"""The instructed pilot's request plus one computed M1 evidence-memory block.

Everything else in the request is the instructed pilot's, byte for byte. The block
is rebuilt from the initial board and the observed transitions only, so a replay
reconstructs it exactly. No route, future frame, object label or role is supplied;
a moved region is a tentative match between consecutive frames.
"""
from collections import Counter
import json
from certification.phase4_multimodal_preflight_v3.images import PALETTE
from research.ls20_discovery_mac import EvidenceMemory
from research.ls20_instruction_v1.policy import make_request as instructed_request, parse

LABEL = 'Evidence memory computed from the observed frames (tentative; it can be wrong):'
NOTE = ('Deterministic evidence memory over observed frames only. Regions are same-colour connected '
        'components; x and y are inclusive native column and row ranges; colour IDs map to the RGB values '
        'in rendered_palette, as drawn in the images. A moved region is a tentative '
        'match between consecutive frames in which both copies contain changed cells; it is not a verified '
        'object, role or cause. Each moved region lists its position after the move and its displacement '
        'dx, dy in native cells. changed_cells and any_change count every changed cell, including interface '
        'cells such as a budget bar, so they can be non-zero when nothing moved; region_moved counts moves in '
        'which some region moved. displacements lists [dx, dy, count], counted per moved region, so one action '
        'can add several. recent_steps_without_moved_region is the number of latest consecutive moves in which '
        'no region moved. Changes are not evidence of progress.')
RECENT = 6

__all__ = ['make_request', 'parse', 'evidence']


def _box(region):
    top, left, bottom, right = region['bbox']
    return dict(color=region['color'], cells=len(region['cells']), x=[left, right], y=[top, bottom])


def evidence(initial, history):
    memory = EvidenceMemory('ls20-memory-evidence', initial)
    for record in history:
        memory.append(record['action'], dict(status='acknowledged', post=record['after']))
    s = memory.snapshot()
    regions = {r['id']: r for scene in s['scenes'] for r in scene['regions']}
    hints = Counter(h['evidence_ids'][0] for h in s['hypotheses'])
    moved_by_transition = {}
    for event in s['events']:
        if event['kind'] != 'computed_change' or event['transition_id'] is None:
            continue
        changed = {(r, c) for r, c, _, _ in event['changes'] or ()}
        before, after = event['before']+':', event['after']+':'
        # The same qualifying links that produced this event's hypotheses, in the same order.
        moved = [dict(_box(regions[link['after']]), dx=link['translation'][1], dy=link['translation'][0])
                 for link in s['identity_candidates']
                 if link['before'].startswith(before) and link['after'].startswith(after)
                 and link['translation'] is not None and any(link['translation'])
                 and changed.intersection(map(tuple, regions[link['before']]['cells']))
                 and changed.intersection(map(tuple, regions[link['after']]['cells']))]
        if len(moved) != hints[event['id']]:
            raise ValueError('evidence projection differs from memory hypotheses')
        moved_by_transition.setdefault(event['transition_id'], []).extend(moved)
    steps, actions = [], {}
    for index, transition in enumerate(s['transitions']):
        changes = [e['changes'] for e in s['events'] if e['kind'] == 'computed_change'
                   and e['transition_id'] == transition['id']]
        moved = moved_by_transition.get(transition['id'], [])
        step = dict(step=index, action_id=transition['action']['action_id'],
                    changed_cells=None if any(c is None for c in changes) else sum(len(c) for c in changes),
                    moved_regions=moved)
        steps.append(step)
        summary = actions.setdefault(step['action_id'], dict(taken=0, any_change=0, region_moved=0, displacements=Counter()))
        summary['taken'] += 1
        summary['any_change'] += bool(step['changed_cells'])
        summary['region_moved'] += bool(moved)
        summary['displacements'].update((m['dx'], m['dy']) for m in moved)
    streak = 0
    for step in reversed(steps):
        if step['moved_regions']:
            break
        streak += 1
    return dict(schema='m1_evidence_memory_v1', note=NOTE, transitions_recorded=len(steps),
                rendered_palette={str(i): list(rgb) for i, rgb in enumerate(PALETTE)},
                current_regions=[_box(r) for r in s['scenes'][-1]['regions']],
                recent_transitions=steps[-RECENT:],
                action_summary=[dict(action_id=a, taken=v['taken'], any_change=v['any_change'],
                                     region_moved=v['region_moved'],
                                     displacements=[[dx, dy, n] for (dx, dy), n in
                                                    sorted(v['displacements'].items(), key=lambda kv: (-kv[1], kv[0]))[:3]])
                                for a, v in sorted(actions.items())],
                recent_steps_without_moved_region=streak)


def make_request(initial, current, history, instructions):
    body = instructed_request(initial, current, history, instructions)
    if (history[-1]['after'] if history else initial) != current:
        raise ValueError('current observation differs from the observed history')
    block = json.dumps(evidence(initial, history), sort_keys=True, separators=(',', ':'), allow_nan=False)
    body['messages'][1]['content'].insert(2, {'type': 'text', 'text': LABEL+'\n'+block})
    return body
