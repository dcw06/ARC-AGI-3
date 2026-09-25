"""Negative regressions from the r1 review: closure failures, semantic replay, contradictory lifecycle evidence."""
import copy,hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from research.action_effect_history_v1 import runner as R
from research.action_effect_history_v1.evaluate import evaluate
from research.action_effect_history_v1.evidence import MANIFEST, load_verified, encode
from research.action_effect_history_v1.engine import DevelopmentAdapter
from tests.test_action_effect_history_v1_runner import ScriptedPolicy

class ClosingAdapter:
    def __init__(self,inner):self.inner=inner
    def bootstrap(self):return self.inner.bootstrap()
    def dispatch(self,action,before):return self.inner.dispatch(action,before)
    def close(self):
        receipt=self.inner.close();receipt['closed']=False;return receipt  # scorecard closure reported as failed

class NegativeRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from research.grounded_action_v1.engine import restore_game_mount
        cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name)
        cls.games=restore_game_mount(root/'games')
        cls.run_dir=root/'normal'
        cls.report=R.run(cls.run_dir,ScriptedPolicy(),lambda g,a,e:DevelopmentAdapter(g,a,e,cls.games,root/'rec'))
        assert cls.report['status']=='complete' and evaluate(cls.report)['replay_passed']
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def rejected(self,report,why):
        result=evaluate(report);self.assertFalse(result['replay_passed'],why);return result

    # Finding 1: failed closure can never yield a completed run.
    def test_closure_failure_stops_run_and_is_reported(self):
        root=Path(self.tmp.name)
        report=R.run(root/'closure',ScriptedPolicy(),lambda g,a,e:ClosingAdapter(DevelopmentAdapter(g,a,e,self.games,root/'rec2')))
        self.assertEqual(report['status'],'technical_failure')
        first=report['episodes'][0]
        self.assertEqual((first['status'],first['stop_reason'],first['play_stop_reason']),('technical_failure','technical_failure','action_cap'))
        result=evaluate(report)
        self.assertEqual(result['reliability_by_arm']['baseline']['closure_failures'],1)
        self.assertEqual(result['behaviour_result'],'inconclusive_incomplete_schedule')
    def test_forged_closure_receipts_rejected_by_replay(self):
        report=copy.deepcopy(self.report)
        for e in report['episodes']:e['cleanup']['closed']=False
        result=self.rejected(report,'closed:false on every episode')
        self.assertTrue(any('closure' in e for e in result['errors']))

    # Finding 2: replay re-derives call validity, continuity, terminal states, finals and accounting.
    def test_call_evidence_is_revalidated(self):
        for field,value in (('server_prompt_tokens',None),('finish_reason','length'),('response_sha256','0'*64)):
            with self.subTest(field=field):
                report=copy.deepcopy(self.report);call=report['episodes'][1]['calls'][3]
                call[field]=call['tokenizer_prompt_tokens']+1 if value is None else value
                self.rejected(report,field)
    def test_empty_episode_labelled_win_is_rejected(self):
        report=copy.deepcopy(self.report);e=report['episodes'][2]
        report['calls']-=len(e['calls']);report['dispatches']-=len(e['steps'])
        e.update(calls=[],steps=[],stop_reason='win',final=e['initial'])
        result=self.rejected(report,'empty episode as win')
        self.assertTrue(any('stop reason win but final state' in x for x in result['errors']))
    def test_observation_continuity_and_final_state(self):
        report=copy.deepcopy(self.report);steps=report['episodes'][0]['steps']
        steps[3]['before']=copy.deepcopy(steps[0]['before']);steps[3]['before']['levels_completed']+=1
        self.rejected(report,'broken pre-state chain')
        report=copy.deepcopy(self.report);report['episodes'][0]['final']['levels_completed']+=1
        self.rejected(report,'forged final observation')
    def test_accounting_and_complete_labels(self):
        report=copy.deepcopy(self.report);report['calls']+=1
        self.rejected(report,'run call total')
        report=copy.deepcopy(self.report);report['episodes'][1]['status']='interrupted'
        self.rejected(report,'complete pair with an interrupted episode')
    def test_rehashed_semantic_forgery_passes_integrity_but_fails_replay(self):
        target=Path(self.tmp.name)/'forged';shutil.copytree(self.run_dir,target)
        name='episodes/'+self.report['episodes'][0]['episode_id']+'.json'
        episode=json.loads((target/name).read_bytes());episode['calls'][2]['finish_reason']='length'
        raw=encode(episode);(target/name).write_bytes(raw)
        manifest=json.loads((target/MANIFEST).read_bytes())
        manifest['files'][name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};(target/MANIFEST).write_bytes(encode(manifest))
        loaded=load_verified(target)  # hashes are consistent...
        self.rejected(loaded,'rehashed finish_reason forgery')  # ...but the semantic replay rejects it

class LifecycleNegativeRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.rehearse_action_effect_history_v1 import rehearse
        base=Path.home()/'aeh-rehearsal-tests';base.mkdir(exist_ok=True)
        cls.work=Path(tempfile.mkdtemp(dir=base))
        receipt,cls.output=rehearse('none',2400,cls.work)
        assert receipt['study_status']=='study_complete_pending_independent_evaluation'
    @classmethod
    def tearDownClass(cls):shutil.rmtree(cls.work,ignore_errors=True)

    def test_contradictory_cleanup_evidence_is_rejected(self):
        from scripts.evaluate_action_effect_history_v1 import evaluate_output
        self.assertTrue(evaluate_output(self.output,mode='rehearsal')['technically_complete'])
        mutations=[('control/first-cell-supervisor-cleanup.json','errors',['supervisor reap: TimeoutExpired']),
                   ('control/first-cell-supervisor-cleanup.json','groups',{}),
                   ('control/first-cell-supervisor-cleanup.json','drain_finished',False),
                   ('control/first-cell-supervisor-cleanup.json','returncode',1),
                   ('control/notebook-cost.json','dependency_trees_removed',False),
                   ('control/notebook-cost.json','error','RuntimeError: x'),
                   ('control/gpu-cleanup.json','groups_absent',False)]
        for name,key,value in mutations:
            with self.subTest(name=name,key=key):
                target=self.work/('mutated-'+key);shutil.rmtree(target,ignore_errors=True);shutil.copytree(self.output,target)
                data=json.loads((target/name).read_bytes());data[key]=value;(target/name).write_text(json.dumps(data))
                result=evaluate_output(target,mode='rehearsal')
                self.assertFalse(result['technically_complete'],(name,key));self.assertTrue(result['lifecycle_errors'])

if __name__=='__main__':unittest.main()
