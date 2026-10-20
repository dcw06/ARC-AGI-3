"""Meaningful faults and contracts; local fakes only, no model/game/provider."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.action_effect_choice_v1.interface import candidates, checked_pair, make_request, parse_choice, VARIANTS
from research.action_effect_choice_v1.flow import run_case, reference_branch
from research.action_effect_choice_v1.preparation import build, verify, protocol
from research.action_effect_choice_v1.scoring import branch_key, score, effect_size
from tests.test_feedback_probe_continuation_v1 import selected as original_selected, FakeEngine, Clock
from tests.test_feedback_probe_interface_v1 import request, observation
from research.initial_geometry_assistance_v1.policy import request_for

def selected():
    cp=original_selected()
    observations=[cp['initial'],cp['current']]+[value for entry in cp['prefix']for value in (entry['before'],entry['after'])]
    for value in observations:value['legal_actions']=[1,2,6]
    cp['base_request']=request_for(cp['initial'],cp['initial_case']['geometry']['reviewed'],cp['current'],
                                   cp['prefix'],len(cp['prefix']),protocol()['model'])
    return cp

def answer(first=True, choice='A', prediction='unknown'):
    return json.dumps({'candidate_predictions': {'A': prediction, 'B': prediction}, 'selected_candidate': choice,
        'observed_previous_change': 'not_applicable' if first else 'unknown',
        'previous_prediction_check': 'not_applicable' if first else 'unknown'})

class Interface(unittest.TestCase):
    def test_missing_evidence_derived_alternative_is_a_refusal_not_invented_click(self):
        with self.assertRaisesRegex(ValueError,'no distinct'):candidates(original_selected(),0)

    def test_two_distinct_legal_actions_and_crossed_label_and_arm_order(self):
        cp = selected(); repeat = cp['prefix'][-1]['action']
        for ordinal in range(8):
            pair = candidates(cp, ordinal)
            checked_pair(pair, cp['current']['legal_actions'])
            self.assertEqual(pair['B' if (ordinal//2)%2 else 'A'], repeat)

    def test_fixed_click_coordinates_are_part_of_action_identity(self):
        pair = {'A': {'action_id': 6, 'action_data': {'x': 1, 'y': 2}},
                'B': {'action_id': 6, 'action_data': {'x': 2, 'y': 2}}}
        checked_pair(pair, [6])
        pair['B'] = deepcopy(pair['A'])
        with self.assertRaises(ValueError): checked_pair(pair, [6])

    def test_illegal_boolean_and_invented_candidate_fields_refused(self):
        cp = selected(); original = candidates(cp, 0)
        for mutate in (lambda p:p['A'].update(action_id=True), lambda p:p['A'].update(answer_key='yes'),
                       lambda p:p['A'].update(action_id=99)):
            pair = deepcopy(original); mutate(pair)
            with self.assertRaises(ValueError): checked_pair(pair, cp['current']['legal_actions'])

    def test_arms_share_all_evidence_schema_and_candidates_only_instruction_differs(self):
        cp = selected(); pair = candidates(cp, 0)
        bodies = [make_request(cp['base_request'], pair, variant) for variant in VARIANTS]
        self.assertEqual(bodies[0]['messages'][0], bodies[1]['messages'][0])
        texts = [json.loads(body['messages'][1]['content'][-1]['text']) for body in bodies]
        self.assertNotEqual(texts[0].pop('decision_instruction'), texts[1].pop('decision_instruction'))
        self.assertEqual(texts[0], texts[1])
        bodies[0]['messages'][1]['content'].pop(); bodies[1]['messages'][1]['content'].pop()
        self.assertEqual(bodies[0], bodies[1])

    def test_preceding_forecast_must_match_actual_displayed_full_action(self):
        cp = selected(); pair = candidates(cp, 0)
        previous = parse_choice(answer(choice='B'), first=True)
        with self.assertRaisesRegex(ValueError, 'actual displayed'): make_request(cp['base_request'], pair, VARIANTS[0], previous)

    def test_first_and_second_output_phases_are_not_interchangeable(self):
        parse_choice(answer(), first=True); parse_choice(answer(False), first=False)
        for first,text in ((False,answer()), (True,answer(False))):
            with self.assertRaises(ValueError): parse_choice(text, first=first)

    def test_legacy_binary_forecasts_do_not_silently_enter_extent_scoring(self):
        for value in ('yes','no'):
            with self.assertRaises(ValueError):parse_choice(answer(prediction=value),first=True)

    def test_output_rejects_repairs_extra_keys_duplicate_nested_fields_and_booleans(self):
        for text in ('```json\n'+answer()+'\n```', answer().replace('"A": "unknown"','"A": true'),
                     answer().replace('"A": "unknown"','"A": "yes", "A": "no"'),
                     answer()[:-1]+',"action_id":1}', answer().replace('"selected_candidate": "A"','"selected_candidate": ["A","B"]')):
            with self.subTest(text=text), self.assertRaises(ValueError): parse_choice(text, first=True)

class Scoring(unittest.TestCase):
    def test_unknowns_and_invalids_remain_on_both_forecast_denominators(self):
        for text in (answer(), '{}'):
            scored = score(text, {'A':'5_to_64','B':'none'}, first=True)
            self.assertFalse(scored['both_forecasts_correct'])
            self.assertEqual(sum(row['correct'] for row in scored['forecasts'].values()), 0)
            self.assertEqual(len(scored['forecasts']), 2)

    def test_full_counterfactual_state_and_action_are_required(self):
        cp = selected(); pair = candidates(cp, 0); before = cp['current']
        branches = {k: {'before':deepcopy(before),'action':deepcopy(pair[k]),'after':deepcopy(before)} for k in pair}
        self.assertEqual(branch_key(before,pair,branches), {'A':'none','B':'none'})
        for mutate in (lambda b:b['B']['before']['grid'][0].__setitem__(0,9),
                       lambda b:b['B'].update(action=pair['A'])):
            changed=deepcopy(branches); mutate(changed)
            with self.assertRaises(ValueError):branch_key(before,pair,changed)

    def test_original_wrong_prediction_cannot_be_corrected_retroactively(self):
        value=json.loads(answer(False));value.update(observed_previous_change='yes',previous_prediction_check='matched')
        result=score(json.dumps(value),{'A':'none','B':'5_to_64'},first=False,previous_forecast='none',previous_observed='yes',previous_effect='5_to_64')
        self.assertTrue(result['previous_observation_correct']);self.assertFalse(result['previous_check_correct'])
        value['previous_prediction_check']='mismatched'
        self.assertTrue(score(json.dumps(value),{'A':'none','B':'5_to_64'},first=False,previous_forecast='none',previous_observed='yes',previous_effect='5_to_64')['previous_check_correct'])

    def test_unknown_previous_forecast_is_not_a_correct_prediction(self):
        result=score(answer(False),{'A':'1_to_4','B':'none'},first=False,previous_forecast='unknown',previous_observed='yes',previous_effect='1_to_4')
        self.assertTrue(result['previous_check_correct']);self.assertFalse(result['previous_forecast_was_known'])
        self.assertFalse(result['previous_observation_correct'])

    def test_effect_bucket_edges_and_binary_collapse_are_not_interchangeable(self):
        before=observation()
        for count,expected in ((0,'none'),(1,'1_to_4'),(4,'1_to_4'),(5,'5_to_64'),(64,'5_to_64'),(65,'65_plus')):
            after=deepcopy(before)
            for i in range(count):after['grid'][i//64][i%64]=1
            self.assertEqual(effect_size(before,after),expected)
        value=json.loads(answer(False));value.update(observed_previous_change='yes',previous_prediction_check='matched')
        result=score(json.dumps(value),{'A':'none','B':'5_to_64'},first=False,
            previous_forecast='1_to_4',previous_observed='yes',previous_effect='5_to_64')
        self.assertFalse(result['previous_check_correct'])
        with self.assertRaisesRegex(ValueError,'contradict'):
            score(answer(False),{'A':'none','B':'5_to_64'},first=False,
                  previous_forecast='none',previous_observed='no',previous_effect='1_to_4')

class Flow(unittest.TestCase):
    def run_case(self, complete=None, sink=None, clock=None, followup=None, variant=VARIANTS[0]):
        cp=selected();engine=FakeEngine(cp,followup=followup);events=[];calls=[]
        def respond(body):
            calls.append(deepcopy(body))
            return complete(len(calls)-1,body) if complete else answer(first=len(calls)==1)
        result=run_case(cp,candidates(cp,0),variant,engine,respond,sink or events.append,deadline=10,now=clock or (lambda:0))
        return cp,engine,events,calls,result

    def test_exact_two_requests_selected_actions_and_own_forecast_carryover(self):
        cp,engine,events,calls,result=self.run_case()
        self.assertEqual(result['new_dispatches'],2);self.assertEqual(result['model_calls'],2)
        self.assertEqual(engine.close_calls,1)
        self.assertEqual(engine.actions[:len(cp['prefix'])],[r['action']for r in cp['prefix']])
        context=json.loads(calls[1]['messages'][1]['content'][-1]['text'])
        self.assertEqual(context['previous_selected_forecast']['prediction'],'unknown')
        self.assertEqual([e['body']for e in events if e['kind']=='request'],calls)

    def test_invalid_output_stops_without_dispatch_repair_or_second_call(self):
        cp,engine,events,calls,result=self.run_case(complete=lambda *_:'{}')
        self.assertEqual(result['reason'],'invalid_answer');self.assertEqual(len(calls),1)
        self.assertEqual(len(engine.actions),len(cp['prefix']));self.assertEqual(engine.close_calls,1)

    def test_slow_journal_cannot_admit_request_after_deadline(self):
        clock=Clock();cp=selected();engine=FakeEngine(cp);events=[];calls=[]
        def sink(event):
            events.append(event)
            if event['kind']=='request':clock.value=11
        with self.assertRaises(TimeoutError):
            run_case(cp,candidates(cp,0),VARIANTS[0],engine,lambda b:calls.append(b),sink,deadline=10,now=clock)
        self.assertEqual(calls,[]);self.assertEqual(engine.close_calls,1)

    def test_slow_response_cannot_dispatch_after_deadline(self):
        cp=selected();engine=FakeEngine(cp);clock=Clock();events=[]
        def complete(_):clock.value=11;return answer()
        with self.assertRaises(TimeoutError):run_case(cp,candidates(cp,0),VARIANTS[0],engine,complete,events.append,deadline=10,now=clock)
        self.assertEqual(len(engine.actions),len(cp['prefix']));self.assertEqual(engine.close_calls,1)

    def test_terminal_or_changed_legal_set_retains_stop_and_skips_second_call(self):
        for update,reason in (({'levels_completed':1},'first_level_complete'),({'legal_actions':[]},'candidate_set_invalid')):
            def followup(_,action,obs):obs.update(update)
            _,engine,events,calls,result=self.run_case(followup=followup)
            self.assertEqual(result['reason'],reason);self.assertEqual(len(calls),1);self.assertEqual(engine.close_calls,1)

    def test_reference_is_evaluation_only_and_closes_on_restore_failure(self):
        cp=selected();engine=FakeEngine(cp,initial_mutation=lambda o:o['grid'][0].__setitem__(0,9))
        with self.assertRaises(ValueError):reference_branch(cp,candidates(cp,0),'A',engine,lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(engine.close_calls,1)

class Preparation(unittest.TestCase):
    def test_roundtrip_and_rehashed_candidate_mutation_or_reference_leak_refused(self):
        cp=selected();cases=[]
        for i in range(8):
            value=deepcopy(cp);identity='board-'+str(i+1).zfill(2)
            value['case_id']=value['initial_case']['case_id']=identity
            value['checkpoint_id']=identity+'-step'+str(value['decision_step']).zfill(2);cases.append(value)
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);write_new(root/'original.json',{'checkpoints':cases})
            frozen=protocol();frozen['source_checkpoint_file_sha256']=sha(root/'original.json')
            with patch('research.action_effect_choice_v1.preparation.protocol',return_value=frozen):
                build(root/'original.json',root/'prepared');pin=sha(root/'prepared/input-manifest.json')
                verify(root/'prepared',pin)
                write_new(root/'prepared/answers.json',{'future_effect':'yes'})
                with self.assertRaisesRegex(ValueError,'extra'):verify(root/'prepared',pin)
                (root/'prepared/answers.json').unlink()
                values=json.loads((root/'prepared/candidate-pairs.json').read_bytes());values[0]['candidates']['A']=values[0]['candidates']['B']
                (root/'prepared/candidate-pairs.json').write_text(json.dumps(values))
                manifest=json.loads((root/'prepared/input-manifest.json').read_bytes())
                manifest['files_sha256']['candidate-pairs.json']=sha(root/'prepared/candidate-pairs.json')
                (root/'prepared/input-manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):verify(root/'prepared',sha(root/'prepared/input-manifest.json'))

if __name__=='__main__':unittest.main()
