"""Independent evaluation of feedback-action v1 sessions from retained run evidence (read-only; no model, no GPU).

Independent of the runner, the live policy and the adapter. It imports only the standard library, the decision
evaluator (`evaluate.py`, itself independent of the adapter) and the frozen transition_evidence_v2 format's own
constructors and verifier, and reads the experiment protocol and owner-gate record as data. From retained bytes only:

1. the session's effective spec is rebuilt from protocol.json and owner_gates.json; the run's protocol digest,
   schedule, pair statuses and episode order must match it;
2. every episode is replayed: raw transitions rebuild and pass `verify_history`, record ids, call/step links,
   continuity and the frozen initial state are checked, and every call's request and response bytes are checked
   (request contract, response hash, cross-process token audit);
3. every carried statement is reconstructed from the previous call's raw response and the transition its action
   produced, and must equal the statement actually sent; model-statement records must match the dispatched blocks;
4. every citation is classified against the window shown at that decision and every rate is recomputed with
   explicit denominators (per episode and per (game, arm));
5. the failure rules of protocol v2 section 10 are applied, F2a and F5 recomputed online from the retained calls and
   dispatches with the effective rule; `session_2_permitted` follows "Session 2 does not start after a session-1 stop
   under F2a or F3-F6";
6. cost is reported per arm: provider prompt and completion tokens, call latency, episode wall time.

In live mode the evaluating checkout must also be the reviewed one, under exactly the launch gate's source-lock
rules (`binding.check_sources`): the newest review lock's scope and GPU-disabled status, the complete embedded-source
inventory, every binding's hash and every review document, this evaluator among them. Otherwise the evaluation
records the problem and never permits session 2, whose gate trusts `session_2_permitted`. That check is the gate's
own static source check (it reads files and their import statements), imported lazily; it imports none of the
runner, the live policy or the adapter.

`evaluate_sessions` pools two evaluated sessions and applies section 9 (solving and exploratory action-selection
rules) and F2b. Free text is never scored for plausibility.
"""
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from research.feedback_action_v1 import evaluate as EV
from research.transition_evidence_v2 import transition as T2

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'research/feedback_action_v1/live/protocol.json'
GATES = 'research/feedback_action_v1/live/owner_gates.json'
HOLDOUT_LEDGER = 'config/holdout_ledger.yaml'
TEXT_LIMIT = 240
BOUNDARY = {'reset_acknowledged', 'level_completed', 'level_count_decreased', 'terminal_state'}
# The adapter's carried-statement texts, copied here as data (a change in the adapter shows up as a mismatch).
NOTE = 'your own previous statement: a hypothesis, not an observation and not evidence'
REASON_NONE = 'no earlier decision in this episode'
REASON_INVALID = 'the previous output had no valid hypothesis_test; no older statement is carried'
REASON_CLEARED = 'cleared: the previous transition ended the segment (reset, level change or terminal)'
CAPS = {'baseline': 128, 'candidate': 640}
PROMPT_CEILING = 60000
ASCII_FREE_TEXT = set(chr(c) for c in range(0x20, 0x7f)) - {'"', '\\'}


def review_lock_status(root=ROOT):
    """(verified lock record or None, problems): the evaluating checkout against its newest review lock, under the
    launch gate's rules (binding.check_sources: scope, GPU-disabled status, the complete embedded-source inventory,
    every binding's hash, every review document)."""
    from research.feedback_action_v1.live.binding import check_sources, review_lock
    root = Path(root)
    try:
        name = review_lock(root)
        check_sources(root, name)
        return {'review_lock': name, 'review_lock_sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()}, []
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError) as exc:
        return None, [f'review lock not verified: {type(exc).__name__}: {str(exc)[:160]}']


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def effective_spec(session, root=ROOT):
    """(spec, gates): one session's runner spec rebuilt independently from the protocol and the owner-gate record."""
    protocol = json.loads((Path(root) / PROTOCOL).read_bytes())
    gates = json.loads((Path(root) / GATES).read_bytes())
    block = protocol['sessions'][str(session)]['block']
    spec = copy.deepcopy(protocol)
    spec['schedule'] = [p for p in protocol['schedule'] if p['block'] == block]
    f5 = gates['f5_early_abort']
    if (f5['decision'] or f5['committed']) == 'denominator_floor_10':
        spec['limits']['session_abort']['dispatch_denominator_floor'] = 10
    return spec, gates


