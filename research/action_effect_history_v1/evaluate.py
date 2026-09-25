"""Independent replay validation, metrics and frozen outcome classes for the action-effect-history run.

Rates with a zero denominator are null, never zero. Opportunities eliminated are reported separately
and never counted as reduced. Every attempted episode is kept in reliability reporting.
"""
import hashlib
import json

from research.action_effect_v1.records import effect_record, EffectHistory
from research.action_effect_history_v1.contract import policy_request
from research.action_effect_history_v1.runner import digest, parse_action, protocol

COMPLETE_STOPS = ('action_cap', 'win', 'game_over')


def rate(numerator, denominator):
    return None if denominator == 0 else numerator / denominator


def frame_key(observation):
    frame = observation['frames'][-1]
    return hashlib.sha256(json.dumps(frame, separators=(',', ':')).encode()).hexdigest(), observation['levels_completed']


# ---------------------------------------------------------------- replay validation

TERMINAL = {'WIN': 'win', 'GAME_OVER': 'game_over'}
CALL_STATUSES = ('valid', 'invalid_output', 'interrupted', 'transport_failure', 'audit_failure', 'started', 'received')


def check_call(call, request_max_tokens, limits):
    """Independently re-derive a call's validity from its retained evidence; return a list of problems."""
    problems = []
    if call.get('status') not in CALL_STATUSES:
        return ['unknown call status']
    if call['status'] in ('valid', 'invalid_output'):
        body = call.get('response')
        raw = body.encode() if type(body) is str else None
        p, c = call.get('server_prompt_tokens'), call.get('tokenizer_prompt_tokens')
        n = call.get('server_completion_tokens')
        if (raw is None or call.get('response_truncated') is not False or call.get('response_bytes') != len(raw)
                or call.get('response_sha256') != hashlib.sha256(raw).hexdigest()):
            problems.append('response evidence does not match its hash/size')
        if type(p) is not int or p != c or not 0 < p <= limits['live_prompt_token_ceiling']:
            problems.append('prompt-token disagreement or out of range')
        if type(n) is not int or not 0 < n <= request_max_tokens:
            problems.append('completion tokens out of range')
        if call['status'] == 'valid' and call.get('finish_reason') != 'stop':
            problems.append('call labelled valid without finish_reason stop')
        if (type(call.get('started_at')) not in (int, float) or type(call.get('returned_at')) not in (int, float)
                or call['returned_at'] < call['started_at']):
            problems.append('call timing')
    return problems


