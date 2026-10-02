"""Stagnation supervision v1 (Track 3): opportunity-based behavioural recovery, reference labels, the provisional
false-interruption gate, realised cost, the remaining-actions gate and the suggestion-block lifetime."""
import copy
import json
import random
import unittest

from research.stagnation_supervision_v1 import outcomes as O, supervision as SV, thresholds as S
from research.transition_evidence_v2 import transition as T2

SPEC = S.load()
H = 40


def grid(seed):
    """A seeded 6x6 frame; distinct seeds give frames differing in far more than 4 cells."""
    rng = random.Random(f'outcomes-grid-{seed}')
    return [[rng.randrange(16) for _ in range(6)] for _ in range(6)]


BASE = grid(0)


def tick(frame, n):
    """`frame` with a 1-cell counter at the bottom row set to n (a tiny, ever-new change)."""
    out = copy.deepcopy(frame)
    out[5][n % 6] = (out[5][n % 6] + 1 + n // 6) % 16
    return out


CLICK = {'action_id': 6, 'action_data': {'x': 1, 'y': 1}}
OTHER = {'action_id': 6, 'action_data': {'x': 4, 'y': 4}}


def move(k):
    return {'action_id': 1 + k % 4, 'action_data': {}}


def raw(i, before, after, action, status='acknowledged', levels=(0, 0), state='NOT_FINISHED', reset=False):
    out = {'identity': {'episode_id': 'o', 'action_index': i},
           'before': {'frames': [before], 'levels_completed': levels[0], 'state': 'NOT_FINISHED', 'full_reset': False},
           'proposal': None, 'dispatched': action, 'environment_source': 'test'}
    if status == 'acknowledged':
        out['outcome'] = {'status': status, 'after': {'frames': [after], 'levels_completed': levels[1], 'state': state,
                                                      'full_reset': reset}}
    else:
        out['outcome'] = {'status': status, 'reason': 'test'}
    return out


def chain(steps):
    """steps: list of (action, after_frame or None for no change, kwargs). Before-frames follow the afters."""
    raws, frame = [], BASE
    for i, (action, after, kw) in enumerate(steps):
        nxt = frame if after is None else after
        raws.append(raw(i, frame, nxt, action, **kw))
        if kw.get('status', 'acknowledged') == 'acknowledged':
            frame = nxt
    return raws


def loop_then(n_loop, tail):
    return chain([(CLICK, None, {})] * n_loop + tail)


def new_states(n, start=1):
    return [(move(k), grid(start + k), {}) for k in range(n)]


def first(raws):
    return O.opportunities(T2.history(raws), SPEC, H)


class Recovery(unittest.TestCase):
    def test_recovery_is_measurable_without_any_reflection(self):
        result = first(loop_then(2, new_states(13)))
        o = result['opportunities'][0]
        self.assertEqual((o['opened_at'], o['exit_at'], o['actions_to_exit'], o['status']), (1, 2, 1, 'recovered'))
        self.assertEqual(o['signals'], ['state_action_recurrence'])
        self.assertGreater(o['new_frames_in_window'], 0)
        self.assertGreater(o['new_state_action_pairs_in_window'], 0)

    def test_continuing_the_loop_is_not_recovery(self):
        o = first(loop_then(15, []))['opportunities'][0]
        self.assertEqual((o['status'], o['exit_at']), ('not_recovered', None))

    def test_escaping_into_another_loop_is_not_recovery(self):
        tail = [(OTHER, None, {})] * 13
        o = first(loop_then(2, tail))['opportunities'][0]
        self.assertEqual((o['exit_at'], o['status']), (2, 'not_recovered'))

    def test_a_late_exit_leaves_no_quiet_period(self):
        o = first(loop_then(8, new_states(10)))['opportunities'][0]
        self.assertEqual(o['opened_at'], 1)
        self.assertEqual((o['exit_at'], o['status']), (8, 'not_recovered'))

    def test_a_moving_counter_is_new_frames_not_recovery(self):
        frames = [tick(BASE, n) for n in range(1, 25)]
        raws = chain([(CLICK, f, {}) for f in frames])
        o = first(raws)['opportunities'][0]
        self.assertEqual(o['signals'], ['tiny_effect_repeat'])
        self.assertEqual(o['status'], 'not_recovered')
        self.assertEqual(o['new_frames_in_window'], 10)  # every frame is new; still the same pattern

    def test_unobserved_steps_make_recovery_indeterminate_and_failed_dispatches_are_skipped(self):
        tail = [(CLICK, None, {'status': 'outcome_unknown'})] + new_states(13)
        self.assertEqual(first(loop_then(2, tail))['opportunities'][0]['status'], 'indeterminate')
        tail = [(move(0), None, {'status': 'failed'})] + new_states(13)
        o = first(loop_then(2, tail))['opportunities'][0]
        self.assertEqual((o['exit_at'], o['status']), (3, 'recovered'))

    def test_horizon_and_terminal_censoring(self):
        result = O.opportunities(T2.history(loop_then(2, new_states(13))), SPEC, horizon=8)
        self.assertEqual((result['opportunities'], result['censored_horizon_firings']), ([], [1]))
        terminal = loop_then(2, new_states(2) + [(move(9), grid(30), {'state': 'GAME_OVER'})])
        self.assertEqual(first(terminal)['opportunities'][0]['status'], 'censored_terminal')
        win = loop_then(2, [(move(0), grid(5), {'levels': (0, 1)})] + new_states(12, start=40))
        o = first(win)['opportunities'][0]
        self.assertTrue(o['level_completed_in_window'])

    def test_windows_never_overlap(self):
        raws = chain([(CLICK, None, {})] * 30)
        opened = [o['opened_at'] for o in first(raws)['opportunities']]
        self.assertEqual(opened, [1, 12, 23])
        self.assertTrue(all(b - a > O.WINDOW for a, b in zip(opened, opened[1:])))

    def test_opportunities_do_not_depend_on_the_arm(self):
        raws = loop_then(3, new_states(12))
        a = O.recovery_summary([{'arm': 'continuation', 'records': T2.history(raws)}], SPEC, H)['continuation']
        b = O.recovery_summary([{'arm': 'triggered', 'records': T2.history(raws)}], SPEC, H)['triggered']
        self.assertEqual(a, b)


class ReferenceLabels(unittest.TestCase):
    def test_lc_st_ind(self):
        raws = chain(new_states(3) + [(CLICK, None, {})] * 4 + [(CLICK, None, {'status': 'outcome_unknown'})])
        labels = O.labels(T2.history(raws))
        self.assertEqual(labels[:3], ['LC', 'LC', 'LC'])
        self.assertEqual(labels[3:5], ['LC', 'LC'])  # the last new-frame move is still within the last 3 steps
        self.assertEqual(labels[5:7], ['ST', 'ST'])
        self.assertEqual(labels[7], 'UNOBSERVED')
        self.assertEqual(O.labels(T2.history(chain([(CLICK, None, {})] * 2))), ['IND', 'IND'])

    def test_a_counter_alone_is_not_lc(self):
        raws = chain([(CLICK, tick(BASE, n), {}) for n in range(1, 6)])
        self.assertEqual(O.labels(T2.history(raws))[2:], ['ST', 'ST', 'ST'])


class FalseInterruptionGate(unittest.TestCase):
    def episodes(self, n_eps, games, hits_per_ep):
        out = []
        for e in range(n_eps):
            records = T2.history(chain(new_states(20, start=e * 50 + 1)))
            out.append({'arm': 'triggered', 'game': games[e % len(games)], 'records': records,
                        'triggers': list(range(hits_per_ep)), 'calls': []})
        return out

    def test_wilson_reference_values(self):
        self.assertAlmostEqual(O.wilson(0, 60)[1], 0.0602, places=3)
        self.assertAlmostEqual(O.wilson(2, 60)[1], 0.1136, places=3)

    def test_minimum_evidence_is_required(self):
        r = O.interruptions(self.episodes(2, ['g1'], 0), 'triggered')
        self.assertEqual(r['status'], 'not_certifiable_minimum_not_met')
        self.assertIn('not establish that an interruption is genuinely harmful', r['limitation'])

    def test_within_and_exceeding_the_provisional_cap(self):
        ok = O.interruptions(self.episodes(6, ['g1', 'g2'], 0), 'triggered')
        self.assertEqual((ok['lc_points'], ok['interruptions_at_lc'], ok['status']), (120, 0, 'within_provisional_cap'))
        bad = O.interruptions(self.episodes(6, ['g1', 'g2'], 3), 'triggered')
        self.assertEqual(bad['status'], 'exceeds_provisional_cap')
        self.assertGreaterEqual(bad['upper_bound_used'], bad['wilson_95'][1])


class RealisedCost(unittest.TestCase):
    def test_equal_budget_is_not_equal_cost(self):
        rows = lambda n, tok: [{'status': 'called', 'valid': True, 'input_tokens': tok, 'output_tokens': 50,  # noqa: E731
                                'latency_s': 1.0}] * n
        cost = O.realised_cost([{'arm': 'periodic', 'reflections': rows(4, 900)},
                                {'arm': 'triggered', 'reflections': rows(2, 900)},
                                {'arm': 'continuation', 'reflections': []}])
        self.assertEqual(cost['by_arm']['periodic']['calls'], 4)
        self.assertEqual(cost['by_arm']['triggered']['tokens'], 1900)
        self.assertAlmostEqual(cost['triggered_to_periodic_token_ratio'], 0.5)
        self.assertIn('equal budget', cost['note'])


def echo(text):
    content = json.loads(text.split('Evidence:\n', 1)[1])
    shown = [e['action_index'] for e in content['evidence']]
    legal = [a for a in content['available_actions'] if 1 <= a <= 7]
    action = {'action_id': legal[0], 'action_data': {'x': 0, 'y': 0} if legal[0] == 6 else {}}
    return {'text': json.dumps({'observed_pattern': 'Repeats.', 'evidence_refs': shown[-2:],
                                'assumption_to_reconsider': 'That it responds.',
                                'distinguishing_test': {'description': 'Probe once.', 'actions': [action]}}),
            'input_tokens': 100, 'output_tokens': 50, 'latency_s': 0.5}


class SupervisionAdditions(unittest.TestCase):
    def run_arm(self, arm, raws, policy=None, call=echo):
        s = SV.Supervisor(arm, SPEC, call, {**SV.POLICY, **(policy or {})}, clock=lambda: 0.0, episode_actions=H)
        for r in raws:
            s.observe(r)
        return s

    def test_no_reflection_without_a_full_recovery_window(self):
        raws = chain([(CLICK, None, {})] * H)
        s = self.run_arm('triggered', raws, {'max_interventions_per_episode': 99})
        self.assertEqual([e['action_index'] for e in s.events if e['outcome'] == 'called'], [1, 7, 13, 19, 25])
        late = [e for e in s.events if e['outcome'] == 'suppressed_insufficient_remaining_actions']
        self.assertEqual(min(e['action_index'] for e in late), 30)
        p = self.run_arm('periodic', raws, {'period_actions': 10})
        self.assertEqual([e['action_index'] for e in p.events if e['outcome'] == 'called'], [9, 19, 29])
        self.assertEqual(p.events[39]['outcome'], 'suppressed_insufficient_remaining_actions')

    def test_suggestion_block_lifetime_replacement_and_clearing(self):
        raws = chain([(CLICK, None, {})] * 12)
        s = self.run_arm('triggered', raws)
        self.assertIsNone(s.suggestion_for(2))  # the block from the call at 1 was replaced by the call at 7
        block = s.suggestion_for(8)
        self.assertEqual((block['label'], block['issued_after_action'], block['expires_after_action']),
                         (SV.SUGGESTION_LABEL, 7, 17))
        fresh = SV.Supervisor('triggered', SPEC, echo, clock=lambda: 0.0, episode_actions=H)
        for r in raws[:2]:
            fresh.observe(r)
        self.assertIsNone(fresh.suggestion_for(1))
        self.assertEqual(fresh.suggestion_for(11)['issued_after_action'], 1)
        self.assertIsNone(fresh.suggestion_for(12))  # lifetime: the next 10 policy requests
        reset = chain([(CLICK, None, {})] * 3 + [({'action_id': 0, 'action_data': {}}, grid(9), {'reset': True})])
        r = SV.Supervisor('triggered', SPEC, echo, clock=lambda: 0.0, episode_actions=H)
        for x in reset:
            r.observe(x)
        self.assertEqual(r.events[-1]['suggestion_cleared'], ['reset_acknowledged'])
        self.assertIsNone(r.suggestion_for(4))

    def test_an_invalid_reflection_neither_delivers_nor_replaces(self):
        outputs = iter([echo, lambda _t: {'text': 'not json', 'input_tokens': 10, 'output_tokens': 5}])

        def call(text):
            return next(outputs)(text)
        s = self.run_arm('triggered', chain([(CLICK, None, {})] * 9), call=call)
        called = [e for e in s.events if e['outcome'] == 'called']
        self.assertEqual([e['delivered'] is not None for e in called], [True, False])
        self.assertEqual(s.suggestion_for(8)['issued_after_action'], 1)

    def test_periodic_and_triggered_blocks_are_identical_in_form(self):
        raws = chain([(CLICK, None, {})] * 12)
        t = self.run_arm('triggered', raws).suggestion_for(12)  # issued after action 7
        p = self.run_arm('periodic', raws, {'period_actions': 6}).suggestion_for(12)  # issued after action 11
        self.assertEqual(set(t), set(p))
        self.assertEqual((t['label'], t['expires_after_action'] - t['issued_after_action']),
                         (p['label'], p['expires_after_action'] - p['issued_after_action']))


if __name__ == '__main__':
    unittest.main()
