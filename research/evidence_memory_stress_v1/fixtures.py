"""Continuous stress trajectories with independently constructed answer keys.

Only development cases are generated. Original protocols and locks are read-only.
Keys below follow the declared construction, then are checked against the existing
independent evaluator. They never enter rendered contexts or model requests.
"""
import copy
import hashlib
import random

from research.evidence_memory_v1 import trajectories as TR
from research.transition_evidence_v2 import transition as T

SEED = 'evidence-memory-stress-v1-development-2026-10-07'
FAMILIES = ('coordinates', 'unobserved_dispatch', 'transient_return',
            'hypothesis_pending', 'contradicted_hypothesis', 'reset_boundary', 'level_boundary', 'buried_evidence')
DELAYS = (0, 8, 24)


def build(family, index=0, delay=8):
    if family not in FAMILIES or delay < 0 or index < 0:
        raise ValueError('invalid development fixture parameters')
    rng = random.Random(hashlib.sha256(f'{SEED}/{family}/{index}'.encode()).hexdigest())
    b = TR.Builder(rng)
    start, state = copy.deepcopy(b.frame), b.state()
    questions, keys, relevant, relevant_facts = [], [], [], []
    correction_steps = []

    def recall(action, values, target_state=state, level=0, steps=()):
        questions.append({'kind': 'recall', 'level': level, 'state': target_state, 'action': action})
        keys.append({'values': values})
        relevant.append(list(steps))
        for value in values:
            if value != 'no_evidence':
                fact = {'action': action, 'predicate': 'visual_effect', 'value': value,
                        'state': target_state, 'level': level}
                if fact not in relevant_facts:
                    relevant_facts.append(fact)

    if family == 'coordinates':
        x, y = rng.sample([(x, y) for x in range(8) for y in range(8)], 2)
        dead, live = TR.act(6, x=x[0], y=x[1]), TR.act(6, x=y[0], y=y[1])
        a = b.step(dead, 'none')
        c = b.step(live, 'change')
        b.distract(delay, exclude=(6,))
        b.step(TR.act(0), 'reset', to=start)
        recall(dead, ['no_observed_change'], steps=[a])
        recall(live, ['final_frame_differs'], steps=[c])
    elif family == 'unobserved_dispatch':
        a = b.step(TR.act(5), 'unknown')
        c = b.step(TR.act(3), 'failed')
        d = b.step(TR.act(2), 'none')
        b.distract(delay, exclude=(2, 3, 5))
        b.step(TR.act(0), 'reset', to=start)
        recall(TR.act(5), ['no_evidence'], steps=[a])
        recall(TR.act(3), ['no_evidence'], steps=[c])
        recall(TR.act(2), ['no_observed_change'], steps=[d])
    elif family == 'transient_return':
        a = b.step(TR.act(6, x=2, y=3), 'transient')
        b.distract(delay, exclude=(6,))
        b.step(TR.act(0), 'reset', to=start)
        recall(TR.act(6, x=2, y=3), ['changed_then_returned'], steps=[a])
    elif family in ('hypothesis_pending', 'contradicted_hypothesis'):
        a = b.step(TR.act(1), 'change')
        second_state = b.state()
        c = b.step(TR.act(1), 'change')
        contradiction_state = b.state()
        if family == 'contradicted_hypothesis':
            d = b.step(TR.act(1), 'none')
            correction_steps = [d]
        b.distract(delay, exclude=(1,))
        b.step(TR.act(0), 'reset', to=start)
        recall(TR.act(1), ['final_frame_differs'], steps=[a])
        recall(TR.act(1), ['final_frame_differs'], target_state=second_state, steps=[c])
        if family == 'contradicted_hypothesis':
            recall(TR.act(1), ['no_observed_change'], target_state=contradiction_state, steps=[d])
        questions.append({'kind': 'hypothesis_status', 'level': 0, 'action': TR.act(1),
                          'value': 'final_frame_differs'})
        keys.append({'status': 'contradicted' if correction_steps else 'hypothesis_only'})
        relevant.append([a, c] + correction_steps)
    elif family == 'reset_boundary':
        a = b.step(TR.act(2), 'none')
        b.distract(delay, exclude=(2,))
        b.step(TR.act(0), 'reset', to=start)
        # Exact-state observations survive reset; segment working conclusions do not.
        recall(TR.act(2), ['no_observed_change'], steps=[a])
    elif family == 'level_boundary':
        a = b.step(TR.act(4), 'transient')
        b.step(TR.act(5), 'level', to=start)
        b.distract(delay, exclude=(4,))
        b.step(TR.act(0), 'reset', to=start)
        recall(TR.act(4), ['changed_then_returned'], level=0, steps=[a])
        recall(TR.act(4), ['no_evidence'], level=1)
    else:
        a = b.step(TR.act(6, x=5, y=6), 'transient')
        buried_state = b.state()
        b.step(TR.act(7), 'change')
        remote_state = b.state()
        c = b.step(TR.act(6, x=1, y=2), 'none')
        b.distract(delay, exclude=(6,))
        b.step(TR.act(0), 'reset', to=start)
        recall(TR.act(6, x=5, y=6), ['changed_then_returned'], target_state=buried_state, steps=[a])
        # Historical non-current state tests the state-only retrieval limitation.
        recall(TR.act(6, x=1, y=2), ['no_observed_change'], target_state=remote_state, steps=[c])

    tid = f'development-{family}-{index}-d{delay}'
    episode = 'stress-' + hashlib.sha256(tid.encode()).hexdigest()[:16]
    for raw in b.raws:
        raw['identity']['episode_id'] = episode
    records = T.history(b.raws)
    expected = {**copy.deepcopy(TR.DEFAULTS), 'required_facts': relevant_facts,
                'required_counterexamples': [records[n]['identity']['record_id'] for n in correction_steps],
                'questions': [dict(q, expected_answer=k) for q, k in zip(questions, keys)],
                'relevant_steps': sorted({s for steps in relevant for s in steps}),
                'final_step': len(records)-1}
    if family == 'contradicted_hypothesis':
        expected['must_not_hold'] = [{'action': TR.act(1), 'predicate': 'visual_effect',
                                     'value': 'final_frame_differs', 'scope_kinds': ['level', 'cross_level'],
                                     'level': 0}]
    return {'id': tid, 'family': family, 'index': index, 'delay': delay, 'partition': 'development',
            'raws': b.raws, 'records': records,
            'evaluator_only': {'expected': expected, 'keys': keys, 'relevant_steps_by_question': relevant,
                               'construction': b.construction}}


def generate():
    return [build(f, i, d) for f in FAMILIES for i in range(2) for d in DELAYS]
