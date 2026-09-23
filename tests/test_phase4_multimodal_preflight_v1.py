import copy,json,os,tempfile,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from certification.phase4_multimodal_preflight_v1 import images
from certification.phase4_multimodal_preflight_v1.cases import load_cases,image_part,text_only,request_hash
from certification.phase4_multimodal_preflight_v1.probes import parse,score,behavioural
from certification.phase4_multimodal_preflight_v1.response_evidence import ResponseValidationError

def rows():return {r['probe_id']:r for r in load_cases()}

class CaseTests(unittest.TestCase):
    def test_frozen_inventory_and_images(self):
        r=rows();self.assertEqual(list(r),['T0','I1','I2','I3'])
        self.assertIsNone(image_part(r['T0']['request']))
        for p in ('I1','I2','I3'):
            raw=image_part(r[p]['request']);self.assertEqual(images.grid_from_png(raw),r[p]['image']['grid'])
        self.assertEqual((r['I2']['image']['input_width'],r['I2']['image']['input_height']),(1024,1024))
        self.assertEqual(r['I2']['image']['provisional_arithmetic']['image_tokens'],1024)
        self.assertEqual(r['I1']['image']['provisional_arithmetic']['processed_width'],256)  # below the pixel minimum
        self.assertNotEqual(r['I2']['image']['grid'],r['I3']['image']['grid'])
        self.assertNotEqual(r['I2']['expected'],r['I3']['expected'])
        # T0/I2/I3 differ only by the image part; frozen local expectation gives the 1024+2 delta.
        self.assertEqual(text_only(r['I2']['request']),r['T0']['request'])
        self.assertEqual(r['I2']['frozen_local_expectation']['expected_prompt_tokens']-r['T0']['frozen_local_expectation']['expected_prompt_tokens'],1026)
    def test_drift_rejected(self):
        values=load_cases()
        for mutate in (lambda v:v[0]['request'].update(seed=1),lambda v:v.pop(),
                       lambda v:v[2]['request']['messages'][1]['content'][0]['image_url'].update(url=images.data_url(images.png(images_board()))),
                       lambda v:v[3]['request']['messages'][1]['content'][1].update(text='different question')):
            changed=copy.deepcopy(values);mutate(changed)
            with patch('pathlib.Path.read_bytes',return_value=json.dumps(changed).encode()),self.assertRaises(ValueError):load_cases()
    def test_resize_arithmetic(self):
        self.assertEqual(images.smart_resize(64,64),(256,256));self.assertEqual(images.smart_resize(1024,1024),(1024,1024))
        self.assertEqual(images.expected_image_tokens(2048,2048)['image_tokens'],4096)
    def test_independent_decoder_when_available(self):
        try:from PIL import Image
        except ImportError:self.skipTest('Pillow unavailable')
        import io
        raw=image_part(rows()['I3']['request']);im=Image.open(io.BytesIO(raw));grid=rows()['I3']['image']['grid']
        self.assertEqual(im.size,(1024,1024));self.assertEqual(im.getpixel((40*16+3,40*16+15)),images.PALETTE[grid[40][40]])

def images_board():
    from certification.phase4_multimodal_preflight_v1.cases import board
    return board(3,0,0)

class ProbeScoringTests(unittest.TestCase):
    def test_strict_parse(self):
        for s in ('{}','{"quadrant":"top_left"}','{"quadrant":"top_left","color":2,"color":3}','{"quadrant":"middle","color":1}',
                  '{"quadrant":"top_left","color":16}','{"quadrant":"top_left","color":NaN}','not json','{"quadrant":"top_left","color":1,"x":0}'):
            with self.assertRaises((ValueError,TypeError)):parse(s,'I2')
        with self.assertRaises(ValueError):parse('{"color":null}','I1')
    def test_score_requires_stop_and_behavioural_classes(self):
        r=rows();good=json.dumps(r['I2']['expected'])
        self.assertTrue(score(r['I2'],good,'stop')['correct']);self.assertFalse(score(r['I2'],good,'length')['valid'])
        a=score(r['I2'],good,'stop');b=score(r['I3'],json.dumps(r['I3']['expected']),'stop')
        self.assertEqual(behavioural(a,b),'answers_differ_both_correct')
        self.assertEqual(behavioural(a,score(r['I3'],good,'stop')),'identical_answers_review_required')
        self.assertEqual(behavioural(a,score(r['I3'],'{','stop')),'inconclusive_invalid_or_missing')

class FakeTokenizer:
    PAD=7
    def apply_chat_template(self,messages,tokenize=True,**kw):
        has=any(isinstance(m['content'],list) and any(p.get('type')=='image_url' for p in m['content']) for m in messages)
        ids=[1]*100+([6,self.PAD,8] if has else [])
        return ids if tokenize else 'text'
    def convert_tokens_to_ids(self,token):return self.PAD

