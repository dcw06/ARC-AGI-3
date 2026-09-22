import copy,json,os,tempfile,threading,time,unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from certification.phase4_grounding_v1.answers import parse,recompute,score
from certification.phase4_grounding_v1.cases import load_cases
from certification.phase4_grounding_v1.service import audited_completion
from certification.phase4_grounding_v1.response_evidence import ResponseValidationError

class CasesTests(unittest.TestCase):
    def test_coordinate_swap_and_boundaries(self):
        case={'task':{'kind':'coordinate','grid':[[1,2],[3,4]],'x':1,'y':0}}
        self.assertTrue(score(case,'{"color":3}')['axis_swap_match'])
        case['task'].update(x=1,y=1);self.assertTrue(score(case,'{"color":4}')['correct'])
    def test_unchanged_and_transient(self):
        self.assertEqual(recompute({'kind':'changes','before':[[0]],'after':[[0]]})['count'],0)
        rows=load_cases();self.assertTrue(any(c['task']['kind']=='changes' and c['expected']['count']>0 for c in rows))
        for c in rows:self.assertEqual(recompute(c['task']),c['expected'])
    def test_ambiguous_region(self):
        with self.assertRaises(ValueError):recompute({'kind':'locate','grid':[[1,0,1]],'color':1,'area':1})
        self.assertEqual(recompute({'kind':'locate','grid':[[1,1,0],[0,0,0]],'color':1,'area':2})['bbox'],[0,0,1,0])
    def test_malformed_wrong_and_duplicate_keys(self):
        for s in ('{}','{"color":true}','{"color":2,"color":3}','{"color":1,"extra":0}','not json','{"color":NaN}'):
            with self.assertRaises((ValueError,TypeError)):parse(s,'coordinate')
        case=next(c for c in load_cases() if c['task']['kind']=='coordinate')
        self.assertFalse(score(case,json.dumps({'color':(case['expected']['color']+1)%16}))['correct'])
    def test_omission_duplicate_and_request_drift(self):
        rows=load_cases()
        for values in (rows[:-1],rows[:-1]+[rows[0]]):
            with patch('pathlib.Path.read_bytes',return_value=json.dumps(values).encode()),self.assertRaises(ValueError):load_cases()
        values=copy.deepcopy(rows);values[0]['request']['seed']=1
        with patch('pathlib.Path.read_bytes',return_value=json.dumps(values).encode()),self.assertRaises(ValueError):load_cases()
    def test_retention_before_token_validation(self):
        class Tokenizer:
            def apply_chat_template(self,*a,**kw):return [1]*10
        retained=[]
        for request in [load_cases()[0]['request'],{'messages':[{'role':'user','content':'canary'}],'max_tokens':128}]:
            with self.assertRaises(ResponseValidationError) as caught:
                audited_completion(Tokenizer(),request,lambda _:SimpleNamespace(content='{"color":2}',prompt_tokens=11,completion_tokens=5),retain=retained.append)
            self.assertEqual(caught.exception.response_evidence['response_content'],'{"color":2}')
            self.assertEqual(retained[-1]['audit']['server_prompt_tokens'],11)
    def test_bridge_retains_mismatch(self):
        from certification.phase4_grounding_v1.bridge import BridgeServer,ModelProxy
        from certification.phase4_grounding_v1.worker import ScriptedService
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);service=ScriptedService('mismatch');server=BridgeServer(folder/'model.sock',service,time.monotonic()+10,folder/'cancel')
            thread=threading.Thread(target=server.serve_forever);thread.start()
            proxy=ModelProxy(folder,'unused',time.monotonic()+10,folder/'cancel');proxy.started=True
            try:
                with self.assertRaises(ResponseValidationError) as caught:proxy.complete(load_cases()[0]['request'])
                self.assertIn('response_sha256',caught.exception.response_evidence)
            finally:server.shutdown();thread.join(5);server.server_close()

class LifecycleTests(unittest.TestCase):
    def test_supervised_correct_incorrect_malformed_and_failed(self):
        from certification.phase4_grounding_v1.pilot import run
        from certification.phase4_grounding_v1.replay import replay
        from certification.phase4_grounding_v1.evaluate import evaluate
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ('correct','incorrect','malformed','transport','mismatch'):
                with self.subTest(mode=mode),patch.dict(os.environ,{'GROUNDING_FIXTURE_MODE':mode}):
                    output=Path(tmp)/mode;report,result=run(output,Path(tmp),mode='local',seconds=120,reserve=10)
                    self.assertEqual(result['passed'],mode in ('correct','incorrect','malformed'),result['errors'])
                    self.assertTrue(report['cleanup_verified']);self.assertTrue(report['scratch_removed'])
                    self.assertEqual(report['worker']['environment_actions'],0);self.assertEqual(report['worker']['scorecards'],0)
                    if result['passed']:
                        self.assertTrue(replay(output,live=False,seconds=120)['passed'])
                        self.assertEqual(sum(v['correct'] for v in result['comparison']['by_task'].values()),12 if mode=='correct' else 0)
                        changed=copy.deepcopy(report);changed['cleanup_verified']=False
                        self.assertFalse(evaluate(changed,live=False,seconds=120)['passed'])
                    else:self.assertEqual(report['worker']['requests_started'],1)
    def test_supervised_monitor_evidence_and_deadline_failures(self):
        from certification.phase4_grounding_v1.pilot import run
        with tempfile.TemporaryDirectory() as tmp:
            for fault in ('monitor','evidence','cancel'):
                with self.subTest(fault=fault):
                    report,result=run(Path(tmp)/fault,Path(tmp),mode='local',seconds=12,reserve=6,fault=fault)
                    self.assertFalse(result['passed']);self.assertTrue(report['cleanup_verified']);self.assertTrue(report['scratch_removed'])

if __name__=='__main__':unittest.main()
