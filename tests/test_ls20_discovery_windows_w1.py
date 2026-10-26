import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.ls20_discovery_windows import M1View, HypothesisManager, execute_step, replay_step, validate_action
from research.ls20_discovery_windows.contract import digest
from research.ls20_discovery_windows.journal import read_checked
from tests.ls20_windows_fixture import PRODUCER, RawMemory, action, obs, observe


def manager(memory):
    return HypothesisManager(M1View(memory.snapshot(), PRODUCER))


class ContractTests(unittest.TestCase):
    def test_accepts_initial_and_replayed_raw_observations(self):
        m=RawMemory()
        self.assertEqual(M1View(m.snapshot(),PRODUCER).context()['next_step'],0)
        observe(m,obs([[0,1]]))
        v=M1View(m.snapshot(),PRODUCER)
        self.assertEqual(v.context()['next_step'],1)
        self.assertNotEqual(v.context()['before_sha256'],v.context()['before_frame_sha256'])

    def test_coordinates_and_actions_are_strict(self):
        for bad in (action(True),action(0),action(7),action(1,x=0,y=0),action(6),
                    action(6,x=True,y=0),action(6,x=0.5,y=0),action(6,x=64,y=0)):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                validate_action(bad,[1,2,6])
        self.assertEqual(validate_action(action(6,x=3,y=7),[6])['action_data'],{'x':3,'y':7})

    def test_tampered_raw_provenance_is_rejected(self):
        m=RawMemory()
        observe(m,obs([[0,1]]))
        for field,value in (('before_sha256','0'*64),('after_observation_id','o99'),
                             ('episode_id','other'),('segment',True),('elapsed_seconds',float('inf'))):
            broken=m.snapshot()
            broken['transitions'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                M1View(broken,PRODUCER)

    def test_tampered_computed_effect_rejected(self):
        m=RawMemory()
        observe(m,obs([[0,1]]))
        value=m.snapshot()
        value['transitions'][0]['effect']['any_frame_changed']=False
        with self.assertRaises(ValueError): M1View(value,PRODUCER)

    def test_tampered_raw_frame_rejected(self):
        m=RawMemory()
        value=m.snapshot()
        value['observations'][0]['grid'][0][0]=3
        with self.assertRaises(ValueError): M1View(value,PRODUCER)

    def test_boolean_alias_in_raw_frames_and_effect_counts_rejected(self):
        m=RawMemory(obs([[1,0]]))
        value=m.snapshot()
        value['observations'][0]['grid'][0][0]=True
        with self.assertRaises(ValueError): M1View(value,PRODUCER)
        observe(m,obs([[1,0]]))
        value=m.snapshot()
        value['transitions'][0]['effect']['changed_cells_by_frame']=[False]
        with self.assertRaises(ValueError): M1View(value,PRODUCER)

    def test_source_commit_required(self):
        for commit in ('main','f4bf522',None):
            with self.assertRaises(ValueError): M1View(RawMemory().snapshot(),commit)

    def test_failed_request_is_not_no_change_evidence(self):
        m=RawMemory()
        m.append(action(),dict(status='dispatch_failed',error='not delivered'))
        self.assertEqual(manager(m).hypotheses(),[])
        self.assertEqual(manager(m).predict(action())['status'],'no_candidates')

    def test_unknown_request_suspends_predictions(self):
        m=RawMemory()
        m.append(action(),dict(status='outcome_unknown',reason='lost'))
        self.assertTrue(manager(m).export()['context']['suspended'])
        with self.assertRaises(ValueError): manager(m).predict(action())
        observe(m,obs())
        with self.assertRaises(ValueError): M1View(m.snapshot(),PRODUCER)

    def test_multiframe_transient_is_not_no_change(self):
        m=RawMemory()
        observe(m,obs(frames=[[[0,1]],[[0,0]]]))
        self.assertEqual(M1View(m.snapshot(),PRODUCER).history[-1]['label'],'transient_change')

    def test_dimension_change_is_distinct(self):
        m=RawMemory()
        observe(m,obs([[0],[0]]))
        self.assertEqual(M1View(m.snapshot(),PRODUCER).history[-1]['label'],'dimensions_changed')

    def test_level_and_reset_clear_applicability(self):
        for post in (obs(level=1),obs(reset=True)):
            m=RawMemory()
            observe(m,obs([[0,1]]))
            observe(m,post)
            self.assertEqual(manager(m).predict(action())['status'],'no_candidates')

    def test_derived_role_hints_are_not_promoted(self):
        value=RawMemory().snapshot()
        value['hypotheses']=[dict(role='player',confidence=1.0)]
        h=HypothesisManager(M1View(value,PRODUCER))
        self.assertEqual(h.hypotheses(),[])


class HypothesisTests(unittest.TestCase):
    def test_candidate_display_limit_cannot_hide_disagreement(self):
        m=RawMemory()
        observe(m,obs())
        h=manager(m)
        template=h.hypotheses()[0]
        h._hypotheses=[]
        for index in range(6):
            item=copy.deepcopy(template)
            item['id']=f'wh{index}'
            item['predicted_label']='visible_change' if index==5 else 'no_visible_change'
            h._hypotheses.append(item)
        result=h.predict(action())
        self.assertEqual(len(result['candidate_ids']),4)
        self.assertEqual(result['omitted_candidate_count'],2)
        self.assertEqual(result['status'],'candidate_disagreement')
        self.assertEqual(result['predicted_labels'],['no_visible_change','visible_change'])

    def test_first_observation_generates_candidates(self):
        m=RawMemory()
        observe(m,obs())
        hs=manager(m).hypotheses()
        self.assertEqual(len(hs),3)
        self.assertEqual({h['predicted_label'] for h in hs},{'no_visible_change'})
        self.assertEqual({h['status'] for h in hs},{'tentative'})

    def test_repetition_supports_but_does_not_prove_causation(self):
        m=RawMemory()
        observe(m,obs())
        observe(m,obs())
        h=manager(m)
        self.assertEqual({x['status'] for x in h.hypotheses()},{'supported'})
        self.assertTrue(h.predict(action())['unknown_alternative'])

    def test_contradiction_preserved_and_new_explanation_created(self):
        m=RawMemory()
        observe(m,obs())
        first=manager(m).predict(action())
        self.assertEqual(first['predicted_labels'],['no_visible_change'])
        observe(m,obs(frames=[[[0,1]],[[0,0]]]))
        h=manager(m)
        old=h.hypotheses()[:3]
        self.assertEqual({x['status'] for x in old},{'contradicted'})
        self.assertEqual(old[0]['counterexamples'][0]['id'],'t1')
        self.assertIn('transient_change',{x['predicted_label'] for x in h.hypotheses()[3:]})
        self.assertEqual(h.predict(action())['predicted_labels'],['transient_change'])

    def test_confounded_scopes_disagree_and_immediate_commits(self):
        m=RawMemory(obs(state='A'))
        observe(m,obs([[0,1]],state='B'),1)
        observe(m,obs([[0,1]],state='B'),2)
        h=manager(m)
        self.assertEqual(h.predict(action())['predicted_labels'],['no_visible_change','visible_change'])
        self.assertEqual(h.predict(action())['status'],'candidate_disagreement')
        self.assertEqual(h.predict(action(),mode='immediate')['predicted_labels'],['visible_change'])

    def test_counterexamples_are_not_erased_by_repeat(self):
        m=RawMemory()
        observe(m,obs())
        observe(m,obs([[1,0]]))
        observe(m,obs([[1,0]]))
        self.assertEqual(manager(m).hypotheses()[0]['status'],'contradicted')
        self.assertEqual(len(manager(m).hypotheses()[0]['supporting_evidence']),1)

    def test_prediction_binds_complete_snapshot_and_action(self):
        m=RawMemory()
        h=manager(m)
        p=h.predict(action())
        self.assertEqual(p['snapshot_sha256'],digest(m.snapshot()))
        p0=copy.deepcopy(p)
        ident=p0.pop('prediction_id')
        self.assertEqual(ident,digest(p0))
        self.assertNotEqual(ident,h.predict(action(2))['prediction_id'])

    def test_exact_click_coordinates_are_part_of_scope(self):
        m=RawMemory(obs(legal=[6]))
        m.append(action(6,x=1,y=2),dict(status='acknowledged',post=obs(legal=[6])))
        h=manager(m)
        p=h.predict(action(6,x=3,y=2))
        self.assertEqual(len(p['candidate_ids']),1)  # state-only generalization, not click-specific evidence
        self.assertIsNone(next(x for x in h.hypotheses() if x['id']==p['candidate_ids'][0])['scope']['action'])

    def test_export_is_copied_and_targets_are_not_invented(self):
        m=RawMemory()
        observe(m,obs())
        h=manager(m)
        export=h.export()
        export['hypotheses'].clear()
        self.assertEqual(len(h.hypotheses()),3)
        self.assertEqual(h.export()['objective_hypotheses'],[])
        self.assertEqual(h.export()['candidate_targets'],[])

    def test_palette_permutation_changes_no_predictions(self):
        outputs=[]
        for transform in (lambda x:x,lambda x:15-x):
            m=RawMemory(obs([[transform(0),transform(2)]]))
            observe(m,obs([[transform(2),transform(0)]]))
            outputs.append(manager(m).predict(action())['predicted_labels'])
        self.assertEqual(outputs,[['visible_change'],['visible_change']])


class JournalTests(unittest.TestCase):
    def test_prediction_is_fsynced_before_callback_and_replay_passes(self):
        m=RawMemory()
        with tempfile.TemporaryDirectory() as directory:
            def dispatch(act):
                self.assertTrue((Path(directory)/'step-0000.prediction.json').is_file())
                self.assertEqual(read_checked(Path(directory)/'step-0000.prediction.json')['action'],act)
                self.assertEqual(len(m.snapshot()['transitions']),0)
                return dict(status='acknowledged',post=obs())
            execute_step(m,action(),dispatch,directory,producer_commit=PRODUCER)
            self.assertEqual(replay_step(directory,0,PRODUCER)['label'],'no_visible_change')

    def test_existing_prepared_step_never_dispatches(self):
        m=RawMemory()
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'step-0000.before.json').write_text('{}')
            with self.assertRaises(FileExistsError):
                execute_step(m,action(),lambda _:self.fail('duplicate dispatch'),directory,producer_commit=PRODUCER)

    def test_dispatch_exception_is_unknown_and_suspends(self):
        m=RawMemory()
        with tempfile.TemporaryDirectory() as directory:
            def dispatch(_): raise RuntimeError('lost reply')
            result=execute_step(m,action(),dispatch,directory,producer_commit=PRODUCER)
            self.assertEqual(result['status'],'outcome_unknown')
            self.assertFalse(replay_step(directory,0,PRODUCER)['scored'])
            with self.assertRaises(ValueError): manager(m).predict(action())

    def test_malformed_reply_is_unknown_not_noop(self):
        m=RawMemory()
        with tempfile.TemporaryDirectory() as directory:
            result=execute_step(m,action(),lambda _:dict(status='acknowledged',post={}),
                                directory,producer_commit=PRODUCER)
            self.assertEqual(result['status'],'outcome_unknown')

    def test_illegal_action_never_reaches_dispatch(self):
        with tempfile.TemporaryDirectory() as directory,self.assertRaises(ValueError):
            execute_step(RawMemory(),action(6),lambda _:self.fail('illegal dispatch'),directory,producer_commit=PRODUCER)

    def test_forged_prediction_rejected_even_with_recomputed_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            execute_step(RawMemory(),action(),lambda _:dict(status='acknowledged',post=obs()),
                         directory,producer_commit=PRODUCER)
            path=Path(directory)/'step-0000.prediction.json'
            envelope=json.loads(path.read_text())
            envelope['payload']['predicted_labels']=['visible_change']
            envelope['sha256']=digest(envelope['payload'])
            path.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError): replay_step(directory,0,PRODUCER)

    def test_history_substitution_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            m=RawMemory()
            execute_step(m,action(),lambda _:dict(status='acknowledged',post=obs()),directory,producer_commit=PRODUCER)
            execute_step(m,action(),lambda _:dict(status='acknowledged',post=obs([[1,0]])),directory,producer_commit=PRODUCER)
            self.assertTrue(replay_step(directory,1,PRODUCER)['covered'])
            path=Path(directory)/'step-0001.after.json'
            envelope=json.loads(path.read_text())
            envelope['payload']['transitions'][0]['action']['action_id']=2
            envelope['sha256']=digest(envelope['payload'])
            path.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError): replay_step(directory,1,PRODUCER)


if __name__=='__main__': unittest.main()
