"""Continuous synthetic diagnostic trajectories for evidence-linked memory (Track 2, evidence_memory_v1).

Each trajectory is one continuous episode of raw transitions in the contract's raw input format, turned into
records by `research.transition_evidence_v2.transition.history` (frozen format, consumed read-only, no masks):
version 1 records plus `identity.record_id` and `context`. The construction hashes frames with the contract's
`transition_evidence_v1.transition.frame_sha256`. Nothing here is real-game data, and no action id has a game
meaning. The raws do not report available actions, so those v2 fields are `absent`.

Families (each takes `delay`, the number of distractor transitions placed between the relevant evidence and the
question or the decisive later evidence):
- early_crucial: an effective action is observed early in state S0; distractors follow; a reset returns to S0.
- supported_then_contradicted: an action changes the frame in two states, then does not in a later state.
- similar_states: two states differing in one cell give the same action different outcomes.
- coordinate_specific: three coordinates do nothing, a fourth changes the frame, all in one state.
- reset_keeps_mechanism: a reset changes the state but not the level-scoped mechanism.
- level_change: a rule supported in level 0 does not hold in level 1.
- unknown_outcome: failed and unknown dispatches that cannot support any factual claim.

Evaluator-only expectations are derived from the construction (which states were visited, which steps were
effective), kept apart from the raw transitions, and never shown to a writer or reader. Only a development
partition exists in v1. An evaluation partition must use a different seed, be generated after the protocol is
frozen, and stay withheld; it is deliberately not implemented here.
"""
import copy
import hashlib
import json
import random

from research.transition_evidence_v1 import transition as T1
from research.transition_evidence_v2 import transition as T2

VERSION = 'evidence_memory_v1_trajectories'
PARTITION, SEED = 'development', 'evidence-memory-v1-development'
SOURCE = 'synthetic_memory_diagnostic'
RESET_ACTION = 0
DISTRACTOR_IDS = (1, 2, 3, 4, 5, 7)


def act(action_id, **data):
    return {'action_id': action_id, 'action_data': dict(data)}


class Builder:
    def __init__(self, rng, size=8):
        self.rng = rng
        self.background = rng.randrange(16)
        self.frame = [[self.background] * size for _ in range(size)]
        for _ in range(3):
            self.frame = self.mutate(self.frame)
        self.levels, self.raws, self.construction = 0, [], []

    def mutate(self, frame, cells=None):
        """A copy of `frame` differing in a known non-empty set of cells."""
        size = len(frame)
        while True:
            x, y = self.rng.randrange(size - 1), self.rng.randrange(size - 1)
            spots = cells or [(x, y), (x + 1, y), (x, y + 1)]
            colour = self.rng.choice([c for c in range(16) if c != frame[spots[0][1]][spots[0][0]]])
            out = copy.deepcopy(frame)
            for cx, cy in spots:
                out[cy][cx] = colour
            if out != frame:
                return out

    def state(self):
        return T1.frame_sha256(self.frame)

    def observation(self, frame=None, **changes):
        value = {'frames': [copy.deepcopy(frame if frame is not None else self.frame)],
                 'levels_completed': self.levels, 'state': 'NOT_FINISHED', 'full_reset': False}
        value.update(changes)
        return value

    def step(self, action, kind, to=None):
        """Append one transition. kind: none, change, transient, level, reset, failed, unknown."""
        before = self.observation()
        if kind == 'none':
            outcome = {'status': 'acknowledged', 'after': self.observation()}
        elif kind in ('change', 'level'):
            new = copy.deepcopy(to) if to is not None else self.mutate(self.frame)
            levels = self.levels + (kind == 'level')
            outcome = {'status': 'acknowledged', 'after': self.observation(new, levels_completed=levels)}
            self.frame, self.levels = new, levels
        elif kind == 'transient':
            outcome = {'status': 'acknowledged',
                       'after': {**self.observation(), 'frames': [self.mutate(self.frame), copy.deepcopy(self.frame)]}}
        elif kind == 'reset':
            outcome = {'status': 'acknowledged', 'after': self.observation(to, full_reset=True)}
            self.frame = copy.deepcopy(to)
        elif kind == 'failed':
            outcome = {'status': 'failed', 'reason': 'request rejected before acknowledgement'}
        elif kind == 'unknown':
            outcome = {'status': 'outcome_unknown', 'reason': 'response timeout after send'}
        else:
            raise ValueError(kind)
        self.raws.append({'identity': {'episode_id': None, 'action_index': len(self.raws)}, 'before': before,
                          'proposal': copy.deepcopy(action), 'dispatched': copy.deepcopy(action),
                          'outcome': outcome, 'environment_source': SOURCE})
        self.construction.append({'kind': kind, 'action': copy.deepcopy(action)})
        return len(self.raws) - 1

    def distract(self, n, exclude):
        allowed = [i for i in DISTRACTOR_IDS if i not in exclude]
        for _ in range(n):
            self.step(act(self.rng.choice(allowed)), 'change' if self.rng.random() < 0.4 else 'none')

    def fact(self, action, value, state, level=None):
        return {'action': action, 'predicate': 'visual_effect', 'value': value, 'state': state,
                'level': self.levels if level is None else level}


