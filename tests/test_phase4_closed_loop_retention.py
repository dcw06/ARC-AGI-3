import contextlib,hashlib,io,json,multiprocessing,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from certification.phase4_closed_loop_v1.service import audited_completion
from certification.phase4_closed_loop_v1.response_evidence import ResponseValidationError,MAX_EVIDENCE_BYTES
from certification.phase4_diagnostic_v4.cases import load_cases
from certification.phase4_closed_loop_v1.bridge import BridgeServer,ModelProxy
from certification.phase4_closed_loop_v1.worker import run_cases
from certification.phase4_closed_loop_v1.fixtures import adapter_factory
from certification.phase4_closed_loop_v1.evidence import EvidenceStore

BODY='{"action":{"action_id":6,"action_data":{"x":12,"y":34}}}'

def child_server(folder,ready):
    root=Path(folder)
    class Service:
        def complete(self,request):
            tokenizer=SimpleNamespace(apply_chat_template=lambda *a,**k:[1]*46)
            def complete(_):
                with (root/'calls').open('a') as f:f.write('1\n')
                return SimpleNamespace(content=BODY,prompt_tokens=45,completion_tokens=29)
            return audited_completion(tokenizer,request,complete)
    with (root/'received.log').open('w') as log,contextlib.redirect_stdout(log):
        with BridgeServer(root/'model.sock',Service(),time.monotonic()+20,root/'cancel') as server:
            ready.set();server.serve_forever(poll_interval=.05)

class MismatchTests(unittest.TestCase):
    def test_helper_retains_before_rejecting_each_usage_failure(self):
        tokenizer=SimpleNamespace(apply_chat_template=lambda *a,**k:[1]*46)
        for prompt,completion in ((45,29),(None,29),(46,None),(46,129),(True,29),(46,float('nan'))):
            with self.subTest(prompt=prompt,completion=completion):
                seen=[];log=io.StringIO()
                with contextlib.redirect_stdout(log),self.assertRaises(ResponseValidationError) as error:
                    audited_completion(tokenizer,load_cases()[0]['request'],
                        lambda _:SimpleNamespace(content=BODY,prompt_tokens=prompt,completion_tokens=completion),retain=seen.append)
                evidence=error.exception.response_evidence
                self.assertEqual(seen,[evidence])
                self.assertEqual(evidence['response_content'],BODY)
                self.assertEqual(evidence['response_sha256'],hashlib.sha256(BODY.encode()).hexdigest())
                self.assertEqual(evidence['audit']['tokenizer_prompt_tokens'],46)
                self.assertEqual(json.loads(log.getvalue())['diagnostic_received_response'],evidence)

    def test_oversized_body_evidence_bounded_on_mismatch(self):
        content='界'*10000
        with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(ResponseValidationError) as error:
            audited_completion(SimpleNamespace(apply_chat_template=lambda *a,**k:[1]),load_cases()[0]['request'],
                lambda _:SimpleNamespace(content=content,prompt_tokens=2,completion_tokens=29))
        evidence=error.exception.response_evidence
        self.assertLessEqual(len(evidence['response_content'].encode()),8192)
        self.assertLessEqual(len(json.dumps(evidence).encode()),MAX_EVIDENCE_BYTES)
        self.assertTrue(evidence['response_truncated']);self.assertEqual(evidence['response_bytes'],30000)
        self.assertEqual(evidence['response_sha256'],hashlib.sha256(content.encode()).hexdigest())

    def test_real_process_bridge_retains_failure_in_worker_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);context=multiprocessing.get_context('spawn');ready=context.Event()
            process=context.Process(target=child_server,args=(directory,ready));process.start()
            try:
                self.assertTrue(ready.wait(10))
                proxy=ModelProxy(root,'unused',time.monotonic()+20,root/'cancel')
                proxy.started=True;proxy.canary_audit={};proxy.artifact={};proxy.startup_seconds=0
                store=EvidenceStore(root/'output','worker')
                with self.assertRaises(ResponseValidationError):
                    run_cases(proxy,store,adapter_factory,started=time.monotonic(),deadline=time.monotonic()+15,
                        cancel=root/'cancel',live=False)
                state=json.loads((root/'output/worker/state.json').read_text())
                self.assertEqual(state['status'],'failed');self.assertEqual(state['requests_started'],1)
                row=json.loads((root/'output/worker'/state['episodes'][0]['steps'][0]).read_text())
                self.assertEqual(row['response_content'],BODY)
                self.assertEqual(row['response_sha256'],hashlib.sha256(BODY.encode()).hexdigest())
                self.assertEqual(row['audit']['server_prompt_tokens'],45)
                self.assertEqual(row['audit']['tokenizer_prompt_tokens'],46)
                self.assertEqual(row['audit']['server_completion_tokens'],29)
                self.assertEqual(row['audit']['request_sha256'],row['request_sha256'])
                self.assertEqual((root/'calls').read_text(),'1\n')
                self.assertIn('response_content',(root/'received.log').read_text())
            finally:
                process.terminate();process.join(5)
                if process.is_alive():process.kill();process.join(5)
            self.assertFalse(process.is_alive())

    def test_proxy_local_parity_failure_carries_evidence(self):
        from unittest.mock import patch
        from certification.phase4_diagnostic_v4.cases import request_hash
        request=load_cases()[0]['request']
        proxy=ModelProxy(Path('/unused'),'unused',time.monotonic()+10,Path('/unused/cancel'));proxy.started=True
        reply={'result':{'content':BODY,'prompt_tokens':46,'completion_tokens':29,'elapsed_seconds':1},
            'audit':{'request_sha256':request_hash(request),'tokenizer_prompt_tokens':45,'server_prompt_tokens':46,'server_completion_tokens':29}}
        with patch.object(proxy,'call',return_value=reply),self.assertRaises(ResponseValidationError) as error:
            proxy.complete(request)
        self.assertEqual(error.exception.response_evidence['response_content'],BODY)
        self.assertEqual(error.exception.response_evidence['audit']['bridge_result_prompt_tokens'],46)

