"""Independent keys: inspect original grids/dispatch receipts, not memory or reader code.

No import of fixtures, writer, score, selection or render. The separately written
decision table is intentionally redundant so agreement is a construction gate.
"""
import hashlib
import json


def derive_facts(raws):
    facts, segment, ended = [], 0, False
    for raw in raws:
        if ended:
            segment += 1
        before, receipt = raw['before'], raw['outcome']
        frame = before['frames'][-1]
        status = receipt['status']
        visual, events, ended = None, None, False
        if status == 'acknowledged':
            after = receipt['after']
            changed = [f != frame for f in after['frames']]
            visual = ('final_frame_differs' if changed[-1] else
                      'changed_then_returned' if any(changed) else 'no_observed_change')
            events = []
            if after['levels_completed'] > before['levels_completed']:
                events.append('level_completed')
            elif after['levels_completed'] < before['levels_completed']:
                events.append('level_count_decreased')
            if after.get('state') not in (None, 'NOT_FINISHED'):
                events.append('terminal_state')
            if after.get('full_reset'):
                events.append('reset_acknowledged')
            ended = bool(events)
            events = events or ['none_reported']
        ident = raw['identity']
        facts.append({'id': ident['episode_id'] + '#' + str(ident['action_index']),
                      'step': ident['action_index'], 'level': before['levels_completed'],
                      'segment': segment,
                      'state': hashlib.sha256(json.dumps(frame, separators=(',', ':')).encode()).hexdigest(),
                      'action': raw['dispatched'],
                      'conditions': dict(zip(('mode', 'layout', 'appearance'), frame[0][:3])),
                      'dispatch': status, 'visual': visual, 'events': events})
    return facts


def keys(case):
    facts = derive_facts(case['raws'])
    rule, t = case['proposed_rule'], case['target']
    last = case['raws'][-1]
    observation = last['outcome'].get('after', last['before'])
    frame = observation['frames'][-1]
    measured_target = {
        'frame': frame, 'level': observation['levels_completed'],
        'state': hashlib.sha256(json.dumps(frame, separators=(',', ':')).encode()).hexdigest(),
        'conditions': dict(zip(('mode', 'layout', 'appearance'), frame[0][:3])),
        'available_actions': observation['available_actions'],
        'segment': facts[-1]['segment'] + int(bool(set(facts[-1]['events'] or []) & {
            'level_completed', 'level_count_decreased', 'reset_acknowledged', 'terminal_state'}))}
    if any(t[k] != value for k, value in measured_target.items()):
        raise ValueError('target observable annotation differs from raw evidence')
    qualified, original, current = [], [], []
    for f in facts:
        if f['action'] != rule['action']:
            continue
        if any(f['conditions'].get(k) != v for k, v in rule['preconditions'].items()):
            continue
        qualified.append(f)
        scope = rule['scope']
        if f['level'] == scope['level']:
            scope_ok = {'level': True, 'state': f['state'] == scope.get('state'),
                        'segment': f['segment'] == scope.get('segment')}[scope['kind']]
            if scope_ok:
                original.append(f)
        if (f['level'], f['state'], f['segment']) == (t['level'], t['state'], t['segment']):
            current.append(f)
    if any(k not in t['conditions'] for k in rule['preconditions']):
        condition = 'unknown'
    else:
        condition = 'match'
        if t['action'] != rule['action'] or any(t['conditions'][k] != v for k, v in rule['preconditions'].items()):
            condition = 'mismatch'
    orig_good, orig_bad, cur_good, cur_bad, cur_missing = [], [], [], [], []
    for f in original:
        if f['visual'] == rule['effect']:
            orig_good.append(f['id'])
        elif f['visual'] is not None:
            orig_bad.append(f['id'])
    if condition == 'match':
        for f in current:
            if f['visual'] is None:
                cur_missing.append(f['id'])
            elif f['visual'] == rule['effect']:
                cur_good.append(f['id'])
            else:
                cur_bad.append(f['id'])
    all_bad = sorted(set(orig_bad) | set(cur_bad))
    all_relevant = [f['id'] for f in qualified if f in original or f in current]
    target_id = [t['observation_id']]
    support_answer = 'unobserved'
    support_refs = []
    if cur_good:
        support_answer, support_refs = 'supported', [cur_good]
    if cur_bad:
        support_answer, support_refs = 'contradicted', [cur_bad]
    if not cur_good and not cur_bad and cur_missing:
        support_refs = [cur_missing]
    transfer_answer, transfer_refs = 'unestablished', [target_id]
    if condition == 'mismatch':
        transfer_answer = 'not_applicable'
    elif condition == 'match':
        if all_bad:
            transfer_answer, transfer_refs = 'contradicted', [target_id, all_bad]
        elif cur_good:
            transfer_answer, transfer_refs = 'supported_local', [target_id, cur_good]
        elif cur_missing:
            transfer_refs = [target_id, cur_missing]
    update_answer, update_refs = 'retain', [orig_good] if orig_good else []
    if cur_bad:
        update_answer, update_refs = 'narrow', [cur_bad]
    if orig_bad:
        update_answer, update_refs = 'retire', [orig_bad]
    table = {'conditions': (condition, [target_id]),
             'target_support': (support_answer, support_refs),
             'contradiction': ('present' if all_bad else 'not_observed', [all_bad] if all_bad else []),
             'transfer': (transfer_answer, transfer_refs),
             'evidence': ('records' if all_relevant else 'no_evidence', [[r] for r in all_relevant]),
             'update': (update_answer, update_refs)}
    return {name: {'answer': a, 'required_groups': refs,
                   'eligible_ids': sorted({r for group in refs for r in group})}
            for name, (a, refs) in table.items()}
