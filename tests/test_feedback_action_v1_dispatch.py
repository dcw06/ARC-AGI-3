"""Feedback-action v1 terminal-aware CPU dispatch checks through the derived runner (no model, no GPU).

Real offline development engine (seed 0): session 2 plays 24 scripted actions per game and arm (session 1 is played
by tests/test_feedback_action_v1_live.py); s5i5 is run on a check-only extended cap to its GAME_OVER, which the
scripted policies reach at action 50 on that engine, to verify that nothing is called or dispatched after a terminal
state. Neither ls20 nor sk48 reached a terminal state, a level change or a reset within 100 scripted actions in a
probe, so level, WIN, GAME_OVER-at-24, reset and dispatch-fault boundaries are exercised through the same runner
with a synthetic adapter (synthetic diagnostics, never real-game data).
"""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.feedback_action_v1 import adapter as AD, environments as ENV, evidence as E
from research.feedback_action_v1.live import policy as P, runner as R
from research.feedback_action_v1.live.engine import DevelopmentAdapter
from research.feedback_action_v1.live.fake_server import FakeServer
from research.transition_evidence_v2 import transition as T


def user(call):
    return json.loads(call['request']['messages'][1]['content'])


def assert_terminal_aware(test, episode):
    """No call and no dispatch after a terminal state; the stop reason names the terminal state."""
    afters = [s['after']['state'] for s in episode['steps'] if s.get('after')]
    terminal = [i for i, s in enumerate(afters) if s in ('WIN', 'GAME_OVER')]
    if terminal:
        test.assertEqual(terminal, [len(episode['steps']) - 1])  # only the last dispatch may produce it
        test.assertEqual(episode['stop_reason'], {'WIN': 'win', 'GAME_OVER': 'game_over'}[afters[-1]])
        test.assertEqual(episode['calls'][-1]['status'], 'valid')
        test.assertEqual(len(episode['calls']), episode['steps'][-1]['call_index'] + 1)  # no call after it
    for step in episode['steps']:
        test.assertNotIn(step['before']['state'], ('WIN', 'GAME_OVER'))


class RealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from research.grounded_action_v1.engine import restore_game_mount
        cls.tmp = tempfile.TemporaryDirectory()
        cls.games = restore_game_mount(Path(cls.tmp.name) / 'games')
        cls.session2 = cls.run_spec(P.session_spec(2))
        terminal = P.session_spec(1)
        terminal['schedule'] = [p for p in terminal['schedule'] if p['pair_id'] == 'b1-s5i5']
        terminal['limits'].update(actions_per_episode=60, decision_calls_per_episode=64, maximum_policy_calls=200)
        cls.terminal = cls.run_spec(terminal)  # check-only cap; the experiment's horizon stays 24

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def run_spec(cls, spec):
        folder = Path(tempfile.mkdtemp(dir=cls.tmp.name))
        return R.run(folder / 'run', FakeServer(), lambda g, a, e: DevelopmentAdapter(g, a, e, cls.games, folder / 'rec'),
                     spec=spec)

    def test_session2_24_actions_per_game_and_arm(self):
        report = self.session2
        self.assertEqual((report['status'], report['calls'], report['dispatches']), ('complete', 144, 144))
        cases = {c['game_id']: c for c in R.protocol()['cases']}
        self.assertEqual([(e['game_id'][:4], e['arm']) for e in report['episodes']],
                         [('s5i5', 'candidate'), ('s5i5', 'baseline'), ('ls20', 'baseline'), ('ls20', 'candidate'),
                          ('sk48', 'candidate'), ('sk48', 'baseline')])
        for e in report['episodes']:
            self.assertEqual(e['initial']['canonical_hash'], cases[e['game_id']]['initial_canonical_hash'])
            self.assertEqual((e['stop_reason'], len(e['steps'])), ('action_cap', 24))
            self.assertEqual({s['status'] for s in e['steps']}, {'acknowledged'})
            assert_terminal_aware(self, e)
            records = T.history([s['raw_transition'] for s in e['steps']])
            self.assertEqual([r['continuity']['status'] for r in records][1:], ['matches_previous_final'] * 23)
            self.assertEqual({r['dispatch']['status'] for r in records}, {'acknowledged'})

    def test_s5i5_game_over_ends_the_episode_with_nothing_after_it(self):
        for e in self.terminal['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps']), len(e['calls'])), ('game_over', 50, 50))
            self.assertEqual(e['steps'][-1]['after']['state'], 'GAME_OVER')
            assert_terminal_aware(self, e)
            records = T.history([s['raw_transition'] for s in e['steps']])
            self.assertEqual(T.verify_history(records, [s['raw_transition'] for s in e['steps']]), [])
            self.assertIn('terminal_state', records[-1]['environment']['events'])


