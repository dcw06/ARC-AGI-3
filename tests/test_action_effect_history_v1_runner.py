"""CPU rehearsals of the action-effect-history runner on the real offline development engine (no model)."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from research.action_effect_history_v1 import runner as R
from research.action_effect_history_v1.evaluate import evaluate,rate,classify_pair
from research.action_effect_history_v1.engine import DevelopmentAdapter

LATTICE=[(16,16),(24,16),(40,20),(8,40),(56,8),(32,48),(48,32),(4,4),(60,60),(20,50),(50,20),(12,28)]

class ScriptedPolicy:
    """Stands in for the model. baseline: repeats one action. history arm: changes action after a no-change entry."""
    def __init__(self,mode='normal',clock=None,seconds_per_call=0.0):
        self.mode,self.calls,self.clock,self.seconds=mode,0,clock,seconds_per_call
    def complete(self,request):
        self.calls+=1
        if self.clock is not None:self.clock.t+=self.seconds
        obs=json.loads(request['messages'][1]['content'])['observation'];legal=sorted(obs['legal_actions'])
        history=obs.get('action_effect_history');arm='history' if history is not None else 'baseline'
        if self.mode=='transport' and self.calls==5:raise ConnectionError('scripted transport failure')
        k=0
        if arm=='history' and self.mode!='same_policy':
            entries=history['entries'];k=len(entries)
            if entries and entries[-1]['final_frame_changed'] is False:k+=1
        action_id=legal[k%len(legal)]
        answer={'action':{'action_id':action_id,'action_data':{'x':LATTICE[k%12][0],'y':LATTICE[k%12][1]} if action_id==6 else {}}}
        raw=json.dumps(answer)
        if self.mode=='invalid_history' and arm=='history' and history and len(history['entries'])==2:raw='{"action":'
        prompt=10 if self.mode!='mismatch' or self.calls!=3 else 11
        return {'content':raw,'tokenizer_prompt_tokens':10,'server_prompt_tokens':prompt,'server_completion_tokens':12,
                'finish_reason':'stop'}

class FaultAdapter:
    def __init__(self,inner,fault,at):self.inner,self.fault,self.at,self.n=inner,fault,at,0
    def bootstrap(self):return self.inner.bootstrap()
    def dispatch(self,action,before):
        self.n+=1
        if self.n==self.at:
            if self.fault=='reject':raise R.DispatchRejected('HTTP 503 before acknowledgement')
            if self.fault=='unknown':raise TimeoutError('no response after send')
            if self.fault=='frameless':
                post,receipt=self.inner.dispatch(action,before);return SimpleNamespace(frames=(),canonical_hash=post.canonical_hash),receipt
        return self.inner.dispatch(action,before)
    def close(self):return self.inner.close()

class Clock:
    def __init__(self):self.t=0.0
    def __call__(self):return self.t

class RunnerRehearsals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from research.grounded_action_v1.engine import restore_game_mount
        cls.tmp=tempfile.TemporaryDirectory();cls.games=restore_game_mount(Path(cls.tmp.name)/'games')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def run_schedule(self,policy,fault=None,spec=None,deadline=3000,clock=None):
        folder=Path(tempfile.mkdtemp(dir=self.tmp.name))
        def factory(game_id,arm,episode_id):
            a=DevelopmentAdapter(game_id,arm,episode_id,self.games,folder/'rec')
            if fault and fault[0]==episode_id:a=FaultAdapter(a,fault[1],fault[2])
            return a
        kwargs={'clock':clock} if clock else {}
        report=R.run(folder/'run',policy,factory,deadline_seconds=deadline,spec=spec,**kwargs)
        self.assertEqual(R.load(folder/'run'),report)  # durable records reassemble to the returned report
        return report,evaluate(report,spec)
    def test_full_schedule_replays_and_classifies(self):
        report,result=self.run_schedule(ScriptedPolicy())
        self.assertEqual(report['status'],'complete');self.assertTrue(result['replay_passed'],result['errors'])
        self.assertEqual(len(report['episodes']),12);self.assertTrue(result['all_six_pairs_complete'])
        self.assertLessEqual(report['calls'],144)
        for m in result['episodes']:
            self.assertEqual(m['stop_reason'] in ('action_cap','win','game_over'),True)
            if m['immediate_repeat_opportunities']==0:self.assertIsNone(m['immediate_repeat_rate'])
        # History requests carry the field; baseline requests never do.
        for e in report['episodes']:
            for c in e['calls']:
                has='action_effect_history' in json.loads(c['request']['messages'][1]['content'])['observation']
                self.assertEqual(has,e['arm']=='history')
    def test_same_policy_in_both_arms_is_not_an_improvement(self):
        report,result=self.run_schedule(ScriptedPolicy('same_policy'))
        self.assertTrue(result['replay_passed'],result['errors'])
        self.assertNotEqual(result['behaviour_result'],'behaviour_changed_as_hypothesized')
        self.assertEqual(result['solving_result'],'no_demonstrated_solving_improvement')
    def test_invalid_output_stops_episode_and_makes_pair_ineligible(self):
        report,result=self.run_schedule(ScriptedPolicy('invalid_history'))
        self.assertTrue(result['replay_passed'],result['errors'])
        hist=[m for m in result['episodes'] if m['arm']=='history']
        self.assertTrue(all(m['stop_reason']=='invalid_output' and m['invalid_outputs']==1 for m in hist))
        self.assertTrue(all(p['class']=='ineligible' for p in result['pairs']))
        self.assertEqual(result['behaviour_result'],'candidate_worse')  # arm failures cannot hide behind fewer actions
    def test_dispatch_failures_are_never_no_ops(self):
        for fault in ('reject','unknown','frameless'):
            with self.subTest(fault=fault):
                report,result=self.run_schedule(ScriptedPolicy(),fault=('b1-s5i5-history',fault,3))
                self.assertTrue(result['replay_passed'],result['errors'])
                ep=next(e for e in report['episodes'] if e['episode_id']=='b1-s5i5-history')
                self.assertEqual(ep['stop_reason'],'dispatch_failure');last=ep['steps'][-1]['effect_record']
                self.assertEqual(last['status'],'dispatch_failed' if fault=='reject' else 'outcome_unknown')
                self.assertIsNone(last['changed_cells_by_frame']);self.assertIsNone(last['final_frame_changed'])
                self.assertEqual(report['status'],'complete')  # the run continues; the episode stops
                self.assertEqual(next(p for p in result['pairs'] if p['pair_id']=='b1-s5i5')['class'],'ineligible')
    def test_technical_failures_stop_the_run_and_keep_evidence(self):
        for mode in ('transport','mismatch'):
            with self.subTest(mode=mode):
                report,result=self.run_schedule(ScriptedPolicy(mode))
                self.assertEqual(report['status'],'technical_failure')
                self.assertEqual([p['status'] for p in report['pairs']][0],'interrupted')
                self.assertEqual(len(report['pairs']),6);self.assertIn('not_started',[p['status'] for p in report['pairs']])
                self.assertEqual(result['behaviour_result'],'inconclusive_incomplete_schedule')
                self.assertTrue(any(e['status']=='technical_failure' for e in report['episodes']))
    def test_deadline_overrun_interrupts_mid_pair_and_is_reported(self):
        clock=Clock();spec=copy.deepcopy(R.protocol());spec['limits']['pair_admission_seconds']=100
        # 10 s per call: pair 1 is admitted at t=0, and the deadline falls inside its second episode.
        report,result=self.run_schedule(ScriptedPolicy(clock=clock,seconds_per_call=10.0),spec=spec,deadline=180,clock=clock)
        self.assertEqual(report['status'],'deadline_exceeded')
        self.assertEqual(report['pairs'][0]['status'],'interrupted')
        self.assertEqual({e['status'] for e in report['episodes']},{'complete','interrupted'})
        self.assertTrue(result['replay_passed'],result['errors'])
        self.assertEqual(result['behaviour_result'],'inconclusive_incomplete_schedule')
        self.assertTrue(any(m['status']=='interrupted' for m in result['episodes']))  # kept in reliability reporting
    def test_pair_admission_records_unadmitted_pairs(self):
        spec=copy.deepcopy(R.protocol());spec['limits']['pair_admission_seconds']=10**6
        report,result=self.run_schedule(ScriptedPolicy(),spec=spec)
        self.assertEqual([p['status'] for p in report['pairs']],['not_admitted']*6);self.assertEqual(report['episodes'],[])

class MetricRuleTests(unittest.TestCase):
    def m(self,arm,rep,opp,stop='action_cap',status='complete'):
        return {'arm':arm,'status':status,'stop_reason':stop,'immediate_repeats':rep,'immediate_repeat_opportunities':opp,'immediate_repeat_rate':rate(rep,opp)}
    def test_null_denominators_and_classes(self):
        self.assertIsNone(rate(0,0));self.assertEqual(rate(0,4),0)
        self.assertEqual(classify_pair(self.m('baseline',0,5),self.m('history',0,3))[0],'ineligible')  # baseline rate not positive
        self.assertEqual(classify_pair(self.m('baseline',4,8),self.m('history',0,0))[0],'opportunities_eliminated')
        self.assertEqual(classify_pair(self.m('baseline',4,8),self.m('history',1,8))[0],'reduced')
        self.assertEqual(classify_pair(self.m('baseline',2,8),self.m('history',6,8))[0],'worse')
        self.assertEqual(classify_pair(self.m('baseline',4,8),self.m('history',3,8))[0],'not_reduced')
        self.assertEqual(classify_pair(self.m('baseline',4,8),self.m('history',0,2,stop='invalid_output'))[0],'ineligible')
        self.assertEqual(classify_pair(self.m('baseline',4,8),self.m('history',0,2,status='interrupted'))[0],'ineligible')

if __name__=='__main__':unittest.main()
