"""Independent evaluator for stagnation-supervision run evidence (hand-written; CPU only; no model).

It trusts nothing the runner or the supervisor concluded. From the verified run evidence (`evidence.load_verified`:
manifest, inventory, hashes, index agreement) it:
1. rebuilds every raw transition with the replay script's own `raw_step` (scripts/replay_transition_evidence_v1.py,
   not the runner's bridge) and every transition_evidence_v2 record, unmasked, and requires `verify_history` to pass;
2. replays a fresh supervisor (frozen trigger, the experiment policy) over those transitions, feeding it the stored
   model responses in order and the stored exact admission counts, with remaining actions recomputed from actual
   play; every recomputed decision must equal the stored one (outcome, detector signals, delivery, clearing,
   remaining actions, admission);
3. checks every policy request against its contract and checks that the suggestion block it carries equals the
   recomputed one (never in continuation), and checks every reflection request contract, request hash and response
   hash;
4. computes the protocol's outcomes from the rebuilt records: detector-defined opportunities and behavioural
   recovery per arm, completed levels, the provisional false-interruption gate, and realised cost.
A run is technically complete only if the run and every scheduled group completed, the evidence verified and there
is no disagreement. Disagreements are listed, never repaired.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

from research.stagnation_supervision_v1 import detector as D, outcomes as O, supervision as SV, thresholds as S
from research.stagnation_supervision_v1.closed_loop import bridge as B, service as SVC
from research.transition_evidence_v2 import transition as T2

ROOT = Path(__file__).resolve().parents[3]
VERSION = 'stagnation_supervision_v1_evaluation'
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


class _Replay:
    """The stored reflection responses, in order, and the stored exact token counts, in the order the supervisor
    asks for them (one admission count per admitted decision, plus a charge count for each failed call)."""

    def __init__(self, episode):
        self.rows = list(episode['reflections'])
        self.counts = []
        for e in (episode.get('supervision') or {}).get('events', []):
            if 'admission' in e:
                self.counts.append(e['admission']['input_tokens'])
                if e.get('call', {}).get('error') is not None:
                    self.counts.append(e['call']['input_tokens'])

    def call(self, _text):
        row = self.rows.pop(0)
        if row['status'] in ('failed', 'audit_failure'):
            raise RuntimeError(row.get('error') or row['status'])
        return {'text': row['response'], 'input_tokens': row['server_prompt_tokens'],
                'output_tokens': row['server_completion_tokens'], 'latency_s': row['latency_s'],
                'finish_reason': row['finish_reason']}

    def count(self, _text):
        return self.counts.pop(0)


def _compare(stored, mine):
    return {k: {'stored': stored.get(k), 'recomputed': mine.get(k)} for k in COMPARED if stored.get(k) != mine.get(k)}


def evaluate_episode(episode, spec, trigger_spec, replay):
    problems, horizon = [], spec['limits']['actions_per_episode']
    raws = [replay.raw_step(episode['episode_id'], s, None, B.SOURCE) for s in episode['steps']]
    records = T2.history(raws) if raws else []
    problems += [f'record: {p}' for p in (T2.verify_history(records, raws) if raws else [])]
    stored = (episode.get('supervision') or {}).get('events', [])
    if (episode.get('supervision') or {}).get('policy') != B.EXPERIMENT_POLICY:
        problems.append('stored supervision policy differs from the frozen experiment policy')
    feed = _Replay(episode)
    sup = SV.Supervisor(episode['arm'], trigger_spec, feed.call, B.EXPERIMENT_POLICY, clock=lambda: 0.0,
                        episode_actions=horizon, token_counter=feed.count)
    calls = episode['calls']
    for i, (step, raw) in enumerate(zip(episode['steps'], raws)):
        shown = sup.suggestion_for(step['index'])
        if step.get('suggestion_shown') != shown:
            problems.append(f'step {i}: suggestion shown differs from the recomputed block')
        request = calls[step['call_index']]['request']
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
    if len(stored) != len(episode['steps']):
        problems.append('supervision events do not match the steps')
    if feed.rows:
        problems.append(f'{len(feed.rows)} stored reflection responses were never requested in replay')
    for j, row in enumerate(episode['reflections']):
        request = row['request']
        try:
            SVC.validate_reflection_request(request)
        except ValueError as exc:
            problems.append(f'reflection {j}: request contract: {exc}')
        if row['request_sha256'] != _sha(request):
            problems.append(f'reflection {j}: request hash')
        if row['status'] in ('received', 'audit_failure') and not row.get('response_truncated'):
            if hashlib.sha256(row['response'].encode()).hexdigest() != row['response_sha256']:
                problems.append(f'reflection {j}: response hash')
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
    episodes = [evaluate_episode(e, spec, trigger_spec, replay) for e in report['episodes']]
    problems = [f"{e['episode_id']}: {p}" for e in episodes for p in e['problems']]
    if report.get('reflection_calls') != sum(len(e['reflections']) for e in report['episodes']):
        problems.append('run reflection call count differs from the episode rows')
    complete_groups = {p['pair_id'] for p in report['pairs'] if p.get('status') == 'complete'}
    admitted = [e['evaluation_input'] for e in episodes if e['pair_id'] in complete_groups and e['status'] == 'complete']
    horizon = spec['limits']['actions_per_episode']
    by_arm = {}
    for e in episodes:
        a = by_arm.setdefault(e['arm'], {'episodes': 0, 'levels_completed': 0})
        a['episodes'] += 1
        a['levels_completed'] += e['levels_completed']
    technically_complete = (report.get('status') == 'complete' and not problems
                            and all(p.get('status') == 'complete' for p in report['pairs']))
    return {'version': VERSION, 'technically_complete': technically_complete, 'run_status': report.get('status'),
            'problems': problems, 'admitted_groups': sorted(complete_groups),
            'episodes': [{k: v for k, v in e.items() if k != 'evaluation_input'} for e in episodes],
            'solving': by_arm,
            'recovery': O.recovery_summary(admitted, trigger_spec, horizon),
            'false_interruptions': {arm: O.interruptions(admitted, arm) for arm in ('triggered', 'periodic')},
            'false_interruptions_calls': {arm: O.interruptions(admitted, arm, what='calls')
                                          for arm in ('triggered', 'periodic')},
            'realised_cost': O.realised_cost(admitted)}


def evaluate_output(folder, spec, trigger_spec=None):
    from research.stagnation_supervision_v1.closed_loop.evidence import EvidenceError, load_verified
    try:
        report = load_verified(folder)
    except (EvidenceError, OSError, ValueError, KeyError) as exc:
        return {'version': VERSION, 'technically_complete': False, 'evidence_verified': False,
                'problems': [f'run evidence: {type(exc).__name__}: {exc}']}
    return {**evaluate_report(report, spec, trigger_spec), 'evidence_verified': True}
