"""No-inference regressions for independent feedback recognition and probes."""
from copy import deepcopy
import json
import unittest

from research.initial_geometry_assistance_v1.policy import request_for
from research.feedback_probe_v1.interface import (
    PROBE_INSTRUCTION, RECOGNITION_QUESTION, RECOGNITION_SYSTEM,
    parse_recognition, policy_request, recognition_key, recognition_request,
)


def observation():
    return {'grid': [[0]*64 for _ in range(64)], 'state': 'NOT_FINISHED',
            'levels_completed': 0, 'legal_actions': [1, 6]}


def transition(step=0, changed=False, action=None):
    before, after = observation(), observation()
    if changed:
        after['grid'][8][11] = 2
    return {'step': step, 'before': before, 'after': after,
            'action': action or {'action_id': 6, 'action_data': {'x': 11, 'y': 8}},
            'predicted_visible_change': 'unknown'}


def request(history=None, current=None):
    history = history if history is not None else [transition()]
    return request_for(observation(), [], current or observation(), history, len(history), 'fixture-model')


def answer():
    return {'historical_step': 0, 'historical_action': {
        'action_id': 6, 'action_data': {'x': 11, 'y': 8}},
        'visible_change': 'no', 'current_matches_before': 'yes', 'legal_actions': [1, 6]}