def replay_episode(episode, case, limits):
    """Rebuild every request and record from retained observations only, and independently re-check every
    call, observation transition, terminal state, final observation, closure and count. Returns errors."""
    from agent.state import GameRuntimeState
    from certification.phase4_transient_v2.contract import unpack
    eid = episode.get('episode_id', '?')
    errors = []
    status, stop = episode.get('status'), episode.get('stop_reason')
    if status not in ('complete', 'interrupted', 'technical_failure', 'opening', 'running'):
        return [f'{eid}: unknown status']
    if status == 'complete' and stop not in COMPLETE_STOPS + ('invalid_output', 'dispatch_failure'):
        errors.append(f'{eid}: complete episode with stop reason {stop}')
    if status == 'complete':
        cleanup = episode.get('cleanup')
        if not isinstance(cleanup, dict) or cleanup.get('closed') is not True:
            errors.append(f'{eid}: complete episode without a successful client/scorecard closure')
    if episode.get('initial') is None:
        if status == 'complete' or episode['calls'] or episode['steps']:
            errors.append(f'{eid}: missing initial observation')
        return errors
    if episode['initial']['canonical_hash'] != case['initial_canonical_hash'] or episode['initial'].get('full_reset') is not True:
        errors.append(f'{eid}: initial state')
    obs = unpack(episode['initial'])
    last_observed = episode['initial']
    runtime = GameRuntimeState(obs, action_budget_limit=limits['actions_per_episode'])
    history = EffectHistory(limit=16)
    arm = episode['arm']
    steps, calls = episode['steps'], episode['calls']
    if len(steps) > limits['actions_per_episode']:
        errors.append(f'{eid}: action cap exceeded')
    for index, call in enumerate(calls):
        for problem in check_call(call, call['request'].get('max_tokens', 0), limits):
            errors.append(f'{eid} call {index}: {problem}')
        if call['status'] != 'valid' and index != len(calls) - 1:
            errors.append(f'{eid} call {index}: a non-valid call must be the last call of its episode')
    stopped_early = False
    for i, step in enumerate(steps):
        if step.get('index') != i or step.get('call_index') != i or i >= len(calls):
            errors.append(f'{eid} step {i}: step/call index accounting')
            break
        if step['before'] != last_observed:
            errors.append(f'{eid} step {i}: pre-state is not the preceding observation')
        if obs.state.value in TERMINAL:
            errors.append(f'{eid} step {i}: action after a terminal state')
        call = calls[i]
        expected = policy_request(runtime, arm, history if arm == 'history' else None, seed=limits['request_seed'])
        if call['request'] != expected or call['request_sha256'] != digest(expected):
            errors.append(f'{eid} step {i}: request not reproducible from past observations')
        try:
            parsed = parse_action(call['response'], obs.available_actions) if call['status'] == 'valid' else None
        except (ValueError, KeyError, TypeError):
            parsed = None
        if call['status'] != 'valid' or parsed != step['action']:
            errors.append(f'{eid} step {i}: action not bound to a valid call')
        record = step.get('effect_record')
        if record is None:
            if i != len(steps) - 1 or status == 'complete':
                errors.append(f'{eid} step {i}: missing effect record')
            stopped_early = True
            break
        if record['status'] == 'acknowledged':
            outcome = {'status': 'acknowledged', 'post': step.get('after')}
        elif record['status'] == 'dispatch_failed':
            outcome = {'status': 'dispatch_failed', 'error': record['detail']}
        else:
            outcome = {'status': 'outcome_unknown', 'reason': record['detail']}
        try:
            if effect_record(step['before'], step['action'], outcome) != record:
                raise ValueError('mismatch')
        except (ValueError, KeyError, TypeError):
            errors.append(f'{eid} step {i}: effect record not reproducible from retained frames')
        history.append(record)
        if record['status'] != 'acknowledged':
            if i != len(steps) - 1 or stop != 'dispatch_failure':
                errors.append(f'{eid}: dispatch failure must be the last step and stop the episode')
            stopped_early = True
            break
        post = unpack(step['after'])
        runtime.counters.conservative_spent_actions += 1
        runtime.replace_observation(post, action_id=step['action']['action_id'],
                                    action_data=step['action']['action_data'], transition_id=f'{eid}-{i}')
        obs, last_observed = post, step['after']
    extra = len(calls) - len(steps)
    if extra not in (0, 1):
        errors.append(f'{eid}: call/action accounting ({len(calls)} calls, {len(steps)} actions)')
    if stop == 'invalid_output':
        last = calls[-1] if calls else None
        if extra != 1 or last['status'] != 'invalid_output':
            errors.append(f'{eid}: invalid-output stop not bound to a final invalid call')
        else:
            try:
                if last.get('finish_reason') == 'stop':
                    parse_action(last['response'], obs.available_actions)
                    errors.append(f'{eid}: output labelled invalid but parses')
            except (ValueError, KeyError, TypeError):
                pass
    if status == 'complete' and not stopped_early:
        state = obs.state.value
        if stop in ('win', 'game_over') and TERMINAL.get(state) != stop:
            errors.append(f'{eid}: stop reason {stop} but final state is {state}')
        if state in TERMINAL and stop != TERMINAL[state]:
            errors.append(f'{eid}: terminal state {state} not reported as the stop reason')
        if stop == 'action_cap' and (len(steps) != limits['actions_per_episode'] or state in TERMINAL):
            errors.append(f'{eid}: action_cap without 12 actions or with a terminal state')
        if stop in COMPLETE_STOPS and extra != 0:
            errors.append(f'{eid}: extra call after the final action')
        if episode.get('final') != last_observed:
            errors.append(f'{eid}: final observation is not the last observed state')
    return errors


# ---------------------------------------------------------------- metrics