def _decision(b, candidates, expected):
    return {'kind': 'decision', 'level': b.levels, 'state': b.state(), 'candidates': candidates,
            'goal': 'prefer an action observed to change the frame in this exact state; otherwise one not '
                    'observed to leave it unchanged here', 'expected_answer': expected}


def _recall(b, action, expected, state=None):
    return {'kind': 'recall', 'level': b.levels, 'state': state or b.state(), 'action': action,
            'expected_answer': expected}


def early_crucial(b, delay):
    s0, start = b.state(), copy.deepcopy(b.frame)
    click = act(6, x=b.rng.randrange(8), y=b.rng.randrange(8))
    b.step(act(1), 'none')
    b.step(act(2), 'none')
    crucial = b.step(click, 'change')
    b.distract(delay, exclude=(1, 2))
    b.step(act(RESET_ACTION), 'reset', to=start)
    return {'required_facts': [b.fact(act(1), 'no_observed_change', s0), b.fact(act(2), 'no_observed_change', s0),
                               b.fact(click, 'final_frame_differs', s0)],
            'relevant_steps': [0, 1, crucial],
            'questions': [_recall(b, click, ['final_frame_differs']), _recall(b, act(1), ['no_observed_change']),
                          _decision(b, [act(1), act(2), click], [click])]}


def supported_then_contradicted(b, delay):
    a = b.state()
    b.step(act(1), 'change')
    s1 = b.state()
    b.step(act(1), 'change')
    b.distract(delay, exclude=(1, 3))
    x = b.state()
    counter = b.step(act(1), 'none')
    return {'required_facts': [b.fact(act(1), 'final_frame_differs', a), b.fact(act(1), 'final_frame_differs', s1),
                               b.fact(act(1), 'no_observed_change', x)],
            'required_counterexamples': [counter],
            'must_not_hold': [{'action': act(1), 'predicate': 'visual_effect', 'value': 'final_frame_differs',
                               'scope_kinds': ['level', 'cross_level'], 'level': 0}],
            'relevant_steps': [0, 1, counter],
            'questions': [_recall(b, act(1), ['no_observed_change']), _decision(b, [act(1), act(3)], [act(3)])]}


def similar_states(b, delay):
    s, start = b.state(), copy.deepcopy(b.frame)
    cell = [(b.rng.randrange(8), b.rng.randrange(8))]
    toggled = b.mutate(b.frame, cells=cell)
    b.step(act(3), 'change', to=toggled)
    s_prime = b.state()
    unchanged = b.step(act(2), 'none')
    b.step(act(3), 'change', to=start)
    effective = b.step(act(2), 'change')
    b.distract(delay, exclude=(2, 3, 4))
    b.step(act(RESET_ACTION), 'reset', to=start)
    b.step(act(3), 'change', to=toggled)
    return {'required_facts': [b.fact(act(2), 'no_observed_change', s_prime), b.fact(act(2), 'final_frame_differs', s)],
            'must_not_hold': [{'action': act(2), 'predicate': 'visual_effect', 'value': v,
                               'scope_kinds': ['level', 'cross_level'], 'level': 0}
                              for v in ('final_frame_differs', 'no_observed_change')],
            'relevant_steps': [unchanged, effective],
            'questions': [_recall(b, act(2), ['no_observed_change']), _recall(b, act(2), ['final_frame_differs'], s),
                          _decision(b, [act(2), act(4)], [act(4)])]}


def coordinate_specific(b, delay):
    s, start = b.state(), copy.deepcopy(b.frame)
    spots = b.rng.sample([(x, y) for x in range(8) for y in range(8)], 5)
    dead = [act(6, x=x, y=y) for x, y in spots[:3]]
    live, untried = act(6, x=spots[3][0], y=spots[3][1]), act(6, x=spots[4][0], y=spots[4][1])
    for click in dead:
        b.step(click, 'none')
    effective = b.step(live, 'change')
    b.distract(delay, exclude=())
    b.step(act(RESET_ACTION), 'reset', to=start)
    return {'required_facts': [b.fact(c, 'no_observed_change', s) for c in dead] +
                              [b.fact(live, 'final_frame_differs', s)],
            'must_not_hold': [{'action': {'action_id': 6, 'action_data': 'any'}, 'predicate': 'visual_effect',
                               'value': 'no_observed_change', 'scope_kinds': ['level', 'cross_level'], 'level': 0}],
            'relevant_steps': [0, 1, 2, effective],
            'questions': [_recall(b, live, ['final_frame_differs']), _recall(b, untried, ['no_evidence']),
                          _decision(b, [dead[0], live, untried], [live])]}


