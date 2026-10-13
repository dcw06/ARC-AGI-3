"""Source-target pairs; all keys are derived from visible evidence, never a hidden mechanic."""
import copy
import hashlib
import random

from research.transition_evidence_v1 import transition as T1
from research.transition_evidence_v2 import transition as T2

FAMILIES = ('layout_change', 'appearance_match', 'coordinate_change', 'state_dependent_rule',
            'level_reset_boundary', 'contradiction', 'unknown_outcome', 'distractor_history')
DELAYS = (0, 8, 24)
DEV_SEED = 'conditional-transfer-v1-development-2026-10-13'
DEV_GROUPS = tuple(range(6))
EVAL_GROUPS = tuple(range(100, 106))


def conditions(frame):
    # Explicitly supplied observable annotation, equal in all arms. Not hidden state.
    return {'mode': frame[0][0], 'layout': frame[0][1], 'appearance': frame[0][2]}


class Builder:
    def __init__(self, rng, episode):
        self.rng, self.episode, self.raws = rng, episode, []
        self.frame = [[rng.randrange(8) for _ in range(4)] for _ in range(4)]
        self.frame[0][:3] = [1, 2, 3]
        self.level = 0

    def observation(self):
        return {'frames': [copy.deepcopy(self.frame)], 'levels_completed': self.level,
                'state': 'NOT_FINISHED', 'full_reset': False, 'available_actions': [1, 2, 3, 4, 5, 6, 7]}

    def step(self, action, result, to=None, boundary=None, large=False):
        before = self.observation()
        if result in ('failed', 'outcome_unknown'):
            outcome = {'status': result, 'reason': 'synthetic dispatch receipt: ' + result}
        else:
            new = copy.deepcopy(to if to is not None else self.frame)
            frames = [new]
            if result == 'changed_then_returned':
                flash = copy.deepcopy(self.frame)
                x, y = action['action_data'].get('x', 2), action['action_data'].get('y', 2)
                flash[y][x] = (flash[y][x] + 1) % 16
                frames = [flash] * (32 if large else 1) + [copy.deepcopy(self.frame)]
                new = copy.deepcopy(self.frame)
            elif result == 'final_frame_differs' and to is None:
                new[3][3] = (new[3][3] + 1) % 16
                frames = [new]
            elif result not in ('no_observed_change', 'final_frame_differs'):
                raise ValueError(result)
            if boundary == 'level':
                self.level += 1
            after = self.observation()
            after.update(frames=frames, levels_completed=self.level, full_reset=boundary == 'reset')
            outcome = {'status': 'acknowledged', 'after': after}
            self.frame = new
        raw = {'identity': {'episode_id': self.episode, 'action_index': len(self.raws)},
               'before': before, 'proposal': copy.deepcopy(action), 'dispatched': copy.deepcopy(action),
               'outcome': outcome, 'environment_source': 'synthetic_conditional_transfer_development'}
        self.raws.append(raw)
        return len(self.raws)-1


def action(x=1, y=1):
    return {'action_id': 6, 'action_data': {'x': x, 'y': y}}


def build(family, group=0, delay=0, split='development', seed=DEV_SEED):
    if family not in FAMILIES or delay not in DELAYS:
        raise ValueError('unknown family or distractor delay')
    if split == 'development' and (group not in DEV_GROUPS or seed != DEV_SEED):
        raise ValueError('development identity is frozen')
    if split == 'evaluation' and (group not in EVAL_GROUPS or seed == DEV_SEED or not seed):
        raise ValueError('evaluation requires reserved groups and a fresh private seed')
    if split not in ('development', 'evaluation'):
        raise ValueError('partition')
    # Delays share one underlying source-target scenario and one split.
    sid = hashlib.sha256(f'{seed}/{family}/{group}'.encode()).hexdigest()[:12]
    rng = random.Random(sid)
    b = Builder(rng, 'ct-' + sid)
    source = copy.deepcopy(b.frame)
    exact = action(rng.randrange(1, 4), rng.randrange(1, 4))
    first = b.step(exact, 'changed_then_returned')
    b.step(exact, 'changed_then_returned')  # redundant support: one record can suffice
    records = T2.history(b.raws)
    proposed = {'rule_id': 'rule-' + sid, 'effect': 'changed_then_returned', 'action': exact,
                'preconditions': {'mode': 1},
                'scope': {'kind': 'level', 'level': 0}, 'epistemic_status': 'hypothesis'}
    target = copy.deepcopy(source)
    proposed_action = copy.deepcopy(exact)
    ordinal = (DEV_GROUPS if split == 'development' else EVAL_GROUPS).index(group)
    category = ordinal % 3  # same balanced categories in each disjoint partition
    if family == 'layout_change':
        proposed['preconditions']['layout'] = 2
        proposed['scope'] = {'kind': 'state', 'level': 0, 'state': T1.frame_sha256(source)}
        if category == 1:
            target[0][1] = 7
        elif category == 2:
            target[3][3] = (target[3][3]+1) % 16  # preconditions match, exact state differs
    elif family == 'appearance_match':
        proposed['preconditions'] = {'appearance': 3}
        target[3][0] = (target[3][0]+1) % 16
    elif family == 'coordinate_change':
        if category != 0:
            proposed_action = action(exact['action_data']['x'] % 3 + 1, exact['action_data']['y'])
    elif family == 'state_dependent_rule':
        if category == 1:
            target[0][0] = 0
    elif family == 'level_reset_boundary':
        proposed['scope'] = {'kind': 'segment', 'level': 0, 'segment': 0}

    for n in range(delay):
        b.step({'action_id': 1 + n % 4, 'action_data': {}}, 'no_observed_change')

    if family in ('appearance_match', 'level_reset_boundary', 'unknown_outcome') or (
            category == 2 and family != 'coordinate_change'):
        b.step({'action_id': 0, 'action_data': {}}, 'final_frame_differs' if target != b.frame else 'no_observed_change',
               to=target, boundary='reset' if family == 'level_reset_boundary' and ordinal >= 3 else 'level')
    elif target != b.frame:
        b.step({'action_id': 7, 'action_data': {}}, 'final_frame_differs', to=target)

    # A supplied target trial has known before-observation; it is not a hidden future outcome.
    if category == 0:
        b.step(proposed_action, 'changed_then_returned')
    elif category == 1:
        b.step(proposed_action, 'no_observed_change')
    elif family == 'unknown_outcome':
        b.step(proposed_action, 'failed' if ordinal >= 3 else 'outcome_unknown')
    # Category 2 elsewhere supplies no target confirmation at all.

    b.step({'action_id': 7, 'action_data': {}}, 'changed_then_returned',
           large=family == 'distractor_history' and ordinal >= 3)
    current = b.observation()
    records = T2.history(b.raws)
    if T2.verify_history(records, b.raws):
        raise ValueError('record contract mismatch: ' + str(T2.verify_history(records, b.raws)))
    target_view = {'observation_id': 'target-' + sid, 'state': T1.frame_sha256(current['frames'][-1]),
                   'level': current['levels_completed'], 'segment': records[-1]['segment'],
                   'conditions': conditions(current['frames'][-1]), 'action': proposed_action,
                   'frame': current['frames'][-1], 'available_actions': current['available_actions']}
    return {'scenario_id': sid, 'family': family, 'group': group, 'delay': delay, 'split': split,
            'raws': b.raws, 'records': records, 'proposed_rule': proposed, 'target': target_view,
            'evaluator_only': {'declared_category': category, 'source_support_step': first}}


def generate():
    return [build(f, g, d) for f in FAMILIES for g in DEV_GROUPS for d in DELAYS]