def free_text_option(gates):
    entry = gates['free_text_format']
    return entry['decision'] or entry['committed']


def parsed_block(call, arm):
    """(value, block or None): the evaluator's own parse of a retained response."""
    value, problem = EV.parse_output(call.get('response'), call.get('finish_reason'), arm)
    if value is None or arm != 'candidate':
        return value, None
    block = value.get('hypothesis_test')
    return value, (block if EV.block_problem(block) is None else None)


def expected_statement(previous_call, previous_step, record):
    """The carried statement the candidate's next request must contain (rules of the adapter's docstring)."""
    if previous_call is None:
        return {'record': 'model_statement', 'available': False, 'reason': REASON_NONE}
    _, block = parsed_block(previous_call, 'candidate')
    if block is None:
        return {'record': 'model_statement', 'available': False, 'reason': REASON_INVALID}
    if record is not None and set(record['environment']['events']) & BOUNDARY:
        return {'record': 'model_statement', 'available': False, 'reason': REASON_CLEARED}
    return {'record': 'model_statement', 'available': True, 'statement_status': 'hypothesis', 'note': NOTE,
            'about': f"T{previous_step['index']}" if previous_step is not None else None,
            'hypothesis': block['hypothesis'][:TEXT_LIMIT], 'status': block['status'],
            'prediction': copy.deepcopy(block['prediction']), 'if_different': block['if_different'][:TEXT_LIMIT]}


def call_problems(call, arm, index):
    """Request/response integrity of one retained call (from its bytes only)."""
    problems = []
    request = call.get('request') or {}
    try:
        user = json.loads(request['messages'][1]['content'])
    except (KeyError, IndexError, TypeError, ValueError):
        return [f'call {index}: request unreadable']
    expected = {'observation', 'previous_model_statement'} if arm == 'candidate' else {'observation'}
    if (set(user) != expected or request.get('max_tokens') != CAPS[arm] or request.get('temperature') != 0
            or request.get('seed') != 0 or request.get('chat_template_kwargs') != {'enable_thinking': False}
            or (request.get('response_format') or {}).get('type') != 'json_schema'):
        problems.append(f'call {index}: request outside the frozen contract for the {arm} arm')
    if call.get('request_sha256') != canonical_digest(request):
        problems.append(f'call {index}: request hash')
    if call.get('status') not in ('valid', 'invalid_output'):
        problems.append(f'call {index}: no retained response ({call.get("status")})')
        return problems
    raw = (call.get('response') or '').encode()
    if call.get('response_truncated') or call.get('response_bytes') != len(raw) or call.get(
            'response_sha256') != hashlib.sha256(raw).hexdigest():
        problems.append(f'call {index}: response bytes')
    p, c = call.get('server_prompt_tokens'), call.get('server_completion_tokens')
    if (type(p) is not int or p != call.get('tokenizer_prompt_tokens') or not 0 < p <= PROMPT_CEILING
            or type(c) is not int or not 0 < c <= CAPS[arm]):
        problems.append(f'call {index}: token audit')
    return problems


def trajectory(episode):
    """The decision evaluator's trajectory, built here from the retained calls and steps (not the policy's)."""
    steps = [s for s in episode['steps'] if 'raw_transition' in s]
    raws = [s['raw_transition'] for s in steps]
    by_call = {s['call_index']: n for n, s in enumerate(steps)}
    rows = []
    for index, call in enumerate(episode['calls']):
        user = json.loads(call['request']['messages'][1]['content'])
        rows.append({'raws_before': sum(1 for c in by_call if c < index),
                     'legal_actions': user['observation']['legal_actions'],
                     'current_frame': user['observation']['current_grid'],
                     'request_user_content': call['request']['messages'][1]['content'],
                     'response': {'content': call.get('response'), 'finish_reason': call.get('finish_reason'),
                                  'completion_tokens': call.get('server_completion_tokens')},
                     'prompt_chars': sum(len(m['content']) for m in call['request']['messages']),
                     'dispatched_index': by_call.get(index)})
    return {'arm': episode['arm'], 'environment': episode['game_id'], 'raws': raws, 'steps': rows,
            'stop_reason': episode['stop_reason']}


