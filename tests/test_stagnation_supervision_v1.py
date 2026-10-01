"""Stagnation supervision v1 (Track 3): labelled fixtures, mechanical detector and the frozen trigger spec."""
import copy
import hashlib
import json
import random
import unittest

from research.stagnation_supervision_v1 import detector as D, fixtures as F, thresholds as S
from research.transition_evidence_v1 import transition as T

DEV = F.generate('development')
EVAL = F.generate('evaluation')
SPEC = S.load()


def run(raws, params, predictions=None, cooldown=S.COOLDOWN_ACTIONS):
    return D.triggers(D.statistics(T.history(raws), predictions), params, cooldown)


def fired(raws, params, predictions=None):
    return [d['action_index'] for d in run(raws, params, predictions) if d['signals']]


ALL_ON = {'repeat_no_effect': 2, 'state_action_recurrence': 2, 'tiny_effect_repeat': 2, 'novelty_stall': [2, 0],
          'prediction_failures': 1, 'no_progress_horizon': 1}


def raw(index, before, after=None, action=None, status='acknowledged', reset=False, levels=(0, 0)):
    out = {'identity': {'episode_id': 'u', 'action_index': index},
           'before': {'frames': [before], 'levels_completed': levels[0], 'state': 'NOT_FINISHED', 'full_reset': False},
           'proposal': None, 'dispatched': action or {'action_id': 6, 'action_data': {'x': 1, 'y': 1}},
           'environment_source': 'test'}
    if status == 'acknowledged':
        out['outcome'] = {'status': status, 'after': {'frames': [] if after is None else [after],
                                                      'levels_completed': levels[1], 'state': 'NOT_FINISHED',
                                                      'full_reset': reset}}
    else:
        out['outcome'] = {'status': status, 'reason': 'test'}
    return out


GRID = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]


class Fixtures(unittest.TestCase):
    def test_generation_is_deterministic_and_partitions_differ(self):
        self.assertEqual(F.encode(F.generate('development')), F.encode(DEV))
        self.assertNotEqual(F.digest('development'), F.digest('evaluation'))
        key = lambda f: hashlib.sha256(json.dumps(f['raws'], sort_keys=True).encode()).hexdigest()  # noqa: E731
        self.assertFalse({key(f) for f in DEV['fixtures']} & {key(f) for f in EVAL['fixtures']})

    def test_coverage_and_labels(self):
        for generated in (DEV, EVAL):
            truth = generated['evaluator_only']
            self.assertEqual({t['family'] for t in truth.values()}, set(F.FAMILIES))
            for fixture in generated['fixtures']:
                t = truth[fixture['id']]
                self.assertEqual(len(t['labels']), len(fixture['raws']))
                self.assertEqual(t['positive'], F.STAGNANT in t['labels'], fixture['id'])
                self.assertEqual(t['positive'], t['family'] in F.POSITIVE)
            self.assertTrue(any(f['predictions'] for f in generated['fixtures']))
            self.assertTrue(any(f['predictions'] is None for f in generated['fixtures']))

    def test_every_raw_builds_a_valid_transition_record(self):
        for fixture in DEV['fixtures'] + EVAL['fixtures']:
            for record in T.history(fixture['raws']):
                self.assertEqual(T.validate(record), [], fixture['id'])

    def test_no_labels_or_family_names_in_public_evidence(self):
        text = json.dumps([{k: f[k] for k in ('raws', 'predictions')} for f in DEV['fixtures'] + EVAL['fixtures']])
        for word in [F.STAGNANT, F.PRODUCTIVE, 'loop', 'counter', 'family', 'label'] + list(F.FAMILIES):
            self.assertNotIn(word, text)

    def test_hard_negative_families_have_the_stated_shape(self):
        for fixture in DEV['fixtures']:
            family = DEV['evaluator_only'][fixture['id']]['family']
            records = T.history(fixture['raws'])
            visual = [r['measurements']['visual_effect']['status'] for r in records]
            if family == 'delayed_effect':  # no observed change until the release
                self.assertEqual(set(visual[:-1]), {'no_observed_change'})
                self.assertEqual(visual[-1], 'final_frame_differs')
            if family == 'backtracking_required':  # states are revisited, never with the same action
                fps = [r['observations']['before_frames_sha256'][-1] for r in records]
                pairs = [(fp, D.action_key(r['action']['dispatched'])) for fp, r in zip(fps, records)]
                self.assertLess(len(set(fps)), len(fps))
                self.assertEqual(len(set(pairs)), len(pairs))
            if family == 'reset_then_replay':
                self.assertGreater(len({r['segment'] for r in records}), 1)


