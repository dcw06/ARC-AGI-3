"""Recovery study switches. Credential-free: the game and the model are small scripted fakes.

The last class replays the saved November 6 run when it is on this machine, to show that the control's
requests are unchanged and that a resumed game rebuilds the saved notes and history exactly.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from arcengine import GameState
from agent.action import ActionDecision
from agent.e1_policy import CompletionResult
from agent.state import Observation
import agent.framework_adapter as pinned
from research.claude_arc_v1 import arc, audit, config, policy, recovery, resume, run
from research.claude_arc_v1.backends import Budget

ROOT = Path(__file__).resolve().parents[1]
NOV6 = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
# sha256 of the control's system prompt and of each stage's reply schema (sorted keys), taken from the
# code as committed before the recovery switches existed.
CONTROL_SYSTEM = '2209f8773781469f3832633770154639f6580f999cf7ac1159632f3e54f09969'
CONTROL_SCHEMAS = {
    'baseline': '939f1b3610651819f4274ccdb69499a9a98c36593655e4c317846b06a6446036',
    'history': '939f1b3610651819f4274ccdb69499a9a98c36593655e4c317846b06a6446036',
    'hypotheses': '02d2ba886c7ca811739b089cda01326df95cb7a96ff2d587398406886978fefe',
    'experiments': 'ac082cc235a6b04e59216dea8b9f545757b539c00468521ccbf20a5f886c4951',
    'world_model': '09c99fb21c7afa1e15793ce88262edf7de15828f72516bbf36464566c37cc8d5',
    'planning': '817976a6ad995b13a16e4cdb4a212f69442b900b9efb4a6e1168d28a06ab8d7e',
}


def settings(**kw):
    base = dict(live_enabled=True, spend_limit_usd=10, stage='hypotheses', max_actions_per_game=8,
                resets_per_game=3, model_retries_per_action=1, games=('toy',))
    return replace(config.Config(), **{**base, **kw})


class Toy:
    """A corridor: ACTION1 steps right, ACTION4 steps left, ACTION2 only ticks the counter, ACTION3 is fatal.

    Reaching cell 3 ends the level. Row 0 shows the position, row 3 a step counter that fills one cell per
    action. RESET restarts the level exactly. Faults for tests: `drift` shows a different board from the
    third action on; `trap` makes ACTION1 fatal from the fourth action on; `full_reset` makes RESET send
    the game back to its first level.
    """
    WIN_LEVELS = 2

    def __init__(self, drift=False, trap=False, full_reset=False, odd_start=False):
        self.level, self.position, self.ticks, self.over, self.steps = 0, int(odd_start), 0, False, 0
        self.drift, self.trap, self.full_reset = drift, trap, full_reset

    def board(self):
        grid = np.zeros((4, 12), dtype=np.uint8)
        grid[0, self.position] = 5
        grid[1, 0] = self.level + 1
        grid[3, :min(self.ticks, 12)] = 9
        if self.drift and self.steps > 2:
            grid[2, 7] = 7
        return grid

    def step(self, action_id):
        if action_id == 0:
            self.position, self.ticks, self.over = 0, 0, False
            if self.full_reset:
                self.level = 0
        elif self.over:
            raise AssertionError('action sent after GAME_OVER')
        else:
            self.ticks += 1
            self.steps += 1
            if action_id == 1:
                self.position += 1
                self.over = self.trap and self.steps > 3
            elif action_id == 4:
                self.position = max(0, self.position - 1)
            elif action_id == 3:
                self.over = True
            if self.position == 3 and not self.over:
                self.level, self.position, self.ticks = self.level + 1, 0, 0
        return self.state()

    def state(self):
        if self.level >= self.WIN_LEVELS:
            return GameState.WIN
        return GameState.GAME_OVER if self.over else GameState.NOT_FINISHED


class ToyArc:
    def __init__(self, games=('toy-test',), **faults):
        """faults: a fault name mapped to True (every game) or to the games that have it."""
        self.games = tuple(games)
        self.toys = {g: Toy(**{k: v is True or g in v for k, v in faults.items()}) for g in self.games}
        self.actions, self.closed = [], 0

    def observe(self, game):
        toy = self.toys[game]
        return Observation(game, (toy.board(),), toy.state(), toy.level, Toy.WIN_LEVELS, 'guid-' + game, (1, 2, 3, 4))

    def list_game_ids(self):
        return self.games

    def open_scorecard(self, tags):
        return 'synthetic-card'

    def bootstrap(self, game):
        return SimpleNamespace(observation=self.observe(game), game_id=game)

    def dispatch(self, client, decision):
        self.actions.append((decision.action_id, decision.source))
        self.toys[client.game_id].step(decision.action_id)
        client.observation = self.observe(client.game_id)
        return client.observation

    def finalize_client(self, client):
        pass

    def close_scorecard(self):
        self.closed += 1
        return {'score': 0, 'card_id': 'synthetic-card'}


class Script:
    """A model that answers from a list. Each entry is an action id or a full answer dict."""

    def __init__(self, c, answers):
        self.config, self.budget, self.requests, self.last_record = c, Budget(c), [], None
        self.answers = list(answers)

    def complete(self, request):
        reserved = self.budget.reserve()
        self.requests.append(request)
        entry = self.answers.pop(0)
        answer = dict(entry) if isinstance(entry, dict) else {'action': {'action_id': entry, 'action_data': {}}}
        answer.setdefault('hypotheses', [])
        self.budget.settle(reserved, 10, 10)
        self.last_record = {'outcome': 'response_received', 'scripted': True}
        return CompletionResult(json.dumps(answer), 10, 10, 0)


def act(action_id, **extra):
    return {'action': {'action_id': action_id, 'action_data': {}}, **extra}


def payload(request):
    return json.loads(request['messages'][1]['content'])


def step(tracker, toy, action_id, by_model=True, notes=None, name='t'):
    """Send one action to a toy and tell the tracker, as the controller does."""
    def observation():
        return Observation('toy-test', (toy.board(),), toy.state(), toy.level, 2, 'guid', (1, 2, 3, 4))
    before = observation()
    toy.step(action_id)
    return tracker.record(name, SimpleNamespace(action_id=action_id, action_data={}), before, observation(),
                          by_model=by_model, notes=notes)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def play(self, c, answers, arc=None):
        folder = Path(self.temp.name) / ('run-%d' % len(list(Path(self.temp.name).iterdir())))
        arc, backend = arc or ToyArc(), Script(c, answers)
        result = run.evaluate(c, backend, arc, run.Evidence(folder))
        events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
        return result, arc, backend, events, folder


class Switches(Base):
    def test_control_prompt_and_schemas_are_the_committed_ones(self):
        control = json.loads((ROOT / 'config/claude_arc_v1.opus55_competition.json').read_text())
        c = config.Config(**control)
        self.assertFalse(c.recovery_on)
        self.assertEqual(hashlib.sha256(policy.system_prompt(c).encode()).hexdigest(), CONTROL_SYSTEM)
        for stage, wanted in CONTROL_SCHEMAS.items():
            for schema in (policy.response_schema(stage), policy.response_schema(stage, replace(c, stage=stage))):
                self.assertEqual(hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(), wanted, stage)

    def test_objective_is_appended_to_the_control_prompt_and_changes_nothing_else(self):
        control = config.Config(**json.loads((ROOT / 'config/claude_arc_v1.opus55_competition.json').read_text()))
        told = replace(control, state_objective=True)
        self.assertEqual(policy.system_prompt(told), policy.system_prompt(control) + policy.OBJECTIVE)
        self.assertIn('including one that changes nothing', policy.OBJECTIVE)
        for stage in CONTROL_SCHEMAS:
            self.assertEqual(policy.response_schema(stage, replace(told, stage=stage)), policy.response_schema(stage))
        with self.assertRaises(ValueError):
            settings(state_objective=1)
        plain, _, plain_backend, _, _ = self.play(settings(), [1, 1])
        _, _, backend, _, folder = self.play(settings(state_objective=True), [1, 1])
        self.assertEqual(payload(backend.requests[0]), payload(plain_backend.requests[0]))
        audit.audit(folder)

    def test_defaults_add_no_row_fields_events_or_evidence(self):
        result, arc_, backend, events, folder = self.play(settings(), [1, 1])
        self.assertNotIn('model_resets', result['games'][0])
        self.assertFalse({'recovery_state', 'recovery_check', 'replay_entered', 'resume_source'}
                         & {e['kind'] for e in events})
        self.assertEqual(set(payload(backend.requests[0])['evidence']), {'current', 'history', 'history_omitted', 'hypotheses'})
        audit.audit(folder)

    def test_switch_combinations_are_validated(self):
        for bad in (dict(stall_window=3), dict(recovery_pricing=True), dict(model_may_reset=True, stall_same_notes=True),
                    dict(model_may_reset=True, stall_level_ratio=1.0), dict(resume_actions=2),
                    dict(resume_events='x.jsonl'), dict(model_may_reset=1), dict(level_baselines={'toy': [0]}),
                    dict(model_may_reset=True, stall_level_floor=5), dict(pin_game_overs=9), dict(pin_game_overs=True)):
            with self.assertRaises(ValueError, msg=str(bad)):
                settings(**bad)

    def test_reset_permission_changes_only_the_reset_sentence(self):
        c = settings(model_may_reset=True)
        text = policy.system_prompt(c)
        self.assertNotIn('Never reset', text)
        self.assertEqual(text.replace(recovery.RESET_ALLOWED, 'Never reset (action 0). '), policy.system_prompt(settings()))
        self.assertEqual(policy.response_schema('hypotheses', c)['properties']['action']['properties']['action_id']['minimum'], 0)

    def test_adapter_widens_the_reset_rule_for_one_call_only(self):
        seen = []

        def stub(self, client, decision):
            # What the pinned dispatch does first: check the action against the legal ones.
            seen.append(pinned.serialize_action(decision, game_id='g', guid='u', legal_actions=(1,),
                                                allow_level_reset=False).endpoint)
            return 'sent'
        live = SimpleNamespace(observation=SimpleNamespace(state=GameState.NOT_FINISHED))
        original = pinned.serialize_action
        with patch.object(pinned.RemoteFrameworkAdapter, 'dispatch', stub):
            adapter = arc.VoluntaryResetAdapter.__new__(arc.VoluntaryResetAdapter)
            self.assertEqual(adapter.dispatch(live, ActionDecision(0, {}, source='api_evaluation')), 'sent')
            self.assertEqual(adapter.dispatch(live, ActionDecision(1, {}, source='api_evaluation')), 'sent')
        self.assertEqual(seen, ['RESET', 'ACTION1'])
        self.assertIs(pinned.serialize_action, original)
        with self.assertRaises(Exception):      # outside that call the pinned rule is back
            pinned.serialize_action(ActionDecision(0, {}, source='x'), game_id='g', guid='u', legal_actions=(1,))


class Signals(unittest.TestCase):
    def test_counter_cells_are_learned_and_then_ignored(self):
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        facts = [step(tracker, toy, a) for a in (2, 2, 2, 1, 2)]
        # Three actions that only tick the counter, a real step, then another tick. Two ticks are not yet
        # a counter; the third reveals the bar and the attempt is judged again.
        self.assertEqual([f['new_board'] for f in facts], [True, True, False, True, False])
        self.assertEqual([f['stale'] for f in facts], [0, 0, 3, 0, 1])
        self.assertEqual(facts[-1]['counter_cells'], 12)      # the whole counter row, ticks to come included

    def test_a_bar_stays_recognised_when_it_starts_again_after_a_reset(self):
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        for a in (2, 2, 2):
            step(tracker, toy, a)
        step(tracker, toy, 0, by_model=False)
        facts = [step(tracker, toy, a) for a in (1, 4, 1, 4)]
        self.assertEqual([f['new_board'] for f in facts], [True, False, False, False])

    def test_a_vertical_bar_is_recognised_too(self):
        counter = recovery.CounterMask()
        board = np.zeros((8, 6), dtype=np.uint8)
        for y in range(3):
            after = board.copy()
            after[y, 4] = 9
            counter.update(board, after)
            board = after
        self.assertTrue(counter.mask[:, 4].all())
        self.assertEqual(counter.cells, 8)

    def test_a_small_moving_piece_and_a_switch_are_not_taken_for_a_counter(self):
        counter = recovery.CounterMask()
        board = np.zeros((6, 10), dtype=np.uint8)
        board[2, 0] = 5
        seen = []
        for x in (1, 2, 3, 4, 3, 2):                # a one-cell piece walks along a row and back
            after = np.zeros((6, 10), dtype=np.uint8)
            after[2, x] = 5
            counter.update(board, after)
            board = after
            seen.append(counter.key(board))
        self.assertEqual(len(set(seen[:4])), 4)      # every position still looks different
        self.assertEqual(seen[4], seen[2])           # and coming back is recognised as a repeat
        for _ in range(3):                           # a switch flipped on and off
            after = board.copy()
            after[5, 9] ^= 7
            counter.update(board, after)
            self.assertNotEqual(counter.key(board), counter.key(after))
            board = after

    def test_an_estimate_that_would_ignore_too_much_is_dropped(self):
        counter = recovery.CounterMask()
        board = np.zeros((6, 6), dtype=np.uint8)
        for y in range(6):                           # every row fills like a bar
            for x in range(3):
                after = board.copy()
                after[y, x] = 9
                counter.update(board, after)
                board = after
        self.assertLessEqual(counter.cells, counter.MAX_LINES * 6)

    def test_a_revisit_is_seen_while_the_counter_ticks_during_larger_actions(self):
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        for a in (2, 2, 2):
            step(tracker, toy, a)
        # Each step moves the piece and ticks a counter cell the estimate has not reached yet.
        facts = [step(tracker, toy, a) for a in (1, 4, 1, 4)]
        self.assertEqual([f['new_board'] for f in facts], [True, False, False, False])
        self.assertEqual(facts[-1]['stale'], 3)

    def test_repeats_before_the_counter_was_found_are_counted_once_it_is(self):
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        early = [step(tracker, toy, a) for a in (1, 4, 1, 4)]
        self.assertEqual([f['stale'] for f in early], [0, 0, 0, 0])     # every board looks new: the counter ticks
        late = [step(tracker, toy, a) for a in (2, 2, 2)]
        # With three counter-only actions the bar is recognised and the attempt is judged again.
        self.assertEqual(late[-1]['stale'], 6)

    def test_controller_actions_do_not_count_as_stalled_model_actions(self):
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        for a in (2, 2, 2):
            step(tracker, toy, a, by_model=False)
        self.assertEqual(tracker.stale, 0)
        self.assertEqual(step(tracker, toy, 2)['stale'], 1)

    def test_a_check_is_due_at_the_window_and_then_only_after_another_window(self):
        c = settings(model_may_reset=True, stall_window=2)
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        due = []
        for _ in range(5):
            step(tracker, toy, 2)
            reasons = tracker.due(c)
            due.append(reasons)
            if reasons:
                tracker.checked(reasons)
        # The third tick reveals the counter and three stale actions at once; then one more window.
        self.assertEqual(due, [[], [], ['no_new_board'], [], ['no_new_board']])

    def test_same_notes_condition_holds_the_check_back_while_claims_change(self):
        c = settings(model_may_reset=True, stall_window=2, stall_same_notes=True)
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        for n in range(3):
            notes = [{'id': 'h', 'statement': 's%d' % n, 'status': 'tentative' if n < 1 else 'contradicted'}]
            step(tracker, toy, 2, notes=notes)
            if n == 1:
                self.assertEqual(tracker.due(c), [])      # two stale actions, but the claim's status just changed
        self.assertEqual(tracker.due(c), [])              # the status has now been the same for only one action
        self.assertEqual(tracker.due(replace(c, stall_same_notes=False)), ['no_new_board'])
        step(tracker, toy, 2, notes=[{'id': 'h', 'statement': 'reworded', 'status': 'contradicted'}])
        self.assertEqual(tracker.due(c), ['no_new_board'])   # rewording alone is not a change of memory

    def test_level_check_repeats_one_baseline_after_the_last_check(self):
        c = settings(model_may_reset=True, stall_level_ratio=1.0, level_baselines={'toy': [4, 4]})
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        fired = []
        for n in range(1, 13):
            step(tracker, toy, 2)
            baseline = recovery.baseline_for(c, 'toy-test', tracker.level)
            reasons = tracker.due(c, baseline)
            if reasons:
                fired.append(n)
                tracker.checked(reasons, {'choice': 'continue', 'reason': 'r'}, baseline)
        self.assertEqual(fired, [4, 8, 12])
        self.assertEqual(tracker.last_answer['at_actions_on_this_level'], 12)
        self.assertIsNone(recovery.baseline_for(c, 'other-game', 0))
        self.assertIsNone(recovery.baseline_for(c, 'toy-test', 2))

    def test_a_tracker_that_starts_far_past_the_threshold_checks_once_not_every_turn(self):
        """After a resume the level count is already high: one check, then one baseline later."""
        c = settings(model_may_reset=True, stall_level_ratio=1.0, level_baselines={'toy': [3, 3]})
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        for _ in range(10):                     # ten actions with nobody asking, as during a resume
            step(tracker, toy, 2)
        fired = []
        for n in range(11, 18):
            reasons = tracker.due(c, 3)
            if reasons:
                fired.append(n)
                tracker.checked(reasons, None, 3)
            step(tracker, toy, 2)
        self.assertEqual(fired, [11, 14, 17])

    def test_level_floor_delays_the_first_level_check(self):
        c = settings(model_may_reset=True, stall_level_ratio=1.0, stall_level_floor=6, level_baselines={'toy': [2, 2]})
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        fired = []
        for n in range(1, 8):
            step(tracker, toy, 2)
            if tracker.due(c, 2):
                fired.append(n)
                tracker.checked(['level_actions'], None, 2)
        self.assertEqual(fired[0], 6)

    def test_reset_keeps_the_ended_attempt_and_never_offers_its_fatal_action(self):
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        step(tracker, toy, 1, name='t1')
        step(tracker, toy, 3, name='t2')
        self.assertEqual(tracker.replay_limit(), 0)        # an attempt in progress has nothing to replay
        step(tracker, toy, 0, by_model=False, name='t3')
        self.assertEqual((len(tracker.ended_attempt), tracker.replay_limit()), (2, 1))
        offer = tracker.offer()
        self.assertEqual((offer['ended_attempt'], offer['ended_by']), ([[1, 't1', 1]], 'GAME_OVER'))
        self.assertEqual((tracker.level_actions, tracker.level_resets, tracker.level_game_overs), (3, 1, 1))
        self.assertIsNone(tracker.offer(at_most=0))

    def test_a_reset_must_leave_room_for_a_new_attempt(self):
        self.assertFalse(recovery.can_pay_back(1))
        self.assertTrue(recovery.can_pay_back(2))
        self.assertTrue(recovery.can_pay_back(17, baseline=32))     # 16 left after the reset, half of 32
        self.assertFalse(recovery.can_pay_back(16, baseline=32))

    def test_check_shows_only_the_agents_own_play(self):
        c = settings(model_may_reset=True, stall_level_ratio=1.0, recovery_pricing=True, level_baselines={'toy': [2, 2]})
        toy = Toy()
        tracker = recovery.Tracker(toy.board())
        for _ in range(3):
            step(tracker, toy, 2)
        block = recovery.check_block(tracker, ['level_actions'], c)
        self.assertEqual(block['a_reset_would_cost'], {'the_reset': 1, 'actions_on_this_attempt_given_up': 3})
        text = json.dumps(block)
        for word in ('human', 'baseline', 'left', 'budget', 'remain'):
            self.assertNotIn(word, text)


class Controller(Base):
    def test_model_reset_is_sent_counted_and_audited(self):
        c = settings(model_may_reset=True, max_actions_per_game=4)
        result, arc_, backend, events, folder = self.play(c, [1, 0, 1, 1])
        self.assertEqual([a for a, _ in arc_.actions], [1, 0, 1, 1])
        row = result['games'][0]
        self.assertEqual((row['model_resets'], row['actions_acknowledged']), (1, 4))
        states = [e for e in events if e['kind'] == 'recovery_state']
        self.assertEqual([s['attempt_actions'] for s in states], [1, 0, 1, 2])
        self.assertEqual(states[-1]['level_actions'], 4)   # the reset is counted on the level
        audit.audit(folder)

    def test_reset_is_refused_wherever_no_action_has_been_taken_on_the_attempt(self):
        cases = {'at the start': [0, 1, 1],
                 'after a reset': [1, 0, 0, 1, 1],
                 'after a level change': [1, 1, 1, 0, 1, 1],
                 'after a controller reset': [3, 0, 1, 1]}
        for name, answers in cases.items():
            with self.subTest(name):
                c = settings(model_may_reset=True, max_actions_per_game=len(answers))
                result, arc_, backend, events, folder = self.play(c, answers)
                refused = [payload(r).get('previous_reply_rejected', '') for r in backend.requests]
                self.assertEqual(sum('reset refused' in text for text in refused), 1)
                sent = [a for a, _ in arc_.actions]
                self.assertFalse(any(x == y == 0 for x, y in zip(sent, sent[1:])), sent)
                audit.audit(folder)

    def test_control_still_rejects_a_model_reset(self):
        c = settings(max_actions_per_game=2)
        result, arc_, backend, events, folder = self.play(c, [1, 0, 1])
        self.assertEqual([a for a, _ in arc_.actions], [1, 1])
        self.assertIn('invalid action', payload(backend.requests[2])['previous_reply_rejected'])

    def test_audit_refuses_resets_the_rules_do_not_allow(self):
        """A reset that slipped past the policy (forced here) must not pass the independent audit."""
        def forged(self, text, observation, recovery=None):
            return ActionDecision(0, {}, source='api_evaluation'), {'action': {'action_id': 0, 'action_data': {}},
                                                                    'hypotheses': []}
        with patch.object(policy.Policy, 'parse', forged):
            # Without the switch the controller sends it (the fake game accepts anything) and the audit refuses.
            result, arc_, backend, events, folder = self.play(settings(max_actions_per_game=1), [0])
        self.assertEqual(arc_.actions, [(0, 'api_evaluation')])
        with self.assertRaisesRegex(ValueError, 'illegal level reset'):
            audit.audit(folder)
        with patch.object(policy.Policy, 'parse', forged):
            # With the switch the controller's own second lock stops it before it is sent.
            result, arc_, backend, events, folder = self.play(settings(model_may_reset=True, max_actions_per_game=1), [0])
        self.assertEqual(arc_.actions, [])
        self.assertIn('reset before the first action', [e for e in events if e['kind'] == 'game_failed'][0]['error'])

        class Fooled(recovery.Tracker):
            # A tracker that wrongly believes an action was already taken, so both controller locks pass.
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                self.attempt = [{'transition_id': 't0', 'action': {'action_id': 1, 'action_data': {}},
                                 'after_sha256': '', 'state': 'NOT_FINISHED'}]
        with patch.object(policy.Policy, 'parse', forged), patch.object(recovery, 'Tracker', Fooled):
            result, arc_, backend, events, folder = self.play(settings(model_may_reset=True, max_actions_per_game=1), [0])
        self.assertEqual(arc_.actions, [(0, 'api_evaluation')])
        with self.assertRaisesRegex(ValueError, 'illegal model reset'):      # the audit is the last lock
            audit.audit(folder)

    def test_on_a_replay_turn_the_models_prediction_is_not_scored_against_the_controllers_action(self):
        c = settings(model_may_reset=True, replay_after_reset=True, max_actions_per_game=4, stage='world_model')
        guess = {'any_frame_changed': False, 'final_frame_changed': False, 'level_increased': True}
        full = lambda a, **extra: act(a, experiment='', prediction=dict.fromkeys(policy.PREDICATES), **extra)
        answers = [full(1), full(0), {**full(2, replay=1), 'prediction': guess}, full(2)]
        result, arc_, backend, events, folder = self.play(c, answers)
        self.assertEqual(arc_.actions[2], (1, 'controller_replay'))
        replayed = [e for e in events if e['kind'] == 'transition'][2]
        self.assertTrue(all(check['predicted'] is None for check in replayed['prediction_checks'].values()))
        self.assertEqual(result['games'][0]['prediction_scored'], 0)

    def test_a_reset_that_restarts_the_whole_game_ends_that_game_and_fails_the_audit(self):
        c = settings(model_may_reset=True, max_actions_per_game=6, games=('toy', 'toz'))
        world = ToyArc(('toy-test', 'toz-test'), full_reset=('toy-test',))
        # toy: finish level 1, one action on level 2, reset -> the faulty game goes back to level 1.
        result, arc_, backend, events, folder = self.play(c, [1, 1, 1, 1, 0, 2, 2, 2, 2, 2, 2], arc=world)
        first, second = result['games']
        self.assertEqual((first['actions_acknowledged'], first['stop_reason']), (5, 'WholeGameReset'))
        self.assertEqual(second['actions_acknowledged'], 6)       # the other game was still played
        with self.assertRaisesRegex(ValueError, 'changed the number of completed levels'):
            audit.audit(folder)

    def test_stall_check_reaches_the_model_and_its_answer_is_logged(self):
        c = settings(model_may_reset=True, stall_window=2, max_actions_per_game=5)
        answers = [2, 2, 2, act(2, recovery={'choice': 'continue', 'reason': 'counter only'}), 1]
        result, arc_, backend, events, folder = self.play(c, answers)
        first, third = payload(backend.requests[0]), payload(backend.requests[3])
        self.assertNotIn('recovery_check', first['evidence'])
        self.assertNotIn('recovery', first['output_contract'])
        check = third['evidence']['recovery_check']
        self.assertEqual((check['why'], check['your_actions_in_a_row_without_a_new_board']), (['no_new_board'], 3))
        self.assertNotIn('a_reset_would_cost', check)
        self.assertIn('recovery', third['output_contract'])
        logged = [e for e in events if e['kind'] == 'recovery_check']
        self.assertEqual((len(logged), logged[0]['answer']['choice'], result['games'][0]['recovery_checks']),
                         (1, 'continue', 1))
        self.assertNotIn('recovery_check', payload(backend.requests[4])['evidence'])
        audit.audit(folder)

    def test_level_check_reaches_the_model_without_baseline_or_budget_and_recalls_the_last_answer(self):
        c = settings(model_may_reset=True, stall_level_ratio=1.0, level_baselines={'toy': [3, 3]},
                     max_actions_per_game=7)
        again = {'choice': 'continue', 'reason': 'still learning the counter'}
        answers = [2, 2, 2, act(2, recovery=again), 2, 2, act(2, recovery=again)]
        result, arc_, backend, events, folder = self.play(c, answers)
        checks = [payload(r)['evidence'].get('recovery_check') for r in backend.requests]
        self.assertEqual([bool(x) for x in checks], [False, False, False, True, False, False, True])   # at 3, then 3 later
        self.assertEqual(checks[3]['why'], ['level_actions'])
        self.assertNotIn('your_answer_at_the_last_check', checks[3])
        self.assertEqual(checks[6]['your_answer_at_the_last_check'],
                         {'at_actions_on_this_level': 3, **again})
        for request in backend.requests:
            for word in ('human', 'baseline', 'actions_left', 'budget'):
                self.assertNotIn(word, request['messages'][1]['content'])
        audit.audit(folder)

    def test_check_answer_must_agree_with_the_action(self):
        c = settings(model_may_reset=True, stall_window=2, max_actions_per_game=5)
        answers = [2, 2, 2, act(2, recovery={'choice': 'reset', 'reason': 'stuck'}),
                   act(0, recovery={'choice': 'reset', 'reason': 'stuck'}), 1]
        result, arc_, backend, events, folder = self.play(c, answers)
        self.assertEqual([a for a, _ in arc_.actions], [2, 2, 2, 0, 1])
        self.assertIn('disagree', payload(backend.requests[4])['previous_reply_rejected'])
        self.assertIn('recovery_check', payload(backend.requests[4])['evidence'])   # the retry keeps the facts
        self.assertEqual(result['games'][0]['recovery_checks'], 1)                   # one check, asked twice
        audit.audit(folder)

    def test_missing_recovery_answer_is_rejected_when_a_check_is_due(self):
        c = settings(model_may_reset=True, stall_window=2, max_actions_per_game=4, model_retries_per_action=0)
        result, arc_, backend, events, folder = self.play(c, [2, 2, 2, 2])
        self.assertEqual(len(arc_.actions), 3)
        failed = [e for e in events if e['kind'] == 'game_failed'][0]
        self.assertIn('a recovery check is due', failed['error'])

    def test_recovery_fields_nobody_asked_for_are_dropped_not_rejected(self):
        c = settings(model_may_reset=True, stall_window=5, replay_after_reset=True, max_actions_per_game=2)
        extra = act(1, recovery={'choice': 'continue', 'reason': 'unasked'}, replay=0)
        result, arc_, backend, events, folder = self.play(c, [extra, extra])
        self.assertEqual(([a for a, _ in arc_.actions], len(backend.requests)), ([1, 1], 2))
        self.assertFalse([e for e in events if e['kind'] in ('recovery_check', 'replay_entered')])
        # A replay nobody offered is a real request for something that will not happen: say so.
        result, arc_, backend, events, folder = self.play(c, [act(1, replay=3), 1, 1])
        self.assertIn('replay is only available', payload(backend.requests[1])['previous_reply_rejected'])
        self.assertEqual([a for a, _ in arc_.actions], [1, 1])
        # The control has no such fields in its schema and still rejects them.
        result, arc_, backend, events, folder = self.play(settings(max_actions_per_game=1, model_retries_per_action=0),
                                                          [extra])
        self.assertEqual(arc_.actions, [])

    def test_pricing_refuses_a_reset_that_cannot_pay_back_and_never_shows_the_budget(self):
        c = settings(model_may_reset=True, stall_window=2, recovery_pricing=True, max_actions_per_game=5)
        answers = [2, 2, 2, act(2, recovery={'choice': 'continue', 'reason': 'r'}), 0, 2]
        result, arc_, backend, events, folder = self.play(c, answers)
        cost = payload(backend.requests[3])['evidence']['recovery_check']['a_reset_would_cost']
        self.assertEqual(cost, {'the_reset': 1, 'actions_on_this_attempt_given_up': 3})
        self.assertEqual([a for a, _ in arc_.actions], [2, 2, 2, 2, 2])     # the reset on the last action was refused
        self.assertIn('too few actions remain', payload(backend.requests[5])['previous_reply_rejected'])
        for request in backend.requests[:5]:
            self.assertNotIn('actions_left', request['messages'][1]['content'])

    def test_pricing_uses_the_level_baseline_when_it_is_known(self):
        c = settings(model_may_reset=True, stall_level_ratio=4.0, recovery_pricing=True, max_actions_per_game=6,
                     level_baselines={'toy': [8, 8]})
        # Four of the baseline's eight actions must remain after a reset: sent with 5 left, refused with 3.
        result, arc_, backend, events, folder = self.play(c, [2, 0, 2, 0, 2, 2, 2])
        self.assertEqual([a for a, _ in arc_.actions], [2, 0, 2, 2, 2, 2])
        self.assertIn('too few actions remain', payload(backend.requests[4])['previous_reply_rejected'])

    def test_replay_repeats_the_ended_attempt_without_model_calls(self):
        c = settings(model_may_reset=True, replay_after_reset=True, max_actions_per_game=7)
        answers = [1, 1, 0, act(2, replay=2), 2, 2]
        result, arc_, backend, events, folder = self.play(c, answers)
        self.assertEqual(arc_.actions, [(1, 'api_evaluation'), (1, 'api_evaluation'), (0, 'api_evaluation'),
                                        (1, 'controller_replay'), (1, 'controller_replay'),
                                        (2, 'api_evaluation'), (2, 'api_evaluation')])
        offer = payload(backend.requests[3])['evidence']['replay_offer']
        self.assertEqual((offer['largest_replay'], offer['ended_by'], [r[2] for r in offer['ended_attempt']]),
                         (2, 'RESET', [1, 1]))
        self.assertNotIn('replay_offer', payload(backend.requests[2])['evidence'])
        self.assertNotIn('replay_offer', payload(backend.requests[4])['evidence'])
        self.assertEqual((len(backend.requests), result['games'][0]['replayed_actions']), (6, 2))
        entered = [e for e in events if e['kind'] == 'replay_entered']
        self.assertEqual((entered[0]['actions'], entered[0]['model_action_not_sent']['action_id']), (2, 2))
        self.assertFalse([e for e in events if e['kind'] == 'replay_diverged'])
        audit.audit(folder)

    def test_replay_stops_at_the_first_board_that_differs(self):
        c = settings(model_may_reset=True, replay_after_reset=True, max_actions_per_game=6)
        answers = [1, 1, 0, act(2, replay=2), 2, 2]
        result, arc_, backend, events, folder = self.play(c, answers, arc=ToyArc(drift=True))
        self.assertEqual(arc_.actions[3], (1, 'controller_replay'))
        self.assertEqual(arc_.actions[4][1], 'api_evaluation')            # the second replayed action was dropped
        diverged = [e for e in events if e['kind'] == 'replay_diverged']
        self.assertEqual((len(diverged), diverged[0]['actions_dropped']), (1, 1))

    def test_a_replayed_action_that_ends_in_game_over_drops_the_rest(self):
        c = settings(model_may_reset=True, replay_after_reset=True, max_actions_per_game=8)
        # Three safe actions, a reset, then a replay of all three: the trap makes the first replayed step fatal.
        answers = [1, 4, 2, 0, act(2, replay=3), 2, 2]
        result, arc_, backend, events, folder = self.play(c, answers, arc=ToyArc(trap=True))
        self.assertEqual(arc_.actions[:6], [(1, 'api_evaluation'), (4, 'api_evaluation'), (2, 'api_evaluation'),
                                            (0, 'api_evaluation'), (1, 'controller_replay'),
                                            (0, 'controller_level_reset')])
        self.assertEqual(result['games'][0]['replayed_actions'], 1)
        audit.audit(folder)

    def test_replay_is_offered_after_a_game_over_and_leaves_out_the_fatal_action(self):
        c = settings(replay_after_reset=True, max_actions_per_game=6)
        answers = [1, 3, act(2, replay=1), 2, 2]
        result, arc_, backend, events, folder = self.play(c, answers)
        self.assertEqual(arc_.actions[:4], [(1, 'api_evaluation'), (3, 'api_evaluation'),
                                            (0, 'controller_level_reset'), (1, 'controller_replay')])
        offer = payload(backend.requests[2])['evidence']['replay_offer']
        self.assertEqual((offer['largest_replay'], offer['ended_by']), (1, 'GAME_OVER'))
        audit.audit(folder)

    def test_replay_above_the_offer_is_rejected(self):
        c = settings(model_may_reset=True, replay_after_reset=True, max_actions_per_game=5)
        answers = [1, 0, act(2, replay=5), act(2, replay=0), 2]
        result, arc_, backend, events, folder = self.play(c, answers)
        self.assertIn('replay must be', payload(backend.requests[3])['previous_reply_rejected'])
        self.assertEqual([a for a, _ in arc_.actions], [1, 0, 2, 2])

    def test_with_pricing_the_offer_never_exceeds_what_can_still_be_sent(self):
        c = settings(model_may_reset=True, replay_after_reset=True, recovery_pricing=True, max_actions_per_game=6)
        result, arc_, backend, events, folder = self.play(c, [1, 4, 2, 0, act(2, replay=1), 2])
        offer = payload(backend.requests[4])['evidence']['replay_offer']
        self.assertEqual(offer['largest_replay'], 1)      # three were played, two actions remain: at most one


class PinnedGameOvers(Base):
    """Memory fix: an action that ended in GAME_OVER stays in the input after it leaves the recent history."""

    def test_off_by_default_and_absent_from_the_request(self):
        result, arc_, backend, events, folder = self.play(settings(max_actions_per_game=4), [3, 2, 2])
        self.assertTrue(all('game_overs' not in payload(r)['evidence'] for r in backend.requests))

    def test_a_game_over_stays_in_every_later_request_with_both_boards(self):
        c = settings(pin_game_overs=2, history_limit=1, max_actions_per_game=7)
        # action 1, fatal action 3, controller reset, then four more actions: far beyond a history of 1.
        result, arc_, backend, events, folder = self.play(c, [1, 3, 2, 2, 2, 2])
        seen = [payload(r)['evidence'].get('game_overs') for r in backend.requests]
        self.assertEqual([bool(x) for x in seen], [False, False, True, True, True, True])
        record = seen[-1][0]
        self.assertEqual((record['transition_id'], record['action']['action_id'], record['after']['state']),
                         ('t2', 3, 'GAME_OVER'))
        self.assertEqual((record['before']['observation_id'], record['after']['observation_id']), ('o1', 'o2'))
        self.assertEqual(len(record['before']['final_frame']), 4)            # the toy board has four rows
        self.assertNotEqual(record['before']['final_frame'], record['after']['final_frame'])
        last = payload(backend.requests[-1])
        self.assertNotIn('t2', [h['transition_id'] for h in last['evidence']['history']])   # it had scrolled away
        self.assertIn(policy.GAME_OVER_NOTE, last['procedure'])
        self.assertNotIn(policy.GAME_OVER_NOTE, payload(backend.requests[0])['procedure'])
        audit.audit(folder)

    def test_only_the_most_recent_ones_are_kept_and_a_new_level_starts_clean(self):
        c = settings(pin_game_overs=1, max_actions_per_game=9, resets_per_game=5)
        # two deaths on level 1, then the level is completed (three steps right).
        result, arc_, backend, events, folder = self.play(c, [3, 3, 1, 1, 1, 2, 2])
        seen = [payload(r)['evidence'].get('game_overs') for r in backend.requests]
        self.assertEqual([x[0]['transition_id'] if x else None for x in seen],
                         [None, 't1', 't3', 't3', 't3', None, None])


class LevelTarget(Base):
    def test_a_game_ends_once_the_wanted_number_of_levels_is_done(self):
        c = settings(stop_after_levels=1, max_actions_per_game=8)
        result, arc_, backend, events, folder = self.play(c, [1, 1, 1, 2, 2])
        row = result['games'][0]
        self.assertEqual((row['actions_acknowledged'], row['levels_completed'], row['stop_reason']), (3, 1, 'level_target'))
        self.assertEqual(len(backend.requests), 3)
        audit.audit(folder)
        result, arc_, backend, events, folder = self.play(settings(max_actions_per_game=5), [1, 1, 1, 2, 2])
        self.assertEqual(result['games'][0]['actions_acknowledged'], 5)       # off by default: it plays on


class GameOverLessons(Base):
    """Memory fix: after a GAME_OVER the agent writes a general lesson, the controller keeps it, and (with
    lesson_check) every later action is checked against it."""
    LESSON = {'rule': 'ACTION3 ends the game wherever it is used.',
              'applies_when': 'The chosen action is ACTION3, on any board.'}

    def test_off_by_default(self):
        c = settings(max_actions_per_game=4)
        result, arc_, backend, events, folder = self.play(c, [3, 2, 2])
        for request in backend.requests:
            body = payload(request)
            self.assertNotIn('game_over_lessons', body['evidence'])
            self.assertFalse({'game_over_lesson', 'lesson_check'} & set(body['output_contract']))
        self.assertNotIn('game_over_lesson', policy.response_schema('hypotheses', c)['properties'])
        with self.assertRaises(ValueError):
            settings(lesson_check=True)

    def test_the_lesson_is_asked_for_once_kept_and_shown_from_then_on(self):
        c = settings(game_over_lessons=True, history_limit=1, max_actions_per_game=7)
        answers = [1, 3, act(2, game_over_lesson=self.LESSON), 2, 2, 2]
        result, arc_, backend, events, folder = self.play(c, answers)
        bodies = [payload(r) for r in backend.requests]
        asked = ['game_over_lesson' in b['output_contract'] for b in bodies]
        self.assertEqual(asked, [False, False, True, False, False, False])     # only on the turn after the reset
        self.assertIn(policy.LESSON_ASK % 't2', bodies[2]['procedure'])
        shown = [b['evidence'].get('game_over_lessons') for b in bodies]
        self.assertEqual(shown[:3], [None, None, None])
        self.assertEqual(shown[3], [{'after': 't2', 'level': 1, **self.LESSON}])
        self.assertEqual(shown[5], shown[3])                                    # still there, long after t2 left history
        self.assertFalse(any('lesson_check' in b['output_contract'] for b in bodies))
        audit.audit(folder)

    def test_a_reply_without_the_lesson_is_sent_back_with_the_reason(self):
        c = settings(game_over_lessons=True, max_actions_per_game=4)
        result, arc_, backend, events, folder = self.play(c, [1, 3, 2, act(2, game_over_lesson=self.LESSON), 2])
        self.assertIn('write game_over_lesson', payload(backend.requests[3])['previous_reply_rejected'])
        self.assertEqual([a for a, _ in arc_.actions], [1, 3, 0, 2])

    def test_with_the_check_every_later_reply_must_test_its_action_against_the_lessons(self):
        c = settings(game_over_lessons=True, lesson_check=True, max_actions_per_game=6)
        answers = [1, 3, act(2, game_over_lesson=self.LESSON), act(2, lesson_check='Not ACTION3, so the lesson does not apply.'),
                   2, act(2, lesson_check='Not ACTION3.')]
        result, arc_, backend, events, folder = self.play(c, answers)
        bodies = [payload(r) for r in backend.requests]
        self.assertEqual(['lesson_check' in b['output_contract'] for b in bodies], [False, False, False, True, True, True])
        self.assertIn(policy.CHECK_NOTE, bodies[3]['procedure'])
        self.assertIn('lesson_check is required', bodies[5]['previous_reply_rejected'])
        self.assertEqual(len(arc_.actions), 6)

    def test_lessons_survive_a_new_level_and_a_lesson_nobody_asked_for_is_dropped(self):
        c = settings(game_over_lessons=True, max_actions_per_game=8)
        answers = [3, act(1, game_over_lesson=self.LESSON), 1, 1, act(2, game_over_lesson={'rule': 'x', 'applies_when': 'y'}), 2]
        result, arc_, backend, events, folder = self.play(c, answers)
        last = payload(backend.requests[-1])
        self.assertEqual(last['evidence']['current']['levels_completed'], 1)
        self.assertEqual(last['evidence']['game_over_lessons'], [{'after': 't1', 'level': 1, **self.LESSON}])
        self.assertEqual(len(arc_.actions), 7)

    def test_schema_allows_the_new_fields_only_when_switched_on(self):
        on = policy.response_schema('hypotheses', settings(game_over_lessons=True, lesson_check=True))
        self.assertEqual(on['required'], ['action', 'hypotheses'])
        self.assertTrue({'game_over_lesson', 'lesson_check'} <= set(on['properties']))
        half = policy.response_schema('hypotheses', settings(game_over_lessons=True))
        self.assertNotIn('lesson_check', half['properties'])


class Resume(Base):
    def test_resume_rebuilds_the_position_and_the_next_request(self):
        c = settings(max_actions_per_game=5)
        notes = [{'id': 'h1', 'statement': 'ACTION1 steps right', 'status': 'supported_locally', 'evidence_ids': ['t1']}]
        answers = [1, act(2, hypotheses=notes), 3, 1, 2]       # the third action is fatal: the controller resets
        first = self.play(c, answers)
        saved = first[4] / 'events.jsonl'
        again = replace(c, resume_events=str(saved), resume_actions=4)
        result, arc_, backend, events, folder = self.play(again, [2])
        self.assertEqual(arc_.actions, [(1, 'controller_resume'), (2, 'controller_resume'), (3, 'controller_resume'),
                                        (0, 'controller_resume'), (2, 'api_evaluation')])
        self.assertEqual(len(backend.requests), 1)
        self.assertEqual(backend.requests[0], first[2].requests[3])       # the same request the first run made
        row = result['games'][0]
        self.assertEqual((row['resumed_actions'], row['level_resets'], row['actions_acknowledged']), (4, 1, 5))
        self.assertTrue([e for e in events if e['kind'] == 'resume_source'])
        audit.audit(folder)

    def test_a_game_whose_position_differs_is_stopped_and_the_next_game_is_still_played(self):
        c = settings(max_actions_per_game=4, games=('toy', 'toz'))
        games = ('toy-test', 'toz-test')
        first = self.play(c, [1, 1, 2, 2] * 2, arc=ToyArc(games))
        again = replace(c, resume_events=str(first[4] / 'events.jsonl'), resume_actions=3)
        # The first game now shows a different board from its third action on.
        result, arc_, backend, events, folder = self.play(again, [2], arc=ToyArc(games, drift=('toy-test',)))
        one, two = result['games']
        self.assertEqual((one['actions_acknowledged'], one['stop_reason']), (3, 'Diverged'))
        self.assertEqual((two['resumed_actions'], two['actions_acknowledged']), (3, 4))
        self.assertEqual(len(backend.requests), 1)        # only the second game reached the model
        self.assertIn('resume differed', [e for e in events if e['kind'] == 'game_failed'][0]['error'])

    def test_resume_refuses_before_any_scorecard(self):
        c = settings(max_actions_per_game=2)
        first = self.play(c, [1, 1])
        saved = str(first[4] / 'events.jsonl')
        treated = self.play(settings(model_may_reset=True, max_actions_per_game=2), [1, 1])
        cases = {'too short': replace(c, resume_events=saved, resume_actions=5),
                 'different prompt settings': replace(c, history_limit=3, resume_events=saved, resume_actions=1),
                 'different reset allowance': replace(c, resets_per_game=0, resume_events=saved, resume_actions=1),
                 'saved run was not a control run': replace(c, resume_events=str(treated[4] / 'events.jsonl'),
                                                            resume_actions=1)}
        for name, again in cases.items():
            with self.subTest(name):
                result, arc_, backend, events, folder = self.play(again, [])
                self.assertEqual((arc_.actions, arc_.closed), ([], 0))
                self.assertIn('controller: ValueError', result['problems'])

    def test_a_game_that_does_not_open_on_the_saved_board_is_dropped_before_any_action(self):
        c = settings(max_actions_per_game=2)
        first = self.play(c, [1, 1])
        again = replace(c, resume_events=str(first[4] / 'events.jsonl'), resume_actions=1)
        result, arc_, backend, events, folder = self.play(again, [1], arc=ToyArc(odd_start=True))
        self.assertEqual((arc_.actions, result['games'][0]['stop_reason']), ([], 'Diverged'))
        self.assertIn('first board differs', [e for e in events if e['kind'] == 'game_failed'][0]['error'])

    def test_a_saved_reply_must_belong_to_the_saved_action(self):
        c = settings(max_actions_per_game=2)
        first = self.play(c, [1, 2])
        lines = (first[4] / 'events.jsonl').read_text().splitlines()
        swapped = Path(self.temp.name) / 'swapped.jsonl'
        # Give the first action the reply recorded for the second: the loader must notice.
        replies = [i for i, line in enumerate(lines) if '"kind":"model_returned"' in line]
        lines[replies[0]], lines[replies[1]] = lines[replies[1]], lines[replies[0]]
        swapped.write_text('\n'.join(lines) + '\n')
        with self.assertRaisesRegex(ValueError, 'disagree'):
            resume.load(swapped, ['toy-test'], 2, c)


class SavedArc:
    """Serves one game of a saved run: the action sent must be the saved one."""

    def __init__(self, game, initial, steps):
        self.game, self.initial, self.steps, self.sent = game, initial, steps, 0

    @staticmethod
    def observation(value):
        return Observation(value['game_id'], tuple(np.asarray(f, dtype=np.uint8) for f in value['frames']),
                           GameState[value['state']], value['levels_completed'], value['win_levels'], 'saved-guid',
                           tuple(value['available_actions']), value['full_reset'])

    def list_game_ids(self):
        return (self.game,)

    def open_scorecard(self, tags):
        return 'saved-card'

    def bootstrap(self, game):
        return SimpleNamespace(observation=self.observation(self.initial), game_id=game)

    def dispatch(self, client, decision):
        action, after = self.steps[self.sent]
        if {'action_id': decision.action_id, 'action_data': dict(decision.action_data)} != action:
            raise AssertionError('not the saved action')
        self.sent += 1
        client.observation = self.observation(after)
        return client.observation

    def finalize_client(self, client):
        pass

    def close_scorecard(self):
        return {'score': 0, 'card_id': 'saved-card'}


@unittest.skipUnless(NOV6.exists(), 'the saved November 6 run is not on this machine')
class SavedRun(Base):
    """The control must still build the requests it built on November 6."""
    GAMES = {'bp35-0a0ad940': 60, 'tn36-ef4dde99': 80, 'ft09-0d8bbf25': 30}   # game -> actions repeated

    @classmethod
    def setUpClass(cls):
        cls.saved = {game: {'steps': [], 'requests': {}} for game in cls.GAMES}
        with NOV6.open() as handle:
            for line in handle:
                event = json.loads(line)
                game = event.get('game_id')
                if event['kind'] == 'configuration':
                    cls.config = event['config']
                if game not in cls.saved:
                    continue
                if event['kind'] == 'initial_observation':
                    cls.saved[game]['initial'] = event['observation']
                elif event['kind'] == 'model_entered' and not event.get('attempt'):
                    cls.saved[game]['requests'][event['action_index']] = event['request']
                elif event['kind'] == 'transition':
                    cls.saved[game]['steps'].append((event['action'], event['after']))

    def test_resumed_control_builds_the_saved_request(self):
        for game, count in self.GAMES.items():
            with self.subTest(game=game):
                saved = self.saved[game]
                c = config.Config(**{**self.config, 'mode': 'online', 'games': [game],
                                     'max_actions_per_game': count + 1, 'resume_events': str(NOV6),
                                     'resume_actions': count})
                self.assertFalse(c.recovery_on)
                wanted = saved['requests'][count]
                answer = {'action': saved['steps'][count][0], 'hypotheses': []}
                world = SavedArc(game, saved['initial'], saved['steps'])
                result, world, backend, events, folder = self.play(c, [answer], arc=world)
                self.assertEqual(len(backend.requests), 1)
                self.assertEqual(backend.requests[0], wanted)
                self.assertEqual(result['games'][0]['resumed_actions'], count)

    def test_tracker_follows_the_saved_run_without_changing_the_request(self):
        game, count = 'tn36-ef4dde99', 80
        saved = self.saved[game]
        c = config.Config(**{**self.config, 'mode': 'online', 'games': [game], 'max_actions_per_game': count + 1,
                             'resume_events': str(NOV6), 'resume_actions': count, 'model_may_reset': True})
        answer = {'action': saved['steps'][count][0], 'hypotheses': []}
        result, world, backend, events, folder = self.play(c, [answer], arc=SavedArc(game, saved['initial'], saved['steps']))
        got, wanted = backend.requests[0], saved['requests'][count]
        # Only the reset sentence and the action_id description differ from the saved control request.
        self.assertEqual(got['messages'][0]['content'].replace(recovery.RESET_ALLOWED, 'Never reset (action 0). '),
                         wanted['messages'][0]['content'])
        mine, theirs = payload(got), json.loads(wanted['messages'][1]['content'])
        self.assertEqual(mine['evidence'], theirs['evidence'])
        self.assertEqual(mine['procedure'], theirs['procedure'])
        states = [e for e in events if e['kind'] == 'recovery_state']
        self.assertEqual(len(states), count + 1)
        self.assertEqual(states[count - 1]['level_actions'], count)


if __name__ == '__main__':
    unittest.main()
