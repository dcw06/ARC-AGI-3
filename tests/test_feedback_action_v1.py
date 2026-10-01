"""Feedback-action v1 (Track 1): fixtures, evidence view, adapter isolation, independent evaluator, rehearsals."""
import ast
import copy
import json
from pathlib import Path
import unittest

from research.feedback_action_v1 import (adapter as AD, environments as ENV, evaluate as EV, evidence as E,
                                         fixtures as F, rehearsal as R)
from research.transition_evidence_v1 import transition as T

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads(F.OUTPUT.read_bytes())
FIXTURES = {f['id']: f for f in FROZEN['fixtures']}
RESULTS = R.rehearse()


def fixture(name):
    fid = f'fa1-{name}'
    return FIXTURES[fid], FROZEN['evaluator_only'][fid]


def key_of(text):
    return tuple(int(v) for v in text.split(','))


def decision(fx, action, procedure=None, arm='candidate', previous_statement=None):
    return {'arm': arm, 'legal_actions': fx['legal_actions'], 'current_frame': fx['current_frame'],
            'response': {'content': R.content(arm, action, procedure), 'finish_reason': 'stop'},
            'previous_statement': previous_statement}


def sent(trajectory, n):
    """The user message actually sent at step n, parsed from the retained request bytes."""
    return json.loads(trajectory['steps'][n]['request_user_content'])


