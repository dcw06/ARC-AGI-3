"""Single-threaded local prospective protocol. Stop after any write/dispatch error."""
import json
import os
from copy import deepcopy
from pathlib import Path
from .memory import EvidenceMemory, digest
from .models import predict, plan, current, state_key
from .object_effects import object_effects


def object_scores(before, after, prediction, status, boundary):
    """Score only unambiguous single-frame correspondence; report unknowns explicitly."""
    candidates = []
    if status == 'acknowledged' and not boundary and len(current(after)['frames']) == 1:
        candidates = object_effects(current(before)['frames'][-1], current(after)['frames'][-1])['candidates']
    scores = []
    for forecast in prediction['object_predictions']:
        matches = [c for c in candidates if c['before'] == forecast['before_region_id']
                   and c['unique_within_candidates'] and c['kind'] in ('translation_candidate', 'unchanged_mask')]
        scored = len(matches) == 1
        scores.append(dict(before_region_id=forecast['before_region_id'], scored=scored,
                           correct=scored and matches[0]['displacement'] == forecast['displacement']))
    return scores


def write_once(path, payload):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def execute(memory, action, dispatch, directory, *, planned=None):
    before = memory.snapshot()
    prediction = predict(before, action)
    if planned is not None:
        expected = plan(before, planned['objective'], horizon=planned['horizon'],
                        max_expansions=planned['max_expansions'])
        if planned != expected or not planned['actions'] or planned['actions'][0] != action:
            raise ValueError('stale, altered or incompatible plan')
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    prefix = root / f'step-{len(before["transitions"]):04d}'
    # Exclusive record blocks a second dispatch after a crash or uncertain outcome.
    write_once(str(prefix)+'.prediction.json', dict(before=before, prediction=prediction, plan=planned))
    try:
        outcome = dispatch(deepcopy(action))
    except Exception as error:
        outcome = dict(status='outcome_unknown', reason=f'dispatch exception: {type(error).__name__}')
    try:
        transition = memory.append(action, outcome)
    except (ValueError, TypeError, KeyError):
        transition = memory.append(action, dict(status='outcome_unknown', reason='malformed dispatch outcome'))
    after = memory.snapshot()
    status = transition['outcome']['status']
    # Reset/level transitions invalidate the old plan even if a state hash happened to agree.
    boundary = after['observations'][-1]['segment'] != before['observations'][-1]['segment']
    scored = status == 'acknowledged' and not boundary and prediction['predicted_state'] is not None
    correct = scored and state_key(current(after)) == prediction['predicted_state']
    result = dict(prediction_sha256=digest(prediction), outcome_status=status,
        scored=scored, correct=correct, plan_invalidated=planned is not None and (not correct or boundary),
        object_scores=object_scores(before, after, prediction, status, boundary),
        next_action='replan' if correct else 'request_probe' if status == 'acknowledged' else 'stop')
    write_once(str(prefix)+'.result.json', dict(after=after, result=result))
    memory.save(str(prefix)+'.memory.json')
    return result


def verify(directory):
    """Reconstruct forecasts using only their saved pre-state and check continuity."""
    root = Path(directory)
    previous, count = None, 0
    for file in sorted(root.glob('step-*.prediction.json')):
        record = json.loads(file.read_text())
        before = record['before']
        if previous is not None and before != previous:
            raise ValueError('discontinuous evidence')
        expected = predict(before, record['prediction']['action'])
        if record['prediction'] != expected:
            raise ValueError('prediction not derived from pre-state')
        retained = json.loads(Path(str(file).replace('.prediction.json', '.result.json')).read_text())
        restored = EvidenceMemory.load(str(file).replace('.prediction.json', '.memory.json')).snapshot()
        if retained['after'] != restored or restored['transitions'][:-1] != before['transitions']:
            raise ValueError('post-state mismatch')
        # Restore also the pre-state, including all derived records, via raw replay.
        rebuilt = EvidenceMemory(before['episode_id'], before['initial'])
        for t in before['transitions']:
            rebuilt.append(t['action'], t['outcome'], elapsed_seconds=t['elapsed_seconds'])
        if rebuilt.snapshot() != before:
            raise ValueError('invalid pre-state')
        last = restored['transitions'][-1]
        if file.name != f'step-{len(before["transitions"]):04d}.prediction.json':
            raise ValueError('step index mismatch')
        if last['action'] != expected['action']:
            raise ValueError('action mismatch')
        rebuilt.append(last['action'], last['outcome'], elapsed_seconds=last['elapsed_seconds'])
        if rebuilt.snapshot() != restored:
            raise ValueError('post-state does not extend this pre-state')
        planned = record['plan']
        if planned is not None and (planned != plan(before, planned['objective'], horizon=planned['horizon'], max_expansions=planned['max_expansions']) or not planned['actions'] or planned['actions'][0] != last['action']):
            raise ValueError('plan mismatch')
        boundary = restored['observations'][-1]['segment'] != before['observations'][-1]['segment']
        status = last['outcome']['status']
        scored = status == 'acknowledged' and not boundary and expected['predicted_state'] is not None
        correct = scored and state_key(current(restored)) == expected['predicted_state']
        result = dict(prediction_sha256=digest(expected), outcome_status=status, scored=scored, correct=correct,
            object_scores=object_scores(before, restored, expected, status, boundary),
            plan_invalidated=planned is not None and (not correct or boundary),
            next_action='replan' if correct else 'request_probe' if status == 'acknowledged' else 'stop')
        if result != retained['result']:
            raise ValueError('score mismatch')
        previous, count = restored, count+1
    if not count:
        raise ValueError('no prospective evidence')
    return dict(verified_steps=count)