class DetectorEvidenceRules(unittest.TestCase):
    def test_causal_output_at_t_depends_only_on_records_up_to_t(self):
        for fixture in DEV['fixtures'][::7]:
            full = run(fixture['raws'], ALL_ON, fixture['predictions'])
            for t in range(len(fixture['raws'])):
                self.assertEqual(run(fixture['raws'][:t + 1], ALL_ON, fixture['predictions'])[t], full[t])

    def test_failed_dispatches_are_never_no_effect_evidence(self):
        raws = [raw(i, GRID, status='failed') for i in range(8)]
        self.assertEqual(fired(raws, ALL_ON), [])

    def test_unknown_outcome_and_missing_frames_add_nothing_and_break_streaks(self):
        params = {'repeat_no_effect': None, 'tiny_effect_repeat': 3}
        steady = [raw(i, GRID, GRID) for i in range(3)]
        self.assertEqual(fired(steady, params), [2])
        broken = [raw(0, GRID, GRID), raw(1, GRID, GRID, status='outcome_unknown'), raw(2, GRID, GRID)]
        self.assertEqual(fired(broken, params), [])
        missing = [raw(0, GRID, GRID), raw(1, GRID, None), raw(2, GRID, GRID)]
        self.assertEqual(fired(missing, params), [])
        self.assertEqual(fired([raw(i, GRID, None) for i in range(6)], ALL_ON), [])

    def test_a_failed_dispatch_neither_extends_nor_breaks_a_pattern(self):
        params = {'tiny_effect_repeat': 3}
        raws = [raw(0, GRID, GRID), raw(1, GRID, status='failed'), raw(2, GRID, GRID), raw(3, GRID, GRID)]
        self.assertEqual(fired(raws, params), [3])

    def test_a_reset_starts_a_new_segment(self):
        moved = copy.deepcopy(GRID)
        moved[0][0] = 9
        go = {'action_id': 1, 'action_data': {}}
        raws = [raw(0, GRID, moved, go), raw(1, moved, GRID, {'action_id': 0, 'action_data': {}}, reset=True),
                raw(2, GRID, moved, go)]
        self.assertEqual(fired(raws, {'state_action_recurrence': 2}), [])
        raws[1]['outcome']['after']['full_reset'] = False  # the same frames without a reported reset: a recurrence
        self.assertEqual(fired(raws, {'state_action_recurrence': 2}), [2])

    def test_progress_is_not_inferred_from_pixels(self):
        changes = []
        for i in range(12):
            after = copy.deepcopy(GRID)
            after[i % 3][(i // 3) % 3] = 10 + i % 5
            changes.append(raw(i, GRID, after, {'action_id': 6, 'action_data': {'x': i, 'y': 0}}))
        self.assertIn(9, fired(changes, {'no_progress_horizon': 10}))  # visible change is not progress
        changes[5]['outcome']['after']['levels_completed'] = 1
        for r in changes[6:]:
            r['before']['levels_completed'] = r['outcome']['after']['levels_completed'] = 1
        self.assertEqual(fired(changes, {'no_progress_horizon': 10}), [])  # the level change restarts the count

    def test_prediction_outcomes_are_scored_only_against_measured_effects(self):
        raws = [raw(0, GRID, GRID), raw(1, GRID, None), raw(2, GRID, status='failed'), raw(3, GRID, GRID)]
        predictions = [{'action_index': i, 'expects_change': True} for i in range(4)]
        stats = D.statistics(T.history(raws), predictions)
        self.assertEqual([s.get('prediction_failures') for s in stats], [[0], None, None, [3]])

    def test_consistent_colour_relabelling_preserves_decisions(self):
        perm = list(range(16))
        random.Random(5).shuffle(perm)
        for fixture in DEV['fixtures'][::5]:
            relabelled = copy.deepcopy(fixture['raws'])
            for r in relabelled:
                observations = [r['before']] + ([r['outcome']['after']] if 'after' in r['outcome'] else [])
                for o in observations:
                    o['frames'] = [[[perm[v] for v in row] for row in g] for g in o['frames']]
            strip = lambda ds: [(d['action_index'], d['trigger'], [s['signal'] for s in d['signals']]) for d in ds]  # noqa: E731
            self.assertEqual(strip(run(relabelled, ALL_ON, fixture['predictions'])),
                             strip(run(fixture['raws'], ALL_ON, fixture['predictions'])))

    def test_cooldown_suppresses_and_retains(self):
        raws = [raw(i, GRID, GRID) for i in range(10)]
        decisions = run(raws, {'repeat_no_effect': 2}, cooldown=4)
        self.assertEqual([d['action_index'] for d in decisions if d['trigger']], [1, 5, 9])
        self.assertEqual([d['action_index'] for d in decisions if d.get('suppressed') == 'cooldown'], [2, 3, 4, 6, 7, 8])

    def test_every_signal_cites_its_evidence(self):
        for fixture in DEV['fixtures']:
            for d in run(fixture['raws'], ALL_ON, fixture['predictions']):
                for s in d['signals']:
                    self.assertTrue(s['evidence'])
                    self.assertLessEqual(max(s['evidence']), d['action_index'])


class FrozenTriggerSpec(unittest.TestCase):
    def test_selection_on_development_reproduces_the_frozen_spec(self):
        self.assertEqual(S.encode(S.select(DEV)), S.SPEC.read_text(encoding='utf-8'))
        self.assertEqual(SPEC['development_fixtures_sha256'], F.digest('development'))

    def test_selection_refuses_the_evaluation_partition(self):
        with self.assertRaises(ValueError):
            S.select(EVAL)
        mixed = {**DEV, 'fixtures': DEV['fixtures'] + EVAL['fixtures'][:1]}
        with self.assertRaises(ValueError):
            S.select(mixed)

    def test_spec_respects_its_own_constraint_and_declares_references(self):
        m = SPEC['development_metrics']
        self.assertLessEqual(m['false_intervention_rate'], S.MAX_FALSE_INTERVENTION_RATE)
        self.assertEqual(set(SPEC['params']), set(D.SIGNALS))
        self.assertEqual(set(SPEC['references']), {'repeat_no_effect_only_k3', 'no_progress_horizon_only_10',
                                                   'periodic_every_6'})
        self.assertEqual(SPEC['cooldown_actions'], S.COOLDOWN_ACTIONS)


if __name__ == '__main__':
    unittest.main()
