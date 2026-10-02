"""Transition evidence v2 (draft): version 1 preserved exactly, identity and context, available actions, and the
masked view checked against an independent brute-force count and the archived real development transitions."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

from research.transition_evidence_v1 import fixtures as F1, transition as T1, vocabulary as V1
from research.transition_evidence_v2 import masks as MASKS, transition as T, vocabulary as V

FROZEN = json.loads(F1.OUTPUT.read_bytes())
ROOT = Path(__file__).resolve().parents[1]


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


class ValidationRegressions(unittest.TestCase):
    """Contradictions the first draft's validate() accepted (probed before this fix); each must now be refused."""

    def setUp(self):
        pre = [[0] * 10 for _ in range(8)]
        frame = copy.deepcopy(pre)
        frame[7][9] = 1  # inside the region
        frame[1][1] = 1  # outside it
        self.mask = mask([[5, 7, 9, 7]])
        self.raw = raw(pre, [frame], available=[1, 6])
        self.base = T.build(self.raw, self.mask)
        self.assertEqual(T.validate(self.base), [])

    def refused(self, mutate, base=None):
        record = copy.deepcopy(base or self.base)
        mutate(record)
        return T.validate(record)

    def test_malformed_context_and_available_actions(self):
        def context(key, value):
            return lambda r: r['context'].__setitem__(key, value)
        cases = {
            'level as bool': context('levels_completed_before', V.measured(True)),
            'level as string': context('levels_completed_before', V.measured('2')),
            'negative level': context('levels_completed_before', V.measured(-1)),
            'level not measured': context('levels_completed_before', V.absent('x')),
            'state not a string': context('state_before', V.measured(3)),
            'actions not a list': context('available_actions_before', V.measured('1,6')),
            'actions with a float': context('available_actions_before', V.measured([1, 6.0])),
            'actions with a bool': context('available_actions_before', V.measured([True, 6])),
            'actions duplicated': context('available_actions_before', V.measured([1, 1])),
            'actions unsorted': context('available_actions_before', V.measured([6, 1])),
            'absent without reason': context('available_actions_before', {'status': 'absent'}),
            'measured with a stray reason': context('available_actions_before',
                                                    {'status': 'measured', 'value': [1], 'reason': 'x'}),
            'context removed': lambda r: r.pop('context'),
            'context with an extra field': context('why', 'counter'),
            'level contradicts the reported level': context('levels_completed_before', V.measured(5)),
            'actions after malformed': lambda r: r['environment']['reported'].__setitem__(
                'available_actions_after', V.measured([1.0])),
            'actions-changed contradicts the actions': lambda r: r['environment']['reported'].__setitem__(
                'available_actions_changed', V.measured(True)),
            'actions-changed removed': lambda r: r['environment']['reported'].pop('available_actions_changed'),
        }
        for name, mutate in cases.items():
            self.assertNotEqual(self.refused(mutate), [], name)
        failed = T.build({**self.raw, 'outcome': {'status': 'failed', 'reason': 'test'}})
        self.assertEqual(T.validate(failed), [])
        self.assertNotEqual(self.refused(lambda r: r['environment'].__setitem__(
            'reported', {'available_actions_after': V.measured([1])}), failed), [], 'reported after a failed dispatch')

    def test_contradictory_masked_counts_and_summaries(self):
        def frame(key, value):
            return lambda r: r['masked']['frames'][0].__setitem__(key, value)
        cases = {
            'outside count inflated': frame('changed_outside', V.measured(5)),
            'inside count zeroed': frame('changed_inside', V.measured(0)),
            'count as bool': frame('changed_inside', V.measured(True)),
            'differs_outside contradicts the count': frame('differs_outside', V.measured(False)),
            'summary claims no change outside': lambda r: r['masked'].update(
                any_returned_frame_differs_outside=V.measured(False), final_frame_equals_pre_outside=V.measured(True),
                visual_effect_outside={'status': V.NO_OBSERVED_CHANGE, 'reason': 'x'}),
            'region change denied': lambda r: r['masked'].__setitem__('mask_region_changed', V.measured(False)),
            'mask for another shape': lambda r: r['masked']['mask'].__setitem__('frame_shape', [64, 64]),
            'frames truncated': lambda r: r['masked'].__setitem__('frames', []),
            'frame index shifted': frame('index', 3),
            'extra summary field': lambda r: r['masked'].__setitem__('no_effect', True),
            'unavailable with measurements': lambda r: r['masked'].__setitem__('status', 'unavailable'),
            'malformed mask': lambda r: r['masked']['mask'].__setitem__('rects_xyxy', [[0, 0, 99, 0]]),
        }
        for name, mutate in cases.items():
            self.assertNotEqual(self.refused(mutate), [], name)

    def test_a_consistent_forgery_passes_validate_but_not_verify(self):
        forged = copy.deepcopy(self.base)
        f = forged['masked']['frames'][0]
        f['changed_outside'], f['changed_inside'] = V.measured(0), V.measured(2)  # same total, moved inside
        f['differs_outside'] = V.measured(False)
        forged['masked'].update(T._summary(forged['masked']['frames'], V.COMPLETE))
        self.assertEqual(T.validate(forged), [])  # internally consistent: a record alone cannot reveal it
        self.assertEqual(T.verify(self.base, self.raw, self.mask), [])
        self.assertNotEqual(T.verify(forged, self.raw, self.mask), [])


