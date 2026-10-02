"""Independent evaluator for stagnation-supervision run evidence (hand-written; CPU only; no model).

It trusts nothing the runner or the supervisor concluded. From the verified run evidence (`evidence.load_verified`:
manifest, inventory, hashes, index agreement) it:
1. rebuilds every raw transition with the replay script's own `raw_step` (scripts/replay_transition_evidence_v1.py,
   not the runner's bridge) and every transition_evidence_v2 record, unmasked, and requires `verify_history` to pass;
2. replays a fresh supervisor (frozen trigger, the experiment policy) over those transitions, feeding it the stored
   model responses in order and the stored exact admission counts, with remaining actions recomputed from actual
   play; every recomputed decision must equal the stored one (outcome, detector signals, delivery, clearing,
   remaining actions, admission);
3. reconstructs each policy request from the initial observation and acknowledged trajectory, audits received
   response bytes, tokens and finish status, parses the action and binds it to the dispatch; every reflection
   request is compared with the exact reconstructed evidence request before its response is consumed;
4. computes the protocol's outcomes from the rebuilt records: detector-defined opportunities and behavioural
   recovery per arm, completed levels, the provisional false-interruption gate, and realised cost.
A run is technically complete only if the exact protocol schedule and ordered episode inventory completed,
each episode has an evidence-justified stop and successful closure, counters reconcile, the evidence verified and
there is no disagreement. Disagreements are listed, never repaired. Token parity and bounds are checked from the
retained counts; independently retokenizing requires the separately pinned tokenizer audit. Incorrect but validly
retained model outputs are outcomes, not evidence corruption.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from research.stagnation_supervision_v1 import detector as D, outcomes as O, supervision as SV, thresholds as S
from research.stagnation_supervision_v1.closed_loop import bridge as B, contract as C, service as SVC
from research.transition_evidence_v2 import transition as T2

ROOT = Path(__file__).resolve().parents[3]
VERSION = 'stagnation_supervision_v1_trajectory_evaluation_r4'
COMPARED = ('action_index', 'outcome', 'due', 'detector_signals', 'delivered', 'suggestion_cleared', 'remaining_actions',
            'admission')


def _replay_module():
    spec = importlib.util.spec_from_file_location('replay_transition_evidence_v1',
                                                  ROOT / 'scripts/replay_transition_evidence_v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _same(a, b):
    # JSON equality is type-sensitive; Python would equate True with 1.
    return json.dumps(a, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
        b, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _response_problems(row, limits):
    """Audit retained received evidence, independently of the runner's status label."""
    problems = []
    text = row.get('response')
    if type(text) is not str:
        return ['response body is absent or not text']
    raw = text.encode()
    if (row.get('response_truncated') or len(raw) > limits['max_response_bytes']
            or type(row.get('response_bytes')) is not int or row['response_bytes'] != len(raw)):
        problems.append('response byte count/truncation')
    if row.get('response_sha256') != hashlib.sha256(raw).hexdigest():
        problems.append('response hash')
    p, t, c = (row.get(k) for k in ('server_prompt_tokens', 'tokenizer_prompt_tokens', 'server_completion_tokens'))
    if (type(p) is not int or type(t) is not int or p != t or not 0 < p <= limits['live_prompt_token_ceiling']
            or type(c) is not int or not 0 < c <= row['request']['max_tokens'] or p + c > 65536):
        problems.append('response token counts/parity/limits')
    return problems


def _policy_response(row, legal, limits):
    from certification.phase4_transient_v2.action_contract import validate_action
    problems = _response_problems(row, limits)
    action = None
    invalid = row.get('finish_reason') != 'stop'
    try:
        action = validate_action(row.get('response'), legal)['action']
    except (ValueError, KeyError, TypeError):
        invalid = True
    if row.get('status') == 'valid':
        if invalid:
            problems.append('policy response is not a valid stop-finished action')
    elif row.get('status') == 'invalid_output':
        if not invalid:
            problems.append('policy response marked invalid is actually valid')
        action = None
    else:
        problems.append('policy call has no final valid/invalid status')
        action = None
    return action if not invalid else None, problems


