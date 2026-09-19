import contextlib,hashlib,io,json,multiprocessing,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from certification.phase4_diagnostic_v2.service import audited_completion
from certification.phase4_diagnostic_v2.response_evidence import ResponseValidationError,MAX_EVIDENCE_BYTES
from certification.phase4_diagnostic_v2.cases import load_cases
from certification.phase4_diagnostic_v2.bridge import BridgeServer,ModelProxy
from certification.phase4_diagnostic_v2.worker import run_cases
from certification.phase4_diagnostic_v2.evidence import EvidenceStore

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
                    run_cases(proxy,store,started=time.monotonic(),deadline=time.monotonic()+15,
                        cancel=root/'cancel',live=False)
                state=json.loads((root/'output/worker/state.json').read_text())
                self.assertEqual(state['status'],'failed');self.assertEqual(state['requests_started'],1)
                row=state['cases'][0]
                self.assertEqual(row['response_content'],BODY)
                self.assertEqual(row['response_sha256'],hashlib.sha256(BODY.encode()).hexdigest())
                self.assertEqual(row['audit']['server_prompt_tokens'],45)
                self.assertEqual(row['audit']['tokenizer_prompt_tokens'],46)
                self.assertEqual(row['audit']['server_completion_tokens'],29)
                self.assertTrue(row['received_evidence_request_matches'])
                self.assertEqual((root/'calls').read_text(),'1\n')
                self.assertIn('response_content',(root/'received.log').read_text())
            finally:
                process.terminate();process.join(5)
                if process.is_alive():process.kill();process.join(5)
            self.assertFalse(process.is_alive())

    def test_proxy_local_parity_failure_carries_evidence(self):
        from unittest.mock import patch
        from certification.phase4_diagnostic_v2.cases import request_hash
        request=load_cases()[0]['request']
        proxy=ModelProxy(Path('/unused'),'unused',time.monotonic()+10,Path('/unused/cancel'));proxy.started=True
        reply={'result':{'content':BODY,'prompt_tokens':46,'completion_tokens':29,'elapsed_seconds':1},
            'audit':{'request_sha256':request_hash(request),'tokenizer_prompt_tokens':45,'server_prompt_tokens':46,'server_completion_tokens':29}}
        with patch.object(proxy,'call',return_value=reply),self.assertRaises(ResponseValidationError) as error:
            proxy.complete(request)
        self.assertEqual(error.exception.response_evidence['response_content'],BODY)
        self.assertEqual(error.exception.response_evidence['audit']['bridge_result_prompt_tokens'],46)

if __name__=='__main__':unittest.main()
