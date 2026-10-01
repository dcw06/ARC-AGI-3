"""Transition evidence v2 (draft): version 1 preserved exactly, identity and context, available actions, and the
masked view checked against an independent brute-force count and the archived real development transitions."""
import copy
import json
import random
import unittest

from research.transition_evidence_v1 import fixtures as F1, transition as T1, vocabulary as V1
from research.transition_evidence_v2 import transition as T, vocabulary as V

FROZEN = json.loads(F1.OUTPUT.read_bytes())


def mask(rects, shape=(8, 10), kind=V.DECLARED):
    return {'id': 'm', 'frame_shape': list(shape), 'rects_xyxy': rects,
            'provenance': {'kind': kind, 'source': 'test', 'basis': 'constructed for the test'}}


def raw(before, frames=None, status='acknowledged', index=0, available=None, **after):
    observation = {'frames': [before], 'levels_completed': 2, 'state': 'NOT_FINISHED', 'full_reset': False}
    if available is not None:
        observation['available_actions'] = available
    if status == 'acknowledged':
        outcome = {'status': status, 'after': {**copy.deepcopy(observation), 'frames': frames, **after}}
    else:
        outcome = {'status': status, 'reason': 'test'}
    return {'identity': {'episode_id': 'e', 'action_index': index}, 'before': observation, 'proposal': None,
            'dispatched': {'action_id': 1, 'action_data': {}}, 'outcome': outcome, 'environment_source': 'test'}


def brute(pre, frame, m):
    """Independent outside/inside counts: flatten both frames and test every cell against every rectangle."""
    outside = inside = 0
    width = len(pre[0])
    for i, (a, b) in enumerate(zip(sum(pre, []), sum(frame, []))):
        if a != b:
            x, y = i % width, i // width
            hit = False
            for x0, y0, x1, y1 in m['rects_xyxy']:
                hit = hit or (x0 <= x <= x1 and y0 <= y <= y1)
            inside += hit
            outside += not hit
    return outside, inside


class PreservesVersion1(unittest.TestCase):
    def test_vocabulary_values_are_version_1s(self):
        for name in ('DISPATCH', 'AVAILABILITY', 'VISUAL', 'ENVIRONMENT_EVENTS', 'PROGRESS', 'CONTINUITY',
                     'ALLOWED_PROGRESS_SIGNALS'):
            self.assertEqual(getattr(V, name), getattr(V1, name))

    def test_every_frozen_fixture_contains_its_version_1_record_exactly(self):
        for fixture in FROZEN['fixtures']:
            raws = fixture['raws']
            v1 = T1.history(raws)
            shape = T1.shape(raws[0]['before']['frames'][-1])
            for masks in (None, mask([[0, 0, 0, 0]], shape)):
                v2 = T.history(raws, masks)
                self.assertEqual([T.to_v1(r) for r in v2], v1, fixture['id'])
                for record in v2:
                    self.assertEqual(T.validate(record), [], fixture['id'])


class IdentityAndContext(unittest.TestCase):
    def setUp(self):
        self.pre = [[0] * 10 for _ in range(8)]

    def test_record_id_and_model_statements_cite_it(self):
        record = T.build(raw(self.pre, [self.pre], index=5))
        self.assertEqual(record['identity']['record_id'], 'e#5')
        statement = T.model_statement(record['identity'], 'prediction', {'x': 1}, 'test')
        self.assertEqual(statement['about_record_id'], 'e#5')
        self.assertEqual(statement['status'], 'hypothesis')

    def test_failed_and_unknown_dispatches_keep_the_level_they_started_from(self):
        for status in ('failed', 'outcome_unknown'):
            record = T.build(raw(self.pre, status=status, available=[1, 6]))
            self.assertEqual(record['context']['levels_completed_before'], V.measured(2))
            self.assertEqual(record['context']['available_actions_before'], V.measured([1, 6]))
            self.assertIsNone(record['environment']['reported'])  # nothing after the action was observed
            self.assertEqual(record['masked']['status'], 'unavailable')

    def test_available_actions_are_reported_or_absent_never_assumed(self):
        with_actions = T.build(raw(self.pre, [self.pre], available=[6, 1]))
        self.assertEqual(with_actions['context']['available_actions_before'], V.measured([1, 6]))
        self.assertEqual(with_actions['environment']['reported']['available_actions_after'], V.measured([1, 6]))
        without = T.build(raw(self.pre, [self.pre]))
        self.assertEqual(without['context']['available_actions_before']['status'], 'absent')
        self.assertEqual(without['environment']['reported']['available_actions_after']['status'], 'absent')