def reset_keeps_mechanism(b, delay):
    s0, start = b.state(), copy.deepcopy(b.frame)
    b.step(act(1), 'change')
    s1 = b.state()
    b.step(act(1), 'change')
    s2 = b.state()
    b.step(act(4), 'none')
    b.distract(delay, exclude=(1, 4))
    b.step(act(RESET_ACTION), 'reset', to=start)
    return {'required_facts': [b.fact(act(1), 'final_frame_differs', s0), b.fact(act(1), 'final_frame_differs', s1),
                               b.fact(act(4), 'no_observed_change', s2)],
            'required_live': [{'action': act(1), 'predicate': 'visual_effect', 'value': 'final_frame_differs',
                               'scope_kind': 'level', 'level': 0}],
            'relevant_steps': [0, 1, 2],
            'questions': [_recall(b, act(1), ['final_frame_differs']), _recall(b, act(4), ['no_evidence']),
                          _decision(b, [act(1), act(4)], [act(1)])]}


def level_change(b, delay):
    t0 = b.state()
    b.step(act(4), 'change')
    t1 = b.state()
    b.step(act(4), 'change')
    b.step(act(5), 'level')
    b.distract(delay, exclude=(3, 4))
    u = b.state()
    counter = b.step(act(4), 'none')
    return {'required_facts': [b.fact(act(4), 'final_frame_differs', t0, 0), b.fact(act(4), 'final_frame_differs', t1, 0),
                               b.fact(act(4), 'no_observed_change', u, 1)],
            'required_live': [{'action': act(4), 'predicate': 'visual_effect', 'value': 'final_frame_differs',
                               'scope_kind': 'level', 'level': 0}],
            'must_not_hold': [{'action': act(4), 'predicate': 'visual_effect', 'value': 'final_frame_differs',
                               'scope_kinds': ['level', 'cross_level'], 'level': 1}],
            'required_counterexamples': [counter],
            'relevant_steps': [0, 1, counter],
            'questions': [_recall(b, act(4), ['no_observed_change']), _decision(b, [act(4), act(3)], [act(3)])]}


def unknown_outcome(b, delay):
    s, start = b.state(), copy.deepcopy(b.frame)
    b.step(act(5), 'unknown')
    b.step(act(3), 'failed')
    b.step(act(2), 'none')
    b.step(act(1), 'change')
    b.distract(delay, exclude=(2, 3, 5))
    b.step(act(RESET_ACTION), 'reset', to=start)
    return {'required_facts': [b.fact(act(2), 'no_observed_change', s), b.fact(act(1), 'final_frame_differs', s)],
            'relevant_steps': [0, 1, 2, 3],
            'questions': [_recall(b, act(5), ['no_evidence']), _recall(b, act(3), ['no_evidence']),
                          _recall(b, act(2), ['no_observed_change']),
                          _decision(b, [act(5), act(3), act(2)], [act(5), act(3)])]}


FAMILIES = {'early_crucial': early_crucial, 'supported_then_contradicted': supported_then_contradicted,
            'similar_states': similar_states, 'coordinate_specific': coordinate_specific,
            'reset_keeps_mechanism': reset_keeps_mechanism, 'level_change': level_change,
            'unknown_outcome': unknown_outcome}
DEFAULTS = {'required_facts': [], 'required_counterexamples': [], 'required_live': [], 'must_not_hold': []}


def build(family, index, delay):
    """One trajectory: raw transitions, records (transition_evidence_v2 history, no masks) and evaluator-only
    expectations. Counterexamples are named by the records' own record_id."""
    tid = f'{PARTITION[:3]}-{family}-d{delay}-{index}'
    rng = random.Random(hashlib.sha256(f'{SEED}/{family}/{index}'.encode()).hexdigest())
    b = Builder(rng)
    expected = {**copy.deepcopy(DEFAULTS), **FAMILIES[family](b, delay)}
    episode = 'em-' + hashlib.sha256(tid.encode()).hexdigest()[:12]  # no family label in the evidence
    for raw in b.raws:
        raw['identity']['episode_id'] = episode
    records = T2.history(b.raws)
    expected['required_counterexamples'] = [records[i]['identity']['record_id']
                                            for i in expected['required_counterexamples']]
    expected['final_step'] = len(b.raws) - 1
    return {'id': tid, 'family': family, 'partition': PARTITION, 'delay': delay, 'raws': b.raws,
            'records': records, 'evaluator_only': {'expected': expected, 'construction': b.construction}}


def generate(delays=(0, 3), count=2):
    return [build(family, i, d) for d in delays for family in FAMILIES for i in range(count)]


def digest(trajectories):
    payload = [{k: t[k] for k in ('id', 'raws', 'evaluator_only')} for t in trajectories]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