import sys
from unittest.mock import patch
class CanaryTests(unittest.TestCase):
    def test_startup_canary_success_and_failure_evidence(self):
        from certification.phase4_closed_loop_v1.service import SharedModelService
        from certification.phase4_closed_loop_v1.model_transport import OpenAICompatibleCompletionClient
        class FakeModel:
            def __init__(self,primary):self.primary=primary
            def start(self):self._completion_canary()
        tokenizer=SimpleNamespace(apply_chat_template=lambda *a,**k:[1]*46)
        fake_transformers=SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a,**k:tokenizer))
        good='{"action":{"action_id":6,"action_data":{"x":12,"y":34}}}'
        for content,prompt,completion in ((good,46,29),(good,45,29),(good,46,None),(good,46,129),
                ('{"action":{"action_id":6,"action_data":{}}}',46,29)):
            service=SharedModelService(Path('/unused'));capture=io.StringIO()
            with patch('certification.phase4_closed_loop_v1.service.authority'), \
                 patch('certification.phase4_v6.target_install_probe_r5.MODEL_CHECK','pass'), \
                 patch('certification.phase4_closed_loop_v1.model_process.ModelService',FakeModel), \
                 patch('certification.phase4_closed_loop_v1.model_artifact.verify_artifact',return_value={}), \
                 patch('certification.phase4_closed_loop_v1.service.importlib.metadata.version',return_value='4.57.6'), \
                 patch.dict(sys.modules,{'transformers':fake_transformers}), \
                 patch.object(OpenAICompatibleCompletionClient,'complete',return_value=SimpleNamespace(content=content,prompt_tokens=prompt,completion_tokens=completion)) as call, \
                 contextlib.redirect_stdout(capture):
                if content==good and prompt==46 and completion==29:
                    service.start();self.assertEqual(service.canary_audit['status'],'passed')
                    with self.assertRaises(RuntimeError):service.service._completion_canary()
                else:
                    with self.assertRaises(RuntimeError):service.start()
                    self.assertEqual(service.canary_audit['status'],'failed')
                self.assertEqual(call.call_count,1)
            records=[json.loads(line) for line in capture.getvalue().splitlines()]
            retained=next(r['diagnostic_startup_canary'] for r in records if 'diagnostic_startup_canary' in r)
            self.assertEqual(retained['response_content'],content)
            self.assertEqual(retained['response_sha256'],hashlib.sha256(content.encode()).hexdigest())
            self.assertEqual(retained['server_prompt_tokens'],prompt)
            self.assertEqual(retained['server_completion_tokens'],completion)
            self.assertEqual(retained['tokenizer_prompt_tokens'],46)

if __name__=='__main__':unittest.main()

