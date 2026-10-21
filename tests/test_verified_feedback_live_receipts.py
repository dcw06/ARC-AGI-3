"""Independent checks must catch even a shared producer/replay receipt bug."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.action_effect_choice_v2.interface import candidates
from research.initial_geometry_assistance_v1.geometry import digest
from research.verified_feedback_v1.flow import run_case
from research.verified_feedback_v1.feedback import build_feedback as real_feedback, freeze_forecast as real_freeze
from research.verified_feedback_live_v1.audit import audit_case, independent_commit, paired_context
from tests.verified_feedback_live_fixture import checkpoints
from tests.test_feedback_probe_audit_v1 import ScriptEngine


def case(variant='verified_feedback'):
    cp=checkpoints()[0];pair=candidates(cp,0);events=[];answers=[]
    def complete(body):
        first=not answers
        value={'candidate_predictions':{'A':'unknown','B':'none'},'selected_candidate':'B',
            'observed_previous_change':'not_applicable'if first else'no',
            'previous_prediction_check':'not_applicable'if first else'matched'}
        text=json.dumps(value);answers.append(text);return text
    run_case(cp,pair,variant,ScriptEngine(cp),complete,events.append,deadline=float('inf'),now=lambda:0)
    return cp,pair,events,answers


class IndependentReceipts(unittest.TestCase):
    def test_valid_receipts_and_unchanged_control_replay(self):
        for variant in('summary_only','verified_feedback'):
            cp,pair,events,_=case(variant)
            self.assertEqual(audit_case(cp,pair,variant,events,ScriptEngine(cp))['reason'],'action_cap')

    def test_shared_producer_and_replay_wrong_count_still_rejected(self):
        def broken(*args,**kwargs):
            receipt=real_feedback(*args,**kwargs);receipt['observed_changed_cell_count']+=1;return receipt
        with patch('research.verified_feedback_v1.interface.build_feedback',side_effect=broken):
            cp,pair,events,_=case()
            with self.assertRaisesRegex(ValueError,'independent displayed feedback'):
                audit_case(cp,pair,'verified_feedback',events,ScriptEngine(cp))

    def test_shared_bad_forecast_commitment_still_rejected(self):
        def broken(*args,**kwargs):
            frozen=real_freeze(*args,**kwargs);frozen['before_observation_sha256']='0'*64;return frozen
        with ExitStack()as stack:
            stack.enter_context(patch('research.verified_feedback_v1.flow.freeze_forecast',side_effect=broken))
            stack.enter_context(patch('research.verified_feedback_v1.feedback.freeze_forecast',side_effect=broken))
            cp,pair,events,_=case()
            with self.assertRaisesRegex(ValueError,'independent pre-dispatch'):
                audit_case(cp,pair,'verified_feedback',events,ScriptEngine(cp))

    def test_late_or_rehashed_event_commit_not_trusted(self):
        cp,pair,events,texts=case()
        for mode in('late','answer','index','transition'):
            altered=deepcopy(events)
            commit=next(e for e in altered if e['kind']=='forecast_commit')
            if mode=='late':altered.remove(commit);altered.insert(-2,commit)
            elif mode=='answer':
                commit['forecast']['answer']['candidate_predictions']['B']='unknown'
                commit['forecast_sha256']=digest(commit['forecast'])
            elif mode=='index':
                commit['forecast']['game_action_index']+=1;commit['forecast_sha256']=digest(commit['forecast'])
            else:next(e for e in altered if e['kind']=='transition')['transition_sha256']='a'*64
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                independent_commit(cp,pair,'verified_feedback',altered,texts)

    def test_feedback_never_includes_an_unexecuted_outcome(self):
        cp,pair,events,_=case()
        request=[e for e in events if e['kind']=='request'][1]
        block=json.loads(request['body']['messages'][1]['content'][-1]['text'])
        self.assertEqual(set(block),{'schema','previous_study_decision_index','game_action_index','action',
            'original_selected_forecast','observed_changed_cell_count','observed_changed_cell_category',
            'observed_visible_change','original_forecast_check','forecast_comparison_available','qualification'})
        self.assertEqual(block['action'],pair['B'])
        self.assertNotIn('candidate_predictions',block)

    def test_terminal_or_unreached_second_decision_does_not_get_state_comparison(self):
        cp=checkpoints()[0];rows=[]
        with tempfile.TemporaryDirectory()as folder:
            output=Path(folder)
            for variant in cp['order']:
                events=[{'kind':'transition','decision':0,'record':{'after':cp['current']}}]
                (output/(cp['checkpoint_id']+'-'+variant+'.jsonl')).write_text(json.dumps(events[0])+'\n')
                rows.extend([{'checkpoint_id':cp['checkpoint_id'],'decision':0,'observed':True,
                    'score':{'valid':True,'prediction':{'selected_candidate':'A'}}},
                    {'checkpoint_id':cp['checkpoint_id'],'decision':1,'observed':False}])
            result=paired_context([cp],rows,output)[0]
            self.assertFalse(result['second_state_comparable']);self.assertIsNone(result['second_states_equal'])
            # Reached labels alone cannot substitute for actual retained requests.
            for row in rows:row['observed']=True
            result=paired_context([cp],rows,output)[0]
            self.assertFalse(result['second_state_comparable']);self.assertIsNone(result['second_states_equal'])


if __name__=='__main__':unittest.main()
