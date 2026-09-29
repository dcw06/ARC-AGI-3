"""Transition evidence v1 (Workstream 3): comparator, records, fixtures and the independent reference."""
import ast
import copy
import json
from pathlib import Path
import random
import unittest

from research.transition_evidence_v1 import fixtures as F, reference as REF, transition as T, vocabulary as V

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads(F.OUTPUT.read_bytes())


def value(measure):
    return measure['value'] if measure['status'] == 'measured' else None


def comparator_facts(record):
    m = record['measurements']
    vs_pre, vs_prev = [], []
    for f in m['frames']:
        if not f['valid']:
            vs_pre.append('invalid')
            vs_prev.append('invalid')
            continue
        vs_pre.append(value(f['vs_pre']['changed_cells']))
        prev = f['vs_previous']
        vs_prev.append('no_valid_previous' if prev['comparability'] == V.UNAVAILABLE else value(prev['changed_cells']))
    return {'dispatch': record['dispatch']['status'], 'availability': record['observations']['availability']['status'],
            'visual': m['visual_effect']['status'], 'vs_pre': vs_pre, 'vs_previous': vs_prev,
            'any_differs': value(m['any_returned_frame_differs']), 'final_equals': value(m['final_frame_equals_pre']),
            'events': record['environment']['events'], 'progress': record['progress']['status']}


class Fixtures(unittest.TestCase):
    def test_frozen_fixtures_match_a_fresh_generation(self):
        self.assertEqual(F.encode(F.generate()), F.OUTPUT.read_bytes())

    def test_coverage_and_partitions(self):
        families = {f['family'] for f in FROZEN['fixtures']}
        self.assertEqual(families, set(F.FAMILIES))
        for family in families:
            parts = {f['partition'] for f in FROZEN['fixtures'] if f['family'] == family}
            self.assertEqual(parts, {'development', 'evaluation'})
        raws = [r for f in FROZEN['fixtures'] for r in f['raws']]
        self.assertTrue(any(r['proposal'] is None for r in raws))
        self.assertNotIn('expected', json.dumps(FROZEN['fixtures']))
        self.assertNotIn('construction', json.dumps(FROZEN['fixtures']))

    def test_no_evaluator_data_or_game_rules_in_raw_evidence(self):
        text = json.dumps([f['raws'] for f in FROZEN['fixtures']]).lower()
        for word in ('bottom row', 'counter', 'death', 'reward', 'good action', 'cause'):
            self.assertNotIn(word, text)


class AgreementWithConstruction(unittest.TestCase):
    """Every fixture: comparator == construction-derived expectation == independent reference."""

    def test_every_transition(self):
        for fixture in FROZEN['fixtures']:
            expected = FROZEN['evaluator_only'][fixture['id']]['expected']
            records = T.history(fixture['raws'])
            sequence = REF.sequence(fixture['raws'])
            for raw, record, exp, (segment, continuity) in zip(fixture['raws'], records, expected, sequence):
                with self.subTest(fixture=fixture['id'], index=raw['identity']['action_index']):
                    self.assertEqual(T.validate(record), [])
                    got = comparator_facts(record)
                    ref = REF.facts(raw)
                    for key in ('dispatch', 'availability', 'visual', 'vs_pre', 'vs_previous', 'any_differs',
                                'final_equals', 'events', 'progress'):
                        self.assertEqual(got[key], exp[key], key)
                        self.assertEqual(ref[key], exp[key], 'reference ' + key)
                    self.assertEqual((record['segment'], record['continuity']['status']), (exp['segment'], exp['continuity']))
                    self.assertEqual((segment, continuity), (exp['segment'], exp['continuity']))
                    pe = record['action']['proposal_equals_dispatched']
                    self.assertEqual(value(pe), exp['proposal_equals_dispatched'])

    def test_reference_imports_nothing(self):
        tree = ast.parse((ROOT / 'research/transition_evidence_v1/reference.py').read_text(encoding='utf-8'))
        self.assertEqual([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))], [])


def raw_ack(before, frames, **after):
    return {'identity': {'episode_id': 't', 'action_index': 0},
            'before': {'frames': [before], 'levels_completed': 0, 'state': 'NOT_FINISHED', 'full_reset': False},
            'proposal': None, 'dispatched': {'action_id': 1, 'action_data': {}},
            'outcome': {'status': 'acknowledged', 'after': {'frames': frames, 'levels_completed': 0,
                                                            'state': 'NOT_FINISHED', 'full_reset': False, **after}},
            'environment_source': 'test'}