class _Replay:
    """The stored reflection responses, in order, and the stored exact token counts, in the order the supervisor
    asks for them (one admission count per admitted decision, plus a charge count for each failed call)."""

    def __init__(self, episode, spec):
        self.rows = list(episode['reflections'])
        self.seed = spec['limits']['request_seed']
        self.problems = []
        self.admission = None
        self.elapsed = 0.0
        self.latencies = [e['call']['latency_s'] for e in (episode.get('supervision') or {}).get('events', [])
                          if e.get('outcome') == 'called']
        self.counts = []
        for e in (episode.get('supervision') or {}).get('events', []):
            if 'admission' in e:
                self.counts.append(e['admission']['input_tokens'])
                if e.get('call', {}).get('error') is not None:
                    self.counts.append(e['call']['input_tokens'])

    def call(self, text):
        if not self.rows:
            self.problems.append('reflection response missing during replay')
            raise RuntimeError('reflection response missing')
        row = self.rows[0]
        # Bind the complete chat envelope, including exact evidence text, BEFORE
        # consuming any stored response. A valid manifest alone cannot do this.
        expected = B.reflection_request(text, seed=self.seed)
        if not _same(row.get('request'), expected) or row.get('request_sha256') != _sha(expected):
            self.problems.append('reflection request differs from reconstructed evidence request')
            raise RuntimeError('reflection request binding')
        self.rows.pop(0)
        latency = self.latencies.pop(0)
        if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
            self.problems.append('reflection latency must be finite and nonnegative')
            raise ValueError('reflection latency')
        if row['status'] in ('failed', 'audit_failure'):
            # The service raised, so the supervisor measured elapsed time itself.
            # Replay retains that measured duration; it cannot remeasure transport.
            self.elapsed += latency
            raise RuntimeError(row.get('error') or row['status'])
        if row.get('server_prompt_tokens') != self.admission:
            self.problems.append('reflection admission count differs from response prompt count')
        return {'text': row['response'], 'input_tokens': row['server_prompt_tokens'],
                'output_tokens': row['server_completion_tokens'], 'latency_s': row['latency_s'],
                'finish_reason': row['finish_reason']}

    def count(self, _text):
        self.admission = self.counts.pop(0)
        if type(self.admission) is not int or self.admission <= 0:
            self.problems.append('reflection admission token count must be positive integer')
            raise ValueError('reflection admission count')
        return self.admission

    def clock(self):
        return self.elapsed


def _compare(stored, mine):
    return {k: {'stored': stored.get(k), 'recomputed': mine.get(k)} for k in COMPARED if stored.get(k) != mine.get(k)}


