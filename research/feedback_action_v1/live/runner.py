# Derived from research/action_effect_history_v1/runner.py by research/feedback_action_v1/derive.py; edit the derivation, not this file.
"""Feedback-action v1 comparison runner, one block per session (CPU-rehearsable; no launch authority here).

Evidence discipline follows Stage B: intent is durable before every call and dispatch, and received
bytes are durable before validation. Differences from Stage B: six isolated episodes per session (one block), per-episode
stop reasons, pair admission against a frozen allowance, a run deadline enforced even mid-pair, and
accounting for every attempted episode.
"""
from fractions import Fraction
import hashlib
import json
import os
import time
from pathlib import Path

from research.feedback_action_v1.live.policy import EpisodePolicy, raw_transition

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = Path(__file__).with_name('protocol.json')
VERSION = 'feedback_action_run_v1'
TERMINAL_EPISODE = ('action_cap', 'decision_cap', 'win', 'game_over', 'dispatch_failure')  # an invalid output never ends an episode


class DeadlineExceeded(Exception):
    pass


class TechnicalFailure(Exception):
    pass


class DispatchRejected(Exception):
    """The request was refused before reaching the game (definitely not applied)."""


class SessionAbort(Exception):
    """A session-abort rule fired (protocol v2 §10: F2a invalid outputs, F5 dispatch failures). The session stops
    at once: no further call, dispatch or episode; partial evidence is kept; the run is never complete."""

    def __init__(self, rule, counts):
        super().__init__(rule)
        self.rule, self.record = rule, {'rule': rule, **counts}


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
    """Reassemble and verify the full report (manifest hashes, inventory, index agreement)."""
    from research.feedback_action_v1.live.evidence import load_verified
    return load_verified(folder)


def pack(obs):
    from certification.phase4_transient_v2.contract import pack as frozen_pack
    return frozen_pack(obs)


def parse_action(raw, legal, request):
    """The adapter's parse for the request's arm; both arms share the frozen action validator."""
    from research.feedback_action_v1.live.policy import parse_action as arm_parse
    return arm_parse(raw, legal, request)