class MaskNeverSuppresses(unittest.TestCase):
    def setUp(self):
        self.pre = [[0] * 10 for _ in range(8)]
        self.region = mask([[5, 7, 9, 7]])
        self.counter_only = copy.deepcopy(self.pre)
        self.counter_only[7][9] = 3

    def assert_same_outside_masked(self, r):
        with_mask, without = T.build(r, self.region), T.build(r)
        for key in ('dispatch', 'environment', 'progress', 'context', 'measurements', 'observations'):
            self.assertEqual(with_mask[key], without[key], key)
        return with_mask

    def test_level_completion_terminal_state_and_action_changes_are_reported_regardless(self):
        r = raw(self.pre, [self.counter_only], available=[1, 6], levels_completed=3, state='WIN')
        r['outcome']['after']['available_actions'] = [1]
        record = self.assert_same_outside_masked(r)
        self.assertEqual(record['masked']['visual_effect_outside']['status'], V.NO_OBSERVED_CHANGE)
        self.assertIn(V.LEVEL_COMPLETED, record['environment']['events'])
        self.assertIn(V.TERMINAL_STATE, record['environment']['events'])
        self.assertEqual(record['progress']['status'], V.CONFIRMED)
        self.assertEqual(record['environment']['reported']['available_actions_changed'], V.measured(True))

    def test_dispatch_uncertainty_is_never_masked(self):
        for status in ('failed', 'outcome_unknown'):
            record = self.assert_same_outside_masked(raw(self.pre, status=status))
            self.assertEqual(record['masked']['status'], 'unavailable')
            self.assertEqual(record['measurements']['visual_effect']['status'], V.INDETERMINATE)

    def test_wording_is_no_observed_change_outside_the_declared_region(self):
        record = T.build(raw(self.pre, [self.counter_only]), self.region)
        reason = record['masked']['visual_effect_outside']['reason']
        self.assertTrue(reason.startswith('no observed change outside the declared region'))
        self.assertIn('does not establish that the action had no effect', reason)


