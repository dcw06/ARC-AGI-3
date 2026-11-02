"""Synthetic submission-contract tests; no engine, provider, model or game files.

The tiny memorized program below has three transitions, rather than using the
real demonstration. Adapter calls are recorded so legal bounds, deadline
admission and single-use lifecycle rules can be checked independently of the
runtime's summary counters.
"""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from arcengine import GameState

from agent.action import ActionDecision
from agent.controller import DeterministicFallback
from agent.framework_adapter import OutcomeUnknown
from agent.state import GameRuntimeState, Observation
from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_overfit_v1.policy import GAME_ID, QUALIFICATION
from research.cpu_competition_v1 import runtime


def observation(game_id='zz99-12345678', step=0, *, state=GameState.NOT_FINISHED,
                legal=(1, 2, 3, 4), levels=0, guid='synthetic-guid'):
    grid = np.full((64, 64), 3, dtype=np.uint8)
    grid[0, 0] = step
    grid[-1, -1] = 11 - min(step, 11)
    grid.setflags(write=False)
    return Observation(game_id=game_id, frames=(grid,), state=state,
                       levels_completed=levels, win_levels=7, guid=guid,
                       available_actions=legal)


def native(obs):
    return {'grid': obs.latest_frame.tolist(), 'state': obs.state.value,
            'levels_completed': obs.levels_completed,
            'legal_actions': sorted(obs.available_actions)}


def program():
    states = [observation(GAME_ID, step, levels=step) for step in range(4)]
    return {'schema': 'ls20_overfit_v1', 'game_id': GAME_ID, 'seed': 0,
            'goal_levels': 3, 'source_demo_sha256': 'a' * 64,
            'initial_observation': native(states[0]),
            'steps': [{'index': i, 'action': {'action_id': action, 'action_data': {}},
                       'before_sha256': digest(native(states[i])),
                       'after_sha256': digest(native(states[i + 1])),
                       'before_levels': i, 'after_levels': i + 1}
                      for i, action in enumerate((3, 1, 4))],
            'level_boundaries': [{'level': i, 'after_moves': i, 'moves': 1}
                                 for i in range(1, 4)],
            'qualification': QUALIFICATION}


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class Adapter:
    """Narrow fake of RemoteFrameworkAdapter, with one recorded call per effect."""
    def __init__(self, games=('zz99-12345678',), *, initial=None, after=None):
        self.games = games
        self.initial = initial or {}
        self.after = after or {}
        self.calls = []
        self.clients = {}
        self.decisions = []
        self.bootstrap_errors = {}
        self.dispatch_errors = {}
        self.finalize_error = None
        self.close_error = None
        self.inventory_error = None

    def list_game_ids(self):
        self.calls.append(('inventory',))
        if self.inventory_error:
            raise self.inventory_error
        return self.games

    def open_scorecard(self, tags=None):
        self.calls.append(('open',))
        return 'synthetic-card'

    def bootstrap(self, game_id):
        self.calls.append(('bootstrap', game_id))
        if game_id in self.bootstrap_errors:
            raise self.bootstrap_errors[game_id]
        self.assert_not_already_bootstrapped(game_id)
        client = SimpleNamespace(game_id=game_id,
                                 observation=self.initial.get(game_id, observation(game_id)),
                                 quarantined=False, closed=False, action_requests=0)
        self.clients[game_id] = client
        return client

    def assert_not_already_bootstrapped(self, game_id):
        if game_id in self.clients:
            raise AssertionError('runtime tried to bootstrap one environment twice')

    def dispatch(self, client, decision):
        self.calls.append(('dispatch', client.game_id, decision.action_id))
        self.decisions.append(decision)
        if client.closed or client.quarantined:
            raise AssertionError('dispatch after close or quarantine')
        client.action_requests += 1
        if client.game_id in self.dispatch_errors:
            client.quarantined = True
            raise self.dispatch_errors[client.game_id]
        sequence = self.after.get(client.game_id, ())
        if client.action_requests <= len(sequence):
            client.observation = sequence[client.action_requests - 1]
        return client.observation

    def finalize_client(self, client):
        self.calls.append(('finalize', client.game_id))
        client.closed = True
        if self.finalize_error:
            raise self.finalize_error

    def close_scorecard(self):
        self.calls.append(('close',))
        if self.close_error:
            raise self.close_error
        return {'score': 0.0, 'source': 'synthetic-fixture'}


