"""Track 3 runtime v2: CPU verification of the frozen detector and its supervision/outcome integration.

Every section is recomputed here and must equal the retained write-once receipt
(reports/stagnation_supervision_runtime_v2_detector_verification.json). No model, GPU or provider; the ls20 section
plays three fixed scripted policies on the offline development engine (descriptive, like the Tier B inspection)."""
import json
import unittest

from research.stagnation_supervision_runtime_v2 import verification as VV

RECEIPT = VV.ROOT / 'reports/stagnation_supervision_runtime_v2_detector_verification.json'


class DetectorVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(json.dumps(VV.run(), sort_keys=True))

    def test_all_sections_pass(self):
        for name in ('causality', 'thresholds', 'continuation', 'terminal_and_failures', 'display_vs_progress'):
            with self.subTest(name):
                self.assertTrue(self.result[name]['passed'], self.result[name].get('problems') or self.result[name].get('failures'))

    def test_result_reproduces_the_retained_receipt(self):
        self.assertEqual(self.result, json.loads(RECEIPT.read_bytes()))

    def test_causality_covers_every_fixture_step(self):
        self.assertEqual(self.result['causality']['trajectories'], 152)
        self.assertGreater(self.result['causality']['steps_prefix_replayed'], 1500)

    def test_frozen_thresholds_fire_exactly_where_intended(self):
        t = self.result['thresholds']
        self.assertEqual(t['recurrence_second_repeat'], [[], ['state_action_recurrence']])
        self.assertEqual(t['tiny_streak_first_firing_index'], 9)
        self.assertEqual(t['tiny_streak_with_failed_dispatch_first_firing_index'], 10)
        self.assertEqual(t['tiny_streak_with_unknown_outcome_first_firing_index'], 14)
        self.assertEqual((t['four_cells_tiny'], t['five_cells_tiny']), (True, False))
        self.assertEqual(t['cooldown_trigger_steps'], [1, 7, 13])

    def test_continuation_interruptions_on_held_out_and_archived_play(self):
        c = self.result['continuation']
        self.assertTrue(c['held_out_matches_retained_results'])
        self.assertEqual(c['held_out_fixtures']['families_with_false_interventions'], ['delayed_effect'])
        wa30 = c['archived_real_development_play']['wa30']
        self.assertEqual((wa30['steps'], wa30['lc_points'], wa30['triggers'], wa30['triggers_at_lc']), (48, 48, 1, 1))
        self.assertEqual(c['archived_real_development_play']['ar25']['lc_points'], 0)

    def test_display_novelty_never_becomes_recovery_or_solving_credit(self):
        d = self.result['display_vs_progress']
        osc = d['oscillation_with_display']
        self.assertEqual(osc['state_novelty']['full_frame_new_steps'], 40)
        self.assertGreaterEqual(osc['oscillation']['frame_above_display_revisit_steps'], 38)
        self.assertEqual((osc['detector']['firing_steps'], osc['completed_levels']), ([], 0))
        self.assertEqual(d['counter_only_repeat']['first_opportunity']['status'], 'not_recovered')
        self.assertEqual(d['counter_only_repeat']['first_opportunity']['new_frames_in_window'], 10)
        self.assertEqual(d['genuine_escape']['status'], 'recovered')
        self.assertEqual(d['genuine_escape']['completed_levels'], 1)
        ls20 = d['ls20_engine']['policies']
        for name in ('alternate_1_2', 'rotate_1_2_3_4'):  # oscillation: every full frame new, all LC, no firing
            policy = ls20[name]
            self.assertEqual(policy['state_novelty']['full_frame_new_steps'], 40)
            self.assertGreaterEqual(policy['oscillation']['frame_above_display_revisit_steps'], 35)
            self.assertEqual(policy['labels']['LC'], 40)
            self.assertEqual((policy['detector']['firing_steps'], policy['completed_levels']), ([], 0))
        wall = ls20['repeat_1']  # a blocked move repeats the whole frame: the detector does see it
        self.assertTrue(wall['detector']['triggers'])
        self.assertGreater(wall['labels']['ST'], wall['labels']['LC'])


if __name__ == '__main__':
    unittest.main()
