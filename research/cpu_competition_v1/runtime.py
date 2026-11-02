"""Sequential, bounded CPU competition worker; never imports or installs a model."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import threading
import time
from types import SimpleNamespace

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from arcengine import GameState
from agent.action import ActionDecision
from agent.controller import DeterministicFallback
from agent.framework_adapter import OutcomeUnknown, RemoteFrameworkAdapter
from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_overfit_v1.policy import OverfitPolicy


class DeadlineSession(requests.Session):
    """No retries/redirects, with one absolute deadline over the complete response."""
    def __init__(self, deadline, *, now=time.monotonic):
        super().__init__()
        self.deadline, self.now = deadline, now
        retry = Retry(total=0, connect=0, read=0, redirect=0, status=0)
        self.mount('http://', HTTPAdapter(max_retries=retry))
        self.mount('https://', HTTPAdapter(max_retries=retry))

    def request(self, method, url, **kwargs):
        if threading.current_thread() is not threading.main_thread() or not hasattr(signal, 'setitimer'):
            raise RuntimeError('absolute HTTP deadlines require the sequential Linux main thread')
        if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
            raise RuntimeError('unexpected active alarm in CPU HTTP worker')
        bound = self.deadline() if callable(self.deadline) else self.deadline
        deadline = min(bound, self.now() + 20.0)
        remaining = deadline - self.now()
        if not math.isfinite(remaining) or remaining <= 0:
            raise TimeoutError('HTTP admission closed')
        kwargs.update(timeout=remaining, allow_redirects=False, stream=False)
        previous = signal.getsignal(signal.SIGALRM)
        def expired(_signum, _frame):
            raise TimeoutError('absolute HTTP response deadline')
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, remaining)
        try:
            response = super().request(method, url, **kwargs)
            if self.now() >= deadline:
                response.close()
                raise TimeoutError('HTTP response completed late')
            return response
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)


def normalize(observation):
    """The fitted policy sees the final displayed board, with no GUID or metadata."""
    legal = list(observation.available_actions)
    if (any(type(a) is not int or not 0 <= a <= 7 for a in legal) or
            len(legal) != len(set(legal)) or type(observation.levels_completed) is not int or
            observation.levels_completed < 0 or not isinstance(observation.state, GameState)):
        raise ValueError('invalid observation contract')
    return dict(grid=observation.latest_frame.tolist(), state=observation.state.value,
                levels_completed=observation.levels_completed, legal_actions=sorted(legal))


class _AdmissionClosed(Exception):
    pass


def wait_for_inventory(adapter, *, deadline, now=time.monotonic, sleep=time.sleep, log=None):
    """Poll only the safe inventory GET while the internal gateway starts.

    The production adapter's callbacks narrow its absolute HTTP deadline for
    this phase. No scorecard, bootstrap or action POST is retried here.
    """
    bound = min(deadline, now()+600.0)
    attempts = 0
    if log is not None:
        log(dict(phase='gateway_readiness_start', maximum_seconds=max(0, bound-now())))
    begin = getattr(adapter, 'begin_readiness', None)
    end = getattr(adapter, 'end_readiness', None)
    if begin is not None:
        begin(bound)
    try:
        while True:
            if now() >= bound:
                raise TimeoutError('gateway readiness deadline')
            attempts += 1
            try:
                games = adapter.list_game_ids()
            except requests.HTTPError as exc:
                response = exc.response
                status = None if response is None else response.status_code
                if response is not None:
                    response.close()
                if status not in (429, 500, 502, 503, 504):
                    raise
                error_type = 'HTTPError'
            except (requests.ConnectionError, requests.Timeout, TimeoutError) as exc:
                error_type = type(exc).__name__
            else:
                if now() >= bound:
                    raise TimeoutError('gateway inventory arrived after readiness deadline')
                if log is not None:
                    log(dict(phase='gateway_ready', GET_attempts=attempts))
                return games
            if log is not None:
                log(dict(phase='gateway_readiness_retry', GET_attempts=attempts,
                         error_type=error_type))
            remaining = bound-now()
            if remaining <= 0:
                raise TimeoutError('gateway readiness deadline')
            sleep(min(1.0, remaining))
    finally:
        if end is not None:
            end()


def run(adapter, program, *, work_deadline, now=time.monotonic,
        max_games=110, max_actions=80, gate=None, sleep=time.sleep, log=None):
    """One scorecard and one bootstrap per game; ambiguous work is never retried."""
    if (type(max_games) is not int or not 1 <= max_games <= 110 or
            type(max_actions) is not int or not 1 <= max_actions <= 80):
        raise ValueError('CPU competition limits differ')
    OverfitPolicy(program)  # Validate before the first provider-facing operation.
    def admit():
        if gate is not None:
            gate()
        if now() >= work_deadline:
            raise _AdmissionClosed()
    admit()
    games = wait_for_inventory(adapter, deadline=work_deadline, now=now, sleep=sleep, log=log)
    if (not isinstance(games, (list, tuple)) or not games or len(games) > max_games or
            any(type(game) is not str or not game.strip() for game in games) or
            len(games) != len(set(games))):
        raise ValueError('invalid competition inventory')
    summary = dict(available_games=len(games), attempted_games=0, fitted_games=0,
        fitted_three_level_completions=0, levels_completed=0, actions_admitted=0,
        actions_acknowledged=0, ambiguous_actions=0, bootstrap_failures=0,
        fitted_mismatches=0, stopped_games=0, closed_verified=False,
        finalization_status='not_opened', model_generations=0, automatic_retries=0)
    opened = False
    try:
        admit()
        adapter.open_scorecard(tags=['cpu-ls20-memorized-plus-e0-v1'])
        opened = True
        for game_id in games:
            admit()
            client, observation, fitted = None, None, None
            try:
                summary['attempted_games'] += 1
                try:
                    client = adapter.bootstrap(game_id)
                except Exception:
                    summary['bootstrap_failures'] += 1
                    continue
                observation = client.observation
                if observation.game_id != game_id or type(observation.guid) is not str or not observation.guid:
                    raise ValueError('bootstrap identity differs')
                initial = normalize(observation)
                if game_id == program['game_id'] and digest(initial) == digest(program['initial_observation']):
                    fitted = OverfitPolicy(program)
                    summary['fitted_games'] += 1
                baseline = DeterministicFallback()
                cap = len(program['steps']) if fitted is not None else max_actions
                for index in range(cap):
                    if observation.state in (GameState.WIN, GameState.GAME_OVER):
                        break
                    if not any(action != 0 for action in observation.available_actions):
                        break
                    admit()
                    if fitted is not None:
                        action = fitted.select(game_id, normalize(observation))
                        decision = ActionDecision(action_id=action['action_id'], action_data=action['action_data'],
                            source='ls20_memorized_three_levels', decision_id=f'fitted:{index}')
                    else:
                        decision = baseline.propose(SimpleNamespace(observation=observation))
                    if (type(decision.action_id) is not int or decision.action_id == 0 or
                            decision.action_id not in observation.available_actions):
                        raise ValueError('policy proposed a reset or illegal action')
                    admit()  # Includes time spent selecting, immediately before dispatch.
                    summary['actions_admitted'] += 1
                    try:
                        after = adapter.dispatch(client, decision)
                    except OutcomeUnknown:
                        summary['ambiguous_actions'] += 1
                        client.quarantined = True
                        break
                    summary['actions_acknowledged'] += 1
                    if after.guid != observation.guid or after.game_id != game_id:
                        raise ValueError('acknowledged observation identity differs')
                    normalize(after)
                    observation = after
                    if fitted is not None:
                        fitted.acknowledge(action, normalize(after))
                        if fitted.completed:
                            summary['fitted_three_level_completions'] += 1
                            break
            except _AdmissionClosed:
                raise
            except Exception:
                if fitted is not None:
                    summary['fitted_mismatches'] += 1
                summary['stopped_games'] += 1
            finally:
                if observation is not None:
                    summary['levels_completed'] += observation.levels_completed
                if client is not None:
                    try:
                        adapter.finalize_client(client)
                    except Exception:
                        summary['client_cleanup_failed'] = True
                        raise
    except _AdmissionClosed:
        summary['admission_closed'] = True
    except Exception as exc:
        summary['error_type'] = type(exc).__name__
    finally:
        if opened:
            try:
                cleanup = getattr(adapter, 'begin_cleanup', None)
                if cleanup is not None:
                    cleanup()
                adapter.close_scorecard()
                summary.update(closed_verified=not summary.get('client_cleanup_failed', False),
                               finalization_status='acknowledged')
            except Exception as exc:
                summary.update(finalization_status='unknown', error_type=type(exc).__name__)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program', required=True, type=Path)
    parser.add_argument('--work-seconds', type=int, default=3000)
    parser.add_argument('--final-seconds', type=int, default=3300)
    args = parser.parse_args()
    if not os.environ.get('KAGGLE_IS_COMPETITION_RERUN'):
        raise PermissionError('CPU competition worker requires the scored rerun')
    if not 1 <= args.work_seconds < args.final_seconds <= 3300:
        raise ValueError('CPU deadline envelope differs')
    started = time.monotonic()
    work_deadline, final_deadline = started + args.work_seconds, started + args.final_seconds
    phase = {'cleanup': False, 'readiness_deadline': work_deadline}
    deadline = lambda: final_deadline if phase['cleanup'] else min(work_deadline, phase['readiness_deadline'])
    adapter = RemoteFrameworkAdapter(base_url='http://gateway:8001',
        api_key='test-key-123', competition_mode=True,
        session_factory=lambda: DeadlineSession(deadline))
    adapter.begin_cleanup = lambda: phase.update(cleanup=True)
    adapter.begin_readiness = lambda bound: phase.update(readiness_deadline=bound)
    adapter.end_readiness = lambda: phase.update(readiness_deadline=work_deadline)
    def milestone(value):
        print(json.dumps(value, sort_keys=True), flush=True)
    try:
        result = run(adapter, json.loads(args.program.read_bytes()), work_deadline=work_deadline,
                     log=milestone)
    except BaseException as exc:
        milestone(dict(phase='CPU_worker_error', error_type=type(exc).__name__))
        raise
    finally:
        adapter._master_session.close()
    result['elapsed_seconds'] = time.monotonic() - started
    if time.monotonic() >= final_deadline:
        result.update(closed_verified=False, error_type='FinalDeadlineExceeded')
    print(json.dumps(result, sort_keys=True), flush=True)
    if not result['closed_verified'] or result.get('error_type'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