class SubmissionContract(unittest.TestCase):
    def run_fixture(self, adapter=None, **kwargs):
        adapter = adapter or Adapter()
        clock = kwargs.pop('now', Clock())
        result = runtime.run(adapter, program(), work_deadline=10.0,
                             now=clock, **kwargs)
        return adapter, result

    def assert_lifecycle_once(self, adapter):
        self.assertEqual(adapter.calls.count(('open',)), 1)
        self.assertEqual(adapter.calls.count(('close',)), 1)
        bootstraps = [call[1] for call in adapter.calls if call[0] == 'bootstrap']
        self.assertEqual(len(bootstraps), len(set(bootstraps)))
        self.assertEqual([call for call in adapter.calls if call[0] == 'dispatch'
                          and call[2] == 0], [])

    def test_exact_memorized_initial_state_runs_three_steps_then_stops(self):
        adapter = Adapter((GAME_ID,), initial={GAME_ID: observation(GAME_ID)},
                          after={GAME_ID: [observation(GAME_ID, i, levels=i)
                                           for i in range(1, 4)]})
        adapter, result = self.run_fixture(adapter)
        self.assertEqual([d.action_id for d in adapter.decisions], [3, 1, 4])
        self.assertEqual(result['fitted_games'], 1)
        self.assertEqual(result['fitted_three_level_completions'], 1)
        self.assertEqual(result['levels_completed'], 3)
        self.assertEqual(result['actions_acknowledged'], 3)
        self.assert_lifecycle_once(adapter)

    def test_fitted_observation_mismatch_stops_without_fallback_or_retry(self):
        adapter = Adapter((GAME_ID,), initial={GAME_ID: observation(GAME_ID)},
                          after={GAME_ID: [observation(GAME_ID, 7, levels=1)]})
        adapter, result = self.run_fixture(adapter)
        self.assertEqual([d.action_id for d in adapter.decisions], [3])
        self.assertEqual(result['fitted_mismatches'], 1)
        self.assertEqual(result['fitted_three_level_completions'], 0)
        self.assert_lifecycle_once(adapter)

    def test_changed_initial_grid_or_version_does_not_use_memorized_actions(self):
        for game, initial in [(GAME_ID, observation(GAME_ID, 9)),
                              ('ls20-different', observation('ls20-different'))]:
            with self.subTest(game=game):
                adapter = Adapter((game,), initial={game: initial})
                adapter, result = self.run_fixture(adapter, max_actions=2)
                expected_state = GameRuntimeState(initial)
                fallback = DeterministicFallback()
                expected = [fallback.propose(expected_state) for _ in range(2)]
                self.assertEqual([(d.action_id, dict(d.action_data)) for d in adapter.decisions],
                                 [(d.action_id, dict(d.action_data)) for d in expected])
                self.assertEqual(result['fitted_games'], 0)

    def test_all_unseen_games_use_the_unchanged_e0_policy(self):
        games = ('aa11-00000000', 'bb22-11111111', 'cc33-22222222')
        initial = {game: observation(game, legal=(1, 2, 3, 4, 5, 6, 7),
                                     guid=f'guid-{index}')
                   for index, game in enumerate(games)}
        adapter, result = self.run_fixture(Adapter(games, initial=initial), max_actions=4)
        expected = []
        fallback = DeterministicFallback()
        for game in games:
            state = GameRuntimeState(initial[game])
            for _ in range(4):
                d = fallback.propose(state)
                expected.append((d.action_id, dict(d.action_data)))
        self.assertEqual([(d.action_id, dict(d.action_data)) for d in adapter.decisions], expected)
        self.assertEqual(result['attempted_games'], 3)
        self.assertEqual(result['actions_acknowledged'], 12)
        self.assertEqual(result['fitted_games'], 0)
        self.assert_lifecycle_once(adapter)

    def test_game_cap_is_enforced_before_bootstrap(self):
        adapter = Adapter(('aa11-1', 'bb22-2', 'cc33-3'))
        with self.assertRaises(ValueError):
            self.run_fixture(adapter, max_games=2, max_actions=1)
        self.assertEqual([call for call in adapter.calls if call[0] in
                          ('open', 'bootstrap', 'dispatch')], [])

    def test_action_cap_applies_per_unseen_game(self):
        adapter, result = self.run_fixture(Adapter(('aa11-1', 'bb22-2')), max_actions=3)
        for game in adapter.games:
            self.assertEqual(sum(call[:2] == ('dispatch', game) for call in adapter.calls), 3)
        self.assertEqual(result['actions_admitted'], 6)
        self.assertEqual(result['actions_acknowledged'], 6)

    def test_initial_terminal_states_never_dispatch_or_reset(self):
        for state in (GameState.WIN, GameState.GAME_OVER):
            with self.subTest(state=state):
                game = 'aa11-1'
                adapter = Adapter((game,), initial={game: observation(game, state=state,
                                                                      legal=(0, 1, 2))})
                adapter, result = self.run_fixture(adapter)
                self.assertEqual(adapter.decisions, [])
                self.assertEqual(result['actions_admitted'], 0)
                self.assert_lifecycle_once(adapter)

    def test_terminal_transition_stops_without_level_reset(self):
        for state in (GameState.WIN, GameState.GAME_OVER):
            with self.subTest(state=state):
                game = 'aa11-1'
                adapter = Adapter((game,), after={game: [observation(game, state=state,
                                                                   legal=(0, 1, 2))]})
                adapter, _ = self.run_fixture(adapter)
                self.assertEqual(len(adapter.decisions), 1)
                self.assert_lifecycle_once(adapter)

    def test_no_legal_action_and_reset_only_inventory_never_dispatch(self):
        for legal in ((), (0,)):
            with self.subTest(legal=legal):
                game = 'aa11-1'
                adapter = Adapter((game,), initial={game: observation(game, legal=legal)})
                adapter, result = self.run_fixture(adapter)
                self.assertEqual(adapter.decisions, [])
                self.assertEqual(result['actions_admitted'], 0)
                self.assert_lifecycle_once(adapter)

    def test_illegal_e0_proposal_is_rejected_before_transport(self):
        illegal = ActionDecision.simple(7)
        with patch.object(DeterministicFallback, 'propose', return_value=illegal):
            adapter, result = self.run_fixture()
        self.assertEqual(adapter.decisions, [])
        self.assertEqual(result['actions_admitted'], 0)
        self.assert_lifecycle_once(adapter)

    def test_expired_deadline_prevents_any_bootstrap_or_dispatch(self):
        clock = Clock()
        clock.value = 10.0
        adapter = Adapter()
        with self.assertRaises(runtime._AdmissionClosed):
            self.run_fixture(adapter, now=clock)
        self.assertEqual(adapter.calls, [])

    def test_slow_policy_cannot_dispatch_after_work_deadline(self):
        clock = Clock()

        def slow_policy(_controller, _state):
            clock.value = 10.1
            return ActionDecision.simple(1)

        with patch.object(DeterministicFallback, 'propose', slow_policy):
            adapter, result = self.run_fixture(now=clock)
        self.assertEqual(adapter.decisions, [])
        self.assertEqual(result['actions_admitted'], 0)
        self.assert_lifecycle_once(adapter)

    def test_gate_delay_is_checked_before_action_dispatch(self):
        clock = Clock()
        adapter = Adapter()

        def gate():
            if any(call[0] == 'bootstrap' for call in adapter.calls):
                clock.value = 10.1

        adapter, result = self.run_fixture(adapter, now=clock, gate=gate)
        self.assertEqual(adapter.decisions, [])
        self.assertEqual(result['actions_admitted'], 0)
        self.assert_lifecycle_once(adapter)

    def test_ambiguous_dispatch_is_quarantined_then_next_game_proceeds(self):
        games = ('aa11-1', 'bb22-2')
        adapter = Adapter(games)
        adapter.dispatch_errors[games[0]] = OutcomeUnknown('synthetic lost acknowledgement')
        adapter, result = self.run_fixture(adapter, max_actions=2)
        self.assertEqual(sum(c[:2] == ('dispatch', games[0]) for c in adapter.calls), 1)
        self.assertEqual(sum(c[:2] == ('dispatch', games[1]) for c in adapter.calls), 2)
        self.assertTrue(adapter.clients[games[0]].quarantined)
        self.assertTrue(all(client.closed for client in adapter.clients.values()))
        self.assertEqual(result['ambiguous_actions'], 1)
        self.assertEqual(result['actions_acknowledged'], 2)
        self.assert_lifecycle_once(adapter)

    def test_failed_bootstrap_is_not_retried(self):
        games = ('aa11-1', 'bb22-2')
        adapter = Adapter(games)
        adapter.bootstrap_errors[games[0]] = OutcomeUnknown('synthetic bootstrap failure')
        adapter, result = self.run_fixture(adapter, max_actions=1)
        self.assertEqual(adapter.calls.count(('bootstrap', games[0])), 1)
        self.assertEqual(result['bootstrap_failures'], 1)
        self.assertEqual(result['actions_acknowledged'], 1)
        self.assert_lifecycle_once(adapter)

    def test_missing_or_changed_session_identity_never_dispatches(self):
        game = 'aa11-1'
        bad = [observation(game, guid=''), observation('different-game')]
        for initial in bad:
            with self.subTest(game_id=initial.game_id, guid=initial.guid):
                adapter, _ = self.run_fixture(Adapter((game,), initial={game: initial}))
                self.assertEqual(adapter.decisions, [])
                self.assert_lifecycle_once(adapter)

    def test_response_identity_drift_stops_before_a_second_dispatch(self):
        game = 'aa11-1'
        for after in [observation(game, guid='changed-guid'), observation('different-game')]:
            with self.subTest(game_id=after.game_id, guid=after.guid):
                adapter, _ = self.run_fixture(Adapter((game,), after={game: [after]}))
                self.assertEqual(len(adapter.decisions), 1)
                self.assert_lifecycle_once(adapter)

    def test_duplicate_inventory_refuses_before_bootstrap(self):
        adapter = Adapter(('aa11-1', 'aa11-1'))
        with self.assertRaises(ValueError):
            self.run_fixture(adapter)
        self.assertEqual([c for c in adapter.calls if c[0] == 'bootstrap'], [])

    def test_blank_inventory_ids_refuse_before_bootstrap(self):
        for games in [('',), ('  ',), (None,), (False,)]:
            with self.subTest(games=games):
                adapter = Adapter(games)
                with self.assertRaises(ValueError):
                    self.run_fixture(adapter)
                self.assertEqual([c for c in adapter.calls if c[0] == 'bootstrap'], [])

    def test_empty_inventory_refuses_before_scorecard_open(self):
        adapter = Adapter(())
        with self.assertRaises(ValueError):
            self.run_fixture(adapter)
        self.assertEqual(adapter.calls, [('inventory',)])

    def test_invalid_action_inventory_is_refused_before_dispatch(self):
        game = 'aa11-1'
        for legal in [(True,), (1, 1), (8,), ('1',)]:
            with self.subTest(legal=legal):
                adapter, _ = self.run_fixture(Adapter((game,), initial={game: observation(game, legal=legal)}))
                self.assertEqual(adapter.decisions, [])
                self.assert_lifecycle_once(adapter)

    def test_interruption_still_closes_scorecard_without_retry(self):
        game = 'aa11-1'
        adapter = Adapter((game,))
        adapter.dispatch_errors[game] = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_fixture(adapter)
        self.assertEqual(len(adapter.decisions), 1)
        self.assertTrue(adapter.clients[game].closed)
        self.assert_lifecycle_once(adapter)

    def test_client_finalization_failure_still_attempts_scorecard_close(self):
        adapter = Adapter()
        adapter.finalize_error = RuntimeError('synthetic local session close failure')
        adapter, result = self.run_fixture(adapter, max_actions=1)
        self.assertEqual(result['error_type'], 'RuntimeError')
        self.assert_lifecycle_once(adapter)

    def test_program_validation_precedes_scorecard_open(self):
        bad_program = deepcopy(program())
        bad_program['steps'][0]['action']['action_id'] = 0
        adapter = Adapter()
        with self.assertRaises(ValueError):
            runtime.run(adapter, bad_program, work_deadline=10.0, now=Clock())
        self.assertEqual(adapter.calls, [])

    def test_close_failure_is_attempted_once_and_cannot_claim_verified(self):
        adapter = Adapter()
        adapter.close_error = OutcomeUnknown('synthetic close failure')
        adapter, result = self.run_fixture(adapter, max_actions=1)
        self.assertFalse(result['closed_verified'])
        self.assertEqual(adapter.calls.count(('close',)), 1)
        self.assertTrue(all(client.closed for client in adapter.clients.values()))


if __name__ == '__main__':
    unittest.main()