def evaluate_episode(episode, spec, trigger_spec, replay):
    from agent.state import GameRuntimeState
    from certification.phase4_transient_v2.contract import pack, unpack
    problems, horizon = [], spec['limits']['actions_per_episode']
    initial = unpack(episode['initial'])
    case = next(c for c in spec['cases'] if c['game_id'] == episode['game_id'])
    if (initial.game_id != episode['game_id'] or initial.full_reset is not True
            or initial.canonical_hash != case['initial_canonical_hash']
            or list(initial.available_actions) != case['initial_available_actions']
            or initial.win_levels != case['win_levels']):
        problems.append('initial observation differs from the protocol case')
    runtime = GameRuntimeState(initial, action_budget_limit=horizon)
    if [s['index'] for s in episode['steps']] != list(range(len(episode['steps']))):
        problems.append('step inventory is not consecutive')
    if len(episode['steps']) > horizon:
        problems.append('episode exceeds action horizon')
    raws = [replay.raw_step(episode['episode_id'], s, None, B.SOURCE) for s in episode['steps']]
    records = T2.history(raws) if raws else []
    problems += [f'record: {p}' for p in (T2.verify_history(records, raws) if raws else [])]
    stored = (episode.get('supervision') or {}).get('events', [])
    if episode['steps'] and (episode.get('supervision') or {}).get('policy') != B.EXPERIMENT_POLICY:
        problems.append('stored supervision policy differs from the frozen experiment policy')
    feed = _Replay(episode, spec)
    sup = SV.Supervisor(episode['arm'], trigger_spec, feed.call, B.EXPERIMENT_POLICY, clock=feed.clock,
                        episode_actions=horizon, token_counter=feed.count)
    calls = episode['calls']
    for i, (step, raw) in enumerate(zip(episode['steps'], raws)):
        if step['status'] not in ('acknowledged', 'dispatch_failed', 'outcome_unknown'):
            problems.append(f'step {i}: dispatch is not finalized')
        if step['call_index'] != i or type(step['call_index']) is not int:
            problems.append(f'step {i}: policy call binding/order')
        if runtime.observation.state.value in ('WIN', 'GAME_OVER'):
            problems.append(f'step {i}: action after terminal observation')
        before = unpack(step['before'])
        if not _same(step['before'], pack(runtime.observation)):
            problems.append(f'step {i}: before observation differs from retained trajectory')
        shown = sup.suggestion_for(step['index'])
        if step.get('suggestion_shown') != shown:
            problems.append(f'step {i}: suggestion shown differs from the recomputed block')
        row = calls[step['call_index']]
        request = row['request']
        expected_request = C.policy_request(runtime, episode['arm'], shown, seed=spec['limits']['request_seed'])
        if not _same(request, expected_request):
            problems.append(f'step {i}: policy request differs from reconstructed observation request')
        if row.get('request_sha256') != _sha(request) or row.get('pre_hash') != before.canonical_hash:
            problems.append(f'step {i}: policy request/pre-observation hash')
        action, response_problems = _policy_response(row, before.available_actions, spec['limits'])
        problems += [f'step {i}: {p}' for p in response_problems]
        if row.get('status') != 'valid' or action is None or not _same(action, step['action']):
            problems.append(f'step {i}: policy response does not produce the dispatched action')
        try:
            kind = SVC.validate_policy_request(request)
        except ValueError as exc:
            problems.append(f'step {i}: policy request contract: {exc}')
            kind = None
        payload = json.loads(request['messages'][1]['content'])
        expected = None if shown is None else B.suggestion_payload(shown)
        if payload.get(B.SUGGESTION_FIELD) != expected or (episode['arm'] == 'continuation' and kind == 'with_suggestion'):
            problems.append(f'step {i}: policy request suggestion block differs from the recomputed one')
        after = (raw['outcome'].get('after') or {}).get('state')
        ended = raw['outcome']['status'] != 'acknowledged' or after in ('WIN', 'GAME_OVER')
        try:
            mine = sup.observe(raw, remaining_actions=0 if ended else horizon - (step['index'] + 1))
        except IndexError:
            problems.append(f'step {i}: stored responses or counts ran out during replay')
            break
        if i >= len(stored):
            problems.append(f'step {i}: no stored supervision event')
            continue
        diff = _compare(stored[i], mine)
        if diff:
            problems.append(f'step {i}: supervision decision differs: {sorted(diff)}')
        if mine.get('call') and stored[i].get('call'):
            if mine['call']['parsed']['valid'] != stored[i]['call']['parsed']['valid']:
                problems.append(f'step {i}: reflection validity differs')
        if step['status'] == 'acknowledged':
            if not isinstance(step.get('receipt'), dict) or step['receipt'].get('acknowledged') is not True:
                problems.append(f'step {i}: acknowledgement receipt missing')
            runtime.counters.conservative_spent_actions += 1
            runtime.replace_observation(unpack(step['after']), action_id=step['action']['action_id'],
                                        action_data=step['action']['action_data'],
                                        transition_id=f"{episode['episode_id']}-{step['index']}")
        elif i != len(episode['steps']) - 1:
            problems.append(f'step {i}: work continues after failed/unknown dispatch')
    if not len(episode['steps']) <= len(calls) <= len(episode['steps']) + 1:
        problems.append('policy call inventory differs from dispatches plus optional final rejected call')
    if len(calls) == len(episode['steps']) + 1:
        if (len(episode['steps']) >= horizon or runtime.observation.state.value in ('WIN', 'GAME_OVER')
                or (episode['steps'] and episode['steps'][-1]['status'] != 'acknowledged')):
            problems.append('policy call after the action horizon or stopping transition')
        row = calls[-1]
        request = row['request']
        shown = sup.suggestion_for(len(episode['steps']))
        if not _same(request, C.policy_request(runtime, episode['arm'], shown, seed=spec['limits']['request_seed'])):
            problems.append('final policy request differs from reconstructed observation request')
        if row.get('request_sha256') != _sha(request) or row.get('pre_hash') != runtime.observation.canonical_hash:
            problems.append('final policy request/pre-observation hash')
        if row.get('status') == 'invalid_output':
            _, invalid_problems = _policy_response(row, runtime.observation.available_actions, spec['limits'])
            problems += ['final policy call: ' + p for p in invalid_problems]
        elif episode['status'] == 'complete':
            problems.append('completed episode has an unaccounted policy call')
    if episode['status'] in ('complete', 'failure_rule_stopped'):
        cleanup = episode.get('cleanup')
        if not isinstance(cleanup, dict) or cleanup.get('closed') is not True or cleanup.get('errors'):
            problems.append('episode closure receipt is not successful')
    if episode['status'] == 'complete':
        if not _same(episode.get('final'), pack(runtime.observation)):
            problems.append('final observation differs from retained trajectory')
        state = runtime.observation.state.value
        if state in ('WIN', 'GAME_OVER'):
            expected_stop = {'WIN': 'win', 'GAME_OVER': 'game_over'}[state]
        elif episode['steps'] and episode['steps'][-1]['status'] != 'acknowledged':
            expected_stop = 'dispatch_failure'
        elif len(calls) == len(episode['steps']) + 1 and calls[-1].get('status') == 'invalid_output':
            expected_stop = 'invalid_output'
        elif len(episode['steps']) == horizon:
            expected_stop = 'action_cap'
        else:
            expected_stop = None
        if expected_stop is None or episode['stop_reason'] != expected_stop:
            problems.append('episode completion/stop reason is not justified by retained evidence')
    if len(stored) != len(episode['steps']):
        problems.append('supervision events do not match the steps')
    if feed.rows:
        problems.append(f'{len(feed.rows)} stored reflection responses were never requested in replay')
    if feed.counts:
        problems.append('stored reflection admission counts were never requested in replay')
    problems.extend(feed.problems)
    if episode.get('supervision') is not None:
        summary, recomputed = episode['supervision'].get('summary') or {}, sup.summary()
        if (not _same({k: v for k, v in summary.items() if k != 'latency_s'},
                      {k: v for k, v in recomputed.items() if k != 'latency_s'})
                or not math.isclose(summary.get('latency_s', -1), recomputed['latency_s'], rel_tol=1e-12, abs_tol=1e-9)):
            problems.append('stored supervision summary differs from replay')
    if episode.get('supervision') is not None and not _same(episode['supervision'].get('suggestion'), sup.suggestion):
        problems.append('stored final suggestion differs from replay')
    for j, row in enumerate(episode['reflections']):
        request = row['request']
        try:
            SVC.validate_reflection_request(request)
        except ValueError as exc:
            problems.append(f'reflection {j}: request contract: {exc}')
        if row['request_sha256'] != _sha(request):
            problems.append(f'reflection {j}: request hash')
        if row['status'] == 'received':
            problems += [f'reflection {j}: {p}' for p in _response_problems(row, spec['limits'])]
        elif episode['status'] == 'complete' and row['status'] != 'failed':
            problems.append(f'reflection {j}: unfinished/audit-failed reflection in completed episode')
    called = [e for e in sup.events if e['outcome'] == 'called']
    reflections = [{'status': 'failed' if e['call']['error'] else 'received', 'valid': e['call']['parsed']['valid'],
                    'input_tokens': e['call']['input_tokens'], 'output_tokens': e['call']['output_tokens'],
                    'latency_s': e['call']['latency_s']} for e in called]
    triggers = [d['action_index'] for d in D.triggers(D.statistics(records), trigger_spec['params'],
                                                       trigger_spec['cooldown_actions']) if d['trigger']]
    levels = sum(r['environment']['reported']['levels_completed_after'] - r['environment']['reported']['levels_completed_before']
                 for r in records if r['environment'].get('reported'))
    return {'episode_id': episode['episode_id'], 'pair_id': episode['pair_id'], 'game': episode['game_id'],
            'arm': episode['arm'], 'status': episode['status'], 'stop_reason': episode['stop_reason'],
            'steps': len(records), 'levels_completed': levels, 'problems': problems,
            'evaluation_input': {'arm': episode['arm'], 'game': episode['game_id'], 'episode': episode['episode_id'],
                                 'records': records, 'triggers': triggers,
                                 'calls': [e['action_index'] for e in called], 'reflections': reflections}}


