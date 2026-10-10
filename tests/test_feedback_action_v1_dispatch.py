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
    """The runner's adapter interface over a synthetic environment, with dispatch faults placed by the session's
    dispatch number (a counter shared by every episode of the session): {n: 'reject' | 'unknown'}."""

    def __init__(self, game_id, mode, faults=None, counter=None):
        self.game_id, self.env, self.faults = game_id, Stepper(mode), faults or {}
        self.counter = counter if counter is not None else [0]

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
        self.counter[0] += 1
        fault = self.faults.get(self.counter[0])
        if fault == 'reject':
            raise R.DispatchRejected('synthetic: rejected before acknowledgement')
        self.env.dispatch(action)
        if fault == 'unknown':
            raise TimeoutError('synthetic: no response after send')
        return self.observation(), {'acknowledged': True, 'source': 'synthetic_adapter'}

    def close(self):
        return {'closed': True}



def run_synthetic(test, mode, *, faults=None, invalid_calls=(), expect='complete', committed_f5=False):
    """One synthetic pair (baseline, then candidate) through the derived runner. Returns (report, server).
    `committed_f5`: r0's F5 rule without the owner's denominator floor (gate B), kept as the reference it amends."""
    game = f'syn-{mode}'
    spec = P.session_spec(1)
    if committed_f5:
        spec['limits']['session_abort'].pop('dispatch_denominator_floor', None)
    spec['cases'] = [{'game_id': game, 'environment_seed': 0, 'initial_available_actions': [1, 2], 'win_levels': 2,
                      'initial_canonical_hash': SyntheticAdapter(game, mode).bootstrap().canonical_hash}]
    spec['schedule'] = [{'block': 1, 'pair_id': game, 'game_id': game, 'order': ['baseline', 'candidate']}]
    server, counter = FakeServer(invalid_calls=invalid_calls), [0]
    with tempfile.TemporaryDirectory() as tmp:
        report = R.run(Path(tmp) / 'run', server, lambda g, a, e: SyntheticAdapter(g, mode, faults, counter), spec=spec)
        test.assertEqual(R.load(Path(tmp) / 'run'), report)  # durable (partial) evidence verifies and reassembles
    test.assertEqual(report['status'], expect)
    for e in report['episodes']:
        raws = [s['raw_transition'] for s in e['steps']]
        test.assertEqual(T.verify_history(T.history(raws), raws), [])
        assert_terminal_aware(test, e)
    if expect != 'complete':
        # nothing after the abort: the last episode is the aborted one, and later pairs never started
        test.assertEqual(report['episodes'][-1]['status'], 'aborted')
        test.assertTrue(all(e['status'] != 'aborted' for e in report['episodes'][:-1]))
        test.assertEqual(server.transport.calls, report['calls'])  # every model call is a recorded call
    return report, server


class SyntheticBoundaries(unittest.TestCase):
    def test_level_boundary_clears_evidence_and_carried_statement_and_win_stops(self):
        for e in run_synthetic(self, 'level')[0]['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps']), len(e['calls'])), ('win', 6, 6))
            entries = [len(user(c)['observation'][E.FIELD]['entries']) for c in e['calls']]
            self.assertEqual(entries, [0, 1, 2, 0, 1, 2])  # cleared after the level at the 3rd action
            if e['arm'] == 'candidate':
                carried = [user(c)[AD.PREVIOUS_FIELD] for c in e['calls']]
                self.assertTrue(carried[3]['reason'].startswith('cleared'))
                self.assertTrue(carried[4]['available'])

    def test_reset_boundary_clears_evidence(self):
        for e in run_synthetic(self, 'reset')[0]['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps'])), ('action_cap', 24))
            entries = [len(user(c)['observation'][E.FIELD]['entries']) for c in e['calls']]
            self.assertEqual(entries[:9], [0, 1, 2, 3, 0, 1, 2, 3, 0])
            records = T.history([s['raw_transition'] for s in e['steps']])
            self.assertIn('reset_acknowledged', records[3]['environment']['events'])

    def test_game_over_stops_with_no_further_call_or_action(self):
        for e in run_synthetic(self, 'game_over')[0]['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps']), len(e['calls'])), ('game_over', 5, 5))