def replay_episode(episode, case, gates, *, limits=None, contract=None):
    """Problems found replaying one episode from its retained bytes, plus the counts the report needs."""
    problems, arm, eid = [], episode['arm'], episode['episode_id']
    if case is None:
        return [f'{eid}: game outside the frozen cases'], {}
    if (episode.get('initial') or {}).get('canonical_hash') != case['initial_canonical_hash']:
        problems.append(f'{eid}: initial state differs from the frozen case')
    if limits is not None and contract is not None:
        from research.feedback_action_v1.replay import episode_problems
        try:
            problems += [f'{eid}: {p}' for p in episode_problems(
                episode, case, gates, limits, contract, expected_statement)]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            problems.append(f'{eid}: observation/request reconstruction failed: {type(exc).__name__}: {exc}')
    for index, call in enumerate(episode['calls']):
        problems += [f'{eid}: {p}' for p in call_problems(call, arm, index)]
    steps = episode['steps']
    raws = []
    for n, step in enumerate(steps):
        raw = step.get('raw_transition')
        if step.get('index') != n or raw is None:
            problems.append(f'{eid}: step {n} missing or out of order')
            continue
        if raw['identity'] != {'episode_id': eid, 'action_index': n} or step.get('record_id') != f'{eid}#{n}':
            problems.append(f'{eid}: step {n} identity')
        call = episode['calls'][step['call_index']] if 0 <= step.get('call_index', -1) < len(episode['calls']) else None
        value = parsed_block(call, arm)[0] if call is not None and call.get('status') == 'valid' else None
        if value is None or value.get('action') != step.get('action') or raw.get('dispatched') != step.get('action'):
            problems.append(f'{eid}: step {n} is not the action of a valid call')
        raws.append(raw)
    records = []
    try:
        records = T2.history(raws)
        problems += [f'{eid}: {p}' for p in T2.verify_history(records, raws)]
    except (KeyError, TypeError, ValueError) as exc:
        problems.append(f'{eid}: raw transitions do not rebuild: {type(exc).__name__}: {exc}')
    for record in records[1:]:
        if record['continuity']['status'] == 'differs_from_previous_final':
            problems.append(f"{eid}: continuity broken at {record['identity']['record_id']}")
    statements = {'checked': 0, 'available': 0, 'mismatched': 0}
    free_text_outside = 0
    if arm == 'candidate':
        by_call = {s['call_index']: s for s in steps}
        record_of = {s['index']: records[s['index']] for s in steps if s['index'] < len(records)}
        for index, call in enumerate(episode['calls']):
            sent = json.loads(call['request']['messages'][1]['content']).get('previous_model_statement')
            previous = episode['calls'][index - 1] if index else None
            step = by_call.get(index - 1) if index else None
            expected = expected_statement(previous, step, record_of.get(step['index']) if step else None)
            statements['checked'] += 1
            statements['available'] += expected['available']
            if sent != expected:
                statements['mismatched'] += 1
                problems.append(f'{eid}: carried statement at call {index} differs from its reconstruction')
        # model-statement records: one per dispatched call with a valid block, about that transition, same content
        expected_records = []
        for step in steps:
            _, block = parsed_block(episode['calls'][step['call_index']], arm)
            if block is not None:
                if free_text_option(gates) == 'ascii_only' and any(
                        set(block[f]) - ASCII_FREE_TEXT for f in ('hypothesis', 'if_different')):
                    free_text_outside += 1
                    continue
                expected_records.append(T2.model_statement(step['raw_transition']['identity'], 'hypothesis_test',
                                                           block, 'candidate_policy'))
        if episode.get('model_statements', []) != expected_records:
            problems.append(f'{eid}: model-statement records differ from the dispatched blocks')
    return problems, {'statements': statements, 'free_text_outside_option': free_text_outside, 'records': records}