def imports(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names |= {node.module + '.' + a.name for a in node.names}
    return names


class Fixtures(unittest.TestCase):
    def test_frozen_fixtures_match_a_fresh_generation(self):
        self.assertEqual(F.encode(F.generate()), F.OUTPUT.read_bytes())

    def test_required_decision_boundaries_are_covered(self):
        self.assertEqual({f['id'][4:] for f in FROZEN['fixtures']}, set(F.SPECS))
        for name in ('exact_repeat_no_change_same_state', 'same_action_other_coordinate', 'tested_in_other_state',
                     'failed_dispatch', 'unknown_outcome', 'changed_then_reverted', 'necessary_repeat',
                     'contradicts_hypothesis'):
            self.assertIn(name, F.SPECS)

    def test_rules_synthetic_only_development_only_no_evaluator_data_in_evidence(self):
        for fx in FROZEN['fixtures']:
            self.assertEqual(F.check_rules(fx, FROZEN['evaluator_only'][fx['id']]), [])
            self.assertEqual(fx['source'], 'synthetic')
        text = json.dumps(FROZEN['fixtures'])
        for word in ('expected_status', 'mechanism', 'progress_keys', 'contradiction_ref', 'note'):
            self.assertNotIn(word, text)

    def test_a_real_game_fixture_may_not_assume_a_unique_correct_action(self):
        fx, ev = fixture('necessary_repeat')
        self.assertEqual(F.check_rules({**fx, 'source': 'real_game'}, ev),
                         ['a real-game fixture must not assume a uniquely correct next action'])
        self.assertEqual(F.check_rules({**fx, 'partition': 'h1'}, ev), ['development material only'])

    def test_raw_transitions_satisfy_the_shared_contract(self):
        for fx in FROZEN['fixtures']:
            for record in T.history(fx['raws']):
                self.assertEqual(T.validate(record), [], fx['id'])


class EvidenceStatusAgainstConstruction(unittest.TestCase):
    def test_every_probe(self):
        for fx in FROZEN['fixtures']:
            ev = FROZEN['evaluator_only'][fx['id']]
            shown = EV.shown_window(fx['raws'])
            for text, status in ev['expected_status'].items():
                self.assertEqual(EV.evidence_status(fx['raws'], shown, fx['current_frame'], key_of(text)), status,
                                 (fx['id'], text))
            if 'shown_refs' in ev:
                self.assertEqual(shown, [])

    def test_failed_and_unknown_are_not_ineffective(self):
        for name, status in (('failed_dispatch', EV.FAILED_ONLY), ('unknown_outcome', EV.OUTCOME_UNKNOWN_ONLY)):
            fx, _ = fixture(name)
            shown = EV.shown_window(fx['raws'])
            key = EV.action_key(fx['raws'][0]['dispatched'])
            self.assertEqual(EV.evidence_status(fx['raws'], shown, fx['current_frame'], key), status)
            self.assertNotEqual(status, EV.NO_CHANGE_SAME_STATE)
            self.assertEqual(EV.citation_category(R.cite('T0', 'no_observed_change'), fx['raws'], shown,
                                                  fx['current_frame']), 'failure_read_as_no_change')
            claim = 'dispatch_failed' if name == 'failed_dispatch' else 'outcome_unknown'
            self.assertEqual(EV.citation_category(R.cite('T0', claim), fx['raws'], shown, fx['current_frame']),
                             'supported')


class EvaluatorAtDecisionBoundaries(unittest.TestCase):
    def test_citations_only_earlier_and_shown(self):
        fx, _ = fixture('tested_in_other_state')
        shown = EV.shown_window(fx['raws'])
        here = fx['current_frame']
        cat = lambda ref, claim: EV.citation_category(R.cite(ref, claim), fx['raws'], shown, here)
        self.assertEqual(cat('T0', 'no_observed_change'), 'supported')
        self.assertEqual(cat('T0', 'different_state_from_now'), 'supported')
        self.assertEqual(cat('T0', 'same_state_as_now'), 'wrong_claim')
        self.assertEqual(cat('T1', 'final_frame_differs'), 'supported')
        self.assertEqual(cat('T2', 'final_frame_differs'), 'not_earlier')
        self.assertEqual(cat('T-1', 'final_frame_differs'), 'malformed')
        self.assertEqual(EV.citation_category({'claim': 'final_frame_differs'}, fx['raws'], shown, here), 'malformed')
        for name in ('after_level_boundary', 'after_reset_boundary'):
            fx, _ = fixture(name)
            self.assertEqual(EV.citation_category(R.cite('T0', 'final_frame_differs'), fx['raws'], [],
                                                  fx['current_frame']), 'earlier_not_shown')

    def test_changed_then_reverted_is_not_no_change(self):
        fx, _ = fixture('changed_then_reverted')
        shown = EV.shown_window(fx['raws'])
        self.assertEqual(EV.citation_category(R.cite('T0', 'no_observed_change'), fx['raws'], shown,
                                              fx['current_frame']), 'wrong_claim')
        self.assertEqual(EV.citation_category(R.cite('T0', 'changed_then_returned'), fx['raws'], shown,
                                              fx['current_frame']), 'supported')

    def test_same_action_other_coordinate_is_not_a_repeat(self):
        fx, _ = fixture('same_action_other_coordinate')
        other = EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(6, 5, 5), R.block('h', 'new')))
        same = EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(6, 1, 1), R.block('h', 'new')))
        self.assertEqual(other['chosen_status'], EV.UNTESTED)
        self.assertEqual(same['chosen_status'], EV.NO_CHANGE_SAME_STATE)
        self.assertFalse(same['repeat_cites_its_no_change'])

    def test_contradiction_is_scored_mechanically(self):
        fx, ev = fixture('contradicts_hypothesis')
        prediction = {k: v for k, v in ev['prior_prediction'].items() if k != 'about'}
        self.assertEqual(EV.score_prediction(prediction, fx['raws'][0])['result'], 'incorrect')
        prior = {'ref': ev['contradiction_ref'], 'prediction': prediction}
        statement = AD.carried_statement({'procedure': R.block('ACTION1 moves the marker up', 'new')},
                                         ['none_reported'], 'T0')
        self.assertEqual(statement['prediction'], prediction)
        revised = R.block('ACTION1 is blocked', 'revised', conflicting=[R.cite('T0', 'no_observed_change')])
        cases = {'recognized': revised, 'revised_not_cited': R.block('x', 'revised'),
                 'cited_not_revised': {**revised, 'status': 'retained'}, 'not_recognized': R.block('x', 'retained')}
        for expected, block in cases.items():
            result = EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(2), block, previous_statement=statement),
                                          prior)
            self.assertEqual(result['revision'], expected)
        # Without the statement in the request (or with one about something else), revision is never recognized.
        for carried in (None, {**statement, 'about': 'T5'},
                        {**statement, 'prediction': {**prediction, 'visual_effect': 'no_observed_change'}}):
            result = EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(2), revised, previous_statement=carried),
                                          prior)
            self.assertEqual(result['revision'], 'previous_statement_absent')

    def test_necessary_repeat_is_counted_not_judged(self):
        fx, ev = fixture('necessary_repeat')
        self.assertEqual(ev['progress_keys'], [[5]])
        cited = R.block('presses accumulate', 'retained', supporting=[R.cite('T1', 'no_observed_change')],
                        level=True)
        result = EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(5), cited))
        self.assertEqual(result['chosen_status'], EV.NO_CHANGE_SAME_STATE)
        self.assertTrue(result['repeat_cites_its_no_change'])
        env = ENV.DelayedSwitch()
        for _ in range(3):
            raw = env.dispatch(ENV.action(5))
        self.assertEqual(EV.score_prediction(cited['prediction'], raw)['result'], 'correct')

    def test_free_text_is_never_scored(self):
        fx, _ = fixture('tested_in_other_state')
        a = R.block('ACTION3 moves left', 'new', supporting=[R.cite('T1', 'final_frame_differs')])
        b = {**a, 'hypothesis': 'nonsense words', 'if_different': 'more nonsense'}
        self.assertEqual(EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(3), a)),
                         EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(3), b)))

    def test_legality_and_observability(self):
        fx, _ = fixture('exact_repeat_no_change_same_state')
        bad = EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(6, 1, 1), R.block('h', 'new')))
        self.assertEqual(bad['action_problem'], 'illegal_action')
        for prediction, problem in (({'visual_effect': 'moves', 'level_completed': False, 'changed_region_xyxy': None},
                                     'unobservable_prediction'),
                                    ({'visual_effect': 'no_observed_change', 'level_completed': False,
                                      'changed_region_xyxy': [0, 0, 1, 1]}, 'region_with_no_change'),
                                    ({'visual_effect': 'final_frame_differs', 'level_completed': False,
                                      'changed_region_xyxy': [3, 3, 1, 1]}, 'unobservable_prediction')):
            block = {**R.block('h', 'new'), 'prediction': prediction}
            result = EV.evaluate_decision(fx['raws'], decision(fx, ENV.action(2), block))
            self.assertEqual(result['procedure_problem'], problem)
            self.assertIsNone(result['action_problem'])

    def test_region_prediction(self):
        env = ENV.PushToGoal()
        raw = env.dispatch(ENV.action(2))  # marker (1,1) -> (1,2)
        inside = {'visual_effect': 'final_frame_differs', 'level_completed': False, 'changed_region_xyxy': [1, 1, 1, 2]}
        outside = {**inside, 'changed_region_xyxy': [1, 1, 1, 1]}
        self.assertEqual(EV.score_prediction(inside, raw)['result'], 'correct')
        self.assertEqual(EV.score_prediction(outside, raw)['result'], 'incorrect')


