import copy,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from certification.phase4_perception_v1.cases import load_cases,image_part,score,request_hash
from certification.phase4_multimodal_preflight_v3.images import grid_from_png
from research.perception_v1.fixtures import build,gold
from research.perception_v1.scoring import score as geometry_score
from certification.phase4_perception_v1.worker import ScriptedService,run_cases
from certification.phase4_perception_v1.evidence import EvidenceStore
ROOT=Path(__file__).resolve().parents[1]

class PerceptionTests(unittest.TestCase):
    def test_p1_all_valid_ambiguous_transforms(self):
        case=build()[0];reference=gold(case)
        ambiguous=[r for r in case['reference']['relations'] if len(r['transforms'])>1]
        self.assertEqual(len(ambiguous),3)
        for relation in ambiguous:
            pair=(relation['a'],relation['b'])
            for transform in relation['transforms']:
                with self.subTest(pair=pair,transform=transform):
                    answer=copy.deepcopy(reference)
                    next(r for r in answer['relations'] if (r['a'],r['b'])==pair)['transform']=transform
                    result=geometry_score(case,json.dumps(answer))
                    self.assertTrue(result['valid'])
                    self.assertEqual(result['transform']['numerator'],3)
            answer=copy.deepcopy(reference)
            next(r for r in answer['relations'] if (r['a'],r['b'])==pair)['transform']='uncertain'
            result=geometry_score(case,json.dumps(answer))
            self.assertTrue(result['valid'])
            self.assertEqual(result['transform']['numerator'],2)

    def test_matched_requests_only_observation_differs(self):
        rows=load_cases();self.assertEqual(len(rows),13)
        for j,case in enumerate(build()):
            a,b=copy.deepcopy(rows[1+2*j]['request']),copy.deepcopy(rows[2+2*j]['request'])
            text=a['messages'][1]['content'].pop();image=b['messages'][1]['content'].pop()
            self.assertEqual(a,b)
            self.assertEqual(json.loads(text['text'])['grid'],case['grid'])
            self.assertEqual(grid_from_png(image_part(rows[2+2*j]['request'])),case['grid'])
            self.assertNotIn('reference',json.dumps(a));self.assertEqual(a['max_tokens'],2048)
            self.assertIn('When multiple transforms fit, report any valid transform',a['messages'][1]['content'][0]['text'])
    def run_worker(self,folder,mode='verified',clock=time.monotonic):
        start=clock()
        return run_cases(ScriptedService(mode),EvidenceStore(folder,'worker'),started=start,
            deadline=start+60,cancel=folder/'cancel',live=False,clock=clock)
    def test_correct_incorrect_partial_remain_outcomes(self):
        from certification.phase4_perception_v1.evaluate import check_row
        for mode in ('verified','incorrect','invalid'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                state=self.run_worker(Path(tmp),mode)
                self.assertEqual(state['requests_started'],13)
                for plan,row in zip(load_cases(),state['cases']):check_row(plan,row,state['preflight'])
                if mode=='invalid':self.assertFalse(state['cases'][2]['answer']['valid']);self.assertEqual(state['cases'][2]['response_content'],'{')
                if mode=='incorrect':self.assertEqual(state['cases'][1]['answer']['detection_recall']['rate'],0)
    def test_technical_stop_no_retries_and_retention(self):
        for mode in ('mismatch','transport','evidence'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp)
                with self.assertRaises(Exception):self.run_worker(folder,mode)
                state=json.loads((folder/'worker/state.json').read_bytes())
                self.assertEqual(state['requests_started'],3);self.assertEqual(state['status'],'failed')
                if mode=='mismatch':self.assertIn('response_sha256',state['cases'][-1])
                if mode=='evidence':self.assertTrue(state['cases'][-1]['response_truncated'])
    def test_cancel_and_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'cancel').touch()
            with self.assertRaises(TimeoutError):run_cases(ScriptedService(),EvidenceStore(folder/'out','worker'),
                started=time.monotonic(),deadline=time.monotonic()+60,cancel=folder/'cancel',live=False)
            self.assertEqual(json.loads((folder/'out/worker/state.json').read_bytes())['requests_started'],0)
        with tempfile.TemporaryDirectory() as tmp:
            ticks=iter([0,0,61,62])
            with self.assertRaises(TimeoutError):self.run_worker(Path(tmp),clock=lambda:next(ticks))
    def test_independent_score_and_request_mutations(self):
        from certification.phase4_perception_v1.evaluate import check_row
        with tempfile.TemporaryDirectory() as tmp:state=self.run_worker(Path(tmp))
        plan=load_cases()[1];base=state['cases'][1]
        for mutate in (lambda r:r.update(request_sha256='x'),lambda r:r['answer'].update(valid=False),
            lambda r:r['audit'].update(server_prompt_tokens=1),lambda r:r.update(response_content='{'),
            lambda r:r['audit'].update(transport_attempted=False),lambda r:r['request'].update(seed=1)):
            row=copy.deepcopy(base);mutate(row)
            with self.assertRaises(ValueError):check_row(plan,row,state['preflight'])
    def test_incomplete_pair_and_cleanup_rejected(self):
        from certification.phase4_perception_v1.pilot import run
        from certification.phase4_perception_v1.evaluate import evaluate
        from certification.phase4_perception_v1.telemetry import read_telemetry
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'out';report,result=run(folder,ROOT,mode='local',seconds=120,reserve=10)
            self.assertTrue(result['passed'],result['errors'])
            worker=json.loads((folder/'worker/state.json').read_bytes());report['worker']=worker
            report['gpu_telemetry']=read_telemetry(folder/'monitor')['samples']
            for mutate in (lambda r:r['worker']['cases'].pop(2),lambda r:r.update(cleanup_verified=False),
                           lambda r:r['worker']['cases'][2].update(started_seconds=0)):
                changed=copy.deepcopy(report);mutate(changed)
                self.assertFalse(evaluate(changed,live=False,seconds=120)['passed'])

if __name__=='__main__':unittest.main()
