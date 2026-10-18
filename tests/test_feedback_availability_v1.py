"""Retrospective audit checks; no engine, model or private fixture needed."""
from copy import deepcopy
import unittest

from research.feedback_availability_v1 import changed_cells, decision_feedback, episode_feedback
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import request_for


def observation():
    return {'grid': [[0]*64 for _ in range(64)], 'state': 'NOT_FINISHED',
            'levels_completed': 0, 'legal_actions': [1, 2, 6]}


def action(x=7):
    return {'action_id': 6, 'action_data': {'x': x, 'y': 9}}


def transition(step, move=None, before=None, after=None):
    return {'kind': 'transition', 'step': step, 'action': move or action(),
            'before': deepcopy(before or observation()), 'after': deepcopy(after or observation()),
            'predicted_visible_change': 'unknown'}


class FeedbackAvailabilityTests(unittest.TestCase):
    def test_first_action_has_no_feedback_even_if_subsequent_outcome_is_unchanged(self):
        row = decision_feedback([], action(), observation())
        self.assertEqual(row['prior_same_action_unchanged_grid_steps'], [])
        self.assertFalse(row['consecutive_action_repeat'])

    def test_recent_unchanged_action_is_visible(self):
        row = decision_feedback([transition(0)], action(), observation())
        self.assertEqual(row['visible_same_action_unchanged_grid_steps'], [0])
        self.assertEqual(row['visible_same_action_same_observation_unchanged_grid_steps'], [0])

    def test_older_only_attempt_is_omitted(self):
        history = [transition(0), transition(1, action(8)), transition(2, action(9))]
        row = decision_feedback(history, action(), observation())
        self.assertEqual(row['prior_same_action_unchanged_grid_steps'], [0])
        self.assertEqual(row['visible_same_action_unchanged_grid_steps'], [])
        self.assertEqual(row['omitted_same_action_unchanged_grid_steps'], [0])

    def test_coordinates_distinguish_actions(self):
        self.assertEqual(decision_feedback([transition(0)], action(8), observation())['prior_same_action_steps'], [])

    def test_changed_ui_cell_is_preserved_without_progress_claim(self):
        after = observation()
        after['grid'][63][63] = 1
        row = decision_feedback([transition(0, after=after)], action(), after)
        self.assertEqual(row['prior_same_action_unchanged_grid_steps'], [])
        self.assertEqual(changed_cells(observation(), after), [[63, 63]])

    def test_equal_grids_with_changed_legal_state_are_not_equal_observations(self):
        after = observation()
        after['legal_actions'] = [6]
        row = decision_feedback([transition(0, after=after)], action(), after)
        self.assertEqual(row['visible_same_action_unchanged_grid_steps'], [0])
        self.assertEqual(row['prior_same_action_unchanged_full_observation_steps'], [])
        self.assertEqual(row['visible_same_action_same_observation_unchanged_grid_steps'], [])

    def trace(self, moves):
        case = {'case_id': 'synthetic', 'game_id': 'synthetic', 'geometry': {'reviewed': []}}
        initial = observation()
        events = [{'kind': 'initial', 'observation': initial}]
        history = []
        for i, move in enumerate(moves):
            body = request_for(initial, [], initial, history, i, 'fixture')
            events.append({'kind': 'request', 'step': i, 'body': body, 'request_sha256': digest(body)})
            event = transition(i, move)
            events.append(event)
            history.append(event)
        return case, events

    def test_future_transitions_cannot_supply_earlier_feedback(self):
        case, events = self.trace([action()]*4)
        result = episode_feedback(case, 'reviewed', events, model='fixture')
        self.assertEqual(result['decisions'][0]['prior_same_action_steps'], [])
        self.assertEqual(result['decisions'][1]['prior_same_action_steps'], [0])
        self.assertEqual(result['decisions'][3]['visible_transition_steps'], [1, 2])
        self.assertEqual(result['summary']['visible_prior_unchanged_grid_decisions'], 3)

    def test_rewritten_request_hash_cannot_hide_removed_history(self):
        case, events = self.trace([action()]*2)
        body = events[3]['body']
        body['messages'][1]['content'] = body['messages'][1]['content'][:3]
        events[3]['request_sha256'] = digest(body)
        with self.assertRaisesRegex(ValueError, 'displayed history'):
            episode_feedback(case, 'reviewed', events, model='fixture')

    def test_short_cycle_is_descriptive_and_constant_click_is_not_multi_action_cycle(self):
        case, events = self.trace([{'action_id': i, 'action_data': {}} for i in (1, 2, 1, 2)])
        result = episode_feedback(case, 'reviewed', events, model='fixture')
        self.assertEqual(result['summary']['whole_episode_action_cycle_period_2_to_4'], 2)
        case, events = self.trace([action()]*4)
        self.assertIsNone(episode_feedback(case, 'reviewed', events, model='fixture')['summary']['whole_episode_action_cycle_period_2_to_4'])


if __name__ == '__main__':
    unittest.main()
