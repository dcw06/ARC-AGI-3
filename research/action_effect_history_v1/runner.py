"""Two-block action-effect-history comparison runner (CPU-rehearsable; no launch authority here).

Evidence discipline follows Stage B: intent is durable before every call and dispatch, and received
bytes are durable before validation. Differences from Stage B: twelve isolated episodes, per-episode
stop reasons, pair admission against a frozen allowance, a run deadline enforced even mid-pair, and
accounting for every attempted episode.
"""
import hashlib
import json
import os
import time
from pathlib import Path

from research.action_effect_v1.records import effect_record, EffectHistory
from research.action_effect_history_v1.contract import policy_request

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = Path(__file__).with_name('protocol.json')
VERSION = 'action_effect_history_run_v1'
TERMINAL_EPISODE = ('action_cap', 'win', 'game_over', 'invalid_output', 'dispatch_failure')


class DeadlineExceeded(Exception):
    pass


class TechnicalFailure(Exception):
    pass


class DispatchRejected(Exception):
    """The request was refused before reaching the game (definitely not applied)."""


def protocol():
    return json.loads(PROTOCOL.read_bytes())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, separators=(',', ':'))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def index_view(report):
    """The run index: everything except episode bodies, which live in their own files."""
    return {**{k: v for k, v in report.items() if k != 'episodes'},
            'episodes': [{'episode_id': e['episode_id'], 'status': e['status'], 'stop_reason': e['stop_reason']}
                         for e in report['episodes']]}


def load(folder):
    """Reassemble the full report from the index and per-episode files."""
    folder = Path(folder)
    index = json.loads((folder / 'run.json').read_bytes())
    episodes = [json.loads((folder / 'episodes' / (e['episode_id'] + '.json')).read_bytes()) for e in index['episodes']]
    return {**index, 'episodes': episodes}


def pack(obs):
    from certification.phase4_transient_v2.contract import pack as frozen_pack
    return frozen_pack(obs)


def parse_action(raw, legal):
    from certification.phase4_transient_v2.action_contract import validate_action
    return validate_action(raw, legal)['action']


