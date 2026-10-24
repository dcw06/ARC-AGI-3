"""Regressions for 9ceed209 review. No paid calls, scorecards or real games."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arcengine import GameState
from agent.framework_adapter import PreDispatchFailure
from research.claude_arc_v1 import audit, history_probe, run
from tests.test_claude_arc_v1 import FakeArc, FakeBackend, observation, settings


def rewrite_summary(folder, change):
    """Coherently rewrite both summaries and refresh the whole chain.

    Tests therefore exercise independent event checks, not merely stale hashes.
    """
    path = folder / 'summary.json'
    summary = json.loads(path.read_bytes())
    change(summary)
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
    previous = '0' * 64
    for event in events:
        if event['kind'] == 'summary':
            change(event['summary'])
        event.pop('sha256')
        event['previous_sha256'] = previous
        raw = json.dumps(event, sort_keys=True, separators=(',', ':'), allow_nan=False)
        previous = hashlib.sha256(raw.encode()).hexdigest()
        event['sha256'] = previous
    path.write_text(json.dumps(summary))
    (folder / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))


class Reporting(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, arc, *, c=None, backend=None):
        c = c or settings()
        folder = Path(self.temp.name) / ('run-' + str(len(list(Path(self.temp.name).iterdir()))))
        result = run.evaluate(c, backend or FakeBackend(c), arc, run.Evidence(folder))
        return result, folder

    def test_interrupt_during_dispatch_retains_game_and_uncertain_action(self):
        arc = FakeArc(fail=KeyboardInterrupt)
        result, folder = self.execute(arc)
        self.assertEqual(len(arc.actions), 1)
        self.assertEqual((arc.closed, len(result['games'])), (1, 1))
        row = result['games'][0]
        self.assertEqual((row['actions_acknowledged'], row['actions_uncertain']), (0, 1))
        self.assertEqual(row['stop_reason'], 'KeyboardInterrupt')
        self.assertEqual(row['final_state'], 'NOT_FINISHED')
        self.assertEqual(row['last_dispatch_status'], 'outcome_unknown')
        self.assertEqual(result['games_not_started'], [])
        self.assertFalse(result['full_lifecycle_complete'])
        checked = audit.audit(folder)
        self.assertEqual((checked['games_attempted'], checked['actions_uncertain']), (1, 1))

    def test_second_dispatch_interrupt_preserves_first_acknowledged_action(self):
        class Arc(FakeArc):
            def dispatch(self, client, decision):
                self.actions.append(decision)
                if len(self.actions) == 2:
                    raise KeyboardInterrupt()
                client.observation = observation(client.game_id, frames=[[[1, 1], [0, 0]]])
                return client.observation
        result, folder = self.execute(Arc())
        row = result['games'][0]
        self.assertEqual((row['actions_acknowledged'], row['actions_uncertain']), (1, 1))
        self.assertEqual(audit.audit(folder)['actions_acknowledged'], 1)

    def test_interrupted_adapter_mutation_is_not_credited_as_a_win(self):
        class Arc(FakeArc):
            def dispatch(self, client, decision):
                self.actions.append(decision)
                client.observation = observation(client.game_id, 1, GameState.WIN)
                raise KeyboardInterrupt()
        result, folder = self.execute(Arc())
        row = result['games'][0]
        self.assertEqual((row['levels_completed'], row['final_state']), (0, 'NOT_FINISHED'))
        self.assertEqual(row['actions_uncertain'], 1)
        audit.audit(folder)

    def test_system_exit_during_dispatch_is_also_accounted(self):
        result, folder = self.execute(FakeArc(fail=SystemExit))
        self.assertEqual(result['games'][0]['actions_uncertain'], 1)
        self.assertEqual(result['games'][0]['stop_reason'], 'SystemExit')
        audit.audit(folder)

    def test_interrupt_before_dispatch_retains_game_without_uncertain_action(self):
        c, arc = settings(), FakeArc()
        backend = FakeBackend(c)
        backend.complete = lambda request: (_ for _ in ()).throw(KeyboardInterrupt())
        result, folder = self.execute(arc, c=c, backend=backend)
        row = result['games'][0]
        self.assertEqual((row['actions_acknowledged'], row['actions_uncertain']), (0, 0))
        self.assertEqual(result['games_not_started'], [])
        self.assertEqual(arc.actions, [])
        audit.audit(folder)

    def test_bootstrap_interruption_retains_attempt_without_inventing_observation(self):
        class Arc(FakeArc):
            def bootstrap(self, game):
                self.made.append(game)
                raise KeyboardInterrupt()
        result, folder = self.execute(Arc())
        row = result['games'][0]
        self.assertIsNone(row['levels_completed'])
        self.assertIsNone(row['final_state'])
        self.assertEqual(row['actions_uncertain'], 0)
        audit.audit(folder)

    def test_proven_pre_dispatch_failure_does_not_count_as_uncertain(self):
        result, folder = self.execute(FakeArc(fail=PreDispatchFailure))
        row = result['games'][0]
        self.assertEqual((row['actions_acknowledged'], row['actions_uncertain']), (0, 0))
        self.assertEqual(row['last_dispatch_status'], 'not_sent')
        audit.audit(folder)

    def test_win_on_last_allowed_action_is_win_not_action_cap(self):
        result, folder = self.execute(FakeArc(), c=replace(settings(), max_actions_per_game=1))
        self.assertTrue(result['full_lifecycle_complete'])
        row = result['games'][0]
        self.assertEqual(row['stop_reason'], 'win')
        self.assertEqual(row['final_state'], 'WIN')
        self.assertEqual(row['levels_completed'], 1)
        audit.audit(folder)

    def test_game_over_on_last_allowed_action_is_terminal(self):
        class Arc(FakeArc):
            def dispatch(self, client, decision):
                self.actions.append(decision)
                client.observation = observation(client.game_id, state=GameState.GAME_OVER)
                return client.observation
        result, folder = self.execute(Arc(), c=replace(settings(), max_actions_per_game=1))
        row = result['games'][0]
        self.assertEqual((row['stop_reason'], row['final_state']), ('game_over', 'GAME_OVER'))
        audit.audit(folder)

    def test_nonterminal_last_action_remains_action_cap(self):
        class Arc(FakeArc):
            def dispatch(self, client, decision):
                self.actions.append(decision)
                return client.observation
        result, folder = self.execute(Arc(), c=replace(settings(), max_actions_per_game=1))
        row = result['games'][0]
        self.assertEqual((row['stop_reason'], row['final_state']), ('action_cap', 'NOT_FINISHED'))
        audit.audit(folder)

    def test_audit_rejects_dropped_game_even_with_refreshed_hashes(self):
        _, folder = self.execute(FakeArc(fail=KeyboardInterrupt))
        def omit(summary):
            summary['games'] = []
            summary['games_not_started'] = ['ls20-test']
        rewrite_summary(folder, omit)
        with self.assertRaisesRegex(ValueError, 'attempted-game coverage'):
            audit.audit(folder)

    def test_audit_rejects_hidden_uncertain_dispatch_even_with_refreshed_hashes(self):
        _, folder = self.execute(FakeArc(fail=KeyboardInterrupt))
        rewrite_summary(folder, lambda s: s['games'][0].update(actions_uncertain=0))
        with self.assertRaisesRegex(ValueError, 'uncertain-action'):
            audit.audit(folder)

    def test_audit_rejects_terminal_mislabel_even_with_refreshed_hashes(self):
        _, folder = self.execute(FakeArc(), c=replace(settings(), max_actions_per_game=1))
        rewrite_summary(folder, lambda s: s['games'][0].update(stop_reason='action_cap'))
        with self.assertRaisesRegex(ValueError, 'terminal final state'):
            audit.audit(folder)

    def test_audit_rejects_forged_final_state_even_with_refreshed_hashes(self):
        _, folder = self.execute(FakeArc(), c=replace(settings(), max_actions_per_game=1))
        rewrite_summary(folder, lambda s: s['games'][0].update(final_state='NOT_FINISHED'))
        with self.assertRaisesRegex(ValueError, 'final-state'):
            audit.audit(folder)

    @unittest.skipUnless(hasattr(__import__('signal'), 'pthread_sigmask'), 'POSIX signal masking')
    def test_interrupt_during_acknowledgement_does_not_split_event_and_counters(self):
        import os
        import signal
        c, arc = replace(settings(), max_actions_per_game=1), FakeArc()
        folder = Path(self.temp.name) / 'interrupt-commit'
        evidence = run.Evidence(folder)
        write = evidence.write
        def interrupting(kind, **value):
            write(kind, **value)
            if kind == 'transition':
                os.kill(os.getpid(), signal.SIGINT)
        evidence.write = interrupting
        previous = signal.signal(signal.SIGINT, signal.default_int_handler)
        try:
            result = run.evaluate(c, FakeBackend(c), arc, evidence)
        finally:
            signal.signal(signal.SIGINT, previous)
        row = result['games'][0]
        self.assertEqual((row['actions_acknowledged'], row['actions_uncertain']), (1, 0))
        self.assertEqual((row['levels_completed'], row['final_state']), (1, 'WIN'))
        self.assertFalse(result['full_lifecycle_complete'])
        self.assertEqual(arc.closed, 1)
        audit.audit(folder)


class HistorySize(unittest.TestCase):
    def test_probe_is_deterministic_and_does_not_claim_token_measurements(self):
        with patch('socket.create_connection', side_effect=AssertionError('no network')):
            result = history_probe.measure()
        self.assertEqual(result, history_probe.measure())
        self.assertIsNone(result['model_token_counts'])
        self.assertFalse(result['truncation_policy_changed'])
        self.assertEqual(len(result['rows']), 24)

    def test_multiframe_and_two_digit_grids_are_larger(self):
        rows = history_probe.measure()['rows']
        find = lambda p, f, h: next(r for r in rows if (r['pattern'], r['frames_per_observation'],
                                                       r['history_transitions']) == (p, f, h))
        one = find('one_digit', 1, 6)
        two = find('two_digit', 1, 6)
        multi = find('two_digit', 3, 6)
        self.assertGreater(two['request_characters'], one['request_characters'])
        self.assertGreater(multi['request_characters'], two['request_characters'])


if __name__ == '__main__':
    unittest.main()