def run(path, service, adapter_factory, *, deadline_seconds=3000, kind='scripted_cpu_only',
        clock=time.monotonic, writer=None, spec=None, evidence_budget_bytes=64 * 1024**2, cancel=None,
        evidence_lock_root=None):
    """Run the frozen schedule. `adapter_factory(game_id, arm, episode_id)` returns a fresh adapter with
    bootstrap() -> Observation, dispatch(action, before) -> (Observation, receipt), close() -> dict."""
    spec = spec or protocol()
    limits = spec['limits']
    cases = {c['game_id']: c for c in spec['cases']}
    started = clock()
    deadline = started + deadline_seconds
    report = {'version': VERSION, 'kind': kind, 'status': 'running', 'error': None,
              'protocol_sha256': digest(spec), 'deadline_seconds': deadline_seconds,
              'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
              'abort': None}
    online = {'arm_calls': {}, 'arm_invalid': {}, 'dispatched': 0, 'dispatch_failures': 0}  # session-abort counters

    folder = Path(path)
    if writer is None:
        from research.feedback_action_v1.live.evidence import RunEvidence
        writer = RunEvidence(folder, evidence_budget_bytes, lock_root=evidence_lock_root)

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
        if cancel is not None and Path(cancel).exists():
            raise DeadlineExceeded('supervisor cancellation')

    def abort_check_call(episode, invalid):
        """F2a, online after every policy call: per arm, over that arm's first `invalid_output_calls` calls in this
        session; abort at the call that makes invalid outputs exceed `invalid_output_rate` of that window (then the
        window's rate is certain to exceed it). Calls after the window never count."""
        rule = limits['session_abort']
        arm, window = episode['arm'], rule['invalid_output_calls']
        n = online['arm_calls'][arm] = online['arm_calls'].get(arm, 0) + 1
        if invalid and n <= window:
            online['arm_invalid'][arm] = online['arm_invalid'].get(arm, 0) + 1
        bad = online['arm_invalid'].get(arm, 0)
        if bad > Fraction(rule['invalid_output_rate']) * window:
            raise SessionAbort('F2a_invalid_outputs', {
                'arm': arm, 'invalid_outputs_in_window': bad, 'arm_calls': n, 'window_calls': window,
                'threshold_rate': rule['invalid_output_rate'], 'episode_id': episode['episode_id']})

    def abort_check_dispatch(episode, outcome):
        """F5, online after every dispatch: the whole session (both arms); abort when failed plus unknown dispatches
        exceed `dispatch_failure_rate` of the dispatches so far."""
        rule = limits['session_abort']
        online['dispatched'] += 1
        if outcome['status'] != 'acknowledged':
            online['dispatch_failures'] += 1
        floor = rule.get('dispatch_denominator_floor', 0)  # 0 unless the owner gate records the floor option
        if online['dispatch_failures'] > Fraction(rule['dispatch_failure_rate']) * max(online['dispatched'], floor):
            raise SessionAbort('F5_dispatch_failures', {
                'dispatch_failures': online['dispatch_failures'], 'dispatched': online['dispatched'],
                'threshold_rate': rule['dispatch_failure_rate'], 'denominator_floor': floor,
                'episode_id': episode['episode_id']})

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
            interrupted = clock() >= deadline or (cancel is not None and Path(cancel).exists())
            row.update(status='interrupted' if interrupted else 'transport_failure', returned_at=now(),
                       error=type(exc).__name__ + ': ' + str(exc)[:200], response_evidence=evidence)
            persist(episode)
            if interrupted:  # the bridge refused because the run was being stopped: an interruption, not a model fault
                raise DeadlineExceeded('supervisor cancellation' if clock() < deadline else 'run deadline') from exc
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
            action = parse_action(raw, obs.available_actions, request)
        except (ValueError, KeyError, TypeError) as exc:
            row.update(status='invalid_output', error=str(exc)[:200])
            persist(episode)
            abort_check_call(episode, True)
            return None
        row['status'] = 'valid'
        persist(episode)
        abort_check_call(episode, False)
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
            policy = EpisodePolicy(arm, episode_id, seed=limits['request_seed'])  # isolated per episode and arm
            episode['model_statements'] = policy.statements
            step_index = 0
            while True:
                check()
                if obs.state.value == 'WIN':
                    episode['stop_reason'] = 'win'
                    break
                if obs.state.value == 'GAME_OVER':
                    episode['stop_reason'] = 'game_over'
                    break
                if step_index >= limits['actions_per_episode']:
                    episode['stop_reason'] = 'action_cap'
                    break
                if len(episode['calls']) >= limits['decision_calls_per_episode']:
                    episode['stop_reason'] = 'decision_cap'  # everything retained; the schedule continues
                    break
                request = policy.request(runtime, obs)
                action = call(episode, request, obs)
                policy.decided(episode['calls'][-1], obs)
                if action is None:
                    persist(episode)
                    continue  # an invalid output consumes a call, never an action
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
                raw = raw_transition(episode_id, step_index, step['before'], action, outcome)
                record = policy.dispatched(raw)
                step.update(status=outcome['status'], raw_transition=raw, record_id=record['identity']['record_id'],
                            returned_at=now(), after=outcome.get('post'))
                persist(episode)
                abort_check_dispatch(episode, outcome)
                if outcome['status'] != 'acknowledged':
                    episode['stop_reason'] = 'dispatch_failure'
                    break
                runtime.counters.conservative_spent_actions += 1
                runtime.replace_observation(post, action_id=action['action_id'], action_data=action['action_data'],
                                            transition_id=f'{episode_id}-{step_index}')
                obs = post
                step_index += 1  # terminal states are checked before the caps at the top of the loop
            episode['status'] = 'complete'
            episode['final'] = pack(obs)
        except DeadlineExceeded:
            episode.update(status='interrupted', stop_reason='interrupted')
            raise
        except SessionAbort as exc:
            episode.update(status='aborted', stop_reason='session_abort', abort=exc.record)
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
        # Reached only when play itself ended normally: an unclosed client or scorecard is a technical failure.
        if adapter is None or not isinstance(episode['cleanup'], dict) or episode['cleanup'].get('closed') is not True:
            episode.update(play_stop_reason=episode['stop_reason'], status='technical_failure',
                           stop_reason='technical_failure', error='client/scorecard closure failed')
            persist(episode)
            raise TechnicalFailure('client/scorecard closure failed')
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
        # Complete only when every scheduled pair ran to completion; unadmitted pairs make the run incomplete.
        report['status'] = 'complete' if all(p['status'] == 'complete' for p in report['pairs']) else 'incomplete'
    except DeadlineExceeded as exc:
        canceled = 'cancellation' in str(exc)
        report.update(status='canceled' if canceled else 'deadline_exceeded',
                      error='supervisor cancellation' if canceled else 'run deadline enforced')
        if report['pairs'] and report['pairs'][-1].get('status') == 'running':
            report['pairs'][-1]['status'] = 'interrupted'
    except SessionAbort as exc:  # never complete; later pairs are recorded as not started
        report.update(status='aborted', error='session abort: ' + exc.rule, abort=exc.record)
        if report['pairs'] and report['pairs'][-1].get('status') == 'running':
            report['pairs'][-1]['status'] = 'interrupted'
    except TechnicalFailure as exc:
        report.update(status='technical_failure', error=str(exc)[:200])
        if report['pairs'] and report['pairs'][-1].get('status') == 'running':
            report['pairs'][-1]['status'] = 'interrupted'
    except Exception as exc:  # e.g. StorageExhausted raised while checkpointing an episode
        report.update(status='technical_failure', error=type(exc).__name__ + ': ' + str(exc)[:200])
        if report['pairs'] and report['pairs'][-1].get('status') == 'running':
            report['pairs'][-1]['status'] = 'interrupted'
        if report['episodes'] and report['episodes'][-1]['status'] in ('opening', 'running', 'complete'):
            report['episodes'][-1].setdefault('evidence_error', type(exc).__name__)
    finally:
        # Every scheduled pair appears exactly once, with a status.
        seen = {p['pair_id'] for p in report['pairs']}
        for pair in spec['schedule']:
            if pair['pair_id'] not in seen:
                report['pairs'].append({'pair_id': pair['pair_id'], 'block': pair['block'], 'game_id': pair['game_id'],
                                        'order': pair['order'], 'status': 'not_started'})
        report['ended_at'] = now()
        try:
            persist()
        except Exception as exc:  # e.g. storage exhausted: keep the failure visible, never mask the first error
            report['evidence_error'] = type(exc).__name__ + ': ' + str(exc)[:200]
            if report['status'] == 'complete':
                report['status'] = 'technical_failure'
    return report
