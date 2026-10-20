"""Phase isolation, native-schema parity, and unchanged scientific data contracts."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

from research.action_effect_choice_v2.interface import make_request, response_schema, parse_choice, candidates, VARIANTS, EFFECTS
from research.action_effect_choice_v2.flow import run_case
from research.initial_geometry_assistance_v1.policy import request_for
from research.action_effect_choice_v1.interface import make_request as old_request
from tests.test_action_effect_choice_v1 import selected, answer, FakeEngine, Clock
from research.action_effect_choice_v2.preparation import build, verify, protocol
from research.initial_geometry_assistance_v1.live_io import sha, write_new


def request(cp, variant=VARIANTS[0], previous=None, decision=0, base=None):
    return make_request(base or cp['base_request'], candidates(cp, 0), variant, previous,
                        study_decision_index=decision, restored_prefix_length=len(cp['prefix']))


def second(cp, text=None):
    pair=candidates(cp,0);prior=json.loads(text or answer())
    record={'step':len(cp['prefix']),'before':deepcopy(cp['current']),'after':deepcopy(cp['current']),
            'action':deepcopy(pair[prior['selected_candidate']]),'predicted_visible_change':'unknown'}
    base=request_for(cp['initial'],cp['initial_case']['geometry']['reviewed'],cp['current'],
                     cp['prefix']+[record],len(cp['prefix'])+1,cp['base_request']['model'])
    return prior,base


class Interface(unittest.TestCase):
    def test_restored_history_is_not_first_study_action(self):
        cp=selected();body=request(cp)
        phase=json.loads(body['messages'][1]['content'][-1]['text'])['study_phase']
        self.assertEqual(phase['study_decision_index'],0)
        self.assertEqual(phase['game_action_count'],len(cp['prefix']))
        self.assertFalse(phase['previous_study_decision_exists'])
        self.assertEqual(phase['required_retrospective_fields'],{
            'observed_previous_change':'not_applicable','previous_prediction_check':'not_applicable'})
        self.assertEqual(body['response_format']['json_schema']['schema'],response_schema(0))

    def test_second_phase_is_bound_to_original_first_answer_and_actual_full_action(self):
        cp=selected();prior,base=second(cp)
        body=request(cp,previous=prior,decision=1,base=base)
        context=json.loads(body['messages'][1]['content'][-1]['text'])
        self.assertEqual(context['study_phase']['study_decision_index'],1)
        self.assertTrue(context['study_phase']['previous_study_decision_exists'])
        self.assertEqual(context['previous_selected_forecast']['study_decision_index'],0)
        wrong=deepcopy(prior);wrong['selected_candidate']='B'
        with self.assertRaisesRegex(ValueError,'actual displayed'):request(cp,previous=wrong,decision=1,base=base)

    def test_unknown_prior_does_not_force_the_correct_review_answer(self):
        cp=selected();prior,base=second(cp)
        schema=request(cp,previous=prior,decision=1,base=base)['response_format']['json_schema']['schema']
        self.assertEqual(schema['properties']['previous_prediction_check']['enum'],['matched','mismatched','unknown'])

    def test_phase_cannot_be_guessed_from_a_previous_answer_or_game_step(self):
        cp=selected();prior,base=second(cp)
        for index in (True,False,-1,2,0.0,'0',None):
            with self.subTest(index=index),self.assertRaises(ValueError):request(cp,decision=index)
        with self.assertRaises(ValueError):request(cp,previous=prior)
        with self.assertRaises(ValueError):request(cp,decision=1)
        with self.assertRaises(ValueError):request(cp,decision=1,previous=prior)
        with self.assertRaises(ValueError):request(cp,decision=0,base=base)
        wrong=json.loads(answer(False))
        with self.assertRaises(ValueError):request(cp,decision=1,previous=wrong,base=base)

    def test_images_candidates_summary_and_decoding_settings_remain_fixed(self):
        cp=selected();before=deepcopy(cp['base_request']);pair=candidates(cp,0)
        old=old_request(before,pair,VARIANTS[0]);new=request(cp)
        self.assertEqual(new['messages'][1]['content'][:-1],old['messages'][1]['content'][:-1])
        for key in set(old)-{'messages','response_format'}:self.assertEqual(old[key],new[key])
        self.assertEqual(cp['base_request'],before)
        self.assertEqual(json.loads(new['messages'][1]['content'][-1]['text'])['candidate_choice_v1'],pair)

    def test_arms_differ_only_in_instruction(self):
        cp=selected();bodies=[request(cp,variant)for variant in VARIANTS]
        contexts=[json.loads(b['messages'][1]['content'][-1]['text'])for b in bodies]
        self.assertNotEqual(contexts[0].pop('decision_instruction'),contexts[1].pop('decision_instruction'))
        self.assertEqual(contexts[0],contexts[1])
        for body in bodies:body['messages'][1]['content'].pop()
        self.assertEqual(bodies[0],bodies[1])

    def test_observed_old_failure_shapes_are_rejected_not_repaired(self):
        for value in ('yes','no','unknown'):
            reply=json.loads(answer());reply['observed_previous_change']=value
            with self.assertRaises(ValueError):parse_choice(json.dumps(reply),first=True)
        for value in (0,'0',False,None):
            reply=json.loads(answer());reply['candidate_predictions']['A']=value
            with self.assertRaises(ValueError):parse_choice(json.dumps(reply),first=True)


class Schema(unittest.TestCase):
    def test_all_500_legal_replies_match_unchanged_parser(self):
        from jsonschema import Draft202012Validator
        count=0
        for index in (0,1):
            schema=response_schema(index);Draft202012Validator.check_schema(schema)
            validator=Draft202012Validator(schema)
            for a,b,choice,observed,check in itertools.product(EFFECTS,EFFECTS,('A','B'),
                    ('not_applicable',)if index==0 else('yes','no','unknown'),
                    ('not_applicable',)if index==0 else('matched','mismatched','unknown')):
                value=dict(candidate_predictions={'A':a,'B':b},selected_candidate=choice,
                           observed_previous_change=observed,previous_prediction_check=check)
                validator.validate(value);parse_choice(json.dumps(value),first=index==0);count+=1
        self.assertEqual(count,500)

    def test_wrong_phase_zero_wrong_types_and_extra_fields_rejected(self):
        from jsonschema import Draft202012Validator
        for index in (0,1):
            original=json.loads(answer(first=index==0));mutations=[]
            for value in (0,'0',True,None,[],{},'yes'):
                changed=deepcopy(original);changed['candidate_predictions']['A']=value;mutations.append(changed)
            changed=deepcopy(original);changed['selected_candidate']='C';mutations.append(changed)
            changed=deepcopy(original);changed['observed_previous_change']='yes'if index==0 else'not_applicable';mutations.append(changed)
            changed=deepcopy(original);changed['previous_prediction_check']='matched'if index==0 else'not_applicable';mutations.append(changed)
            changed=deepcopy(original);changed['extra']=True;mutations.append(changed)
            changed=deepcopy(original);changed['candidate_predictions']['extra']='none';mutations.append(changed)
            changed=deepcopy(original);del changed['selected_candidate'];mutations.append(changed)
            validator=Draft202012Validator(response_schema(index))
            for value in mutations:
                self.assertFalse(validator.is_valid(value))
                with self.assertRaises(ValueError):parse_choice(json.dumps(value),first=index==0)

    def test_schema_results_are_independent_copies_and_do_not_relax_old_validation(self):
        schema=response_schema(0);schema['properties']['candidate_predictions']['properties']['A']['enum'].append('0')
        self.assertNotIn('0',response_schema(0)['properties']['candidate_predictions']['properties']['A']['enum'])
        for index in (0,1):
            value=json.loads(answer(first=index==0));raw=json.dumps(value)
            for text in (raw[:-1]+',"selected_candidate":"B"}',raw.replace('"A": "unknown"','"A": "none", "A": "unknown"')):
                with self.assertRaises(ValueError):parse_choice(text,first=index==0)


class Flow(unittest.TestCase):
    def test_two_steps_propagate_indices_and_keep_action_and_deadline_contracts(self):
        cp=selected();engine=FakeEngine(cp);bodies=[];events=[]
        def complete(body):
            bodies.append(body);return answer(first=len(bodies)==1)
        result=run_case(cp,candidates(cp,0),VARIANTS[0],engine,complete,events.append,deadline=10,now=lambda:0)
        self.assertEqual(result['new_dispatches'],2);self.assertEqual(engine.close_calls,1)
        self.assertEqual([json.loads(b['messages'][1]['content'][-1]['text'])['study_phase']['study_decision_index']for b in bodies],[0,1])
        self.assertEqual([b['response_format']['json_schema']['schema']for b in bodies],[response_schema(0),response_schema(1)])

    def test_invalid_answer_does_not_trigger_repair_retry_or_dispatch(self):
        cp=selected();engine=FakeEngine(cp);calls=[]
        def complete(body):calls.append(body);return answer(False)
        result=run_case(cp,candidates(cp,0),VARIANTS[0],engine,complete,lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'invalid_answer');self.assertEqual(len(calls),1)
        self.assertEqual(len(engine.actions),len(cp['prefix']));self.assertEqual(engine.close_calls,1)

    def test_no_late_dispatch_after_response(self):
        cp=selected();engine=FakeEngine(cp);clock=Clock()
        def complete(body):clock.value=11;return answer()
        with self.assertRaises(TimeoutError):run_case(cp,candidates(cp,0),VARIANTS[0],engine,complete,lambda _:None,deadline=10,now=clock)
        self.assertEqual(len(engine.actions),len(cp['prefix']));self.assertEqual(engine.close_calls,1)


class Preparation(unittest.TestCase):
    def test_sealed_inputs_reject_rehashed_wrong_phase_and_extra_reference(self):
        cases=[]
        for i in range(8):
            cp=selected();identity='board-'+str(i+1).zfill(2)
            cp['case_id']=cp['initial_case']['case_id']=identity
            cp['checkpoint_id']=identity+'-step'+str(cp['decision_step']).zfill(2);cases.append(cp)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);write_new(root/'original.json',{'checkpoints':cases})
            frozen=protocol();frozen['source_checkpoint_file_sha256']=sha(root/'original.json')
            with patch('research.action_effect_choice_v2.preparation.protocol',return_value=frozen):
                build(root/'original.json',root/'inputs');pin=sha(root/'inputs/input-manifest.json')
                manifest=verify(root/'inputs',pin)
                self.assertEqual(len(manifest['files_sha256']),18)
                write_new(root/'inputs/reference.json',{'future_effect':'none'})
                with self.assertRaisesRegex(ValueError,'extra'):verify(root/'inputs',pin)
                (root/'inputs/reference.json').unlink()
                name=next(n for n in manifest['files_sha256'] if n.startswith('model-inputs/'))
                body=json.loads((root/'inputs'/name).read_bytes())
                phase=json.loads(body['messages'][1]['content'][-1]['text'])
                phase['study_phase']['study_decision_index']=1
                body['messages'][1]['content'][-1]['text']=json.dumps(phase)
                (root/'inputs'/name).write_text(json.dumps(body))
                manifest['files_sha256'][name]=sha(root/'inputs'/name)
                (root/'inputs/input-manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):verify(root/'inputs',sha(root/'inputs/input-manifest.json'))


if __name__=='__main__':unittest.main()
