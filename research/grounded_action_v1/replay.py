"""Independent read-only replay of the local Stage B evidence contract."""
import hashlib
import json
import math
from pathlib import Path

from agent.state import GameRuntimeState
from certification.phase4_transient_v2.contract import pack, unpack
from .contract import audit_request, digest, parse_audit, parse_policy, policy_request, target_hit
from .local import INITIAL, MAX_CALLS, MAX_RESPONSE_BYTES, MAX_STEPS

GEOMETRY = INITIAL.with_name('geometry_reference.json')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def stamp(value, limit):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= limit, 'timestamp')
    return value


def changed(before, after):
    base = before['frames'][-1]
    result = []
    for index, frame in enumerate(after['frames']):
        if len(frame) != len(base) or len(frame[0]) != len(base[0]):
            result.append({'frame': index, 'shape_changed': True, 'changed_cells': None})
        else:
            count = sum(a != b for row_a, row_b in zip(base, frame) for a, b in zip(row_a, row_b))
            result.append({'frame': index, 'shape_changed': False, 'changed_cells': count})
    return result


def evaluate(value):
    """Reconstruct requests and observations; never consult runner verdicts."""
    require(value.get('version') == 'grounded_action_local_v1' and value.get('kind') == 'scripted_cpu_only', 'record version')
    require(value.get('status') == 'complete' and value.get('error') is None, 'incomplete pair')
    limit = value['limit']
    require(limit['steps_per_arm'] == MAX_STEPS and limit['calls'] == MAX_CALLS and
            type(limit['seconds']) in (int, float) and 0 < limit['seconds'] <= 3600, 'limits')
    end = stamp(value['ended_at'], limit['seconds'])
    episodes = value['episodes']
    require(len(episodes) == 2 and [e['arm'] for e in episodes] == ['control', 'target'], 'arm inventory')
    frozen = json.loads(INITIAL.read_bytes())
    reviewer_regions = json.loads(GEOMETRY.read_bytes())
    reference_cells = {tuple(p) for obj in reviewer_regions['objects'] for p in obj['cells']}
    initial_hashes = []
    calls = dispatches = prompt_tokens = completion_tokens = 0
    summaries = []
    for episode in episodes:
        require(episode['status'] == 'complete' and episode['cleanup'] == {'closed': True, 'fixture': 'scripted_transient_v1'}, 'episode finalization')
        obs = unpack(episode['initial'])
        initial_hashes.append(obs.canonical_hash)
        observed_initial = pack(obs)
        require(obs.full_reset is True and
                {k: v for k, v in observed_initial.items() if k != 'guid'} ==
                {k: v for k, v in frozen.items() if k != 'guid'}, 'frozen initial observation')
        require(len(episode['steps']) <= MAX_STEPS, 'step ceiling')
        runtime = GameRuntimeState(obs, action_budget_limit=MAX_STEPS)
        cursor = 0
        last = 0
        outcomes = []

        def call(stage, expected_request, current):
            nonlocal cursor, last, calls, prompt_tokens, completion_tokens
            require(cursor < len(episode['calls']), 'missing call')
            row = episode['calls'][cursor]
            cursor += 1
            calls += 1
            require(row['stage'] == stage and row['pre_hash'] == current.canonical_hash and
                    row['request'] == expected_request and row['request_sha256'] == digest(expected_request), 'request binding')
            prior = last
            last = stamp(row['started_at'], end)
            returned = stamp(row['returned_at'], end)
            require(prior <= last <= returned, 'call chronology')
            last = returned
            raw = row['response'].encode()
            require(row['status'] == 'valid' and row['response_truncated'] is False and len(raw) <= MAX_RESPONSE_BYTES and row['response_bytes'] == len(raw) and
                    row['response_sha256'] == hashlib.sha256(raw).hexdigest(), 'response evidence')
            p, q, c = (row[k] for k in ('tokenizer_prompt_tokens', 'server_prompt_tokens', 'server_completion_tokens'))
            require(type(p) is int and type(q) is int and type(c) is int and 0 < p == q <= 60000 and
                    0 < c <= expected_request['max_tokens'] and row['finish_reason'] == 'stop', 'token/finish audit')
            prompt_tokens += p
            completion_tokens += c
            if stage in ('control', 'target'):
                return parse_policy(row['response'], stage, current.available_actions, current.latest_frame.tolist())
            return parse_audit(row['response'], stage, current.frames)

        for index, step in enumerate(episode['steps']):
            require(step['index'] == index and step['before'] == pack(obs) and step['status'] == 'acknowledged', 'fresh pre-observation')
            require(step['decision_call'] == cursor, 'decision pointer')
            decision = call(episode['arm'], policy_request(runtime, episode['arm']), obs)
            action = decision['action']
            require(step['action'] == action and step['target'] == decision.get('target'), 'action/target binding')
            require(step['prediction_call'] == cursor, 'prediction pointer')
            prediction = call('prediction', audit_request('prediction', pack(obs), action), obs)
            require(step['prediction'] == prediction, 'sealed prediction binding')
            require(last <= stamp(step['committed_at'], end) <= stamp(step['dispatch_started_at'], end), 'pre-dispatch retention chronology')
            require(step['receipt'] == {'acknowledged': True, 'action': action, 'fixture': 'scripted_transient_v1'}, 'dispatch receipt')
            require(step['dispatch_started_at'] <= stamp(step['returned_at'], end), 'dispatch chronology')
            last = step['returned_at']
            post = unpack(step['after'])
            require(post.guid == obs.guid and post.game_id == obs.game_id and not post.full_reset and
                    obs.levels_completed <= post.levels_completed <= post.win_levels and post.win_levels == obs.win_levels,
                    'post-observation/progress')
            require(step['feedback_call'] == cursor, 'feedback pointer')
            feedback = call('feedback', audit_request('feedback', pack(post), action, before=pack(obs)), post)
            require(step['feedback'] == feedback, 'feedback binding')
            changes = changed(pack(obs), pack(post))
            truth = [r['frame'] for r in changes if r['shape_changed'] or r['changed_cells']]
            supported = (prediction['prediction'] == 'change') == bool(truth)
            reference_contact = None
            if action['action_id'] == 6 and obs.latest_frame.tolist() == frozen['frames'][-1]:
                point = (action['action_data']['x'], action['action_data']['y'])
                reference_contact = point in reference_cells
            outcomes.append({'target_hit': target_hit(decision), 'changed_frames': truth,
                             'feedback_exact': feedback['changed_frames'] == truth,
                             'feedback_assessment_exact': feedback['assessment'] == ('supported' if supported else 'contradicted'),
                             'prediction_supported': supported, 'reviewer_visible_object_contact': reference_contact,
                             'level_delta': post.levels_completed - obs.levels_completed})
            runtime.counters.conservative_spent_actions += 1
            runtime.replace_observation(post, action_id=action['action_id'], action_data=action['action_data'],
                                        transition_id=episode['arm'] + str(index))
            obs = post
            dispatches += 1
        require(cursor == len(episode['calls']) and episode['final'] == pack(obs), 'call/final inventory')
        require(len(episode['steps']) == MAX_STEPS or obs.state.value in ('WIN', 'GAME_OVER') or
                obs.levels_completed > frozen['levels_completed'], 'premature episode stop')
        summaries.append({'arm': episode['arm'], 'actions': len(outcomes), 'outcomes': outcomes,
                          'level_delta': obs.levels_completed - frozen['levels_completed']})
    require(initial_hashes[0] == initial_hashes[1] == frozen['canonical_hash'], 'initial equality')
    require(calls == value['calls'] and dispatches == value['dispatches'] and calls <= MAX_CALLS and
            dispatches <= 2 * MAX_STEPS, 'global budget')
    return {'status': 'valid_local_scripted_pair', 'calls': calls, 'dispatches': dispatches,
            'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens,
            'episodes': summaries, 'interpretation': 'Synthetic transitions only; no model or real-game outcome.'}


def replay_file(path):
    return evaluate(json.loads(Path(path).read_bytes()))
