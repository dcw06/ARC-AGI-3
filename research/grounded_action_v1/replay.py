"""Independent read-only replay of the local Stage B evidence contract."""
import hashlib
import json
import math
from pathlib import Path

from agent.state import GameRuntimeState
from agent.action import ActionDecision, serialize_action
from certification.phase4_transient_v2.contract import pack, unpack
from .contract import audit_request, case_protocol, digest, parse_audit, parse_policy, policy_request, target_hit
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
    case = case_protocol()
    require(value.get('case_protocol_sha256') == hashlib.sha256(
        (INITIAL.parents[1] / 'perception_stage_b_v1_case_protocol.json').read_bytes()).hexdigest(),
        'case protocol binding')
    kind = value.get('kind')
    require(value.get('version') in ('grounded_action_local_v1', 'grounded_action_local_v2',
                                     'grounded_action_local_v3', 'grounded_action_local_v4') and
            kind in ('scripted_cpu_only', 'offline_development_engine'), 'record version')
    feedback_encoding = ('legacy_grid_json_v1' if value['version'] == 'grounded_action_local_v1'
                         else 'hex_rows_v1')
    prediction_contract = ('single_choice_v2' if value['version'] in ('grounded_action_local_v3',
                                                                       'grounded_action_local_v4')
                           else 'legacy_pair_v1')
    feedback_contract = ('frame_flags_v2' if value['version'] == 'grounded_action_local_v4'
                         else 'legacy_indices_v1')
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
    card_ids = set()
    calls = dispatches = prompt_tokens = completion_tokens = 0
    summaries = []
    for episode in episodes:
        cleanup = episode['cleanup']
        require(episode['status'] == 'complete' and type(cleanup) is dict and cleanup.get('closed') is True,
                'episode finalization')
        if kind == 'scripted_cpu_only':
            require(cleanup == {'closed': True, 'fixture': 'scripted_transient_v1'}, 'scripted cleanup')
        else:
            require(cleanup.get('source') == kind and cleanup.get('client_closed') is True and
                    cleanup.get('scorecard_closed') is True, 'development cleanup')
            card_id = cleanup.get('scorecard_id')
            card = cleanup.get('scorecard_receipt')
            require(type(card_id) is str and card_id and card_id not in card_ids and
                    type(card) is dict and card.get('card_id') == card_id,
                    'development scorecard receipt/isolation')
            card_ids.add(card_id)
            life = cleanup.get('lifecycle_journal')
            require(type(life) is list and len(life) == 2 and
                    [r.get('kind') for r in life] == ['scorecard_open', 'scorecard_close'] and
                    all(r.get('status') == 'acknowledged' for r in life) and
                    life[0]['fields']['card_id'] == cleanup.get('scorecard_id') and
                    life[1]['prepared_fields']['card_id'] == cleanup.get('scorecard_id'),
                    'development scorecard lifecycle')
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
            return parse_audit(row['response'], stage, current.frames,
                               prediction_contract=prediction_contract,
                               feedback_contract=feedback_contract)

        for index, step in enumerate(episode['steps']):
            require(step['index'] == index and step['before'] == pack(obs) and step['status'] == 'acknowledged', 'fresh pre-observation')
            require(step['decision_call'] == cursor, 'decision pointer')
            decision = call(episode['arm'], policy_request(runtime, episode['arm']), obs)
            action = decision['action']
            require(step['action'] == action and step['target'] == decision.get('target'), 'action/target binding')
            require(step['prediction_call'] == cursor, 'prediction pointer')
            prediction = call('prediction', audit_request('prediction', pack(obs), action,
                                                           prediction_contract=prediction_contract), obs)
            require(step['prediction'] == prediction, 'sealed prediction binding')
            require(last <= stamp(step['committed_at'], end) <= stamp(step['dispatch_started_at'], end), 'pre-dispatch retention chronology')
            receipt = step['receipt']
            require(receipt.get('acknowledged') is True and receipt.get('action') == action, 'dispatch receipt')
            if kind == 'scripted_cpu_only':
                require(receipt == {'acknowledged': True, 'action': action, 'fixture': 'scripted_transient_v1'}, 'scripted receipt')
            else:
                journal = receipt.get('journal')
                require(receipt.get('source') == kind and type(journal) is dict and
                        journal.get('kind') == 'action' and journal.get('status') == 'acknowledged',
                        'development action journal')
                entries = cleanup['client_journal']
                require(type(entries) is list and len(entries) >= index + 2 and entries[index + 1] == journal,
                        'development journal copy')
            require(step['dispatch_started_at'] <= stamp(step['returned_at'], end), 'dispatch chronology')
            last = step['returned_at']
            post = unpack(step['after'])
            require(post.guid == obs.guid and post.game_id == obs.game_id and not post.full_reset and
                    obs.levels_completed <= post.levels_completed <= post.win_levels and post.win_levels == obs.win_levels,
                    'post-observation/progress')
            if kind == 'offline_development_engine':
                wire = serialize_action(ActionDecision(**action, source='grounded_action_stage_b',
                                                       decision_id=f"{episode['arm']}-{index}"),
                                        game_id=obs.game_id, guid=obs.guid,
                                        legal_actions=obs.available_actions)
                require(journal['fields']['post_state_hash'] == post.canonical_hash and
                        journal['prepared_fields']['pre_state_hash'] == obs.canonical_hash and
                        journal['prepared_fields']['action_id'] == action['action_id'] and
                        journal['prepared_fields']['decision_id'] == f"{episode['arm']}-{index}" and
                        journal['prepared_fields']['payload_sha256'] == wire.payload_sha256,
                        'development journal binding')
            require(step['feedback_call'] == cursor, 'feedback pointer')
            feedback = call('feedback', audit_request('feedback', pack(post), action,
                                                      before=pack(obs), prediction=prediction,
                                                      feedback_encoding=feedback_encoding,
                                                      feedback_contract=feedback_contract), post)
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
        if kind == 'offline_development_engine':
            entries = cleanup['client_journal']
            require(len(entries) == len(episode['steps']) + 1 and
                    entries[0]['kind'] == 'bootstrap_reset' and entries[0]['status'] == 'acknowledged' and
                    entries[0]['fields']['observation_hash'] == initial_hashes[-1] and
                    entries[0]['prepared_fields']['requested_game_id'] == obs.game_id and
                    entries[0]['prepared_fields']['scorecard_id'] == cleanup['scorecard_id'],
                    'development bootstrap binding')
            card = cleanup['scorecard_receipt']
            require(card['total_actions'] == len(episode['steps']) and
                    card['total_levels_completed'] == obs.levels_completed and
                    card['environments'][0]['id'] == obs.game_id,
                    'development scorecard totals')
        require(len(episode['steps']) == MAX_STEPS or obs.state.value in ('WIN', 'GAME_OVER') or
                obs.levels_completed > frozen['levels_completed'], 'premature episode stop')
        summaries.append({'arm': episode['arm'], 'actions': len(outcomes), 'outcomes': outcomes,
                          'level_delta': obs.levels_completed - frozen['levels_completed']})
    require(initial_hashes[0] == initial_hashes[1] == frozen['canonical_hash'], 'initial equality')
    require(calls == value['calls'] and dispatches == value['dispatches'] and calls <= MAX_CALLS and
            dispatches <= 2 * MAX_STEPS and value['prompt_tokens'] == prompt_tokens and
            value['completion_tokens'] == completion_tokens and prompt_tokens <= 720000 and
            completion_tokens <= 1536, 'global budget')
    return {'status': 'valid_local_scripted_pair' if kind == 'scripted_cpu_only' else 'valid_offline_development_pair',
            'primary_outcome': case['primary_outcome'],
            'calls': calls, 'dispatches': dispatches,
            'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens,
            'episodes': summaries,
            'interpretation': ('Synthetic transitions only; no model or real-game outcome.' if kind == 'scripted_cpu_only'
                               else 'Real offline development engine with scripted responses; no model or provider outcome.')}


def replay_file(path):
    return evaluate(json.loads(Path(path).read_bytes()))