class MaskedView(unittest.TestCase):
    def setUp(self):
        self.pre = [[0] * 10 for _ in range(8)]
        self.bar = mask([[5, 7, 9, 7]])  # bottom row, x 5..9

    def changed(self, *cells, base=None):
        frame = copy.deepcopy(base or self.pre)
        for x, y in cells:
            frame[y][x] = (frame[y][x] + 1) % 16
        return frame

    def test_counts_match_an_independent_brute_force_count(self):
        rng = random.Random(11)
        for _ in range(300):
            h, w = rng.randint(1, 9), rng.randint(1, 9)
            pre = [[rng.randrange(16) for _ in range(w)] for _ in range(h)]
            frame = [[v if rng.random() < 0.7 else rng.randrange(16) for v in row] for row in pre]
            rects = []
            for _ in range(rng.randint(1, 3)):
                x0, y0 = rng.randrange(w), rng.randrange(h)
                rects.append([x0, y0, rng.randint(x0, w - 1), rng.randint(y0, h - 1)])
            m = mask(rects, (h, w))
            view = T.build(raw(pre, [frame]), m)['masked']
            got = (view['frames'][0]['changed_outside']['value'], view['frames'][0]['changed_inside']['value'])
            self.assertEqual(got, brute(pre, frame, m))

    def test_a_change_only_inside_the_mask_is_set_aside_not_denied(self):
        record = T.build(raw(self.pre, [self.changed((9, 7))]), self.bar)
        self.assertEqual(record['measurements']['visual_effect']['status'], V.FINAL_FRAME_DIFFERS)  # primary
        self.assertEqual(record['masked']['visual_effect_outside']['status'], V.NO_OBSERVED_CHANGE)
        self.assertEqual(record['masked']['mask_region_changed'], V.measured(True))
        self.assertIn('set aside, not denied', record['masked']['visual_effect_outside']['reason'])

    def test_changes_outside_the_mask_are_kept(self):
        record = T.build(raw(self.pre, [self.changed((9, 7), (1, 1))]), self.bar)
        self.assertEqual(record['masked']['visual_effect_outside']['status'], V.FINAL_FRAME_DIFFERS)
        transient = T.build(raw(self.pre, [self.changed((1, 1)), self.changed((9, 7))]), self.bar)
        self.assertEqual(transient['masked']['visual_effect_outside']['status'], V.CHANGED_THEN_RETURNED)

    def test_a_mask_cannot_create_a_change(self):
        record = T.build(raw(self.pre, [self.pre]), self.bar)
        self.assertEqual(record['masked']['visual_effect_outside']['status'], V.NO_OBSERVED_CHANGE)
        self.assertEqual(record['masked']['mask_region_changed'], V.measured(False))
        forged = copy.deepcopy(record)
        forged['masked']['visual_effect_outside'] = {'status': V.FINAL_FRAME_DIFFERS, 'reason': 'forged'}
        self.assertIn('a mask cannot create a change that the unmasked frames do not show', T.validate(forged))

    def test_invalid_frames_and_shape_changes_stay_undecided_or_changed(self):
        partial = T.build(raw(self.pre, [self.changed((9, 7)), 'bad']), self.bar)
        self.assertEqual(partial['masked']['visual_effect_outside']['status'], V.INDETERMINATE)
        self.assertEqual(partial['masked']['mask_region_changed'], V.measured(True))
        partial_ok_final = T.build(raw(self.pre, ['bad', self.changed((9, 7))]), self.bar)
        self.assertEqual(partial_ok_final['masked']['any_returned_frame_differs_outside']['status'], 'unavailable')
        bigger = T.build(raw(self.pre, [[[0] * 11 for _ in range(8)]]), self.bar)
        self.assertEqual(bigger['masked']['visual_effect_outside']['status'], V.FINAL_FRAME_DIFFERS)
        self.assertEqual(bigger['masked']['frames'][0]['changed_outside']['status'], 'unavailable')

    def test_a_mask_for_another_frame_shape_does_not_apply(self):
        record = T.build(raw(self.pre, [self.changed((9, 7))]), mask([[0, 0, 1, 1]], (5, 5)))
        self.assertEqual(record['masked']['status'], 'unavailable')
        self.assertIn('does not apply', record['masked']['reason'])

    def test_malformed_masks_are_refused(self):
        bad = [mask([[0, 0, 10, 0]]), mask([]), mask([[3, 0, 2, 0]]), mask([[0, 0, 1, 1]], kind='guessed'),
               {**mask([[0, 0, 1, 1]]), 'why': 'a counter'}, {**mask([[0, 0, 1, 1]]), 'id': ''},
               mask([[0, 0, True, 1]])]
        for m in bad:
            with self.assertRaises(ValueError, msg=repr(m)):
                T.build(raw(self.pre, [self.pre]), m)

    def test_the_record_names_no_cause_for_the_masked_region(self):
        record = T.build(raw(self.pre, [self.changed((9, 7))]), self.bar)
        text = json.dumps(record['masked']).lower()
        for word in ('counter', 'timer', 'hud', 'score', 'budget'):
            self.assertNotIn(word, text)