def evaluate_report(report, spec, trigger_spec=None):
    trigger_spec = trigger_spec or S.load()
    replay = _replay_module()
    inventory_problems = []
    schedule = spec['schedule']
    if not schedule or report.get('protocol_sha256') != _sha(spec):
        inventory_problems.append('run protocol binding/required schedule')
    if report.get('version') not in ('stagnation_supervision_run_v1', 'stagnation_supervision_run_v2'):
        inventory_problems.append('run record version')
    pair_keys = ('pair_id', 'block', 'game_id', 'order')
    expected_pairs = [{k: s[k] for k in pair_keys} for s in schedule]
    actual_pairs = [{k: p.get(k) for k in pair_keys} for p in report['pairs']]
    if not _same(actual_pairs, expected_pairs):
        inventory_problems.append('scheduled group inventory/order differs from protocol')
    expected_episodes = [
        {'episode_id': f"{s['pair_id']}-{arm}", 'pair_id': s['pair_id'], 'block': s['block'],
         'game_id': s['game_id'], 'arm': arm, 'order_in_pair': i}
        for s in schedule for i, arm in enumerate(s['order'])]
    actual_episodes = [{k: e.get(k) for k in expected_episodes[0]} for e in report['episodes']] if expected_episodes else []
    if report.get('status') == 'complete' and not _same(actual_episodes, expected_episodes):
        inventory_problems.append('scheduled episode inventory/order differs from protocol')
    elif report.get('status') != 'complete':
        admitted_ids = {p['pair_id'] for p in report['pairs'] if p.get('status') in
                        ('complete', 'partial', 'interrupted', 'running')}
        skipped = {(p['pair_id'], r['arm']) for p in report['pairs'] for r in p.get('skipped_arms', [])}
        expected_partial = [e for e in expected_episodes if e['pair_id'] in admitted_ids
                            and (e['pair_id'], e['arm']) not in skipped]
        if not _same(actual_episodes, expected_partial[:len(actual_episodes)]):
            inventory_problems.append('partial episode inventory/order differs from admitted schedule')
    for s, p in zip(schedule, report['pairs']):
        members = [e for e in report['episodes'] if e.get('pair_id') == s['pair_id']]
        wanted = [e for e in expected_episodes if e['pair_id'] == s['pair_id']]
        if p.get('status') == 'complete' and (len(members) != len(wanted) or any(e.get('status') != 'complete' for e in members)):
            inventory_problems.append(f"{s['pair_id']}: complete group lacks complete scheduled episodes")
    episodes = []
    for e in report['episodes']:
        try:
            episodes.append(evaluate_episode(e, spec, trigger_spec, replay))
        except (KeyError, TypeError, ValueError, IndexError, StopIteration, AttributeError, OverflowError) as exc:
            # Malformed but manifest-valid records must fail closed, not crash replay.
            episodes.append({'episode_id': e.get('episode_id'), 'pair_id': e.get('pair_id'),
                             'game': e.get('game_id'), 'arm': e.get('arm'), 'status': e.get('status'),
                             'stop_reason': e.get('stop_reason'), 'steps': len(e.get('steps', [])),
                             'levels_completed': 0, 'problems': [f'malformed episode evidence: {type(exc).__name__}: {exc}'],
                             'evaluation_input': None})
    problems = [f"{e['episode_id']}: {p}" for e in episodes for p in e['problems']]
    problems += inventory_problems
    totals = {'calls': 0, 'dispatches': 0, 'reflection_calls': 0,
              'prompt_tokens': 0, 'completion_tokens': 0, 'reflection_prompt_tokens': 0, 'reflection_completion_tokens': 0}
    for e in report['episodes']:
        totals['calls'] += len(e['calls'])
        totals['dispatches'] += len(e['steps'])
        totals['reflection_calls'] += len(e['reflections'])
        for rows, prefix, charged in ((e['calls'], '', ('valid', 'invalid_output', 'received')),
                                      (e['reflections'], 'reflection_', ('received',))):
            for row in rows:
                if row.get('status') in charged:
                    for total, field in (('prompt_tokens', 'server_prompt_tokens'), ('completion_tokens', 'server_completion_tokens')):
                        value = row.get(field)
                        if type(value) is not int or value < 0:
                            problems.append('run token accounting contains missing/invalid count')
                        else:
                            totals[prefix + total] += value
    for field, total in totals.items():
        if type(report.get(field)) is not int or report[field] != total:
            problems.append(f'run {field} count differs from the episode rows')
    if totals['calls'] > spec['limits']['maximum_policy_calls'] or totals['reflection_calls'] > spec['limits']['maximum_reflection_calls']:
        problems.append('run exceeds protocol call ceilings')
    # Recompute the predeclared online stops from chronological retained events, independent of labels.
    failed_dispatches = dispatches = attempted_reflections = invalid_reflections = 0
    dispatch_stop = reflection_stop = None
    try:
        for episode_index, episode in enumerate(report['episodes']):
            events = (episode.get('supervision') or {}).get('events', [])
            for step_index, step in enumerate(episode['steps']):
                if dispatch_stop is not None:
                    problems.append('action continued after dispatch reliability stop')
                    break
                dispatches += 1
                if step['status'] in ('dispatch_failed', 'outcome_unknown'):
                    failed_dispatches += 1
                if failed_dispatches * 10 > dispatches:
                    dispatch_stop = (episode_index, step_index, failed_dispatches, dispatches)
                if step_index < len(events) and events[step_index]['outcome'] == 'called':
                    attempted_reflections += 1
                    call = events[step_index]['call']
                    invalid_reflections += call['error'] is None and not call['parsed']['valid']
                    if reflection_stop is None and attempted_reflections >= 10 and invalid_reflections * 2 > attempted_reflections:
                        reflection_stop = (episode_index, step_index, attempted_reflections, invalid_reflections)
            if (reflection_stop is not None and episode_index > reflection_stop[0]
                    and episode['arm'] in ('periodic', 'triggered')):
                problems.append('reflection arm resumed after interface stop')
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        problems.append(f'malformed failure-rule evidence: {type(exc).__name__}: {exc}')
    if report.get('version') == 'stagnation_supervision_run_v2':
        if (report.get('dispatch_failures') != failed_dispatches
                or report.get('full_protocol_proof') is not (spec['limits']['actions_per_episode'] == 40)
                or report.get('reflection_arms_stopped') is not (reflection_stop is not None)):
            problems.append('failure-rule counters/proof differ from retained evidence')
    if dispatch_stop is not None:
        i, j, bad, total = dispatch_stop
        stopped = report['episodes'][i]
        if (j != len(stopped['steps']) - 1 or i != len(report['episodes']) - 1
                or stopped['status'] != 'failure_rule_stopped'
                or stopped['stop_reason'] != 'dispatch_reliability_stop'
                or report.get('status') != 'failure_rule_stopped'):
            problems.append('dispatch reliability stop not enforced')
        if report.get('version') == 'stagnation_supervision_run_v2' and report.get('failure_rule') != {
                'rule': 'dispatch_reliability', 'failed_or_unknown': bad, 'dispatches': total}:
            problems.append('dispatch reliability stop record differs')
    if reflection_stop is not None:
        i, j, total, bad = reflection_stop
        stopped = report['episodes'][i]
        if (j != len(stopped['steps']) - 1 or stopped['status'] != 'failure_rule_stopped'
                or stopped['stop_reason'] != 'reflection_interface_stop'
                or report.get('status') == 'complete'):
            problems.append('reflection interface stop not enforced')
        if (dispatch_stop is None and report.get('version') == 'stagnation_supervision_run_v2'
                and report.get('failure_rule') != {'rule': 'reflection_interface', 'attempted': total,
                                                   'invalid_outputs': bad}):
            problems.append('reflection interface stop record differs')
    if spec['limits']['actions_per_episode'] == 40:
        first = next((e for e in report['episodes'] if e['episode_id'] == 'b1-ar25-continuation'), None)
        if (first is not None and first.get('status') == 'complete'
                and first.get('stop_reason') in ('action_cap', 'win', 'game_over')
                and (first.get('supervision') or {}).get('summary', {}).get('detector_firings') == 0):
            pos = report['episodes'].index(first)
            if (pos != len(report['episodes']) - 1 or report.get('status') != 'failure_rule_stopped'
                    or report.get('version') == 'stagnation_supervision_run_v2' and report.get('failure_rule') != {
                        'rule': 'zero_detector_firings', 'episode_id': first['episode_id']}):
                problems.append('zero detector firings stop not enforced')
    complete_groups = {p['pair_id'] for p in report['pairs'] if p.get('status') == 'complete'}
    if report.get('status') == 'complete' and (report.get('error') is not None
            or any(e['status'] != 'complete' for e in episodes)):
        problems.append('run completion is contradicted by error/episode status')
    # Unverified groups cannot contribute comparative outcomes, even if the stored label says complete.
    verified_groups = {p for p in complete_groups if not inventory_problems and all(
        e['status'] == 'complete' and not e['problems'] for e in episodes if e['pair_id'] == p)}
    admitted = [e['evaluation_input'] for e in episodes if e['pair_id'] in verified_groups and e['evaluation_input'] is not None]
    horizon = spec['limits']['actions_per_episode']
    by_arm = {}
    for e in episodes:
        a = by_arm.setdefault(e['arm'], {'episodes': 0, 'levels_completed': 0})
        a['episodes'] += 1
        a['levels_completed'] += e['levels_completed']
    technically_complete = (report.get('status') == 'complete' and not problems
                            and all(p.get('status') == 'complete' for p in report['pairs']))
    return {'version': VERSION, 'technically_complete': technically_complete, 'run_status': report.get('status'),
            'problems': problems, 'admitted_groups': sorted(verified_groups),
            'episodes': [{k: v for k, v in e.items() if k != 'evaluation_input'} for e in episodes],
            'solving': by_arm,
            'recovery': O.recovery_summary(admitted, trigger_spec, horizon),
            'false_interruptions': {arm: O.interruptions(admitted, arm) for arm in ('triggered', 'periodic')},
            'false_interruptions_calls': {arm: O.interruptions(admitted, arm, what='calls')
                                          for arm in ('triggered', 'periodic')},
            'realised_cost': O.realised_cost(admitted)}


def evaluate_output(folder, spec, trigger_spec=None):
    """Trajectory-only verdict; target completion requires target_evaluate.evaluate_target."""
    from research.stagnation_supervision_v1.closed_loop.evidence import EvidenceError, load_verified
    try:
        report = load_verified(folder)
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        return {'version': VERSION, 'technically_complete': False, 'evidence_verified': False,
                'problems': [f'run evidence: {type(exc).__name__}: {exc}']}
    try:
        result = evaluate_report(report, spec, trigger_spec)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as exc:
        result = {'version': VERSION, 'technically_complete': False,
                  'problems': [f'malformed run evidence: {type(exc).__name__}: {exc}']}
    return {**result, 'evidence_verified': True, 'evaluation_scope': 'trajectory_only',
            'target_lifecycle_evaluated': False}