class FeedbackProbeInterfaceChecks(unittest.TestCase):
    def test_baseline_is_byte_equivalent_and_deeply_independent(self):
        base = request()
        copy = policy_request(base, 'baseline')
        self.assertEqual(json.dumps(copy), json.dumps(base))
        copy['messages'][1]['content'][0]['text'] = 'mutated'
        self.assertNotEqual(copy, base)

    def test_probe_adds_exactly_one_fixed_text_and_preserves_contract(self):
        base, before = request(), request()
        probe = policy_request(base, 'probe_instruction')
        self.assertEqual(probe['messages'][1]['content'].pop(),
                         {'type': 'text', 'text': PROBE_INSTRUCTION})
        self.assertEqual(probe, base)
        self.assertEqual(base, before)
        self.assertIn('repeat when there is a reason', PROBE_INSTRUCTION)
        self.assertIn('predict unknown', PROBE_INSTRUCTION)
        with self.assertRaises(ValueError):
            policy_request(base, 'unknown-condition')

    def test_probe_instruction_does_not_depend_on_action_or_outcome(self):
        different = request([transition(changed=True, action={'action_id': 2, 'action_data': {}})])
        self.assertEqual(policy_request(request(), 'probe_instruction')['messages'][1]['content'][-1],
                         policy_request(different, 'probe_instruction')['messages'][1]['content'][-1])

    def test_recognition_is_separate_and_preserves_displayed_evidence(self):
        base = request([transition(0), transition(1, changed=True)])
        before = deepcopy(base)
        factual = recognition_request(base)
        self.assertEqual(base, before)
        self.assertEqual(factual['messages'][0], {'role': 'system', 'content': RECOGNITION_SYSTEM})
        self.assertEqual(factual['messages'][1]['content'][:-1], base['messages'][1]['content'])
        self.assertEqual(factual['messages'][1]['content'][-1],
                         {'type': 'text', 'text': RECOGNITION_QUESTION})
        for key in ('model', 'temperature', 'seed', 'max_tokens', 'response_format', 'chat_template_kwargs'):
            self.assertEqual(factual[key], base[key])
        self.assertIn('only the most recent', RECOGNITION_QUESTION)
        self.assertNotIn('probe_instruction', json.dumps(factual))
        self.assertNotIn('stratum', json.dumps(factual))
        self.assertNotIn(json.dumps(recognition_key(base), sort_keys=True), json.dumps(factual))
        self.assertEqual(policy_request(base, 'baseline'), base)

    def test_no_history_is_not_given_an_invented_recognition_question(self):
        for function in (recognition_key, recognition_request):
            with self.subTest(function=function.__name__), self.assertRaises(ValueError):
                function(request([]))

    def test_recognition_refuses_prior_answers_or_non_user_evidence(self):
        for function in (recognition_key, recognition_request):
            base = request()
            base['messages'].append({'role': 'assistant', 'content': json.dumps(answer())})
            with self.subTest(function=function.__name__), self.assertRaises(ValueError):
                function(base)
            base = request()
            base['messages'][1]['role'] = 'assistant'
            with self.subTest(function=function.__name__), self.assertRaises(ValueError):
                function(base)

    def test_key_uses_last_displayed_transition_only_and_no_future_information(self):
        history = [transition(0, changed=True), transition(1), transition(2, changed=True)]
        current = deepcopy(history[-1]['after'])
        base = request(history, current)
        expected = {'historical_step': 2, 'historical_action': history[-1]['action'],
                    'visible_change': 'yes', 'current_matches_before': 'no', 'legal_actions': [1, 6]}
        self.assertEqual(recognition_key(base), expected)
        history[0]['after']['grid'][0][0] = 9
        history[1]['after']['grid'][0][0] = 7
        history[-1]['predicted_visible_change'] = 'yes'
        history[-1]['private_function_label'] = 'never copy this'
        changed = request(history, current)
        self.assertEqual(recognition_key(changed), expected)
        self.assertNotIn('never copy this', json.dumps(recognition_request(changed)))

    def test_key_compares_visible_cells_without_claiming_hidden_state(self):
        base = request([transition(changed=True)], current=observation())
        self.assertEqual(recognition_key(base)['visible_change'], 'yes')
        self.assertEqual(recognition_key(base)['current_matches_before'], 'yes')
        key = recognition_key(base)
        key['historical_action']['action_data']['x'] = 63
        key['legal_actions'].clear()
        self.assertEqual(recognition_key(base)['historical_action']['action_data']['x'], 11)
        self.assertEqual(recognition_key(base)['legal_actions'], [1, 6])

    def test_parser_accepts_exact_answer_unknown_null_and_empty_legal_list(self):
        self.assertEqual(parse_recognition(json.dumps(answer())), answer())
        unknown = answer()
        unknown.update(historical_action=None, legal_actions=None,
                       visible_change='unknown', current_matches_before='unknown')
        self.assertEqual(parse_recognition(json.dumps(unknown)), unknown)
        unknown['legal_actions'] = []
        self.assertEqual(parse_recognition(json.dumps(unknown)), unknown)
        for action_id in (1, 2, 3, 4, 5, 7):
            value = answer()
            value['historical_action'] = {'action_id': action_id, 'action_data': {}}
            self.assertEqual(parse_recognition(json.dumps(value)), value)

    def test_parser_rejects_bool_float_and_out_of_bounds_integer_fields(self):
        for field, bad in [('historical_step', True), ('historical_step', 1.0),
                           ('historical_step', -1), ('legal_actions', [True]),
                           ('legal_actions', [1.0]), ('legal_actions', [0]),
                           ('legal_actions', [8]), ('legal_actions', [1, 1])]:
            value = answer()
            value[field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                parse_recognition(json.dumps(value))
        for bad in (True, 6.0, 0, 8):
            value = answer()
            value['historical_action']['action_id'] = bad
            with self.subTest(action_id=bad), self.assertRaises(ValueError):
                parse_recognition(json.dumps(value))
        for bad in (True, 1.0, -1, 64):
            value = answer()
            value['historical_action']['action_data']['x'] = bad
            with self.subTest(x=bad), self.assertRaises(ValueError):
                parse_recognition(json.dumps(value))

    def test_parser_rejects_missing_extra_nested_and_wrong_judgment_fields(self):
        mutations = []
        value = answer(); del value['legal_actions']; mutations.append(value)
        value = answer(); value['recommendation'] = 1; mutations.append(value)
        value = answer(); value['historical_action']['note'] = 'extra'; mutations.append(value)
        value = answer(); value['historical_action']['action_data']['z'] = 0; mutations.append(value)
        value = answer(); value['historical_action']['action_id'] = 1; mutations.append(value)
        value = answer(); del value['historical_action']['action_data']['x']; mutations.append(value)
        value = answer(); value['visible_change'] = None; mutations.append(value)
        value = answer(); value['current_matches_before'] = True; mutations.append(value)
        value = answer(); value['legal_actions'] = 'unknown'; mutations.append(value)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_recognition(json.dumps(value))

    def test_parser_rejects_duplicate_keys_nonfinite_and_extraneous_text(self):
        text = json.dumps(answer())
        invalid = [text[:-1] + ',"historical_step":0}',
                   text.replace('"x": 11', '"x":11,"x":11'),
                   text.replace('"historical_step": 0', '"historical_step":NaN'),
                   text.replace('"historical_step": 0', '"historical_step":Infinity'),
                   text.replace('"historical_step": 0', '"historical_step":1e309'),
                   '```json\n' + text + '\n```', text + '\nexplanation', None]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_recognition(value)


if __name__ == '__main__':
    unittest.main()
