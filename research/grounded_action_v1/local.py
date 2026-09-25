"""CPU-only scripted Stage B lifecycle. It cannot dispatch to a live game."""
import copy
import hashlib
import json
import os
import time
from pathlib import Path

from agent.state import GameRuntimeState
from certification.phase4_transient_v2.contract import pack, unpack
from .contract import audit_request, case_protocol, digest, parse_audit, parse_policy, policy_request

ROOT = Path(__file__).resolve().parents[2]
INITIAL = ROOT / 'reports/integrated_case_v1/initial_observation.json'
MAX_STEPS = 2
MAX_CALLS = 12
MAX_RESPONSE_BYTES = 32768


def save(path, value):
    """Replace and fsync the full local record before any subsequent dispatch."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, separators=(',', ':'))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def initial():
    return json.loads(INITIAL.read_bytes())


class ScriptedAdapter:
    """One isolated synthetic transition source, explicitly not the game engine."""
    def __init__(self, arm, mode='normal'):
        self.arm, self.mode, self.steps, self.closed = arm, mode, 0, False

    def bootstrap(self):
        return unpack(initial())

    def dispatch(self, action, before):
        if self.mode == 'unknown_dispatch':
            raise TimeoutError('unknown acknowledgement; do not retry')
        self.steps += 1
        value = copy.deepcopy(pack(before))
        prior = value['frames'][-1]
        interim = copy.deepcopy(prior)
        interim[0][0] = (interim[0][0] + 1) % 16
        value['frames'] = [interim, copy.deepcopy(prior)]
        value['full_reset'] = False
        value['guid'] = before.guid
        value['canonical_hash'] = unpack_without_hash(value).canonical_hash
        return unpack(value), {'acknowledged': True, 'action': action, 'fixture': 'scripted_transient_v1'}

    def close(self):
        if self.mode == 'cleanup_failure':
            raise RuntimeError('scripted cleanup failure')
        self.closed = True
        return {'closed': True, 'fixture': 'scripted_transient_v1'}


def unpack_without_hash(value):
    from agent.state import Observation
    from arcengine import GameState
    import numpy as np
    return Observation(value['game_id'], tuple(np.asarray(g, dtype=np.uint8) for g in value['frames']),
                       GameState(value['state']), value['levels_completed'], value['win_levels'],
                       value['guid'], tuple(value['available_actions']), value['full_reset'])


class ScriptedService:
    def __init__(self, mode='normal'):
        self.mode = mode

    def complete(self, request):
        name = request['response_format']['json_schema']['name']
        if name == 'arc_action_v12':
            answer = {'action': {'action_id': 6, 'action_data': {'x': 0, 'y': 0}}}
        elif name == 'grounded_target_v1':
            answer = {'action': {'action_id': 6, 'action_data': {'x': 0, 'y': 0}},
                      'target': {'kind': 'cell', 'box': [0, 0, 0, 0]}}
            if self.mode == 'wrong_target':
                answer['target']['box'] = [1, 0, 1, 0]
            if self.mode == 'missing_target':
                answer['target'] = {'kind': 'none', 'box': None}
        elif name == 'grounded_prediction_v2':
            answer = {'prediction': 'change'}
            if self.mode == 'opposite_prediction':
                answer = {'prediction': 'no_change'}
            if self.mode == 'duplicate_prediction_fields':
                answer['alternative'] = 'change'
        elif name == 'grounded_feedback_v1':
            committed = json.loads(request['messages'][1]['content'])['committed_prediction']
            answer = {'assessment': 'supported' if committed['prediction'] == 'change' else 'contradicted',
                      'changed_frames': [0]}
            if self.mode == 'wrong_feedback':
                answer = {'assessment': 'contradicted', 'changed_frames': []}
        else:
            raise ValueError('scripted stage')
        raw = json.dumps(answer, separators=(',', ':'))
        if self.mode == 'partial' and name == 'grounded_target_v1':
            raw = raw[:len(raw) // 2]
        if self.mode == 'partial_prediction' and name == 'grounded_prediction_v2':
            raw = raw[:len(raw) // 2]
        if self.mode == 'oversize' and name == 'grounded_target_v1':
            raw += ' ' * (MAX_RESPONSE_BYTES + 1)
        if self.mode == 'transport' and name == 'grounded_target_v1':
            raise ConnectionError('scripted transport failure')
        return {'content': raw, 'tokenizer_prompt_tokens': 10,
                'server_prompt_tokens': 11 if self.mode == 'mismatch' and name == 'grounded_target_v1' else 10,
                'server_completion_tokens': 16,
                'finish_reason': 'length' if (self.mode == 'partial' and name == 'grounded_target_v1' or
                                              self.mode == 'partial_prediction' and name == 'grounded_prediction_v2')
                else 'stop'}


def run(path, service, adapter_factory, *, deadline_seconds=30, kind='scripted_cpu_only',
        clock=time.monotonic, writer=save):
    """Record all received evidence before validation. Stop both arms on failure."""
    frozen = case_protocol()
    if kind not in ('scripted_cpu_only', 'offline_development_engine'):
        raise ValueError('unsupported local evidence kind')
    started = clock()
    deadline = started + deadline_seconds
    report = {'version': 'grounded_action_local_v3', 'kind': kind, 'status': 'running',
              'case_protocol_sha256': hashlib.sha256((ROOT / 'reports/perception_stage_b_v1_case_protocol.json').read_bytes()).hexdigest(),
              'limit': {'steps_per_arm': MAX_STEPS, 'calls': MAX_CALLS, 'seconds': deadline_seconds},
              'episodes': [], 'calls': 0, 'dispatches': 0,
              'prompt_tokens': 0, 'completion_tokens': 0, 'error': None}
    adapters = {}

    def persist():
        writer(path, report)

    def now():
        return clock() - started

    def check():
        if clock() >= deadline:
            raise TimeoutError('local absolute deadline')

    def call(episode, stage, request, obs):
        check()
        if report['calls'] >= MAX_CALLS:
            raise ValueError('call limit')
        if len(json.dumps(request, separators=(',', ':')).encode()) > 196608:
            raise ValueError('request byte admission')
        row = {'stage': stage, 'pre_hash': obs.canonical_hash, 'request': request,
               'request_sha256': digest(request), 'started_at': now(), 'status': 'started'}
        episode['calls'].append(row)
        report['calls'] += 1
        persist()
        try:
            result = service.complete(request)
            raw = result['content']
            if type(raw) is not str:
                raise ValueError('response type')
            blob = raw.encode()
            retained = blob[:MAX_RESPONSE_BYTES]
            row.update(status='received', returned_at=now(), response=retained.decode('utf-8', errors='replace'),
                       response_truncated=len(blob) > MAX_RESPONSE_BYTES,
                       response_sha256=hashlib.sha256(blob).hexdigest(),
                       response_bytes=len(blob), tokenizer_prompt_tokens=result['tokenizer_prompt_tokens'],
                       server_prompt_tokens=result['server_prompt_tokens'],
                       server_completion_tokens=result['server_completion_tokens'], finish_reason=result['finish_reason'])
            persist()  # Received bytes, count disagreement and finish reason survive any later check.
            check()
            if (len(blob) > MAX_RESPONSE_BYTES or row['tokenizer_prompt_tokens'] != row['server_prompt_tokens'] or
                    type(row['server_prompt_tokens']) is not int or not 0 < row['server_prompt_tokens'] <= 60000 or
                    type(row['server_completion_tokens']) is not int or
                    not 0 < row['server_completion_tokens'] <= request['max_tokens']):
                raise ValueError('response/token audit')
            if row['finish_reason'] != 'stop':
                raise ValueError('non-stop response')
            if row['server_prompt_tokens'] + request['max_tokens'] > 65536:
                raise ValueError('context ceiling')
            report['prompt_tokens'] += row['server_prompt_tokens']
            report['completion_tokens'] += row['server_completion_tokens']
            if report['prompt_tokens'] > 720000 or report['completion_tokens'] > 1536:
                raise ValueError('total token ceiling')
            value = (parse_policy(raw, 'control' if stage == 'control' else 'target', obs.available_actions,
                                  obs.latest_frame.tolist()) if stage in ('control', 'target') else
                     parse_audit(raw, stage, obs.frames))
            row['status'] = 'valid'
            persist()
            return value
        except Exception as exc:
            if hasattr(exc, 'response_evidence'):
                row['bridge_response_evidence'] = exc.response_evidence
            row.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:200])
            persist()
            raise

    persist()
    try:
        # Bootstrap both arms before either policy call; prevent an unequal pair.
        for arm in ('control', 'target'):
            check()
            adapter = adapter_factory(arm)
            adapters[arm] = adapter
            episode = {'arm': arm, 'initial': None, 'calls': [], 'steps': [], 'final': None,
                       'status': 'opening', 'cleanup': None}
            report['episodes'].append(episode)
            persist()
            obs = adapter.bootstrap()
            episode.update(initial=pack(obs), status='bootstrapped')
            persist()
        first, second = (unpack(ep['initial']) for ep in report['episodes'])
        if (first.canonical_hash != second.canonical_hash or first.canonical_hash != frozen['initial_canonical_hash'] or
                not first.full_reset or not second.full_reset):
            raise ValueError('initial-state equality')
        for ep in report['episodes']:
            obs = unpack(ep['initial'])
            runtime = GameRuntimeState(obs, action_budget_limit=MAX_STEPS)
            adapter = adapters[ep['arm']]
            for index in range(MAX_STEPS):
                check()
                if obs.state.value in ('WIN', 'GAME_OVER') or obs.levels_completed > first.levels_completed:
                    break
                stage = ep['arm']
                decision = call(ep, stage, policy_request(runtime, stage), obs)
                action = decision['action']
                prediction = call(ep, 'prediction', audit_request('prediction', pack(obs), action), obs)
                step = {'index': index, 'before': pack(obs), 'decision_call': len(ep['calls']) - 2,
                        'prediction_call': len(ep['calls']) - 1, 'action': action, 'prediction': prediction,
                        'target': decision.get('target'), 'status': 'intent_retained', 'committed_at': now()}
                ep['steps'].append(step)
                persist()  # Action and prediction are durable before dispatch.
                check()
                step['dispatch_started_at'] = now()
                step['status'] = 'dispatch_entered'
                report['dispatches'] += 1
                persist()
                post, receipt = adapter.dispatch(action, obs)
                step.update(status='acknowledged', receipt=receipt, after=pack(post), returned_at=now())
                persist()
                check()
                feedback = call(ep, 'feedback', audit_request('feedback', pack(post), action,
                                                             before=pack(obs), prediction=prediction), post)
                step['feedback_call'] = len(ep['calls']) - 1
                step['feedback'] = feedback
                persist()
                runtime.counters.conservative_spent_actions += 1
                runtime.replace_observation(post, action_id=action['action_id'],
                                            action_data=action['action_data'], transition_id=ep['arm'] + str(index))
                obs = post
            ep['final'] = pack(obs)
            ep['status'] = 'complete'
            persist()
        report['status'] = 'complete'
    except Exception as exc:
        report.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
    finally:
        for ep in report['episodes']:
            adapter = adapters.get(ep['arm'])
            if adapter is not None:
                try:
                    ep['cleanup'] = adapter.close()
                except Exception as exc:
                    ep['cleanup'] = {'closed': False, 'error': type(exc).__name__ + ': ' + str(exc)[:160]}
                    report.update(status='failed', error='cleanup failure')
                persist()
        report['ended_at'] = now()
        persist()
    return report
