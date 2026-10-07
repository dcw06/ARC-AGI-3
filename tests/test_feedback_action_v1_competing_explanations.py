import unittest

from research.feedback_action_v1 import competing_explanations as CE


class CompetingExplanationFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = CE.generate()
        cls.fixtures = {fixture['public']['case_id']: fixture for fixture in cls.data['fixtures']}

    def test_frozen_challenge_fixtures_match_fresh_generation(self):
        self.assertEqual(CE.OUTPUT.read_bytes(), CE.encode(self.data))

    def test_all_requested_scenarios_are_present_and_development_only(self):
        self.assertEqual(set(self.fixtures), set(CE.CASES))
        for fixture in self.fixtures.values():
            self.assertEqual(fixture['source'], 'synthetic')
            self.assertEqual(fixture['partition'], 'development')

    def test_competing_worlds_have_identical_observations_before_probe(self):
        for case_id, case in CE.CASES.items():
            reference = CE.run_world(case_id, case['worlds'][0])
            for hypothesis_id in case['worlds'][1:]:
                candidate = CE.run_world(case_id, hypothesis_id)
                self.assertEqual(reference['history'], candidate['history'], case_id)
                self.assertEqual(reference['action_effect_view'], candidate['action_effect_view'], case_id)

    def test_independent_answer_checks_match_offline_engine_outcomes(self):
        for case_id, case in CE.CASES.items():
            fixture = self.fixtures[case_id]
            self.assertEqual(fixture['evaluator_only']['expected_outcomes'],
                             {key: list(value) for key, value in case['expected'].items()})
            for hypothesis_id, expected in case['expected'].items():
                actual = CE.run_world(case_id, hypothesis_id)['outcomes']
                self.assertEqual(actual, list(expected), f'{case_id}/{hypothesis_id}')

    def test_each_probe_plan_splits_the_listed_explanations(self):
        for case_id, case in CE.CASES.items():
            signatures = {tuple(CE.run_world(case_id, hypothesis_id)['outcomes']) for hypothesis_id in case['worlds']}
            self.assertEqual(len(signatures), len(case['worlds']), case_id)

    def test_public_prompt_contains_no_oracle_answers(self):
        forbidden = {'mechanisms', 'expected_outcomes', 'outcome_supports', 'remaining_unknown'}
        for fixture in self.fixtures.values():
            self.assertTrue(forbidden.isdisjoint(fixture['public']))
            self.assertEqual(fixture['public']['budget']['probe_actions'], len(fixture['public']['probe_plan']))
            self.assertEqual(fixture['public']['budget']['model_calls'], len(fixture['public']['probe_plan']))

    def test_uncertainty_is_retained_after_each_discriminating_outcome(self):
        for fixture in self.fixtures.values():
            world_count = len(fixture['public']['hypotheses'])
            self.assertTrue(fixture['evaluator_only']['remaining_unknown'])
            for supported in fixture['evaluator_only']['outcome_supports'].values():
                self.assertTrue(supported)
                self.assertLess(len(supported), world_count + 1)


if __name__ == '__main__':
    unittest.main()