class Properties(unittest.TestCase):
    def setUp(self):
        rng = random.Random(7)
        self.pre = [[rng.randrange(16) for _ in range(9)] for _ in range(7)]
        self.mid = copy.deepcopy(self.pre)
        self.mid[2][3] = (self.mid[2][3] + 1) % 16
        self.mid[4][5] = (self.mid[4][5] + 2) % 16

    def facts(self, pre, frames):
        return comparator_facts(T.build(raw_ack(pre, frames)))

    def test_consistent_colour_relabelling_preserves_equality_and_counts(self):
        perm = list(range(16))
        random.Random(3).shuffle(perm)
        relabel = lambda g: [[perm[v] for v in row] for row in g]  # noqa: E731
        a = self.facts(self.pre, [self.mid, self.pre])
        b = self.facts(relabel(self.pre), [relabel(self.mid), relabel(self.pre)])
        self.assertEqual(a, b)

    def test_repeating_an_identical_frame_adds_no_change(self):
        once = self.facts(self.pre, [self.mid])
        twice = self.facts(self.pre, [self.mid, self.mid])
        self.assertEqual(twice['vs_previous'][1], 0)
        self.assertEqual((once['visual'], twice['visual']), (V.FINAL_FRAME_DIFFERS, V.FINAL_FRAME_DIFFERS))

    def test_intermediate_change_then_original_stays_transient(self):
        f = self.facts(self.pre, [self.mid, self.pre])
        self.assertEqual((f['visual'], f['any_differs'], f['final_equals']), (V.CHANGED_THEN_RETURNED, True, True))

    def test_missing_observations_never_produce_a_zero_count(self):
        record = T.build(raw_ack(self.pre, []))
        m = record['measurements']
        self.assertEqual(m['any_returned_frame_differs']['status'], 'unavailable')
        self.assertEqual(m['final_frame_equals_pre']['status'], 'unavailable')
        self.assertEqual(m['visual_effect']['status'], V.INDETERMINATE)
        self.assertNotIn('"value": 0', json.dumps(m['any_returned_frame_differs']))

    def test_unknown_outcome_breaks_unsupported_continuity(self):
        first = raw_ack(self.pre, [self.pre])
        first['outcome'] = {'status': 'outcome_unknown', 'reason': 'timeout'}
        second = raw_ack(self.pre, [self.pre])  # identical before-frame: still not evidence the action did nothing
        records = T.history([first, second])
        self.assertEqual(records[1]['continuity']['status'], V.GAP_UNKNOWN_OUTCOME)

    def test_reordering_intermediate_frames_changes_chronology_not_the_final_comparison(self):
        other = copy.deepcopy(self.pre)
        other[0][0] = (other[0][0] + 5) % 16
        a = self.facts(self.pre, [self.mid, other, self.pre])
        b = self.facts(self.pre, [other, self.mid, self.pre])
        self.assertEqual((a['final_equals'], a['visual']), (b['final_equals'], b['visual']))
        self.assertNotEqual(a['vs_pre'], b['vs_pre'])
        self.assertEqual(a['vs_previous'][1], b['vs_previous'][1])  # |mid xor other| is symmetric

    def test_dimension_change_has_no_cell_count_but_differs(self):
        f = self.facts(self.pre, [[row[:] for row in self.pre[:-1]]])
        self.assertEqual((f['vs_pre'], f['visual'], f['final_equals']), ([None], V.FINAL_FRAME_DIFFERS, False))

    def test_failed_dispatch_is_never_a_no_op(self):
        raw = raw_ack(self.pre, [self.pre])
        raw['outcome'] = {'status': 'failed', 'reason': 'rejected'}
        record = T.build(raw)
        self.assertEqual(record['measurements']['visual_effect']['status'], V.INDETERMINATE)
        self.assertEqual(record['observations']['availability']['status'], V.NOT_APPLICABLE)
        with self.assertRaises(ValueError):
            raw['outcome'] = {'status': 'failed'}
            T.build(raw)

    def test_visual_change_is_not_progress_and_progress_needs_an_allowed_signal(self):
        record = T.build(raw_ack(self.pre, [self.mid]))
        self.assertEqual(record['progress']['status'], V.UNKNOWN)
        self.assertIn('does not establish that no progress occurred', record['progress']['reason'])
        done = T.build(raw_ack(self.pre, [self.pre], levels_completed=1))
        self.assertEqual((done['progress']['status'], done['progress']['signals']), (V.CONFIRMED, ['levels_completed_increased']))
        self.assertEqual(done['measurements']['visual_effect']['status'], V.NO_OBSERVED_CHANGE)  # progress without change

    def test_validation_catches_collapsed_semantics(self):
        record = T.build(raw_ack(self.pre, []))
        record['measurements']['any_returned_frame_differs'] = V.measured(False)
        self.assertTrue(T.validate(record))
        record = T.build(raw_ack(self.pre, [self.mid]))
        record['progress'] = {'status': V.CONFIRMED, 'signals': ['pixels_changed']}
        self.assertTrue(T.validate(record))

    def test_model_statements_stay_separate_from_measurements(self):
        record = T.build(raw_ack(self.pre, [self.pre]))
        before = json.dumps(record, sort_keys=True)
        statement = T.model_statement(record['identity'], 'prediction', {'prediction': 'change'}, 'model')
        self.assertEqual(statement['status'], 'hypothesis')
        self.assertEqual(json.dumps(record, sort_keys=True), before)


if __name__ == '__main__':
    unittest.main()
