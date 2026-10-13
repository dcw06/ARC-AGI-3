import copy
import unittest
from research.conditional_transfer_v1 import fixtures as FX, independent_keys as IK, writer as W, score as SC, schema as S, replay as RP
from research.transition_evidence_v2 import transition as T2


class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = FX.generate()

    def test_independent_keys_all_families_and_delays(self):
        self.assertEqual(len(self.cases), 144)
        self.assertEqual(len({c['scenario_id'] for c in self.cases}), 48)
        for c in self.cases:
            with self.subTest(family=c['family'], group=c['group'], delay=c['delay']):
                self.assertEqual(IK.derive_facts(c['raws']), W.source_facts(c))
                for task, key in IK.keys(c).items():
                    self.assertEqual(SC.judge(W.source_facts(c), c['proposed_rule'], c['target'], task), key)

    def test_contract_continuity(self):
        for c in self.cases:
            self.assertEqual(T2.verify_history(c['records'], c['raws']), [])
            self.assertNotIn('differs_from_previous', [r['continuity']['status'] for r in c['records']])
            for left, right in zip(c['raws'], c['raws'][1:]):
                if left['outcome']['status'] == 'acknowledged':
                    self.assertEqual(left['outcome']['after']['frames'][-1], right['before']['frames'][-1])

    def test_failed_and_unknown_do_not_counter(self):
        for group, dispatch in ((2, 'outcome_unknown'), (5, 'failed')):
            c = FX.build('unknown_outcome', group)
            trial = [f for f in W.source_facts(c) if f['dispatch'] == dispatch]
            self.assertEqual(len(trial), 1)
            self.assertIsNone(trial[0]['visual'])
            key = IK.keys(c)
            self.assertEqual(key['target_support']['answer'], 'unobserved')
            self.assertEqual(key['contradiction']['answer'], 'not_observed')
            self.assertEqual(key['transfer']['answer'], 'unestablished')
            self.assertEqual(key['update']['answer'], 'retain')

    def test_coordinates_and_conditions_are_distinct(self):
        c = FX.build('coordinate_change', 1)
        self.assertNotEqual(c['target']['action'], c['proposed_rule']['action'])
        self.assertEqual(IK.keys(c)['transfer']['answer'], 'not_applicable')
        changed = FX.build('layout_change', 2)
        self.assertEqual(IK.keys(changed)['conditions']['answer'], 'match')
        self.assertEqual(IK.keys(changed)['transfer']['answer'], 'unestablished')

    def test_matching_appearance_does_not_prove_transfer(self):
        c = FX.build('appearance_match', 2)
        key = IK.keys(c)
        self.assertEqual(key['conditions']['answer'], 'match')
        self.assertEqual(key['target_support']['answer'], 'unobserved')
        self.assertEqual(key['transfer']['answer'], 'unestablished')

    def test_boundary_update_policy(self):
        self.assertEqual(IK.keys(FX.build('contradiction', 1))['update']['answer'], 'retire')
        self.assertEqual(IK.keys(FX.build('level_reset_boundary', 1))['update']['answer'], 'narrow')
        for g in (2, 5):
            c = FX.build('level_reset_boundary', g)
            self.assertGreater(c['target']['segment'], c['proposed_rule']['scope']['segment'])
            self.assertEqual(IK.keys(c)['transfer']['answer'], 'unestablished')

    def test_intermediate_change_not_no_change(self):
        c = FX.build('contradiction', 0)
        r = c['raws'][0]
        self.assertEqual(r['before']['frames'][-1], r['outcome']['after']['frames'][-1])
        self.assertNotEqual(r['before']['frames'][-1], r['outcome']['after']['frames'][0])
        self.assertEqual(IK.derive_facts(c['raws'])[0]['visual'], 'changed_then_returned')

    def test_split_reservations_and_cluster_identity(self):
        for f in FX.FAMILIES:
            self.assertEqual(len({FX.build(f, 0, d)['scenario_id'] for d in FX.DELAYS}), 1)
        with self.assertRaises(ValueError):
            FX.build('contradiction', 0, split='evaluation', seed='private-new-seed')
        with self.assertRaises(ValueError):
            FX.build('contradiction', 100, split='evaluation')
        c = FX.build('contradiction', 100, split='evaluation', seed='test-only-independent-eval-seed')
        self.assertNotIn(c['scenario_id'], {c['scenario_id'] for c in self.cases})
        self.assertEqual(c['split'], 'evaluation')

    def test_forged_evidence_rejected_after_updating_records_and_hash(self):
        c = copy.deepcopy(FX.build('contradiction', 1))
        c['raws'][0]['dispatched']['action_data']['x'] = 0
        c['records'] = T2.history(c['raws'])
        self.assertEqual(T2.verify_history(c['records'], c['raws']), [])
        self.assertEqual(len(RP.digest(c)), 64)
        with self.assertRaises(ValueError):
            RP.validate_case(c)

    def test_independent_keys_reject_wrong_target_annotation(self):
        c = copy.deepcopy(FX.build('appearance_match', 2))
        c['target']['level'] += 1
        with self.assertRaises(ValueError):
            IK.keys(c)


if __name__ == '__main__':
    unittest.main()
