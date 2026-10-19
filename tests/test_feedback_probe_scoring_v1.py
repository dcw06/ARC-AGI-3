"""CPU checks for strict, full-denominator recognition scoring."""
from copy import deepcopy
import json
import unittest

from research.feedback_probe_v1.scoring import FIELDS, score_recognition


def key():
    return {
        'historical_step': 3,
        'historical_action': {'action_id': 6, 'action_data': {'x': 7, 'y': 9}},
        'visible_change': 'no',
        'current_matches_before': 'yes',
        'legal_actions': [1, 2, 6],
    }


def encoded(value):
    return json.dumps(value, separators=(',', ':'))


class RecognitionScoringChecks(unittest.TestCase):
    def test_all_correct_response_preserves_raw_text_and_scores_every_field(self):
        expected = key()
        text = encoded(expected)
        result = score_recognition(text, expected)
        self.assertTrue(result['valid'])
        self.assertTrue(result['all_fields_correct'])
        self.assertEqual(result['raw_text'], text)
        self.assertEqual(result['prediction'], expected)
        self.assertIsNone(result['invalid_reason'])
        self.assertEqual(set(result['fields']), set(FIELDS))
        self.assertTrue(all(row == {'correct': True, 'covered': True, 'abstained': False}
                            for row in result['fields'].values()))

    def test_legal_action_order_does_not_change_correctness(self):
        response = key()
        response['legal_actions'] = [6, 1, 2]
        self.assertTrue(score_recognition(encoded(response), key())['all_fields_correct'])

    def test_coordinates_are_part_of_full_action_identity(self):
        response = key()
        response['historical_action']['action_data']['x'] += 1
        result = score_recognition(encoded(response), key())
        self.assertTrue(result['valid'])
        self.assertEqual(result['fields']['historical_action'],
                         {'correct': False, 'covered': True, 'abstained': False})
        self.assertFalse(result['all_fields_correct'])

    def test_null_and_unknown_are_abstentions_in_full_denominator(self):
        response = key()
        response.update(historical_action=None, visible_change='unknown',
                        current_matches_before='unknown', legal_actions=None)
        result = score_recognition(encoded(response), key())
        self.assertTrue(result['valid'])
        self.assertFalse(result['all_fields_correct'])
        self.assertTrue(result['fields']['historical_step']['correct'])
        for name in FIELDS[1:]:
            self.assertEqual(result['fields'][name],
                             {'correct': False, 'covered': False, 'abstained': True})
        self.assertEqual(sum(row['correct'] for row in result['fields'].values()), 1)
        self.assertEqual(len(result['fields']), 5)

    def test_incorrect_assertion_is_covered_without_abstention(self):
        response = key()
        response['visible_change'] = 'yes'
        result = score_recognition(encoded(response), key())
        self.assertEqual(result['fields']['visible_change'],
                         {'correct': False, 'covered': True, 'abstained': False})

    def test_duplicate_json_keys_are_invalid_instead_of_last_value_winning(self):
        text = encoded(key()).replace('"historical_step":3',
                                    '"historical_step":2,"historical_step":3')
        result = score_recognition(text, key())
        self.assertFalse(result['valid'])
        self.assertFalse(result['all_fields_correct'])
        self.assertEqual(result['raw_text'], text)
        self.assertIsNone(result['prediction'])
        self.assertTrue(result['invalid_reason'])

    def test_booleans_cannot_masquerade_as_steps_actions_coordinates_or_controls(self):
        responses = []
        for field in ('historical_step', 'legal_actions', 'action_id', 'x'):
            response = key()
            if field == 'legal_actions':
                response[field] = [True, 2, 6]
            elif field == 'action_id':
                response['historical_action'] = {'action_id': True, 'action_data': {}}
            elif field == 'x':
                response['historical_action']['action_data']['x'] = True
            else:
                response[field] = True
            responses.append((field, response))
        for field, response in responses:
            with self.subTest(field=field):
                self.assertFalse(score_recognition(encoded(response), key())['valid'])

    def test_repeated_legal_actions_are_invalid_not_normalized_away(self):
        response = key()
        response['legal_actions'] = [1, 2, 6, 6]
        self.assertFalse(score_recognition(encoded(response), key())['valid'])

    def test_invalid_response_does_not_abort_following_batch_items(self):
        texts = ['not JSON', encoded(key()), '{"historical_step":']
        results = [score_recognition(text, key()) for text in texts]
        self.assertEqual([row['valid'] for row in results], [False, True, False])
        for result in (results[0], results[2]):
            self.assertTrue(all(field == {'correct': False, 'covered': False, 'abstained': False}
                                for field in result['fields'].values()))

    def test_non_text_non_object_and_excessively_nested_responses_are_invalid(self):
        for text in (None, True, 3, '[]', 'null', '[' * 2000 + '0' + ']' * 2000):
            with self.subTest(text_type=type(text).__name__):
                self.assertFalse(score_recognition(text, key())['valid'])

    def test_empty_legal_list_is_an_assertion_rather_than_abstention(self):
        expected = key()
        expected['legal_actions'] = []
        result = score_recognition(encoded(expected), expected)
        self.assertEqual(result['fields']['legal_actions'],
                         {'correct': True, 'covered': True, 'abstained': False})

    def test_malformed_or_abstaining_expected_key_refuses_before_scoring(self):
        malformed = [None, {}, {'extra': 1, **key()}]
        for name, value in (
            ('historical_step', True), ('historical_step', -1),
            ('historical_action', None), ('visible_change', 'unknown'),
            ('current_matches_before', None), ('legal_actions', None),
            ('legal_actions', [1, 1]), ('legal_actions', [True, 2]),
        ):
            candidate = key()
            candidate[name] = value
            malformed.append(candidate)
        for action in (
            {'action_id': 6, 'action_data': {}},
            {'action_id': 6, 'action_data': {'x': 64, 'y': 9}},
            {'action_id': 6, 'action_data': {'x': True, 'y': 9}},
            {'action_id': 2, 'action_data': {'x': 7, 'y': 9}},
            {'action_id': 8, 'action_data': {}},
        ):
            candidate = key()
            candidate['historical_action'] = action
            malformed.append(candidate)
        for candidate in malformed:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    score_recognition(encoded(key()), candidate)

    def test_inputs_are_not_modified_during_scoring(self):
        expected = key()
        original = deepcopy(expected)
        score_recognition(encoded(expected), expected)
        self.assertEqual(expected, original)

    def test_non_click_actions_have_empty_data(self):
        expected = key()
        expected['historical_action'] = {'action_id': 2, 'action_data': {}}
        self.assertTrue(score_recognition(encoded(expected), expected)['all_fields_correct'])


if __name__ == '__main__':
    unittest.main()