class F2aInvalidOutputAbort(unittest.TestCase):
    """Per arm, over its first 24 policy calls of the session: abort when invalid outputs exceed 25% of 24 (> 6)."""

    def test_exactly_25_percent_at_call_24_does_not_abort(self):
        report, _ = run_synthetic(self, 'reset', invalid_calls=range(19, 25))  # 6 invalid in calls 19-24
        self.assertIsNone(report['abort'])
        baseline = report['episodes'][0]
        self.assertEqual((baseline['stop_reason'], len(baseline['calls']), len(baseline['steps'])), ('action_cap', 30, 24))
        self.assertEqual(len(report['episodes']), 2)

    def test_just_over_25_percent_aborts_at_call_24(self):
        report, server = run_synthetic(self, 'reset', invalid_calls=range(18, 25), expect='aborted')  # 7 invalid
        self.assertEqual(report['abort'], {'rule': 'F2a_invalid_outputs', 'arm': 'baseline',
                                           'invalid_outputs_in_window': 7, 'arm_calls': 24, 'window_calls': 24,
                                           'threshold_rate': '1/4', 'episode_id': 'syn-reset-baseline'})
        self.assertEqual([(e['arm'], len(e['calls']), len(e['steps'])) for e in report['episodes']],
                         [('baseline', 24, 17)])  # the candidate episode never started
        self.assertEqual(server.transport.calls, 24)

    def test_invalid_outputs_after_the_window_never_count(self):
        report, _ = run_synthetic(self, 'reset', invalid_calls=range(20, 27))  # 5 inside calls 1-24, 2 after
        self.assertIsNone(report['abort'])
        self.assertEqual(len(report['episodes'][0]['calls']), 31)

    def test_the_window_is_per_arm(self):
        # the baseline arm owns calls 1-24 (all valid); the candidate's first 7 calls (25-31) are invalid
        report, server = run_synthetic(self, 'reset', invalid_calls=range(25, 32), expect='aborted')
        self.assertEqual((report['abort']['arm'], report['abort']['arm_calls'], report['abort']['invalid_outputs_in_window']),
                         ('candidate', 7, 7))
        self.assertEqual([(e['arm'], e['status'], len(e['calls'])) for e in report['episodes']],
                         [('baseline', 'complete', 24), ('candidate', 'aborted', 7)])
        self.assertEqual(server.transport.calls, 31)


class F5DispatchFailureAbort(unittest.TestCase):
    """The whole session: abort after any dispatch at which failed plus unknown dispatches exceed 10% of the
    dispatches so far. Frozen rule (gate B, owner decision of October 10, 2026): failures x 10 > max(dispatches,
    10). The committed r0 rule (failures x 10 > dispatches) is kept below as the reference the floor amends."""

    def test_exactly_10_percent_does_not_abort(self):
        report, _ = run_synthetic(self, 'reset', faults={10: 'reject'})  # 1 failure in 10 dispatches
        self.assertIsNone(report['abort'])
        first, second = report['episodes']
        self.assertEqual((first['stop_reason'], len(first['steps'])), ('dispatch_failure', 10))
        self.assertEqual(first['steps'][-1]['raw_transition']['outcome']['status'], 'failed')
        self.assertEqual((second['stop_reason'], len(second['steps'])), ('action_cap', 24))

    def test_frozen_floor_a_single_early_failure_ends_only_its_episode(self):
        report, _ = run_synthetic(self, 'reset', faults={9: 'reject'})  # 1 in 9: under the floor, no abort
        self.assertIsNone(report['abort'])
        first, second = report['episodes']
        self.assertEqual((first['stop_reason'], len(first['steps'])), ('dispatch_failure', 9))
        self.assertEqual((second['stop_reason'], len(second['steps'])), ('action_cap', 24))

    def test_frozen_floor_a_second_early_failure_aborts_and_records_the_floor(self):
        report, server = run_synthetic(self, 'reset', faults={3: 'reject', 5: 'unknown'}, expect='aborted')
        self.assertEqual(report['abort'], {'rule': 'F5_dispatch_failures', 'dispatch_failures': 2, 'dispatched': 5,
                                           'threshold_rate': '1/10', 'denominator_floor': 10,
                                           'episode_id': 'syn-reset-candidate'})

    def test_committed_rule_just_over_10_percent_aborts(self):
        report, server = run_synthetic(self, 'reset', faults={9: 'reject'}, expect='aborted', committed_f5=True)
        self.assertEqual(report['abort'], {'rule': 'F5_dispatch_failures', 'dispatch_failures': 1, 'dispatched': 9,
                                           'threshold_rate': '1/10', 'denominator_floor': 0,  # committed rule
                                           'episode_id': 'syn-reset-baseline'})
        self.assertEqual([(e['arm'], len(e['steps']), len(e['calls'])) for e in report['episodes']],
                         [('baseline', 9, 9)])
        self.assertEqual(server.transport.calls, 9)

    def test_second_failure_at_and_over_the_threshold(self):
        report, _ = run_synthetic(self, 'reset', faults={10: 'reject', 20: 'unknown'})  # 2 in 20: exactly 10%
        self.assertIsNone(report['abort'])
        self.assertEqual([e['stop_reason'] for e in report['episodes']], ['dispatch_failure', 'dispatch_failure'])
        report, _ = run_synthetic(self, 'reset', faults={10: 'reject', 19: 'unknown'}, expect='aborted')  # 2 in 19
        self.assertEqual((report['abort']['dispatch_failures'], report['abort']['dispatched']), (2, 19))
        self.assertEqual(report['episodes'][-1]['steps'][-1]['raw_transition']['outcome']['status'], 'outcome_unknown')

    def test_unknown_outcome_counts_and_its_record_is_indeterminate(self):
        report, _ = run_synthetic(self, 'level', faults={3: 'unknown'}, expect='aborted', committed_f5=True)
        self.assertEqual(report['abort']['rule'], 'F5_dispatch_failures')
        record = T.build(report['episodes'][0]['steps'][-1]['raw_transition'])
        self.assertEqual(record['measurements']['visual_effect']['status'], 'indeterminate')


if __name__ == '__main__':
    unittest.main()