class ReviewOf19c211b(unittest.TestCase):
    """Review of 19c211b: type-changing edits, nonexistent action ids, and a contradictory starting state."""

    def setUp(self):
        pre = [[0] * 10 for _ in range(8)]
        frame = copy.deepcopy(pre)
        frame[7][9] = 1
        frame[1][1] = 1
        self.mask = mask([[5, 7, 9, 7]])
        self.raw = raw(pre, [frame], available=[1, 6])
        self.base = T.build(self.raw, self.mask)

    def both_refuse(self, record, name):
        self.assertNotEqual(T.validate(record), [], f'validate: {name}')
        self.assertNotEqual(T.verify(record, self.raw, self.mask), [], f'verify: {name}')

    def test_equality_is_type_sensitive(self):
        self.assertFalse(T.same(True, 1))
        self.assertFalse(T.same(6, 6.0))
        self.assertFalse(T.same({'a': [1, False]}, {'a': [1, 0]}))
        self.assertTrue(T.same(self.base, copy.deepcopy(self.base)))

    def test_boolean_flags_replaced_by_integers_are_refused(self):
        def masked_frame(r):
            r['masked']['frames'][0]['differs_outside'] = V.measured(1)

        def masked_summary(r):
            r['masked']['any_returned_frame_differs_outside'] = V.measured(1)
            r['masked']['final_frame_equals_pre_outside'] = V.measured(0)
            r['masked']['mask_region_changed'] = V.measured(1)

        def full_frame(r):
            r['measurements']['any_returned_frame_differs'] = V.measured(1)
            r['measurements']['frames'][0]['vs_pre']['differs'] = V.measured(1)

        def validity(r):
            r['measurements']['frames'][0]['valid'] = 1
            r['masked']['frames'][0]['valid'] = 1

        def actions_changed(r):
            r['environment']['reported']['available_actions_changed'] = V.measured(0)

        for mutate in (masked_frame, masked_summary, full_frame, validity, actions_changed):
            record = copy.deepcopy(self.base)
            mutate(record)
            self.both_refuse(record, mutate.__name__)

    def test_a_float_action_id_is_refused_by_verify_too(self):
        record = copy.deepcopy(self.base)
        record['action']['dispatched']['action_id'] = 1.0
        self.both_refuse(record, 'dispatched action id as float')
        record = copy.deepcopy(self.base)
        record['context']['available_actions_before'] = V.measured([1, 6.0])
        self.both_refuse(record, 'available action as float')

    def test_available_actions_must_exist_in_the_action_vocabulary(self):
        self.assertEqual(V.ACTION_VOCABULARY, (0, 1, 2, 3, 4, 5, 6, 7))
        pre = [[0] * 10 for _ in range(8)]
        ok = T.build(raw(pre, [pre], available=[0, 1, 2, 3, 4, 5, 6, 7]))
        self.assertEqual(T.validate(ok), [])
        for bad in ([8], [999], [-1], [1, 8], ['1']):
            r = raw(pre, [pre], available=bad)
            record = T.build(r)  # retained as reported, never silently repaired
            self.assertNotEqual(T.validate(record), [], bad)
            self.assertNotEqual(T.verify(record, r), [], bad)
            after_only = raw(pre, [pre], available=[1])
            after_only['outcome']['after']['available_actions'] = bad
            self.assertNotEqual(T.validate(T.build(after_only)), [], f'after: {bad}')

    def test_starting_state_must_agree_with_the_environment_report(self):
        record = copy.deepcopy(self.base)
        record['context']['state_before'] = V.measured('GAME_OVER')
        self.assertIn('context state contradicts the reported state before the action', T.validate(record))
        self.assertNotEqual(T.verify(record, self.raw, self.mask), [])
        failed = T.build({**self.raw, 'outcome': {'status': 'failed', 'reason': 'test'}})
        self.assertEqual(T.validate(failed), [])  # nothing was reported after a failed dispatch to disagree with

    def test_verify_history_rejects_type_changes_and_invalid_records(self):
        raws = [raw([[0] * 10 for _ in range(8)], [[[0] * 10 for _ in range(8)]], index=i, available=[1])
                for i in range(2)]
        records = T.history(raws)
        self.assertEqual(T.verify_history(records, raws), [])
        changed = copy.deepcopy(records)
        changed[1]['measurements']['final_frame_equals_pre'] = V.measured(1)
        self.assertNotEqual(T.verify_history(changed, raws), [])


