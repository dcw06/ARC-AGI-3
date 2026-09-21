import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from certification.phase4_transient_v2.selection import select,FIELD,enforce_payload
from certification.phase4_transient_v2.independent_selection import expected
from certification.phase4_transient_v2.contract import request_for,digest
from certification.phase4_transient_v2.worker import run_cases
from certification.phase4_transient_v2.fixtures import adapter_factory,ScriptedService
from certification.phase4_transient_v2.evidence import EvidenceStore
from certification.phase4_transient_v2.trajectory import evaluate_trajectories
from certification.phase4_transient_v2.service import audited_completion

class SelectionTests(unittest.TestCase):
    def transition(self,*frames):return ({'frames':[[[0,0],[0,0]]]},{'frames':list(frames)})
    def test_filter_before_ranking_and_earliest_tie(self):
        a=[[1,0],[0,0]];b=[[0,1],[0,0]];final=[[2,2],[2,2]]
        previous=self.transition(final,a,b,final)
        self.assertEqual(select(previous),{'grid':a,'frame_index_zero_based':1,'returned_frame_count':4})
        self.assertEqual(select(previous),expected(previous))
    def test_nulls(self):
        for p in [None,self.transition([[0,0],[0,0]]),self.transition([[0,0],[0,0]],[[1,1],[1,1]]),
                  self.transition([[1,1],[1,1]],[[1,1],[1,1]])]:
            self.assertIsNone(select(p));self.assertIsNone(expected(p))
    def test_shapes_types_palette_and_limits_fail(self):
        for p in [self.transition([[0]]),self.transition([[0,0],[0,0]],[[1]]),
                  self.transition([[True,0],[0,0]]),self.transition([[16,0],[0,0]]),
                  self.transition(*([[[0,0],[0,0]]]*65))]:
            with self.assertRaises(ValueError):select(p)
            with self.assertRaises(ValueError):expected(p)
    def test_context_and_bytes_reject_before_transport(self):
        class Tokenizer:
            def apply_chat_template(self,*a,**kw):return [1]*65409
        request={'messages':[{'role':'user','content':'x'}],'max_tokens':128}
        with patch('builtins.print'):
            with self.assertRaises(ValueError):audited_completion(Tokenizer(),request,lambda r:self.fail('transport called'))
        request['messages'][0]['content']='x'*65536
        with self.assertRaises(ValueError):enforce_payload(request)
    def test_context_boundary_and_mismatch_retained(self):
        from types import SimpleNamespace
        from certification.phase4_transient_v2.response_evidence import ResponseValidationError
        class Tokenizer:
            def apply_chat_template(self,*a,**kw):return [1]*65408
        req={'messages':[{'role':'user','content':'x'}],'max_tokens':128}
        out=SimpleNamespace(content='{}',prompt_tokens=65408,completion_tokens=2)
        with patch('builtins.print'):
            self.assertEqual(audited_completion(Tokenizer(),req,lambda r:out)[1]['tokenizer_prompt_tokens'],65408)
            out.prompt_tokens=65407
            with self.assertRaises(ResponseValidationError) as caught:audited_completion(Tokenizer(),req,lambda r:out)
        self.assertIn('response_sha256',caught.exception.response_evidence)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=EvidenceStore(self.root,'worker');(self.root/'control').mkdir()
        self.service=ScriptedService();self.start=time.monotonic()
    def tearDown(self):self.temp.cleanup()
    def execute(self,**kw):
        return run_cases(self.service,self.store,kw.pop('factory',adapter_factory),started=self.start,
            deadline=self.start+120,cancel=self.root/'control/cancel.json',live=False,**kw)
    def test_six_episodes_pairing_and_independent_selection(self):
        state=self.execute();result=evaluate_trajectories(state,self.root/'worker',seconds=150)
        self.assertEqual(len(result['pairs']),3);self.assertEqual(state['requests_started'],18)
        for ep in state['episodes']:
            for i,name in enumerate(ep['steps']):
                step=json.loads((self.root/'worker'/name).read_text());obs=json.loads(step['request']['messages'][1]['content'])['observation']
                self.assertEqual(step['request']['seed'],ep['request_seed'])
                self.assertEqual(FIELD in obs,ep['arm']=='transient')
                if ep['arm']=='transient':self.assertEqual(obs[FIELD] is None,i==0)
        with self.assertRaises(ValueError):evaluate_trajectories({**state,'episodes':state['episodes'][:-1]},self.root/'worker')
        ep=next(e for e in state['episodes'] if e['arm']=='transient');path=self.root/'worker'/ep['steps'][1]
        original=path.read_bytes();step=json.loads(original)
        for mutation in ['frame','index','remove','coordinates','seed']:
            bad=copy.deepcopy(step);payload=json.loads(bad['request']['messages'][1]['content'])
            if mutation=='frame':payload['observation'][FIELD]['grid'][0][0]=3
            if mutation=='index':payload['observation'][FIELD]['frame_index_zero_based']=1
            if mutation=='remove':payload['observation'].pop(FIELD)
            if mutation=='coordinates':payload['observation']['recent_action_data']={'x':3,'y':3}
            if mutation=='seed':bad['request']['seed']=2
            bad['request']['messages'][1]['content']=json.dumps(payload,sort_keys=True,separators=(',',':'))
            bad['request_sha256']=digest(bad['request']);bad['audit']['request_sha256']=bad['request_sha256']
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError,msg=mutation):evaluate_trajectories(state,self.root/'worker',seconds=150)
        path.write_bytes(original)
    def test_matched_builder_changes_only_field(self):
        from agent.state import GameRuntimeState
        from certification.phase4_transient_v2.contract import protocol,pack
        from agent.action import ActionDecision
        row=protocol()['schedule'][0];adapter=adapter_factory(row)
        adapter.open_scorecard();client=adapter.bootstrap(row['game_id']);state=GameRuntimeState(client.observation,action_budget_limit=20)
        before=state.observation
        post=adapter.dispatch(client,ActionDecision(action_id=1,action_data={},source='test',decision_id='match'))
        state.replace_observation(post,action_id=1,action_data={},transition_id='match')
        for seed in (0,1,2):
            control=request_for(state,'control',seed,(pack(before),pack(post)))
            treatment=request_for(state,'transient',seed,(pack(before),pack(post)))
            payload=json.loads(treatment['messages'][1]['content'])
            self.assertIsNotNone(payload['observation'].pop(FIELD))
            treatment['messages'][1]['content']=json.dumps(payload,sort_keys=True,separators=(',',':'))
            self.assertEqual(control,treatment)
        adapter.finalize_client(client);adapter.close_scorecard()
    def test_120_action_cap(self):
        from arcengine import GameState
        # A nonterminal scripted arcade makes all six episodes consume their cap.
        from certification.phase4_transient_v2.fixtures import FakeArcade
        from agent.framework_adapter import LocalFrameworkAdapter
        class Nonterminal(FakeArcade):
            def make(self,*args,**kw):
                env=super().make(*args,**kw);original=env.observation
                def observation():
                    value=original();value.state=GameState.NOT_FINISHED;value.levels_completed=0;return value
                env.observation=observation;env.observation_space=observation();return env
        state=self.execute(factory=lambda row:LocalFrameworkAdapter(Nonterminal(row),seed_by_game={row['game_id']:0}),clock=lambda:self.start+1)
        self.assertEqual(state['requests_started'],120);self.assertEqual(state['dispatch_attempts'],120)
        self.assertEqual(len(evaluate_trajectories(state,self.root/'worker',seconds=150)['pairs']),3)
    def test_deadline_and_cleanup_failure(self):
        (self.root/'control/cancel.json').touch()
        with self.assertRaises(TimeoutError):self.execute()
        (self.root/'control/cancel.json').unlink()
        def factory(row):
            adapter=adapter_factory(row)
            adapter.close_scorecard=lambda:(_ for _ in ()).throw(RuntimeError('cleanup failed'))
            return adapter
        with self.assertRaises(RuntimeError):self.execute(factory=factory)
    def test_evidence_exhaustion(self):
        from certification.phase4_transient_v2 import evidence
        with patch.dict(evidence.LIMITS,worker=4500),self.assertRaises(ValueError):self.execute()
        self.assertEqual(len(self.service.audit_records),0)

if __name__=='__main__':unittest.main()