class FakeProcessor:
    def __init__(self,full_offset=0):
        self.image_processor=SimpleNamespace(merge_size=2,patch_size=16);self.full_offset=full_offset
    def __call__(self,text,images,return_tensors):
        w,h=images[0].size;hh,ww=images_module_resize(h,w);thw=[1,hh//16,ww//16]
        n=102+thw[1]*thw[2]//4+self.full_offset
        return {'image_grid_thw':[thw],'input_ids':[[0]*n]}

def images_module_resize(h,w):return images.smart_resize(h,w)

class AuditedProbeTests(unittest.TestCase):
    def setUp(self):
        try:import PIL  # noqa: F401
        except ImportError:self.skipTest('Pillow unavailable (runs in the WSL/target environments)')
    def call(self,probe,complete,processor=FakeProcessor()):
        from certification.phase4_multimodal_preflight_v1.service import audited_probe
        return audited_probe(FakeTokenizer(),processor,rows()[probe]['request'],complete)
    def result(self,prompt):return SimpleNamespace(content='{"quadrant":"top_left","color":8}',prompt_tokens=prompt,completion_tokens=9,finish_reason='stop')
    def test_expected_counts_and_processed_geometry(self):
        _,record=self.call('I2',lambda r:self.result(102+1024))
        e=record['expectation'];self.assertEqual((e['image_grid_thw'],e['processed_width'],e['image_tokens_processor']),([1,64,64],1024,1024))
        self.assertEqual(record['finish_reason'],'stop')
        _,record=self.call('I1',lambda r:self.result(102+64));self.assertEqual(record['expectation']['processed_width'],256)
        _,record=self.call('T0',lambda r:self.result(100),processor=None);self.assertEqual(record['tokenizer_prompt_tokens'],100)
    def test_classified_failures_retain_evidence(self):
        called=[]
        with self.assertRaises(ResponseValidationError) as c:self.call('I2',called.append,processor=None)
        self.assertEqual(c.exception.response_evidence['audit']['failure_kind'],'dependency_missing');self.assertEqual(called,[])
        from certification.phase4_multimodal_preflight_v1.model_transport import ServerRejectedError
        def reject(r):raise ServerRejectedError(400,'{"error":"image input is not supported"}')
        with self.assertRaises(ResponseValidationError) as c:self.call('I2',reject)
        ev=c.exception.response_evidence;self.assertEqual((ev['audit']['failure_kind'],ev['audit']['http_status']),('image_rejected_by_server',400))
        self.assertIn('not supported',ev['response_content'])
        with self.assertRaises(ResponseValidationError) as c:self.call('I2',lambda r:self.result(102+1024+1))
        ev=c.exception.response_evidence['audit'];self.assertEqual(ev['failure_kind'],'token_accounting_mismatch')
        self.assertEqual(ev['expectation']['image_grid_thw'],[1,64,64])  # structured, not a repr string
        with self.assertRaises(ResponseValidationError) as c:self.call('I2',lambda r:self.result(0),processor=FakeProcessor(full_offset=1))
        self.assertEqual(c.exception.response_evidence['audit']['failure_kind'],'token_accounting_mismatch')

class InventoryAndTransportTests(unittest.TestCase):
    def test_mount_inventory_and_missing_processor(self):
        from certification.phase4_multimodal_preflight_v1.service import mount_inventory,load_processor,PINNED_PROCESSOR
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'config.json').write_text('{}');(root/'video_preprocessor_config.json').write_text('{}')
            inv=mount_inventory(root);self.assertEqual(inv['file_count'],2)
            self.assertFalse(inv['processor_files']['preprocessor_config.json']['present'])
            self.assertFalse(inv['processor_files']['video_preprocessor_config.json']['matches_pinned'])
            processor,status=load_processor(root,inv);self.assertIsNone(processor);self.assertIn('missing mounted file',status['error'])
            self.assertEqual(len(PINNED_PROCESSOR),2)
    def test_transport_retains_rejection_and_finish_reason(self):
        from certification.phase4_multimodal_preflight_v1.model_transport import OpenAICompatibleCompletionClient,ServerRejectedError
        session=Mock();session.post.return_value=SimpleNamespace(status_code=400,text='image input not supported')
        with self.assertRaises(ServerRejectedError) as c:OpenAICompatibleCompletionClient(session=session).complete({})
        self.assertEqual((c.exception.status,c.exception.body),(400,'image input not supported'))
        response=Mock(status_code=200);response.json.return_value={'choices':[{'message':{'content':'{}'},'finish_reason':'length'}],'usage':{'prompt_tokens':3,'completion_tokens':4}}
        session.post.return_value=response
        self.assertEqual(OpenAICompatibleCompletionClient(session=session).complete({}).finish_reason,'length')
    def test_bridge_relays_classified_evidence(self):
        from certification.phase4_multimodal_preflight_v1.bridge import BridgeServer,ModelProxy
        from certification.phase4_multimodal_preflight_v1.worker import ScriptedService
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);server=BridgeServer(folder/'model.sock',ScriptedService('rejected'),time.monotonic()+10,folder/'cancel')
            thread=threading.Thread(target=server.serve_forever);thread.start()
            proxy=ModelProxy(folder,'unused',time.monotonic()+10,folder/'cancel');proxy.started=True
            try:
                with self.assertRaises(ResponseValidationError) as c:proxy.complete(rows()['I2']['request'])
                self.assertEqual(c.exception.response_evidence['audit']['failure_kind'],'image_rejected_by_server')
            finally:server.shutdown();thread.join(5);server.server_close()