class Stepper(ENV.Environment):
    """Every action changes one cell. Modes: 'level' completes a level every 3rd action (2 levels: WIN after 6);
    'reset' resets the level every 4th action (full_reset); 'game_over' ends the game at the 5th action."""
    legal_actions = (1, 2)
    win_levels = 2

    def __init__(self, mode):
        self.mode, self.count = mode, 0
        super().__init__()

    def level_frame(self):
        return ENV.blank(self.levels)

    def reset_level(self):
        self.frame = self.level_frame()

    def step(self, action):
        self.count += 1
        cell = self.frame[3][1 + self.count % 6]
        self.frame[3][1 + self.count % 6] = 9 if cell != 9 else 2
        if self.mode == 'level' and self.count % 3 == 0:
            self.complete_level()
        if self.mode == 'reset' and self.count % 4 == 0:
            self.reset_level()
            self.full_reset = True
        if self.mode == 'game_over' and self.count == 5:
            self.state = 'GAME_OVER'
        return [[row[:] for row in self.frame]]


class SyntheticAdapter:
    """The runner's adapter interface over a synthetic environment, with optional dispatch faults."""

    def __init__(self, game_id, mode, fault=None):
        self.game_id, self.env, self.fault, self.n = game_id, Stepper(mode), fault, 0

    def observation(self, full_reset=None):
        from arcengine import GameState
        from agent.state import Observation
        obs = self.env.observe()
        return Observation(self.game_id, (np.array(obs['frames'][-1], dtype=np.uint8),), GameState(obs['state']),
                           obs['levels_completed'], self.env.win_levels, 'synthetic-guid', tuple(self.env.legal_actions),
                           obs['full_reset'] if full_reset is None else full_reset)

    def bootstrap(self):
        return self.observation(full_reset=True)

    def dispatch(self, action, before):
        self.n += 1
        if self.fault == ('reject', self.n):
            raise R.DispatchRejected('synthetic: rejected before acknowledgement')
        self.env.dispatch(action)
        if self.fault == ('unknown', self.n):
            raise TimeoutError('synthetic: no response after send')
        return self.observation(), {'acknowledged': True, 'source': 'synthetic_adapter'}

    def close(self):
        return {'closed': True}


class SyntheticBoundaries(unittest.TestCase):
    def run_mode(self, mode, fault=None):
        game = f'syn-{mode}'
        spec = P.session_spec(1)
        spec['cases'] = [{'game_id': game, 'environment_seed': 0, 'initial_available_actions': [1, 2], 'win_levels': 2,
                          'initial_canonical_hash': SyntheticAdapter(game, mode).bootstrap().canonical_hash}]
        spec['schedule'] = [{'block': 1, 'pair_id': game, 'game_id': game, 'order': ['baseline', 'candidate']}]
        with tempfile.TemporaryDirectory() as tmp:
            report = R.run(Path(tmp) / 'run', FakeServer(), lambda g, a, e: SyntheticAdapter(g, mode, fault), spec=spec)
        self.assertEqual(report['status'], 'complete')
        for e in report['episodes']:
            raws = [s['raw_transition'] for s in e['steps']]
            self.assertEqual(T.verify_history(T.history(raws), raws), [])
            assert_terminal_aware(self, e)
        return report

    def test_level_boundary_clears_evidence_and_carried_statement_and_win_stops(self):
        for e in self.run_mode('level')['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps']), len(e['calls'])), ('win', 6, 6))
            entries = [len(user(c)['observation'][E.FIELD]['entries']) for c in e['calls']]
            self.assertEqual(entries, [0, 1, 2, 0, 1, 2])  # cleared after the level at the 3rd action
            if e['arm'] == 'candidate':
                carried = [user(c)[AD.PREVIOUS_FIELD] for c in e['calls']]
                self.assertTrue(carried[3]['reason'].startswith('cleared'))
                self.assertTrue(carried[4]['available'])

    def test_reset_boundary_clears_evidence(self):
        for e in self.run_mode('reset')['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps'])), ('action_cap', 24))
            entries = [len(user(c)['observation'][E.FIELD]['entries']) for c in e['calls']]
            self.assertEqual(entries[:9], [0, 1, 2, 3, 0, 1, 2, 3, 0])
            records = T.history([s['raw_transition'] for s in e['steps']])
            self.assertIn('reset_acknowledged', records[3]['environment']['events'])

    def test_game_over_stops_with_no_further_call_or_action(self):
        for e in self.run_mode('game_over')['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps']), len(e['calls'])), ('game_over', 5, 5))

    def test_rejected_dispatch_is_retained_as_failed_and_stops_the_episode(self):
        report = self.run_mode('level', fault=('reject', 3))
        for e in report['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps'])), ('dispatch_failure', 3))
            self.assertEqual(e['steps'][-1]['raw_transition']['outcome']['status'], 'failed')
        self.assertEqual(len(report['episodes']), 2)  # the schedule continued to the next episode

    def test_unknown_outcome_is_retained_and_stops_the_episode(self):
        for e in self.run_mode('level', fault=('unknown', 3))['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps'])), ('dispatch_failure', 3))
            self.assertEqual(e['steps'][-1]['raw_transition']['outcome']['status'], 'outcome_unknown')
            record = T.build(e['steps'][-1]['raw_transition'])
            self.assertEqual(record['measurements']['visual_effect']['status'], 'indeterminate')


if __name__ == '__main__':
    unittest.main()
