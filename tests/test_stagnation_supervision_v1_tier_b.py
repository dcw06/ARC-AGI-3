"""Stagnation supervision v1 (Track 3): Tier B CPU scripted probe (offline development engine, no model)."""
import json
import runpy
import unittest

from research.stagnation_supervision_v1 import tier_b_probe as P

STORED = json.loads(P.RESULTS.read_text(encoding='utf-8'))


class TierBProbe(unittest.TestCase):
    def test_result_reproduces_from_the_offline_engine(self):
        self.assertEqual(json.loads(json.dumps(P.run())), STORED)

    def test_candidates_are_development_games_probed_in_the_written_order(self):
        self.assertEqual(STORED['candidates_in_order'], ['ls20-9607627b', 'tr87-cd924810', 'g50t-5849a774'])
        self.assertTrue(set(STORED['candidates_in_order']) <= P.development_games())
        probed = [r['game_id'] for r in STORED['probed']]
        self.assertEqual(probed, STORED['candidates_in_order'][:len(probed)])
        self.assertEqual(STORED['unprobed'], STORED['candidates_in_order'][len(probed):])
        # probing stops at the first qualifying candidate; every earlier one is reported as not qualifying
        self.assertTrue(all(not r['qualifies'] for r in STORED['probed'][:-1]))
        self.assertEqual(STORED['selected'], probed[-1] if STORED['probed'][-1]['qualifies'] else None)

    def test_every_probed_record_verifies_and_the_criterion_is_applied_as_written(self):
        for r in STORED['probed']:
            self.assertEqual(r['record_problems'], [])
            fraction_ok = r['new_frame_fraction'] is not None and r['new_frame_fraction'] >= P.MIN_NEW_FRACTION
            median_ok = r['median_changed_cells'] is not None and r['median_changed_cells'] > P.MIN_MEDIAN_CELLS
            self.assertEqual(r['qualifies'], r['observed_steps'] >= P.MIN_OBSERVED_STEPS and fraction_ok and median_ok)

    def test_result_is_write_once(self):
        with self.assertRaises(SystemExit):
            runpy.run_module('research.stagnation_supervision_v1.tier_b_probe', run_name='__main__')


if __name__ == '__main__':
    unittest.main()