def episode_metrics(episode):
    steps = [s for s in episode['steps'] if s.get('effect_record')]
    acknowledged = [s for s in steps if s['effect_record']['status'] == 'acknowledged']
    m = {'episode_id': episode['episode_id'], 'pair_id': episode['pair_id'], 'block': episode['block'],
         'game_id': episode['game_id'], 'arm': episode['arm'], 'status': episode['status'],
         'stop_reason': episode['stop_reason'], 'play_stop_reason': episode.get('play_stop_reason'),
         'closure_failed': not (isinstance(episode.get('cleanup'), dict) and episode['cleanup'].get('closed') is True),
         'valid_actions': len(steps),
         'acknowledged_actions': len(acknowledged),
         'invalid_outputs': sum(c['status'] == 'invalid_output' for c in episode['calls']),
         'dispatch_failures': sum(s['effect_record']['status'] != 'acknowledged' for s in steps),
         'levels_gained': sum(s['effect_record']['level_delta'] or 0 for s in acknowledged),
         'observable_changes': sum(bool(s['effect_record']['any_frame_changed']) for s in acknowledged),
         'no_change_results': sum(s['effect_record']['final_frame_changed'] is False and s['effect_record']['level_delta'] == 0
                                  for s in acknowledged)}
    immediate_opp = immediate_rep = type_rep = any_opp = any_rep = 0
    seen_states, revisits, no_change_by_state = set(), 0, {}
    segment = None
    for i, s in enumerate(steps):
        key = frame_key(s['before'])
        if key in seen_states and (i == 0 or frame_key(steps[i - 1]['before']) != key):
            revisits += 1
        seen_states.add(key)
        record = s['effect_record']
        seg = s['history_entry']['segment']
        if seg != segment:
            segment, no_change_by_state = seg, {}
        if i > 0:
            prev = steps[i - 1]['effect_record']
            if (prev['status'] == 'acknowledged' and prev['final_frame_changed'] is False and prev['level_delta'] == 0
                    and frame_key(steps[i - 1]['before']) == key):
                immediate_opp += 1
                same_id = s['action']['action_id'] == steps[i - 1]['action']['action_id']
                if s['action'] == steps[i - 1]['action']:
                    immediate_rep += 1
                elif same_id:
                    type_rep += 1
        earlier = no_change_by_state.get(key, [])
        if earlier:
            any_opp += 1
            any_rep += s['action'] in earlier
        if record['status'] == 'acknowledged' and record['final_frame_changed'] is False and record['level_delta'] == 0:
            no_change_by_state.setdefault(key, []).append(s['action'])
    calls = [c for c in episode['calls'] if c.get('returned_at') is not None]
    m.update(immediate_repeat_opportunities=immediate_opp, immediate_repeats=immediate_rep,
             immediate_repeat_rate=rate(immediate_rep, immediate_opp),
             type_repeats_after_no_change=type_rep, type_repeat_rate=rate(type_rep, immediate_opp),
             any_earlier_repeat_opportunities=any_opp, any_earlier_repeats=any_rep,
             any_earlier_repeat_rate=rate(any_rep, any_opp),
             observable_change_rate=rate(m['observable_changes'], m['acknowledged_actions']),
             distinct_states=len(seen_states), state_revisits=revisits,
             distinct_actions=len({json.dumps(s['action'], sort_keys=True) for s in steps}),
             distinct_action_ids=len({s['action']['action_id'] for s in steps}),
             latency_seconds=[round(c['returned_at'] - c['started_at'], 6) for c in calls],
             prompt_tokens=sum(c.get('server_prompt_tokens') or 0 for c in calls),
             completion_tokens=sum(c.get('server_completion_tokens') or 0 for c in calls))
    return m


def classify_pair(baseline, history):
    """Frozen comparison classes; returns (class, reason)."""
    if baseline is None or history is None or baseline['status'] != 'complete' or history['status'] != 'complete':
        return 'ineligible', 'incomplete pair'
    for m in (baseline, history):
        if m['stop_reason'] not in COMPLETE_STOPS:
            return 'ineligible', f"{m['arm']} stopped on {m['stop_reason']}"
    if baseline['immediate_repeats'] < 1:
        return 'ineligible', 'baseline repeat rate not positive'
    if history['immediate_repeat_opportunities'] == 0:
        return 'opportunities_eliminated', 'history arm had no repetition opportunities (rate null)'
    rb, rh = baseline['immediate_repeat_rate'], history['immediate_repeat_rate']
    if rh <= 0.5 * rb:
        return 'reduced', f'{rh:.3f} <= half of {rb:.3f}'
    if rh >= 1.5 * rb and history['immediate_repeats'] >= baseline['immediate_repeats'] + 2:
        return 'worse', f'{rh:.3f} >= 1.5 x {rb:.3f} with at least 2 more repeats'
    return 'not_reduced', f'{rh:.3f} > half of {rb:.3f}'