def online_rules(run, spec):
    """F2a and F5 recomputed online, in schedule order, from the retained calls and dispatches alone."""
    rule = spec['limits']['session_abort']
    window, rate_f2a = rule['invalid_output_calls'], Fraction(rule['invalid_output_rate'])
    rate_f5, floor = Fraction(rule['dispatch_failure_rate']), rule.get('dispatch_denominator_floor', 0)
    calls, invalid, dispatched, failures = {}, {}, 0, 0
    fired = None
    for episode in run['episodes']:
        arm = episode['arm']
        events = [('call', c) for c in episode['calls']]
        # interleave dispatches after the call that produced them, as the runner does
        by_call = {s['call_index']: s for s in episode['steps']}
        ordered = []
        for index, call in enumerate(episode['calls']):
            ordered.append(('call', call))
            if index in by_call:
                ordered.append(('dispatch', by_call[index]))
        events = ordered
        for kind, item in events:
            if kind == 'call':
                if item.get('status') not in ('valid', 'invalid_output'):
                    continue
                n = calls[arm] = calls.get(arm, 0) + 1
                if item['status'] == 'invalid_output' and n <= window:
                    invalid[arm] = invalid.get(arm, 0) + 1
                if invalid.get(arm, 0) > rate_f2a * window:
                    fired = {'rule': 'F2a_invalid_outputs', 'arm': arm, 'invalid_outputs_in_window': invalid[arm],
                             'arm_calls': n, 'window_calls': window, 'threshold_rate': rule['invalid_output_rate'],
                             'episode_id': episode['episode_id']}
                    return fired
            else:
                if item.get('status') not in ('acknowledged', 'dispatch_failed', 'outcome_unknown'):
                    continue
                dispatched += 1
                failures += item['status'] != 'acknowledged'
                if failures > rate_f5 * max(dispatched, floor):
                    fired = {'rule': 'F5_dispatch_failures', 'dispatch_failures': failures, 'dispatched': dispatched,
                             'threshold_rate': rule['dispatch_failure_rate'], 'denominator_floor': floor,
                             'episode_id': episode['episode_id']}
                    return fired
    return None


def holdout_identifiers(root=ROOT):
    ledger = json.loads((Path(root) / HOLDOUT_LEDGER).read_bytes())
    return set(ledger['h1']) | set(ledger['h2']), set(ledger['development'])


