from copy import deepcopy
import unittest
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import request_for
from research.feedback_probe_v1.checkpoints import checked_checkpoint, select_checkpoints

MODEL = 'synthetic'


def fixture(legal_change_at=None):
    initial = {'grid': [[0]*64 for _ in range(64)], 'legal_actions': [1, 6], 'state': 'NOT_FINISHED', 'levels_completed': 0}
    case = {'case_id': 'test', 'game_id': 'synthetic', 'grid': initial['grid'], 'grid_sha256': digest(initial['grid']),
            'geometry': {'reviewed': []}}
    current, history, events = deepcopy(initial), [], [{'kind': 'initial', 'observation': initial}]
    for step in range(6):
        body = request_for(initial, [], current, history, step, MODEL)
        events.append({'kind': 'request', 'step': step, 'body': body, 'request_sha256': digest(body)})
        after = deepcopy(current)
        if step == 2:
            after['grid'][0][0] = 1
        if step == legal_change_at:
            after['legal_actions'] = [6]
        action_id = current['legal_actions'][0]
        entry = {'step': step, 'before': deepcopy(current), 'after': after,
                 'action': {'action_id': action_id, 'action_data': {'x': 7, 'y': 9} if action_id == 6 else {}},
                 'predicted_visible_change': 'unknown'}
        history.append(entry)
        events.append(dict(entry, kind='transition'))
        current = after
    return case, events


class Checkpoints(unittest.TestCase):
    def test_earliest_past_only_classes(self):
        case, events = fixture()
        values = select_checkpoints(case, events, model=MODEL)
        self.assertEqual([(v['decision_step'], v['stratum']) for v in values], [(2, 'unchanged'), (3, 'changed')])
        for value in values:
            checked_checkpoint(value, model=MODEL)

    def test_next_action_or_outcome_cannot_change_earlier_checkpoint(self):
        case, events = fixture()
        expected = select_checkpoints(case, events, model=MODEL)[0]
        # Stop at the exact decision: none of its response/action/outcome is available.
        stop = next(i for i, e in enumerate(events) if e['kind'] == 'request' and e['step'] == 2)
        self.assertEqual(select_checkpoints(case, events[:stop+1], model=MODEL)[0], expected)
        changed = deepcopy(events)
        changed[stop+1]['action'] = {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}
        # The first checkpoint is already fixed before that next-action event.
        self.assertEqual(select_checkpoints(case, changed[:stop+1], model=MODEL)[0], expected)

    def test_prefix_or_full_prompt_mutation_refused(self):
        case, events = fixture()
        value = select_checkpoints(case, events, model=MODEL)[0]
        for field in ('prefix', 'base_request'):
            altered = deepcopy(value)
            if field == 'prefix': altered['prefix'][1]['before']['legal_actions'] = [6]
            else: altered['base_request']['messages'][0]['content'] = 'different'
            with self.assertRaises(ValueError): checked_checkpoint(altered, model=MODEL)

    def test_same_pixels_with_changed_legal_controls_is_not_full_unchanged(self):
        case, events = fixture(legal_change_at=1)
        values = select_checkpoints(case, events, model=MODEL)
        self.assertEqual([(v['decision_step'], v['stratum']) for v in values], [(3, 'changed'), (4, 'unchanged')])


if __name__ == '__main__': unittest.main()
