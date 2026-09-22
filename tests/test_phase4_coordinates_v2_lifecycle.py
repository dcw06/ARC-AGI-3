import copy,json,os,tempfile,threading,time,unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from certification.phase4_coordinates_v2.answers import score
from certification.phase4_coordinates_v2.cases import load_cases
from certification.phase4_coordinates_v2.service import audited_completion
from certification.phase4_coordinates_v2.response_evidence import ResponseValidationError

class LifecycleTests(unittest.TestCase):
    def test_supervised_correct_incorrect_malformed_and_failed(self):
        from certification.phase4_coordinates_v2.pilot import run
        from certification.phase4_coordinates_v2.replay import replay
        from certification.phase4_coordinates_v2.evaluate import evaluate
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ('correct','transposed','other','malformed','transport','mismatch'):
                with self.subTest(mode=mode),patch.dict(os.environ,{'GROUNDING_FIXTURE_MODE':mode}):
                    output=Path(tmp)/mode;report,result=run(output,Path(tmp),mode='local',seconds=120,reserve=10)
                    self.assertEqual(result['passed'],mode in ('correct','transposed','other','malformed'),result['errors'])
                    self.assertTrue(report['cleanup_verified']);self.assertTrue(report['scratch_removed'])
                    self.assertEqual(report['worker']['environment_actions'],0);self.assertEqual(report['worker']['scorecards'],0)
                    if result['passed']:
                        self.assertTrue(replay(output,live=False,seconds=120)['passed'])
                        self.assertEqual(sum(v.get('correct',0) for v in result['comparison']['by_condition'].values()),56 if mode=='correct' else 0)
                        changed=copy.deepcopy(report);changed['cleanup_verified']=False
                        self.assertFalse(evaluate(changed,live=False,seconds=120)['passed'])
                    else:self.assertEqual(report['worker']['requests_started'],1)
    def test_supervised_monitor_evidence_and_deadline_failures(self):
        from certification.phase4_coordinates_v2.pilot import run
        with tempfile.TemporaryDirectory() as tmp:
            for fault in ('monitor','evidence','cancel'):
                with self.subTest(fault=fault):
                    report,result=run(Path(tmp)/fault,Path(tmp),mode='local',seconds=12,reserve=6,fault=fault)
                    self.assertFalse(result['passed']);self.assertTrue(report['cleanup_verified']);self.assertTrue(report['scratch_removed'])

if __name__=='__main__':unittest.main()

class RetentionTests(unittest.TestCase):
    def test_late_response_retained_and_rejected(self):
        from certification.phase4_coordinates_v2.worker import run_cases,ScriptedService
        clock=[0];records={}
        class Store:
            def save(self,name,value):records[name]=copy.deepcopy(value)
        service=ScriptedService();complete=service.complete
        def late(request):
            result=complete(request);clock[0]=101;return result
        service.complete=late
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(TimeoutError):
            run_cases(service,Store(),started=0,deadline=100,cancel=Path(tmp)/'cancel',live=False,clock=lambda:clock[0])
        row=records['state.json']['cases'][0]
        self.assertIn('response_content',row);self.assertEqual(row['status'],'failed')
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
        from certification.phase4_coordinates_v2.bridge import BridgeServer,ModelProxy
        from certification.phase4_coordinates_v2.worker import ScriptedService
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);service=ScriptedService('mismatch');server=BridgeServer(folder/'model.sock',service,time.monotonic()+10,folder/'cancel')
            thread=threading.Thread(target=server.serve_forever);thread.start()
            proxy=ModelProxy(folder,'unused',time.monotonic()+10,folder/'cancel');proxy.started=True
            try:
                with self.assertRaises(ResponseValidationError) as caught:proxy.complete(load_cases()[0]['request'])
                self.assertIn('response_sha256',caught.exception.response_evidence)
            finally:server.shutdown();thread.join(5);server.server_close()