def run(path, service, adapter_factory, *, deadline_seconds=3000, kind='scripted_cpu_only',
        clock=time.monotonic, writer=save, spec=None):
    """Run the frozen schedule. `adapter_factory(game_id, arm, episode_id)` returns a fresh adapter with
    bootstrap() -> Observation, dispatch(action, before) -> (Observation, receipt), close() -> dict."""
    spec = spec or protocol()
    limits = spec['limits']
    cases = {c['game_id']: c for c in spec['cases']}
    started = clock()
    deadline = started + deadline_seconds
    report = {'version': VERSION, 'kind': kind, 'status': 'running', 'error': None,
              'protocol_sha256': digest(spec), 'deadline_seconds': deadline_seconds,
              'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0}

    folder = Path(path)

    def persist(episode=None):
        # Bounded writes: the small index always, plus only the episode that changed.
        if episode is not None:
            writer(folder / 'episodes' / (episode['episode_id'] + '.json'), episode)
        writer(folder / 'run.json', index_view(report))

    def now():
        return round(clock() - started, 6)

    def check():
        if clock() >= deadline:
            raise DeadlineExceeded('run deadline')

    def call(episode, request, obs):
        check()
        if report['calls'] >= limits['maximum_policy_calls']:
            raise TechnicalFailure('policy call ceiling')
        row = {'request': request, 'request_sha256': digest(request), 'pre_hash': obs.canonical_hash,
               'started_at': now(), 'status': 'started'}
        episode['calls'].append(row)
        report['calls'] += 1
        persist(episode)
        try:
            result = service.complete(request)
        except Exception as exc:
            evidence = getattr(exc, 'response_evidence', None)
            row.update(status='transport_failure', returned_at=now(), error=type(exc).__name__ + ': ' + str(exc)[:200],
                       response_evidence=evidence)
            persist(episode)
            raise TechnicalFailure('model transport') from exc
        raw = result['content']
        blob = raw.encode() if type(raw) is str else b''
        row.update(status='received', returned_at=now(), response=blob[:limits['max_response_bytes']].decode('utf-8', errors='replace'),
                   response_bytes=len(blob), response_sha256=hashlib.sha256(blob).hexdigest(),
                   response_truncated=len(blob) > limits['max_response_bytes'],
                   tokenizer_prompt_tokens=result.get('tokenizer_prompt_tokens'),
                   server_prompt_tokens=result.get('server_prompt_tokens'),
                   server_completion_tokens=result.get('server_completion_tokens'), finish_reason=result.get('finish_reason'))
        persist(episode)  # received evidence survives every later check
        p, c = row['server_prompt_tokens'], row['server_completion_tokens']
        if (type(raw) is not str or row['response_truncated'] or type(p) is not int or p != row['tokenizer_prompt_tokens']
                or not 0 < p <= limits['live_prompt_token_ceiling'] or type(c) is not int or not 0 < c <= request['max_tokens']):
            row['status'] = 'audit_failure'
            persist(episode)
            raise TechnicalFailure('response/token audit')
        report['prompt_tokens'] += p
        report['completion_tokens'] += c
        check()
        try:
            if row['finish_reason'] != 'stop':
                raise ValueError('non-stop finish')
            action = parse_action(raw, obs.available_actions)
        except (ValueError, KeyError, TypeError) as exc:
            row.update(status='invalid_output', error=str(exc)[:200])
            persist(episode)
            return None
        row['status'] = 'valid'
        persist(episode)
        return action

    def episode_run(pair, arm, index):
        game_id = pair['game_id']
        episode_id = f"{pair['pair_id']}-{arm}"
        episode = {'episode_id': episode_id, 'pair_id': pair['pair_id'], 'block': pair['block'], 'game_id': game_id,
                   'arm': arm, 'order_in_pair': index, 'status': 'opening', 'stop_reason': None, 'initial': None,
                   'calls': [], 'steps': [], 'cleanup': None, 'started_at': now()}
        report['episodes'].append(episode)
        persist(episode)
        adapter = None
        try:
            check()
            adapter = adapter_factory(game_id, arm, episode_id)
            obs = adapter.bootstrap()
            episode['initial'] = pack(obs)
            if obs.canonical_hash != cases[game_id]['initial_canonical_hash'] or not obs.full_reset:
                raise TechnicalFailure('initial state differs from the frozen case')
            episode['status'] = 'running'
            persist(episode)
            from agent.state import GameRuntimeState
            runtime = GameRuntimeState(obs, action_budget_limit=limits['actions_per_episode'])
            history = EffectHistory(limit=16)  # isolated per episode and arm
            for step_index in range(limits['actions_per_episode']):
                check()
                if obs.state.value == 'WIN':
                    episode['stop_reason'] = 'win'
                    break
                if obs.state.value == 'GAME_OVER':
                    episode['stop_reason'] = 'game_over'
                    break
                request = policy_request(runtime, arm, history if arm == 'history' else None, seed=limits['request_seed'])
                action = call(episode, request, obs)
                if action is None:
                    episode['stop_reason'] = 'invalid_output'
                    break
                step = {'index': step_index, 'call_index': len(episode['calls']) - 1, 'before': pack(obs),
                        'action': action, 'status': 'dispatch_entered', 'dispatch_started_at': now()}
                episode['steps'].append(step)
                report['dispatches'] += 1
                persist(episode)  # intent durable before dispatch
                try:
                    post, receipt = adapter.dispatch(action, obs)
                except DispatchRejected as exc:
                    outcome = {'status': 'dispatch_failed', 'error': type(exc).__name__ + ': ' + str(exc)[:200]}
                    post = None
                except Exception as exc:  # sent but not observed: never a no-op
                    outcome = {'status': 'outcome_unknown', 'reason': type(exc).__name__ + ': ' + str(exc)[:200]}
                    post = None
                else:
                    if not post.frames:
                        outcome = {'status': 'outcome_unknown', 'reason': 'acknowledged without frames'}
                        post = None
                    else:
                        outcome = {'status': 'acknowledged', 'post': pack(post)}
                        step['receipt'] = receipt
                record = effect_record(step['before'], action, outcome)
                entry = history.append(record)
                step.update(status=outcome['status'], effect_record=record, history_entry=entry, returned_at=now(),
                            after=outcome.get('post'))
                persist(episode)
                if outcome['status'] != 'acknowledged':
                    episode['stop_reason'] = 'dispatch_failure'
                    break
                runtime.counters.conservative_spent_actions += 1
                runtime.replace_observation(post, action_id=action['action_id'], action_data=action['action_data'],
                                            transition_id=f'{episode_id}-{step_index}')
                obs = post
            else:
                # The cap was reached; a terminal state produced by the last action takes precedence.
                episode['stop_reason'] = {'WIN': 'win', 'GAME_OVER': 'game_over'}.get(obs.state.value, 'action_cap')
            episode['status'] = 'complete'
            episode['final'] = pack(obs)
        except DeadlineExceeded:
            episode.update(status='interrupted', stop_reason='interrupted')
            raise
        except TechnicalFailure as exc:
            episode.update(status='technical_failure', stop_reason='technical_failure', error=str(exc)[:200])
            raise
        except Exception as exc:
            episode.update(status='technical_failure', stop_reason='technical_failure',
                           error=type(exc).__name__ + ': ' + str(exc)[:200])
            raise TechnicalFailure('episode') from exc
        finally:
            episode['ended_at'] = now()
            if adapter is not None:
                try:
                    episode['cleanup'] = adapter.close()
                except Exception as exc:
                    episode['cleanup'] = {'closed': False, 'error': type(exc).__name__ + ': ' + str(exc)[:200]}
            persist(episode)
        return episode

    persist()
    try:
        for pair in spec['schedule']:
            remaining = deadline - clock()
            entry = {'pair_id': pair['pair_id'], 'block': pair['block'], 'game_id': pair['game_id'],
                     'order': pair['order'], 'remaining_seconds_at_admission': round(remaining, 3)}
            report['pairs'].append(entry)
            if remaining < limits['pair_admission_seconds']:
                entry['status'] = 'not_admitted'
                persist()
                continue  # later pairs are recorded as not admitted too
            entry['status'] = 'running'
            persist()
            for index, arm in enumerate(pair['order']):
                episode_run(pair, arm, index)
            entry['status'] = 'complete'
            persist()
        report['status'] = 'complete'
    except DeadlineExceeded:
        report.update(status='deadline_exceeded', error='run deadline enforced')
        if report['pairs'] and report['pairs'][-1].get('status') == 'running':
            report['pairs'][-1]['status'] = 'interrupted'
    except TechnicalFailure as exc:
        report.update(status='technical_failure', error=str(exc)[:200])
        if report['pairs'] and report['pairs'][-1].get('status') == 'running':
            report['pairs'][-1]['status'] = 'interrupted'
    finally:
        # Every scheduled pair appears exactly once, with a status.
        seen = {p['pair_id'] for p in report['pairs']}
        for pair in spec['schedule']:
            if pair['pair_id'] not in seen:
                report['pairs'].append({'pair_id': pair['pair_id'], 'block': pair['block'], 'game_id': pair['game_id'],
                                        'order': pair['order'], 'status': 'not_started'})
        report['ended_at'] = now()
        persist()
    return report