class EvidenceViewAndAdapterIsolation(unittest.TestCase):
    def steps(self):
        for (name, arm), (trajectory, evaluation) in RESULTS.items():
            for step, row in zip(trajectory['steps'], evaluation['decisions']):
                yield name, arm, trajectory, step, row

    def test_evaluator_window_equals_the_view_shown(self):
        for name, arm, trajectory, step, row in self.steps():
            view = E.view(trajectory['raws'][:step['raws_before']], step['current_frame'])
            self.assertEqual([e['ref'] for e in view['entries']], row['shown_refs'], name)

    def test_undefined_is_never_zero_in_the_view(self):
        trajectory, _ = RESULTS[('unknown_dispatch_outcome', 'candidate')]
        entries = E.view(trajectory['raws'][:4], trajectory['steps'][4]['current_frame'])['entries']
        for entry in entries:
            if entry['dispatch'] != 'acknowledged':
                self.assertEqual(entry['visual_effect'], 'indeterminate')
                self.assertEqual(entry['final_frame_changed_cells'], 'unavailable')
                self.assertEqual(entry['to_state'], 'not_observed')
        self.assertEqual([e['continuity'] for e in entries][2], 'gap_after_unknown_outcome')

    def test_candidate_minus_treatment_is_the_baseline_request(self):
        """From the request bytes actually sent: removing the procedure, the response block, the larger cap and the
        carried statement gives exactly the baseline request for the same observation and evidence."""
        n = 0
        for name, arm, trajectory, step, row in self.steps():
            user = json.loads(step['request_user_content'])
            obs = {k: v for k, v in user['observation'].items() if k != E.FIELD}
            view = user['observation'][E.FIELD]
            self.assertEqual(view, E.view(trajectory['raws'][:step['raws_before']], step['current_frame']))
            carried = user.get(AD.PREVIOUS_FIELD) if arm == 'candidate' else AD.carried_statement(None)
            original = copy.deepcopy(obs)
            candidate, baseline = AD.build_request(obs, view, 'candidate', carried), AD.build_request(obs, view, 'baseline')
            self.assertEqual(obs, original)
            if arm == 'candidate':
                self.assertEqual(candidate['messages'][1]['content'], step['request_user_content'])
            else:
                self.assertEqual(baseline['messages'][1]['content'], step['request_user_content'])
            self.assertEqual(AD.strip_procedure(candidate), baseline)
            self.assertEqual(json.loads(candidate['messages'][1]['content'])['observation'],
                             json.loads(baseline['messages'][1]['content'])['observation'])
            self.assertEqual(candidate['response_format']['json_schema']['schema']['properties']['action'],
                             baseline['response_format']['json_schema']['schema']['properties']['action'])
            self.assertNotIn('hypothesis', json.dumps(baseline))
            self.assertNotIn(AD.PREVIOUS_FIELD, json.dumps(baseline))
            n += 1
        self.assertGreater(n, 40)

    def test_carried_state_must_be_explicit(self):
        fx, _ = fixture('exact_repeat_no_change_same_state')
        obs = R.observation({'frames': [fx['current_frame']], 'levels_completed': 0, 'state': 'NOT_FINISHED'},
                            fx['legal_actions'])
        view = E.view(fx['raws'], fx['current_frame'])
        with self.assertRaises(ValueError):
            AD.build_request(obs, view, 'candidate')
        with self.assertRaises(ValueError):
            AD.build_request(obs, view, 'baseline', AD.carried_statement(None))

    def test_treatment_size_is_reported_not_matched(self):
        trajectory, _ = RESULTS[('delayed_effect', 'candidate')]
        self.assertTrue(all(s['treatment_chars'] > 0 for s in trajectory['steps']))
        trajectory, _ = RESULTS[('delayed_effect', 'baseline')]
        self.assertTrue(all(s['treatment_chars'] == 0 for s in trajectory['steps']))
        self.assertGreater(AD.CANDIDATE_MAX_TOKENS, AD.BASELINE_MAX_TOKENS)

    def test_adapter_and_evaluator_agree_on_action_validity(self):
        for name, arm, trajectory, step, row in self.steps():
            self.assertEqual(step['adapter_decision']['action'] is None, row['action_problem'] is not None, name)
            self.assertEqual(step['dispatched_index'] is not None, step['adapter_decision']['action'] is not None)
            if arm == 'candidate':
                self.assertEqual(step['adapter_decision']['procedure'] is None, row['procedure_problem'] is not None,
                                 name)

    def test_parse_never_raises(self):
        for content in (None, '', '[]', '{"action": null}', '{"hypothesis_test": 1, "action": {}}', '"x"', '{'):
            for arm in AD.ARMS:
                result = AD.parse({'content': content, 'finish_reason': 'stop'}, [1, 2], arm)
                self.assertIsNone(result['action'])
                self.assertIsNotNone(result['action_error'])

    def test_import_boundaries(self):
        here = ROOT / 'research' / 'feedback_action_v1'
        evaluator = imports(here / 'evaluate.py')
        self.assertEqual({n for n in evaluator if n.startswith('research')},
                         {'research.transition_evidence_v1.reference'})
        self.assertTrue(evaluator <= {'hashlib', 'json', 'research.transition_evidence_v1.reference'})
        adapter = imports(here / 'adapter.py')
        for forbidden in ('environments', 'rehearsal', 'evaluate', 'fixtures', 'agent.', 'arc_agi'):
            self.assertFalse(any(forbidden in n for n in adapter), forbidden)


