import copy
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from arcengine import GameState
from agent.action import ActionDecision
from agent.watchdog import DeadlineWatchdog
from certification.phase4_v3.terminal import TerminalAwareLoop
from certification.phase4_v3.evaluate import evaluate
from tests.test_phase1 import observation
from tests import test_phase4_integration as fixtures


class TerminalTests(unittest.TestCase):
    def test_acknowledged_game_over_stops_before_policy(self):
        obs = replace(observation(), state=GameState.GAME_OVER)
        client = SimpleNamespace(game_id=obs.game_id, observation=obs)
        adapter, policy = Mock(), Mock()
        result = TerminalAwareLoop(adapter, client, policy=policy,
                                   watchdog=DeadlineWatchdog(60, 10)).run()
        self.assertEqual(result.terminal_reason, 'game_over')
        self.assertEqual(result.acknowledged_actions, 0)
        policy.propose.assert_not_called()
        adapter.dispatch.assert_not_called()
        adapter.finalize_client.assert_called_once_with(client)

    def test_one_action_to_game_over_no_extra_request(self):
        obs = observation()
        client = SimpleNamespace(game_id=obs.game_id, observation=obs)
        adapter, policy = Mock(), Mock()
        policy.propose.return_value = ActionDecision.simple(1)
        adapter.dispatch.return_value = replace(obs, state=GameState.GAME_OVER)
        result = TerminalAwareLoop(adapter, client, policy=policy,
                                   watchdog=DeadlineWatchdog(60, 10)).run()
        self.assertEqual(result.terminal_reason, 'game_over')
        self.assertEqual(result.acknowledged_actions, 1)
        policy.propose.assert_called_once()
        adapter.dispatch.assert_called_once()

    def test_cancellation_is_not_relabelled_game_over(self):
        obs = replace(observation(), state=GameState.GAME_OVER)
        client = SimpleNamespace(game_id=obs.game_id, observation=obs)
        watchdog = DeadlineWatchdog(60, 10);watchdog.cancel()
        result = TerminalAwareLoop(Mock(), client, policy=Mock(), watchdog=watchdog).run()
        self.assertEqual(result.terminal_reason, 'global_finalization_reserve')

    def test_evaluator_requires_terminal_observation_and_journal(self):
        report, rows = fixtures.EvaluatorTests().fixture()
        c = report['worker']['clients'][0]
        c['result']['terminal_reason'] = 'game_over'
        self.assertFalse(evaluate(report, rows)['passed'])
        c['terminal_observation'] = {'state': 'GAME_OVER', 'hash': 'h', 'rendered_frames': 1}
        c['dispatch_audit'][-1].update(post_state='GAME_OVER', post_hash='h')
        c['client_journal'][-1]['fields'] = {'post_state_hash': 'h'}
        self.assertTrue(evaluate(report, rows)['passed'])
        bad = copy.deepcopy(report)
        bad['worker']['clients'][0]['client_journal'][-1]['fields']['post_state_hash'] = 'different'
        self.assertFalse(evaluate(bad, rows)['passed'])

    def test_post_terminal_dispatch_rejected(self):
        report, rows = fixtures.EvaluatorTests().fixture()
        report['worker']['clients'][0]['dispatch_audit'][0]['pre_state'] = 'GAME_OVER'
        self.assertFalse(evaluate(report, rows)['passed'])


if __name__ == '__main__': unittest.main()