def evaluate_session(run, *, session, mode='live', output=None, root=ROOT, lifecycle_errors=()):
    """The independent evaluation of one session (`run` is the manifest-verified run report)."""
    spec, gates = effective_spec(session, root) if session in (1, 2) else (None, None)
    if spec is None:
        return {'session': session, 'replay_passed': False, 'technical_validity': 'technically_invalid',
                'problems': ['session must be 1 or 2'], 'session_2_permitted': False, 'failure_rules': {}}
    cases = {c['game_id']: c for c in spec['cases']}
    review, problems = review_lock_status(root) if mode == 'live' else (None, [])
    contract = json.loads((Path(root) / 'research/feedback_action_v1/replay_contract.json').read_bytes())
    if run.get('protocol_sha256') != canonical_digest(spec):
        problems.append('the run did not use the reviewed effective session spec')
    expected_episodes = [(p['pair_id'], arm) for p in spec['schedule'] for arm in p['order']]
    seen_pairs = [p['pair_id'] for p in run.get('pairs', [])]
    if seen_pairs != [p['pair_id'] for p in spec['schedule']]:
        problems.append('pairs differ from the session schedule')
    observed = [(e['pair_id'], e['arm']) for e in run['episodes']]
    if observed != expected_episodes[:len(observed)]:
        problems.append('episodes out of schedule order')
    holdout, development = holdout_identifiers(root)
    leaked = sorted(i for i in holdout if any(i in json.dumps(c['request']) or i in (c.get('response') or '')
                                              for e in run['episodes'] for c in e['calls']))
    f3 = bool(leaked) or any(e['game_id'] not in cases or e['game_id'] not in development for e in run['episodes'])
    per_episode, evaluations, cost = [], {}, {}
    statements = {'checked': 0, 'available': 0, 'mismatched': 0}
    free_text_outside = 0
    for episode in run['episodes']:
        eproblems, extra = replay_episode(episode, cases.get(episode['game_id']), gates,
                                          limits=spec['limits'], contract=contract)
        problems += eproblems
        for k in statements:
            statements[k] += extra.get('statements', {}).get(k, 0)
        free_text_outside += extra.get('free_text_outside_option', 0)
        entry = {'episode_id': episode['episode_id'], 'game_id': episode['game_id'], 'arm': episode['arm'],
                 'status': episode['status'], 'stop_reason': episode['stop_reason'], 'calls': len(episode['calls']),
                 'dispatches': len(episode['steps'])}
        try:
            result = EV.evaluate_trajectory(trajectory(episode))
            entry['metrics'] = result['metrics']
            evaluations.setdefault((episode['game_id'], episode['arm']), []).append(result)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            problems.append(f"{episode['episode_id']}: decisions could not be evaluated: {type(exc).__name__}")
        a = cost.setdefault(episode['arm'], {'calls': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
                                             'call_seconds': [], 'episode_seconds': []})
        for call in episode['calls']:
            a['calls'] += 1
            a['prompt_tokens'] += call.get('server_prompt_tokens') or 0
            a['completion_tokens'] += call.get('server_completion_tokens') or 0
            if type(call.get('returned_at')) in (int, float):
                a['call_seconds'].append(round(call['returned_at'] - call['started_at'], 6))
        if type(episode.get('ended_at')) in (int, float):
            a['episode_seconds'].append(round(episode['ended_at'] - episode['started_at'], 6))
        per_episode.append(entry)
    for a in cost.values():
        seconds = a.pop('call_seconds')
        a['call_seconds_total'] = round(sum(seconds), 3)
        a['call_seconds_max'] = max(seconds) if seconds else None
        a['episode_seconds'] = [round(s, 3) for s in a['episode_seconds']]
    online = online_rules(run, spec)
    recorded = run.get('abort')
    if (online is None) != (recorded is None) or (online and online != recorded):
        problems.append('session-abort record differs from the online recomputation')
    episodes_complete = (len(run['episodes']) == len(expected_episodes)
                         and all(e['status'] == 'complete' for e in run['episodes'])
                         and all((e.get('cleanup') or {}).get('closed') is True for e in run['episodes']))
    totals = {'calls': sum(len(e['calls']) for e in run['episodes']),
              'dispatches': sum(len(e['steps']) for e in run['episodes']),
              'prompt_tokens': sum(c['server_prompt_tokens'] for e in run['episodes'] for c in e['calls']
                                   if c.get('status') in ('valid', 'invalid_output')),
              'completion_tokens': sum(c['server_completion_tokens'] for e in run['episodes'] for c in e['calls']
                                       if c.get('status') in ('valid', 'invalid_output'))}
    for name, total in totals.items():
        if type(run.get(name)) is not int or run[name] != total:
            problems.append(f'run aggregate {name} differs from retained events')
    if totals['calls'] > spec['limits']['maximum_policy_calls'] or totals['dispatches'] > (
            len(expected_episodes) * spec['limits']['actions_per_episode']):
        problems.append('run exceeds the frozen call/action ceilings')
    for frozen, pair in zip(spec['schedule'], run.get('pairs', [])):
        if any(pair.get(k) != frozen[k] for k in ('pair_id', 'block', 'game_id', 'order')):
            problems.append('pair identity differs from frozen schedule')
        episodes = [e for e in run['episodes'] if e['pair_id'] == frozen['pair_id']]
        for order, episode in enumerate(episodes):
            if (episode.get('game_id') != frozen['game_id'] or episode.get('block') != frozen['block']
                    or episode.get('order_in_pair') != order or order >= len(frozen['order'])
                    or episode['episode_id'] != frozen['pair_id'] + '-' + episode['arm']):
                problems.append('episode identity differs from frozen pair')
        complete = len(episodes) == 2 and all(e['status'] == 'complete' for e in episodes)
        if (pair.get('status') == 'complete') != complete or (pair.get('status') in ('not_admitted', 'not_started')
                                                            and episodes):
            problems.append('pair accounting differs from retained episodes')
    if run.get('status') == 'complete' and (not episodes_complete or any(
            p.get('status') != 'complete' for p in run.get('pairs', []))):
        problems.append('run completion differs from reconstructed pair accounting')
    isolation_or_integrity = [p for p in problems if 'token audit' in p or 'request outside' in p
                              or 'response bytes' in p or 'request hash' in p or 'reconstruction' in p
                              or 'transition before' in p or 'transition after' in p]
    f4 = bool(isolation_or_integrity) or any('canary' in e or 'prefix' in e for e in lifecycle_errors) or bool(
        free_text_outside) or any('verify_history' in p or 'rebuild' in p for p in problems)
    rules = {
        'F1_technically_incomplete': bool(problems) or bool(lifecycle_errors) or run.get('status') != 'complete'
        or not episodes_complete,
        'F2a_invalid_outputs': bool(online and online['rule'] == 'F2a_invalid_outputs'),
        'F2b_decision_cap_episodes_by_arm': {arm: sum(e['stop_reason'] == 'decision_cap' for e in run['episodes']
                                                      if e['arm'] == arm) for arm in ('baseline', 'candidate')},
        'F3_holdout_identifier': f3,
        'F4_integrity': f4,
        'F5_dispatch_failures': bool(online and online['rule'] == 'F5_dispatch_failures'),
        'F6_deadline_or_cancellation': run.get('status') in ('deadline_exceeded', 'canceled'),
    }
    stop_rules = [k for k in ('F2a_invalid_outputs', 'F3_holdout_identifier', 'F4_integrity', 'F5_dispatch_failures',
                              'F6_deadline_or_cancellation') if rules[k]]
    validity = ('technically_invalid' if rules['F4_integrity'] else 'technically_incomplete'
                if rules['F1_technically_incomplete'] else 'technically_complete')
    pooled = {f'{game}|{arm}': EV.aggregate(rows) for (game, arm), rows in sorted(evaluations.items())}
    return {
        'version': 'feedback_action_v1_live_evaluation', 'session': session, 'mode': mode,
        'run_sha256': canonical_digest(run), 'effective_spec_sha256': canonical_digest(spec),
        'owner_gates_sha256': canonical_digest(gates), 'lifecycle_errors': list(lifecycle_errors),
        'run_status': run.get('status'), 'replay_passed': not problems, 'problems': problems[:50],
        'problem_count': len(problems), 'technical_validity': validity, 'failure_rules': rules,
        'stop_rules_fired': stop_rules, 'online_abort_recomputed': online,
        'session_2_permitted': session == 1 and validity == 'technically_complete' and not stop_rules
        and (mode != 'live' or review is not None),
        'review_lock_verified': review,
        'carried_statements': statements, 'free_text_option': free_text_option(gates),
        'free_text_outside_option': free_text_outside,
        'holdout_identifiers_found': leaked, 'episodes': per_episode, 'pooled_by_game_and_arm': pooled,
        'cost_by_arm': cost,
        'interpretation': 'the candidate arm is a bundled treatment (procedure, hypothesis block, carried statements, '
                          '640-token completion cap); a difference cannot be attributed to one component',
    }