class ArchivedDevelopmentTransitions(unittest.TestCase):
    """The 144 real development transitions of action-effect-history v1, read after the archive lock verifies.

    The s5i5 mask was declared from these same transitions, so this is a description of what the masked view
    reports there, not a validation of the mask."""
    S5I5_BAR = {'id': 's5i5-bottom-row-x49-63', 'frame_shape': [64, 64], 'rects_xyxy': [[49, 63, 63, 63]],
                'provenance': {'kind': V.DECLARED, 'source': 'action_effect_history_v1 development archive',
                               'basis': 'in all 48 s5i5 transitions every changed cell lay in row 63, x 49..63'}}

    @classmethod
    def setUpClass(cls):
        from scripts.replay_transition_evidence_v1 import AEH_LOCK, parse_action, raw_step, verified_zip
        lock, bundle = verified_zip(AEH_LOCK)
        cls.games = {}
        for name in sorted(n for n in lock['members'] if '/episodes/' in n and n.endswith('.json')):
            episode = json.loads(bundle.read(name))
            raws = [raw_step(episode['episode_id'], s, parse_action(episode['calls'][s['call_index']]['response']),
                             'offline_development_engine') for s in episode['steps']]
            cls.games.setdefault(episode['game_id'].split('-')[0], []).append(raws)

    def records(self, game, masks=None):
        return [r for raws in self.games[game] for r in T.history(raws, masks)]

    def test_every_record_validates_and_reports_available_actions(self):
        records = [r for game in self.games for r in self.records(game)]
        self.assertEqual(len(records), 144)
        for r in records:
            self.assertEqual(T.validate(r), [])
            self.assertEqual(r['context']['available_actions_before']['status'], 'measured')
            self.assertEqual(r['environment']['reported']['available_actions_after']['status'], 'measured')

    def test_s5i5_every_change_is_inside_the_declared_bar(self):
        records = self.records('s5i5', self.S5I5_BAR)
        self.assertEqual(len(records), 48)
        self.assertEqual({r['measurements']['visual_effect']['status'] for r in records}, {V.FINAL_FRAME_DIFFERS})
        self.assertEqual({r['masked']['visual_effect_outside']['status'] for r in records}, {V.NO_OBSERVED_CHANGE})
        self.assertTrue(all(r['masked']['mask_region_changed'] == V.measured(True) for r in records))

    def test_other_games_are_unchanged_without_a_mask(self):
        for game in ('ar25', 'wa30'):
            for r in self.records(game):
                self.assertEqual(r['masked']['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