def evaluate(report, spec=None):
    spec = spec or protocol()
    limits = spec['limits']
    cases = {c['game_id']: c for c in spec['cases']}
    errors = []
    if [p['pair_id'] for p in report['pairs']] != [p['pair_id'] for p in spec['schedule']]:
        errors.append('pair inventory differs from the schedule')
    for episode in report['episodes']:
        errors.extend(replay_episode(episode, cases[episode['game_id']], limits))
    # Run-level accounting, independent of the runner's own totals and labels.
    episodes = report['episodes']
    if report.get('calls') != sum(len(e['calls']) for e in episodes):
        errors.append('run call total differs from the episodes')
    if report.get('dispatches') != sum(len(e['steps']) for e in episodes):
        errors.append('run dispatch total differs from the episodes')
    if sum(len(e['calls']) for e in episodes) > limits['maximum_policy_calls']:
        errors.append('policy call ceiling exceeded')
    schedule = {p['pair_id']: p for p in spec['schedule']}
    for pair in report['pairs']:
        members = [e for e in episodes if e['pair_id'] == pair['pair_id']]
        if [e['arm'] for e in members] != schedule[pair['pair_id']]['order'][:len(members)]:
            errors.append(f"{pair['pair_id']}: episodes out of schedule order")
        if pair['status'] == 'complete' and (len(members) != 2 or any(e['status'] != 'complete' for e in members)):
            errors.append(f"{pair['pair_id']}: pair labelled complete without two complete episodes")
    if report.get('status') == 'complete' and (any(p['status'] != 'complete' for p in report['pairs'])
                                               or any(e['status'] != 'complete' for e in episodes)):
        errors.append('run labelled complete with incomplete pairs or episodes')
    metrics = [episode_metrics(e) for e in report['episodes']]
    by_pair = {}
    for m in metrics:
        by_pair.setdefault(m['pair_id'], {})[m['arm']] = m
    pairs = []
    for p in report['pairs']:
        arms = by_pair.get(p['pair_id'], {})
        cls, reason = classify_pair(arms.get('baseline'), arms.get('history'))
        if p['status'] != 'complete' and cls != 'ineligible':
            cls, reason = 'ineligible', 'pair not complete'
        pairs.append({'pair_id': p['pair_id'], 'block': p['block'], 'game_id': p['game_id'], 'pair_status': p['status'],
                      'class': cls, 'reason': reason,
                      'levels': {a: arms[a]['levels_gained'] for a in arms}})
    complete = [p for p in pairs if p['pair_status'] == 'complete' and len(p['levels']) == 2]
    all_six = len(complete) == len(spec['schedule'])
    failures = {arm: sum(m['invalid_outputs'] + m['dispatch_failures'] > 0 for m in metrics if m['arm'] == arm)
                for arm in ('baseline', 'history')}
    blocks = sorted({p['block'] for p in pairs})
    count = lambda cls, block: sum(p['class'] == cls for p in pairs if p['block'] == block)
    if not all_six:
        behaviour = 'inconclusive_incomplete_schedule'
    elif any(count('worse', b) >= 2 for b in blocks) or failures['history'] > failures['baseline']:
        behaviour = 'candidate_worse'
    elif all(count('reduced', b) >= 2 for b in blocks) and not any(count('worse', b) for b in blocks):
        behaviour = 'behaviour_changed_as_hypothesized'
    elif all(p['class'] not in ('ineligible',) for p in pairs) and not any(p['class'] in ('reduced', 'opportunities_eliminated') for p in pairs):
        behaviour = 'no_improvement_observed'
    else:
        behaviour = 'inconclusive'
    solving_games = [g for g in cases if all(
        p['levels'].get('history', 0) > p['levels'].get('baseline', 0) for p in pairs if p['game_id'] == g) and
        sum(p['game_id'] == g for p in complete) == 2]
    solving = ('strong_exploratory_solving_signal' if all_six and len(solving_games) >= 2
               else 'no_demonstrated_solving_improvement')
    pooled = {}
    for arm in ('baseline', 'history'):
        ms = [m for m in metrics if m['arm'] == arm]
        opp, rep = sum(m['immediate_repeat_opportunities'] for m in ms), sum(m['immediate_repeats'] for m in ms)
        pooled[arm] = {'immediate_repeats': rep, 'immediate_repeat_opportunities': opp, 'immediate_repeat_rate': rate(rep, opp),
                       'levels_gained': sum(m['levels_gained'] for m in ms), 'episodes': len(ms),
                       'episodes_with_invalid_output_or_dispatch_failure': failures[arm]}
    # Reliability is reported for every attempted episode, whatever the behaviour classification.
    reliability = {}
    for arm in ('baseline', 'history'):
        ms = [m for m in metrics if m['arm'] == arm]
        stops = {}
        for m in ms:
            stops[m['stop_reason'] or 'unfinished'] = stops.get(m['stop_reason'] or 'unfinished', 0) + 1
        reliability[arm] = {'episodes_attempted': len(ms), 'stop_reasons': stops,
                            'invalid_outputs': sum(m['invalid_outputs'] for m in ms),
                            'dispatch_failures': sum(m['dispatch_failures'] for m in ms),
                            'interrupted_or_technical': sum(m['status'] in ('interrupted', 'technical_failure') for m in ms),
                            'closure_failures': sum(m['closure_failed'] for m in ms)}
    arm_specific = [key for key in ('invalid_outputs', 'dispatch_failures', 'interrupted_or_technical', 'closure_failures')
                    if reliability['history'][key] != reliability['baseline'][key]]
    return {'replay_passed': not errors, 'errors': errors, 'episodes': metrics, 'pairs': pairs, 'pooled': pooled,
            'reliability_by_arm': reliability, 'arm_specific_reliability_differences': arm_specific,
            'all_six_pairs_complete': all_six, 'behaviour_result': behaviour, 'solving_result': solving,
            'opportunities_eliminated_pairs': [p['pair_id'] for p in pairs if p['class'] == 'opportunities_eliminated'],
            'run_status': report['status'], 'interpretation_scope': 'exploratory; development cases only; not generalization'}