class CarriedStatement(unittest.TestCase):
    """Review finding P1: the candidate's previous statement must be in the request bytes, never assumed."""

    def test_next_request_contains_the_previous_block(self):
        trajectory, evaluation = RESULTS[('contradiction_revised', 'candidate')]
        first, second = sent(trajectory, 0), sent(trajectory, 1)
        self.assertEqual(first[AD.PREVIOUS_FIELD], {'record': 'model_statement', 'available': False,
                                                     'reason': 'no earlier decision in this episode'})
        carried = second[AD.PREVIOUS_FIELD]
        made = trajectory['steps'][0]['adapter_decision']['procedure']
        self.assertTrue(carried['available'])
        self.assertEqual((carried['record'], carried['statement_status'], carried['about']),
                         ('model_statement', 'hypothesis', 'T0'))
        self.assertEqual({k: carried[k] for k in ('hypothesis', 'status', 'prediction', 'if_different')},
                         {k: made[k] for k in ('hypothesis', 'status', 'prediction', 'if_different')})
        self.assertNotIn('supporting', carried)
        self.assertNotIn(AD.PREVIOUS_FIELD, second['observation'])  # beside the observation, never inside it
        self.assertNotIn('hypothesis', json.dumps(second['observation']))
        self.assertEqual(evaluation['decisions'][1]['revision'], 'recognized')
        self.assertTrue(evaluation['decisions'][1]['previous_statement_in_request'])

    def test_stateless_request_can_no_longer_score_recognized(self):
        """The reviewer's capture: the same scripted outputs, with the statement removed from the request bytes."""
        trajectory, _ = RESULTS[('contradiction_revised', 'candidate')]
        stateless = copy.deepcopy(trajectory)
        for step in stateless['steps']:
            user = json.loads(step['request_user_content'])
            user.pop(AD.PREVIOUS_FIELD)
            step['request_user_content'] = json.dumps(user, sort_keys=True, separators=(',', ':'))
        evaluation = EV.evaluate_trajectory(stateless)
        self.assertFalse(evaluation['decisions'][1]['previous_statement_in_request'])
        self.assertEqual(evaluation['metrics']['revision_after_contradiction'], {'previous_statement_absent': 1})

    def test_invalid_or_missing_previous_block_is_not_carried(self):
        trajectory, _ = RESULTS[('invalid_structured_output', 'candidate')]
        reasons = [sent(trajectory, n)[AD.PREVIOUS_FIELD].get('reason') for n in range(5)]
        none_valid = 'the previous output had no valid hypothesis_test; no older statement is carried'
        self.assertEqual(reasons[0], 'no earlier decision in this episode')
        self.assertEqual(reasons[1], none_valid)  # step 0 was not JSON
        carried = sent(trajectory, 2)[AD.PREVIOUS_FIELD]  # step 1: illegal action, valid block
        self.assertTrue(carried['available'])
        self.assertIsNone(carried['about'])  # its action was never dispatched
        self.assertEqual(reasons[3], none_valid)  # step 2 truncated
        self.assertEqual(reasons[4], none_valid)  # step 3: valid action, invalid block; step 1's block is not reused

    def test_reset_and_level_change_clear_it(self):
        cleared = 'cleared: the previous transition ended the segment (reset, level change or terminal)'
        trajectory, _ = RESULTS[('reset_and_level_boundaries', 'candidate')]
        reasons = [sent(trajectory, n)[AD.PREVIOUS_FIELD].get('reason') for n in range(6)]
        self.assertEqual((reasons[3], reasons[5]), (cleared, cleared))  # after the reset (T2) and the level (T4)
        self.assertTrue(all(sent(trajectory, n)[AD.PREVIOUS_FIELD]['available'] for n in (1, 2, 4)))
        trajectory, _ = RESULTS[('delayed_effect', 'candidate')]
        self.assertEqual(sent(trajectory, 3)[AD.PREVIOUS_FIELD].get('reason'), cleared)  # after the first level

    def test_statements_stay_out_of_transition_records(self):
        for (name, arm), (trajectory, _) in RESULTS.items():
            self.assertNotIn('hypothesis', json.dumps(trajectory['raws']), name)
            for record in T.history(trajectory['raws']):
                self.assertEqual(T.validate(record), [])
            expected = sum(s['adapter_decision']['procedure'] is not None for s in trajectory['steps'])
            self.assertEqual(len(trajectory['model_statements']), expected)
            for statement in trajectory['model_statements']:
                self.assertEqual((statement['record'], statement['status']), ('model_statement', 'hypothesis'))
            if arm == 'baseline':
                self.assertEqual(trajectory['model_statements'], [])
                self.assertTrue(all(AD.PREVIOUS_FIELD not in s['request_user_content'] for s in trajectory['steps']))

    def test_text_is_capped(self):
        long = R.block('h' * 1000, 'new', if_different='d' * 1000)
        carried = AD.carried_statement({'procedure': long}, ['none_reported'], 'T0')
        self.assertEqual((len(carried['hypothesis']), len(carried['if_different'])), (AD.TEXT_LIMIT, AD.TEXT_LIMIT))