EXPECTED={'verified':('image_input_verified',True,[]),'incorrect':('image_input_verified',True,[]),
    'identical':('image_input_verified',False,['review_required_behavioural']),
    'invalid':('image_input_verified',False,['review_required_behavioural']),
    'arithmetic':('image_input_verified',False,['arithmetic_revision_required']),
    'dependency':('dependency_missing',False,[]),'rejected':('image_rejected_by_server',False,[]),
    'mismatch':('token_accounting_mismatch',False,[]),'not_consumed':('image_not_consumed',False,[])}

class LifecycleTests(unittest.TestCase):
    def test_supervised_outcome_classes(self):
        from certification.phase4_multimodal_preflight_v1.pilot import run
        from certification.phase4_multimodal_preflight_v1.replay import replay
        from certification.phase4_multimodal_preflight_v1.evaluate import evaluate
        with tempfile.TemporaryDirectory() as tmp:
            for mode,(verdict,unblocked,flags) in list(EXPECTED.items())+[('transport',('lifecycle_failure',False,[]))]:
                with self.subTest(mode=mode),patch.dict(os.environ,{'PREFLIGHT_FIXTURE_MODE':mode}):
                    output=Path(tmp)/mode;report,result=run(output,Path(tmp),mode='local',seconds=120,reserve=10)
                    self.assertTrue(report['cleanup_verified']);self.assertTrue(report['scratch_removed'])
                    self.assertEqual(report['worker']['environment_actions'],0)
                    c=result['comparison'];self.assertEqual(result['passed'],mode!='transport',result['errors'])
                    self.assertEqual((c['verdict'],c['representation_comparison_unblocked'],c['flags']),(verdict,unblocked,flags))
                    if mode=='transport':continue
                    self.assertEqual(report['worker']['requests_started'],4)  # every probe attempted
                    self.assertEqual(replay(output,live=False,seconds=120)['comparison'],c)
                    changed=copy.deepcopy(report);changed['cleanup_verified']=False
                    self.assertFalse(evaluate(changed,live=False,seconds=120)['passed'])
    def test_evaluator_rejects_inconsistent_claims(self):
        from certification.phase4_multimodal_preflight_v1.pilot import run
        from certification.phase4_multimodal_preflight_v1.evaluate import evaluate
        with tempfile.TemporaryDirectory() as tmp:
            for mode,mutate in [('dependency',lambda w:w['preflight']['processor'].update(available=True)),
                                ('verified',lambda w:w['cases'][2]['answer'].update(correct=False)),
                                ('verified',lambda w:w['cases'][2]['audit']['expectation'].update(image_tokens_processor=1)),
                                ('mismatch',lambda w:w['cases'][2]['audit'].update(server_prompt_tokens=w['cases'][2]['audit']['tokenizer_prompt_tokens']))]:
                with self.subTest(mode=mode),patch.dict(os.environ,{'PREFLIGHT_FIXTURE_MODE':mode}):
                    report,result=run(Path(tmp)/(mode+str(id(mutate))),Path(tmp),mode='local',seconds=120,reserve=10)
                    self.assertTrue(result['passed'])
                    changed=copy.deepcopy(report);mutate(changed['worker'])
                    value=evaluate(changed,live=False,seconds=120);self.assertFalse(value['passed'])
                    self.assertEqual(value['comparison']['verdict'],'lifecycle_failure')
    def test_supervised_monitor_and_deadline_failures(self):
        from certification.phase4_multimodal_preflight_v1.pilot import run
        with tempfile.TemporaryDirectory() as tmp:
            for fault in ('monitor','evidence','cancel'):
                with self.subTest(fault=fault):
                    report,result=run(Path(tmp)/fault,Path(tmp),mode='local',seconds=12,reserve=6,fault=fault)
                    self.assertFalse(result['passed']);self.assertTrue(report['cleanup_verified']);self.assertTrue(report['scratch_removed'])

if __name__=='__main__':unittest.main()