def _levels(evaluation, game, arm):
    return sum(e['metrics']['levels_completed'] for e in evaluation['episodes']
               if e['game_id'] == game and e['arm'] == arm and 'metrics' in e)


def evaluate_sessions(first, second, runs, *, root=ROOT):
    """Pool two evaluated sessions (blocks 1 and 2) and apply protocol v2 section 9 and F2b. `runs` are the two
    verified run reports, used only for the per-episode decisions the pooled minimums need."""
    if first['session'] != 1 or second['session'] != 2:
        raise ValueError('sessions 1 and 2 required, in order')
    if len(runs) != 2:
        raise ValueError('exactly two input runs required')
    for session, evaluation, run in zip((1, 2), (first, second), runs):
        if evaluation.get('run_sha256') != canonical_digest(run):
            raise ValueError(f'session {session}: pooled input differs from its evaluation')
        # Bind both the inputs and derived metrics. Merely editing an old digest cannot certify a new run.
        checked = evaluate_session(run, session=session, mode=evaluation['mode'], root=root,
                                   lifecycle_errors=evaluation['lifecycle_errors'])
        if canonical_digest(checked) != canonical_digest(evaluation):
            raise ValueError(f'session {session}: stale or altered evaluation, spec or reviewed checkout')
    valid = all(e['technical_validity'] == 'technically_complete' for e in (first, second))
    games = sorted({e['game_id'] for e in first['episodes'] + second['episodes']})
    caps = {arm: first['failure_rules']['F2b_decision_cap_episodes_by_arm'][arm]
            + second['failure_rules']['F2b_decision_cap_episodes_by_arm'][arm] for arm in ('baseline', 'candidate')}
    solving = {}
    for game in games:
        solving[game] = {block: {arm: _levels(e, game, arm) for arm in ('baseline', 'candidate')}
                         for block, e in (('1', first), ('2', second))}
    better = sum(all(solving[g][b]['candidate'] > solving[g][b]['baseline'] for b in ('1', '2')) for g in games)
    worse = sum(any(solving[g][b]['candidate'] < solving[g][b]['baseline'] for b in ('1', '2')) for g in games)
    evaluations = {}
    for run in runs:
        for episode in run['episodes']:
            evaluations.setdefault((episode['game_id'], episode['arm']), []).append(
                EV.evaluate_trajectory(trajectory(episode)))
    pooled = {f'{game}|{arm}': EV.aggregate(rows) for (game, arm), rows in sorted(evaluations.items())}
    thresholds = {}
    for arm_rates in (pooled,):
        cand = [v for k, v in arm_rates.items() if k.endswith('|candidate')]
        base = [v for k, v in arm_rates.items() if k.endswith('|baseline')]
        n = lambda rows, name: (sum(r[name]['numerator'] for r in rows), sum(r[name]['denominator'] for r in rows))
        ci, cd = n(cand, 'invalid_action')
        bi, bd = n(base, 'invalid_action')
        ui, ud = n(cand, 'unsupported_citation')
        si, sd = n(cand, 'citation_supply')
        thresholds = {
            'invalid_action': {'candidate': EV.rate(ci, cd), 'baseline': EV.rate(bi, bd),
                               'met': cd > 0 and bd > 0 and Fraction(ci, cd) <= Fraction(bi, bd) + Fraction(1, 20)},
            'unsupported_citation': {'candidate': EV.rate(ui, ud, 10), 'citation_supply': EV.rate(si, sd, 10),
                                     'met': ud >= 10 and Fraction(ui, ud) <= Fraction(1, 5)},
            'note': 'exploratory gates only; not evidence of reliable grounding (protocol v2 section 9.4)'}
    return {
        'technically_valid_both_sessions': valid,
        'F2b_inconclusive_reliability': {arm: caps[arm] >= 2 for arm in caps},
        'solving': {'levels_by_game_block_arm': solving, 'games_better_in_both_blocks': better,
                    'games_worse_in_some_block': worse,
                    'claim': 'solving_improvement' if valid and better >= 2 and worse == 0 else 'no_solving_claim'},
        'pooled_rates_by_game_and_arm': pooled,
        'exploratory_thresholds': thresholds,
        'rule': 'behavioural improvement is reported only for a defined failure-inclusive rate in at least two games, '
                'in the same direction in both blocks, with the arm difference exceeding that arm\'s block-1/block-2 '
                'difference; otherwise inconclusive or within run-to-run variance (protocol v2 section 9.3)',
    }
