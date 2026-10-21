"""Executed-feedback provenance, withheld outcomes and admission regressions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.action_effect_choice_v2.interface import candidates, make_request as baseline
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.policy import request_for
from research.verified_feedback_v1.feedback import build_feedback, freeze_forecast, extent, display
from research.verified_feedback_v1.interface import CONDITIONS, make_request
from research.verified_feedback_v1.flow import run_case
from research.verified_feedback_v1.preparation import build, verify, protocol
from tests.test_action_effect_choice_v1 import selected, answer, FakeEngine, Clock


def fixture(count=2, forecast='1_to_4', choice='A'):
    cp = selected(); pair = candidates(cp, 0); before = deepcopy(cp['current']); after = deepcopy(before)
    for index in range(count):
        y, x = divmod(index, 64); after['grid'][y][x] = (before['grid'][y][x]+1) % 16
    prior = json.loads(answer(prediction=forecast, choice=choice))
    frozen = freeze_forecast(prior, pair, trajectory_id='fixture', study_decision_index=0,
        game_action_index=len(cp['prefix']), before=before)
    transition = dict(step=len(cp['prefix']), before=before, after=after, action=deepcopy(pair[choice]),
        predicted_visible_change='unknown' if forecast=='unknown' else 'no' if forecast=='none' else 'yes')
    return cp, pair, prior, frozen, transition


def receipt(frozen, transition, **overrides):
    args=dict(trajectory_id='fixture', study_decision_index=1,
              restored_prefix_length=transition['step'], current=transition['after'])
    args.update(overrides)
    return build_feedback(frozen, digest(frozen), transition, digest(transition), **args)


def second(condition, data=None, **overrides):
    cp, pair, prior, frozen, transition = data or fixture()
    base=request_for(cp['initial'], cp['initial_case']['geometry']['reviewed'], transition['after'],
        cp['prefix']+[transition], len(cp['prefix'])+1, cp['base_request']['model'])
    args=dict(study_decision_index=1, restored_prefix_length=len(cp['prefix']), trajectory_id='fixture',
              frozen=frozen, forecast_pin=digest(frozen), transition=transition,
              transition_pin=digest(transition), current=transition['after'])
    args.update(overrides)
    return make_request(base, pair, condition, prior, **args)


class Receipt(unittest.TestCase):
    def test_all_category_boundaries_and_no_change(self):
        for count, expected in ((0,'none'),(1,'1_to_4'),(4,'1_to_4'),(5,'5_to_64'),(64,'5_to_64'),(65,'65_plus'),(4096,'65_plus')):
            with self.subTest(count=count):
                *_, frozen, transition=fixture(count, expected)
                result=receipt(frozen, transition)
                self.assertEqual(result['observed_changed_cell_count'], count)
                self.assertEqual(result['observed_changed_cell_category'], expected)
                self.assertEqual(result['observed_visible_change'], 'yes' if count else 'no')
                self.assertEqual(result['original_forecast_check'], 'matched')

    def test_changed_count_rejects_booleans_wrong_types_and_out_of_range(self):
        for count in (True, False, -1, 4097, 1.0, '1', None):
            with self.subTest(count=count), self.assertRaises(ValueError): extent(count)

    def test_original_wrong_forecast_is_not_rewritten(self):
        *_, frozen, transition=fixture(2, '5_to_64'); before=deepcopy(frozen)
        result=receipt(frozen, transition)
        self.assertEqual(result['original_selected_forecast'], '5_to_64')
        self.assertEqual(result['original_forecast_check'], 'mismatched')
        self.assertEqual(frozen, before)

    def test_original_unknown_does_not_hide_an_observed_change(self):
        for count in (0, 1, 65):
            *_, frozen, transition=fixture(count, 'unknown'); result=receipt(frozen, transition)
            self.assertEqual(result['original_forecast_check'], 'unknown')
            self.assertFalse(result['forecast_comparison_available'])
            self.assertEqual(result['observed_visible_change'], 'yes' if count else 'no')

    def test_prior_forecast_mutation_cannot_reuse_original_pin(self):
        *_, frozen, transition=fixture(); pin=digest(frozen)
        frozen['answer']['candidate_predictions']['A']='none'
        with self.assertRaisesRegex(ValueError,'forecast.*pin'):
            build_feedback(frozen,pin,transition,digest(transition),trajectory_id='fixture',
                study_decision_index=1,restored_prefix_length=transition['step'],current=transition['after'])

    def test_transition_mutation_cannot_reuse_original_pin(self):
        *_, frozen, transition=fixture(); pin=digest(transition)
        transition['after']['grid'][10][10]=7
        with self.assertRaisesRegex(ValueError,'transition.*pin'):
            build_feedback(frozen,digest(frozen),transition,pin,trajectory_id='fixture',
                study_decision_index=1,restored_prefix_length=transition['step'],current=transition['after'])

    def test_rehashed_wrong_trajectory_step_before_action_or_binary_prediction_refused(self):
        for field in ('trajectory','step','before','action','prediction','extra'):
            *_, frozen, transition=fixture()
            if field=='trajectory': frozen['trajectory_id']='other'
            elif field=='step': frozen['game_action_index']+=1
            elif field=='before': transition['before']['grid'][1][1]=7
            elif field=='action': transition['action']['action_id']=99
            elif field=='prediction': transition['predicted_visible_change']='no'
            else: transition['future_reference_key']='none'
            with self.subTest(field=field), self.assertRaises(ValueError): receipt(frozen,transition)

    def test_full_click_coordinates_are_part_of_identity(self):
        cp,pair,prior,_,transition=fixture()
        pair={'A':{'action_id':6,'action_data':{'x':1,'y':2}},'B':{'action_id':6,'action_data':{'x':3,'y':2}}}
        frozen=freeze_forecast(prior,pair,trajectory_id='fixture',study_decision_index=0,
            game_action_index=transition['step'],before=transition['before'])
        transition['action']=deepcopy(pair['A']); self.assertEqual(receipt(frozen,transition)['action'],pair['A'])
        transition['action']['action_data']['x']=2
        with self.assertRaisesRegex(ValueError,'full dispatched'): receipt(frozen,transition)

    def test_same_action_on_different_event_is_not_the_previous_study_event(self):
        *_, frozen, transition=fixture(); transition['step']+=1
        with self.assertRaises(ValueError): receipt(frozen,transition)

    def test_current_state_must_equal_actual_full_after_observation(self):
        *_, frozen, transition=fixture(); current=deepcopy(transition['after']);current['legal_actions']=[1]
        with self.assertRaisesRegex(ValueError,'current observation'): receipt(frozen,transition,current=current)

    def test_missing_evidence_and_invalid_phase_refuse_without_receipt(self):
        *_, frozen, transition=fixture()
        for index in (0,True,1.0,2,None):
            with self.subTest(index=index), self.assertRaises(ValueError): receipt(frozen,transition,study_decision_index=index)
        with self.assertRaisesRegex(ValueError,'unavailable'):
            build_feedback(None,None,None,None,trajectory_id='fixture',study_decision_index=1,restored_prefix_length=2,current=transition['after'])

    def test_display_is_deep_copy_of_observed_whitelist_without_raw_frames_or_unexecuted_outcome(self):
        *_, frozen, transition=fixture(); full=receipt(frozen,transition); shown=display(full)
        self.assertNotIn('provenance',shown);self.assertNotIn('trajectory_id',shown)
        self.assertNotIn('candidates',shown);self.assertNotIn('grid',json.dumps(shown))
        shown['action']['action_id']=99
        self.assertNotEqual(shown['action'],full['action'])


class Interface(unittest.TestCase):
    def test_first_requests_identical_to_existing_neutral_control(self):
        cp=selected();pair=candidates(cp,0)
        expected=baseline(cp['base_request'],pair,'neutral_choice',study_decision_index=0,restored_prefix_length=len(cp['prefix']))
        for condition in CONDITIONS:
            self.assertEqual(make_request(cp['base_request'],pair,condition,study_decision_index=0,
                restored_prefix_length=len(cp['prefix']),trajectory_id='fixture'),expected)

    def test_second_conditions_differ_only_by_one_appended_fact_block(self):
        data=fixture();control=second('summary_only',data);treated=second('verified_feedback',data)
        added=treated['messages'][1]['content'].pop()
        self.assertEqual(control,treated)
        facts=json.loads(added['text']);self.assertEqual(facts['observed_changed_cell_count'],2)
        self.assertEqual(facts['original_forecast_check'],'matched')

    def test_first_phase_rejects_injected_future_receipt(self):
        cp=selected();pair=candidates(cp,0)
        with self.assertRaisesRegex(ValueError,'no previous'):
            make_request(cp['base_request'],pair,'verified_feedback',study_decision_index=0,
                restored_prefix_length=len(cp['prefix']),trajectory_id='fixture',frozen={})

    def test_displayed_frame_mismatch_refused_in_both_conditions(self):
        cp,pair,prior,frozen,t=fixture();current=deepcopy(t['after']);current['grid'][40][40]=7
        wrong=request_for(cp['initial'],cp['initial_case']['geometry']['reviewed'],current,
            cp['prefix']+[t],len(cp['prefix'])+1,cp['base_request']['model'])
        for condition in CONDITIONS:
            with self.subTest(condition=condition), self.assertRaisesRegex(ValueError,'displayed'):
                make_request(wrong,pair,condition,prior,study_decision_index=1,restored_prefix_length=len(cp['prefix']),
                    trajectory_id='fixture',frozen=frozen,forecast_pin=digest(frozen),transition=t,transition_pin=digest(t),current=t['after'])

    def test_previous_request_answer_cannot_differ_from_immutable_envelope(self):
        data=list(fixture());data[2]=deepcopy(data[2]);data[2]['candidate_predictions']['A']='none'
        with self.assertRaisesRegex(ValueError,'previous answer'): second('verified_feedback',data)

    def test_no_outcome_is_forced_by_schema_and_future_unknown_stays_allowed(self):
        schema=second('verified_feedback')['response_format']['json_schema']['schema']['properties']
        self.assertEqual(schema['observed_previous_change']['enum'],['yes','no','unknown'])
        self.assertIn('unknown',schema['candidate_predictions']['properties']['A']['enum'])


class Flow(unittest.TestCase):
    def test_forecast_journal_precedes_dispatch_and_feedback_is_dynamic(self):
        for condition in CONDITIONS:
            cp=selected();pair=candidates(cp,0);engine=FakeEngine(cp);events=[];bodies=[]
            def complete(body):
                first=not bodies;bodies.append(deepcopy(body));return answer(first=first,prediction='none')
            result=run_case(cp,pair,condition,engine,complete,events.append,deadline=10,now=lambda:0)
            self.assertEqual(result['model_calls'],2);self.assertEqual(result['new_dispatches'],2)
            self.assertEqual(engine.close_calls,1)
            kinds=[e['kind']for e in events]
            self.assertLess(kinds.index('forecast_commit'),kinds.index('dispatch_intent'))
            if condition=='verified_feedback':
                facts=json.loads(bodies[1]['messages'][1]['content'][-1]['text'])
                self.assertEqual(facts['observed_changed_cell_count'],0)
                self.assertEqual(facts['original_forecast_check'],'matched')

    def test_forecast_journal_failure_prevents_new_dispatch_and_closes(self):
        cp=selected();engine=FakeEngine(cp)
        def sink(event):
            if event['kind']=='forecast_commit':raise OSError('forecast journal failed')
        with self.assertRaisesRegex(OSError,'forecast journal'):
            run_case(cp,candidates(cp,0),'verified_feedback',engine,lambda b:answer(),sink,deadline=10,now=lambda:0)
        self.assertEqual(len(engine.actions),len(cp['prefix']));self.assertEqual(engine.close_calls,1)

    def test_late_response_or_commit_cannot_admit_action(self):
        for point in ('response','forecast_commit'):
            cp=selected();engine=FakeEngine(cp);clock=Clock()
            def sink(event):
                if event['kind']==point:clock.value=10
            with self.subTest(point=point):
                result=run_case(cp,candidates(cp,0),'verified_feedback',engine,lambda b:answer(),sink,deadline=10,now=clock)
                self.assertEqual(result['reason'],'deadline')
            self.assertEqual(len(engine.actions),len(cp['prefix']));self.assertEqual(engine.close_calls,1)

    def test_invalid_answer_not_repaired_or_retried(self):
        cp=selected();engine=FakeEngine(cp)
        result=run_case(cp,candidates(cp,0),'verified_feedback',engine,lambda b:'{}',lambda e:None,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'invalid_answer');self.assertEqual(result['model_calls'],1)
        self.assertEqual(result['new_dispatches'],0);self.assertEqual(engine.close_calls,1)

    def test_early_terminal_preserves_missing_second_phase(self):
        cp=selected()
        def followup(index,action,obs):obs['levels_completed']=1
        engine=FakeEngine(cp,followup=followup)
        result=run_case(cp,candidates(cp,0),'verified_feedback',engine,lambda b:answer(),lambda e:None,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'first_level_complete');self.assertEqual(result['model_calls'],1)


class Preparation(unittest.TestCase):
    def test_freeze_both_requests_and_reject_rehashed_future_input_or_request_edit(self):
        cases=[]
        for index in range(8):
            cp=selected();identity='fixture-'+str(index)
            cp['case_id']=cp['initial_case']['case_id']=identity
            cp['checkpoint_id']=identity+'-step'+str(cp['decision_step']).zfill(2);cases.append(cp)
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);source=root/'checkpoints.json';write_new(source,{'checkpoints':cases})
            frozen=protocol();frozen['source_checkpoint_file_sha256']=sha(source)
            frozen['planning_ceiling_not_authorization']['prefix_dispatches']=32
            with patch('research.verified_feedback_v1.preparation.protocol',return_value=frozen),patch(
                    'research.verified_feedback_v1.preparation.source_inventory',return_value={'fixture.py':'a'*64}):
                out=root/'prepared';build(source,out);pin=sha(out/'input-manifest.json');verify(out,pin)
                with self.assertRaises(FileExistsError):build(source,out)
                manifest=json.loads((out/'input-manifest.json').read_bytes())
                for cp in cases:
                    names=[out/'model-inputs'/(cp['checkpoint_id']+'-'+condition+'.json')for condition in CONDITIONS]
                    self.assertEqual(names[0].read_bytes(),names[1].read_bytes())
                leaked=out/'future-key.json';write_new(leaked,{'A':'none'})
                with self.assertRaisesRegex(ValueError,'extra'):verify(out,pin)
                leaked.unlink()
                name=next(n for n in manifest['files_sha256']if n.startswith('model-inputs/'))
                body=json.loads((out/name).read_bytes());body['temperature']=1
                (out/name).write_text(json.dumps(body));manifest['files_sha256'][name]=sha(out/name)
                (out/'input-manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'frozen first'):verify(out,sha(out/'input-manifest.json'))


if __name__=='__main__':unittest.main()