class Rehearsals(unittest.TestCase):
    def metrics(self, name, arm='candidate'):
        return RESULTS[(name, arm)][1]['metrics']

    def test_deterministic(self):
        self.assertEqual(R.summary(RESULTS), R.summary())

    def test_invalid_outputs_are_retained_and_never_dispatched(self):
        for arm in AD.ARMS:
            m = self.metrics('invalid_structured_output', arm)
            self.assertEqual(m['invalid_actions'], {'illegal_action': 1, 'not_json': 1, 'truncated': 1})
            self.assertEqual((m['decisions'], m['dispatched']), (5, 2))
        m = self.metrics('invalid_structured_output')
        self.assertEqual(m['invalid_procedures'], {'not_json': 1, 'truncated': 1, 'unobservable_prediction': 1})

    def test_missing_and_invented_references(self):
        m = self.metrics('missing_and_invented_references')
        self.assertEqual(m['citations'], {'not_earlier': 2, 'supported': 1, 'wrong_claim': 1})
        self.assertEqual(m['invalid_procedures'], {'missing_reference': 1})
        self.assertEqual(m['dispatched'], 4)

    def test_delayed_effect_repeats_are_not_waste(self):
        for arm in AD.ARMS:
            m = self.metrics('delayed_effect', arm)
            self.assertEqual(m['exact_repeats_after_no_change_same_state'], 4)
            self.assertEqual(m['of_which_followed_by_visible_change_or_level'], 2)
            self.assertEqual((m['levels_completed'], m['stop_reason']), (2, 'terminal_WIN'))

    def test_unknown_and_failed_dispatch(self):
        m = self.metrics('unknown_dispatch_outcome')
        self.assertEqual(m['dispatch_outcomes'], {'acknowledged': 3, 'failed': 1, 'outcome_unknown': 1})
        self.assertEqual(m['citations'], {'failure_read_as_no_change': 1, 'supported': 3})
        self.assertEqual(m['predictions']['unscoreable'], 2)
        self.assertEqual(m['chosen_status'][EV.FAILED_ONLY], 1)

    def test_reset_and_level_boundaries(self):
        m = self.metrics('reset_and_level_boundaries')
        self.assertEqual(m['citations'], {'earlier_not_shown': 2, 'supported': 3})
        self.assertEqual(m['levels_completed'], 1)
        # the prediction falsified by the level completion was cleared with the segment: not scoreable as revision
        self.assertEqual(m['revision_after_contradiction'], {'previous_statement_absent': 1})
        events = [r['outcome']['events'] for r in RESULTS[('reset_and_level_boundaries', 'candidate')][1]['decisions']]
        self.assertIn('reset_acknowledged', events[2])
        self.assertIn('level_completed', events[4])

    def test_budgets(self):
        self.assertEqual(self.metrics('action_budget_exhausted', 'baseline')['stop_reason'], 'action_budget')
        m = self.metrics('completion_budget_exhausted')
        self.assertEqual((m['stop_reason'], m['decisions'], m['completion_tokens']), ('completion_budget', 3, 900))
        for arm in AD.ARMS:
            m = self.metrics('decision_budget_exhausted_all_invalid', arm)
            self.assertEqual((m['stop_reason'], m['decisions'], m['dispatched']), ('decision_budget', 3, 0))

    def test_contradiction_revision(self):
        self.assertEqual(self.metrics('contradiction_revised')['revision_after_contradiction'], {'recognized': 1})
        m = self.metrics('contradiction_ignored')
        self.assertEqual(m['revision_after_contradiction'], {'not_recognized': 1})
        self.assertEqual(m['exact_repeats_after_no_change_same_state'], 1)

    def test_contradiction_at_reset_cannot_be_recognized(self):
        trajectory, evaluation = RESULTS[('contradiction_at_reset', 'candidate')]
        self.assertFalse(sent(trajectory, 1)[AD.PREVIOUS_FIELD]['available'])
        self.assertEqual(evaluation['metrics']['revision_after_contradiction'], {'previous_statement_absent': 1})
        self.assertEqual(trajectory['steps'][1]['adapter_decision']['procedure']['status'], 'revised')  # scripted

    def test_coordinate_actions(self):
        for arm in AD.ARMS:
            m = self.metrics('coordinate_actions', arm)
            self.assertEqual((m['wins'], m['exact_repeats_after_no_change_same_state']), (1, 1))
        self.assertEqual(self.metrics('coordinate_actions')['revision_after_contradiction'],
                         {'not_recognized': 1, 'revised_not_cited': 1})


if __name__ == '__main__':
    unittest.main()
