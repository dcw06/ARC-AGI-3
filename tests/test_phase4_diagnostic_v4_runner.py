import copy,hashlib,json,subprocess,sys,tempfile,time,unittest
import contextlib,io
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from certification.phase4_diagnostic_v4.worker import run_cases,ScriptedService
from certification.phase4_diagnostic_v4.cases import load_cases
from certification.phase4_diagnostic_v4.pilot import run
from certification.phase4_diagnostic_v4.evaluate import evaluate,evaluate_local_smoke
from certification.phase4_diagnostic_v4.build_notebook import build
from certification.phase4_diagnostic_v4.authority import require

ROOT=Path(__file__).resolve().parents[1]

class Store:
    def __init__(self):self.values={}
    def save(self,name,value):self.values[name]=copy.deepcopy(value)

class RunnerTests(unittest.TestCase):
    def worker(self,service=None,clock=lambda:1):
        store=Store();service=service or ScriptedService()
        with tempfile.TemporaryDirectory() as tmp:
            state=run_cases(service,store,started=0,deadline=100,cancel=Path(tmp)/'cancel',live=False,clock=clock)
        return state,store

    def test_exact_inventory_and_raw_evidence(self):
        state,store=self.worker()
        self.assertEqual(state['requests_started'],45)
        self.assertEqual(len(state['cases']),45)
        self.assertEqual(state['environment_actions'],0)
        self.assertEqual(state['scorecards'],0)
        for row,case in zip(state['cases'],load_cases()):
            self.assertEqual(row['request_sha256'],case['request_sha256'])
            self.assertEqual(row['response_sha256'],hashlib.sha256(row['response_content'].encode()).hexdigest())

    def test_transport_error_not_retried(self):
        service=ScriptedService();store=Store()
        with tempfile.TemporaryDirectory() as tmp,patch.object(service,'complete',side_effect=RuntimeError('HTTP error')) as call:
            with self.assertRaises(RuntimeError):run_cases(service,store,started=0,deadline=10,cancel=Path(tmp)/'c',live=False,clock=lambda:1)
        self.assertEqual(call.call_count,1)
        self.assertEqual(store.values['state.json']['requests_started'],1)

    def test_invalid_output_retained_before_abort(self):
        service=ScriptedService();original=service.complete;store=Store()
        def bad(request):
            result=original(request);result.content='{"action":{"action_id":6,"action_data":{}}}';return result
        with tempfile.TemporaryDirectory() as tmp,patch.object(service,'complete',side_effect=bad) as call:
            with self.assertRaises(ValueError):run_cases(service,store,started=0,deadline=10,cancel=Path(tmp)/'c',live=False,clock=lambda:1)
        self.assertEqual(call.call_count,1)
        self.assertIn('response_content',store.values['state.json']['cases'][0])

    def test_cancel_and_expired_start_do_not_call_model(self):
        for cancel in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'cancel'
                if cancel:path.touch()
                service=ScriptedService()
                with patch.object(service,'complete') as call,self.assertRaises(TimeoutError):
                    run_cases(service,Store(),started=0,deadline=1,cancel=path,live=False,clock=lambda:1)
                call.assert_not_called()

    def test_late_completion_retained_and_rejected(self):
        times=iter([0,0,0,11,11,11]);store=Store();service=ScriptedService()
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(TimeoutError):
            run_cases(service,store,started=0,deadline=10,cancel=Path(tmp)/'c',live=False,clock=lambda:next(times))
        self.assertEqual(len(service.audit_records),1)
        self.assertIn('response_content',store.values['state.json']['cases'][0])

    def test_oversized_response_bounded_and_rejected(self):
        service=ScriptedService();original=service.complete;store=Store()
        def bad(request):
            result=original(request);result.content='x'*9000;return result
        with tempfile.TemporaryDirectory() as tmp,patch.object(service,'complete',side_effect=bad),self.assertRaises(ValueError):
            run_cases(service,store,started=0,deadline=10,cancel=Path(tmp)/'c',live=False,clock=lambda:1)
        row=store.values['state.json']['cases'][0]
        self.assertEqual(len(row['response_content']),8192);self.assertTrue(row['response_truncated'])

    def test_live_authority_closed_before_output(self):
        with tempfile.TemporaryDirectory() as tmp,patch('subprocess.Popen') as launch:
            output=Path(tmp)/'out'
            with self.assertRaises(PermissionError):run(output,tmp,mode='live',seconds=3300,reserve=300)
            self.assertFalse(output.exists());launch.assert_not_called()

    def test_model_side_count_and_request_allowlist(self):
        from certification.phase4_diagnostic_v4.service import SharedModelService
        service=SharedModelService(Path('/unused'));service.diagnostic_calls=45;service.started=True
        with patch('requests.Session') as session,self.assertRaises(ValueError):
            service.complete(load_cases()[0]['request'])
        session.assert_not_called()
        service.diagnostic_calls=0
        request=copy.deepcopy(load_cases()[0]['request']);request['max_tokens']=129
        with patch('requests.Session') as session,self.assertRaises(ValueError):service.complete(request)
        session.assert_not_called()

    def test_startup_canary_success_and_failure_evidence(self):
        from certification.phase4_diagnostic_v4.service import SharedModelService
        from certification.phase4_diagnostic_v4.model_transport import OpenAICompatibleCompletionClient
        class FakeModel:
            def __init__(self,primary):self.primary=primary
            def start(self):self._completion_canary()
        tokenizer=SimpleNamespace(apply_chat_template=lambda *a,**k:[1]*46)
        fake_transformers=SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a,**k:tokenizer))
        good='{"action":{"action_id":6,"action_data":{"x":12,"y":34}}}'
        for content,prompt,completion in ((good,46,29),(good,45,29),(good,46,None),(good,46,129),
                ('{"action":{"action_id":6,"action_data":{}}}',46,29)):
            service=SharedModelService(Path('/unused'));capture=io.StringIO()
            with patch('certification.phase4_diagnostic_v4.service.authority'), \
                 patch('certification.phase4_v6.target_install_probe_r5.MODEL_CHECK','pass'), \
                 patch('certification.phase4_diagnostic_v4.model_process.ModelService',FakeModel), \
                 patch('certification.phase4_diagnostic_v4.model_artifact.verify_artifact',return_value={}), \
                 patch('certification.phase4_diagnostic_v4.service.importlib.metadata.version',return_value='4.57.6'), \
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
    def test_separate_diagnostic_authority_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'certification/phase4_diagnostic_v4';folder.mkdir(parents=True)
            (folder/'protocol.json').write_text('{}')
            (root/'reports').mkdir();(root/'reports/phase4_action_selection_probe_proposal.json').write_text('{}')
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            put=lambda p,v:p.write_text(json.dumps(v))
            review=root/'review.json'
            put(review,{'bindings':{p.relative_to(root).as_posix():sha(p) for p in
                [folder/'protocol.json',root/'reports/phase4_action_selection_probe_proposal.json']}})
            put(root/'source.json',{'status':'approved','review_lock_sha256':sha(review)})
            compute={'scope':'phase4-action-diagnostic-v4','authorized_seconds':3600,'maximum_attempts':1,
                'automatic_retries':0,'maximum_total_completions':46,'source_approval_reference':'source.json'}
            put(root/'compute.json',compute)
            put(folder/'execution_lock.json',{'review_lock':'review.json','review_sha256':sha(review),
                'source_approval_reference':'source.json','attempt_id':'test'})
            put(folder/'compute_ledger.json',{'authorized_seconds':3600,'maximum_attempts':1,
                'attempt_id':'test','approval_reference':'compute.json','events':[
                    {'kind':'reserve','seconds':3600,'execution_lock_sha256':sha(folder/'execution_lock.json')},
                    {'kind':'launch_request_started','attempt_id':'test'}]})
            self.assertEqual(require(root)['attempt_id'],'test')
            for field,value in [('authorized_seconds',28800),('maximum_total_completions',47),('automatic_retries',1),('scope','full-pilot')]:
                put(root/'compute.json',{**compute,field:value})
                with self.assertRaises(PermissionError):require(root)

    def test_final_receipt_requires_cleanup_and_deadline(self):
        from certification.phase4_diagnostic_v4.finalize import finalize
        from certification.phase4_diagnostic_v4.evidence import EvidenceStore
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            EvidenceStore(out,'evaluation').save('result.json',{'passed':True})
            EvidenceStore(out,'control').save('notebook-cost.json',{'error':None,'dependency_trees_removed':False})
            with patch('certification.phase4_diagnostic_v4.finalize.time.monotonic',return_value=100),self.assertRaises(RuntimeError):finalize(out,0,True)
            EvidenceStore(out,'control').save('notebook-cost.json',{'error':None,'dependency_trees_removed':True})
            with patch('certification.phase4_diagnostic_v4.finalize.time.monotonic',return_value=3300),self.assertRaises(RuntimeError):finalize(out,0,True)
            with patch('certification.phase4_diagnostic_v4.finalize.time.monotonic',return_value=100):self.assertTrue(finalize(out,0,True)['passed'])

    def test_disabled_notebook_rejects_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'review';lock=build(folder)
            self.assertIn('reports/phase4_action_selection_probe_proposal.json',lock['bindings'])
            self.assertFalse(json.loads((folder/'kernel-metadata.json').read_text())['enable_gpu'])
            code=json.loads((folder/'profile.ipynb').read_text())['cells'][1]['source']
            script=Path(tmp)/'review.py';script.write_text(code)
            result=subprocess.run([sys.executable,'-I',str(script)],capture_output=True,text=True,timeout=40)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('diagnostic requires approved source lock',result.stderr)

    def test_integrated_cpu_and_direct_cleanup_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            report,result=run(Path(tmp)/'out',tmp,seconds=60,reserve=10)
            self.assertTrue(result['passed'],result)
            self.assertFalse(result['model_inference'])
            self.assertEqual(report['worker']['requests_started'],45)
            self.assertIsNone(result['capacity_candidate'])
            # No synthetic supervisor error: the live evaluator must reject missing independent cleanup itself.
            changed=copy.deepcopy(report);changed['independent_gpu_cleanup_verified']=False
            self.assertIn('independent_gpu_cleanup_verified',evaluate(changed)['errors'])
            changed=copy.deepcopy(report);changed['worker']['cases'][0]['request_sha256']='wrong'
            self.assertFalse(evaluate_local_smoke(changed,seconds=60)['passed'])
            changed=copy.deepcopy(report);changed['worker']['cases'].pop()
            self.assertFalse(evaluate_local_smoke(changed,seconds=60)['passed'])
            changed=copy.deepcopy(report);changed['worker']['cases'][0]['response_content']='{}'
            self.assertFalse(evaluate_local_smoke(changed,seconds=60)['passed'])
            self.assertEqual(result['comparison']['arms']['baseline']['cases'],15)
            live=copy.deepcopy(report)
            live.update(resource_evidence_class='live_resource_monitor',gpu_cleanup_verified=True,
                independent_gpu_cleanup_verified=True)
            live['worker']['model_inference']=True
            content='{"action":{"action_id":6,"action_data":{"x":12,"y":34}}}'
            live['worker']['canary_audit']={'status':'passed','action_contract':'arc_action_v12',
                'request_sha256':'06853cc44e570cebee4b4623655b73c43072ee040d025e87e47696b3e15fac38',
                'server_prompt_tokens':46,'tokenizer_prompt_tokens':46,'server_completion_tokens':29,
                'service_seconds':1,'response_content':content,'response_sha256':hashlib.sha256(content.encode()).hexdigest()}
            live['worker']['model_artifact']={'tree_sha256':'052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627'}
            self.assertTrue(evaluate(live)['passed'],evaluate(live))
            live['worker']['canary_audit']['response_content']='{}'
            self.assertFalse(evaluate(live)['passed'])

    def test_fault_cleanup(self):
        for fault in ('worker','monitor','evidence','cancel'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as tmp:
                report,result=run(Path(tmp)/'out',tmp,seconds=9,reserve=6,fault=fault)
                self.assertFalse(result['passed'])
                self.assertTrue(report['cleanup_verified'])
                self.assertTrue(report['scratch_removed'])

if __name__=='__main__':unittest.main()