class ArchivedDevelopmentTransitions(unittest.TestCase):
    """The 144 real development transitions of action-effect-history v1, read after the archive lock verifies.

    The s5i5 region was declared from these same transitions: this describes what the masked view reports there.
    It is development evidence, not an independent validation of the region."""

    @classmethod
    def setUpClass(cls):
        from scripts.replay_transition_evidence_v1 import AEH_LOCK, parse_action, raw_step, verified_zip
        lock, bundle = verified_zip(AEH_LOCK)
        cls.games = {}
        for name in sorted(n for n in lock['members'] if '/episodes/' in n and n.endswith('.json')):
            episode = json.loads(bundle.read(name))
            raws = [raw_step(episode['episode_id'], s, parse_action(episode['calls'][s['call_index']]['response']),
                             'offline_development_engine') for s in episode['steps']]
            cls.games.setdefault(episode['game_id'], []).append(raws)

    def records(self, game_id, use_mask):
        mask = MASKS.declared_mask(game_id) if use_mask else None
        out = []
        for raws in self.games[game_id]:
            records = T.history(raws, mask)
            self.assertEqual(T.verify_history(records, raws, mask), [])
            out += records
        return out

    def game(self, prefix):
        return next(g for g in self.games if g.startswith(prefix))

    def test_every_record_validates_verifies_and_reports_available_actions(self):
        records = [r for g in self.games for r in self.records(g, use_mask=True)]
        self.assertEqual(len(records), 144)
        for r in records:
            self.assertEqual(T.validate(r), [])
            self.assertEqual(r['context']['available_actions_before']['status'], 'measured')
            self.assertEqual(r['environment']['reported']['available_actions_after']['status'], 'measured')

    def test_s5i5_every_change_is_inside_the_declared_region(self):
        records = self.records(self.game('s5i5'), use_mask=True)
        self.assertEqual(len(records), 48)
        self.assertEqual({r['measurements']['visual_effect']['status'] for r in records}, {V.FINAL_FRAME_DIFFERS})
        self.assertEqual({r['masked']['visual_effect_outside']['status'] for r in records}, {V.NO_OBSERVED_CHANGE})
        self.assertTrue(all(r['masked']['mask_region_changed'] == V.measured(True) for r in records))

    def test_ar25_and_wa30_stay_unmasked(self):
        for prefix in ('ar25', 'wa30'):
            self.assertIsNone(MASKS.declared_mask(self.game(prefix)))
            for r in self.records(self.game(prefix), use_mask=True):
                self.assertEqual(r['masked'], {'status': 'unavailable', 'reason': 'no mask was supplied'})


class FrozenDeclaredMasks(unittest.TestCase):
    def test_only_s5i5_is_declared_with_its_exact_region_and_source(self):
        table = MASKS.load()
        self.assertEqual(table['status'], 'frozen')
        self.assertEqual(set(table['masks']), {'s5i5'})
        self.assertEqual(set(table['unmasked']), {'ar25', 'wa30'})
        mask = MASKS.declared_mask('s5i5-18d95033')
        self.assertEqual(mask['frame_shape'], [64, 64])
        self.assertEqual(mask['rects_xyxy'], [[49, 63, 63, 63]])
        self.assertEqual(mask['provenance']['kind'], V.DECLARED)
        self.assertIn('selected from development evidence', mask['provenance']['basis'])
        self.assertIn('not established as irrelevant', mask['provenance']['basis'])
        lock = json.loads((ROOT / table['source_archive']['lock']).read_bytes())
        self.assertEqual(table['source_archive']['sha256'], lock['archive_sha256'])
        self.assertIn(lock['archive_sha256'], mask['provenance']['source'])

    def test_games_are_matched_on_their_full_id(self):
        for game_id in ('s5i5', 's5i5-00000000', 'ar25-0c556536', 'wa30-ee6fef47'):
            self.assertIsNone(MASKS.declared_mask(game_id), game_id)

    def test_an_edited_table_is_refused(self):
        original = MASKS.PATH
        try:
            edited = Path(tempfile.mkdtemp()) / 'declared_masks.json'
            edited.write_bytes(original.read_bytes().replace(b'[49, 63, 63, 63]', b'[48, 63, 63, 63]'))
            MASKS.PATH = edited
            with self.assertRaises(ValueError):
                MASKS.load()
        finally:
            MASKS.PATH = original
            edited.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
