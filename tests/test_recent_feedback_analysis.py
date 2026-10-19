"""Frozen denominator and full-action comparisons; no engine, inference or GPU."""
from copy import deepcopy
import unittest
from research.recent_feedback_v1.analysis import episode_metrics


def fixture(actions, changes=None):
    changes = changes or [False]*len(actions)
    grid = [[0]]
    events = [{'kind': 'initial', 'observation': {'grid': deepcopy(grid)}}]
    for step, (action, change) in enumerate(zip(actions, changes)):
        before = deepcopy(grid)
        if change:
            grid[0][0] += 1
        events.extend([{'kind': 'request', 'step': step}, {'kind': 'transition', 'step': step,
            'before': {'grid': before}, 'after': {'grid': deepcopy(grid)},
            'action': {'action_id': 6, 'action_data': {'x': action, 'y': 1}},
            'predicted_visible_change': 'unknown'}])
    return events


class AnalysisChecks(unittest.TestCase):
    def test_two_duplicate_candidates_count_one_eligible_decision(self):
        result = episode_metrics(fixture([1, 1, 1]))
        self.assertEqual(result['repeat_after_unchanged']['all'], {'eligible': 2, 'repeated': 2, 'unexecuted': 0})
        self.assertEqual(result['repeat_after_unchanged']['same_grid'], result['repeat_after_unchanged']['all'])
        self.assertEqual(result['repeat_after_unchanged']['different_grid']['eligible'], 0)

    def test_click_coordinates_are_part_of_action_identity(self):
        result = episode_metrics(fixture([1, 2, 3]))
        self.assertEqual(result['repeat_after_unchanged']['all']['eligible'], 2)
        self.assertEqual(result['repeat_after_unchanged']['all']['repeated'], 0)
        self.assertEqual(result['distinct_full_actions'], 3)
        self.assertEqual(result['distinct_action_ids'], 1)

    def test_changed_current_context_is_reported_separately(self):
        result = episode_metrics(fixture([1, 2, 1], [False, True, False]))
        self.assertEqual(result['repeat_after_unchanged']['different_grid'], {'eligible': 1, 'repeated': 1, 'unexecuted': 0})
        self.assertEqual(result['consecutive_repeat']['repeated'], 0)

    def test_only_two_recent_transitions_are_eligible(self):
        result = episode_metrics(fixture([1, 2, 3, 1], [False, True, True, False]))
        self.assertEqual(result['repeat_after_unchanged']['all']['eligible'], 2)
        self.assertEqual(result['repeat_after_unchanged']['all']['repeated'], 0)

    def test_missing_action_not_credited_and_unknown_not_scored_as_wrong(self):
        events = fixture([1, 1])
        events.pop()
        result = episode_metrics(events)
        self.assertEqual(result['repeat_after_unchanged']['all'], {'eligible': 1, 'repeated': 0, 'unexecuted': 1})
        self.assertEqual(result['prediction'], {'asserted': 0, 'dispatched': 1, 'correct_assertions': 0})

    def test_duplicate_steps_refused(self):
        events = fixture([1])
        with self.assertRaises(ValueError):
            episode_metrics(events+[deepcopy(events[-1])])


if __name__ == '__main__':
    unittest.main()
