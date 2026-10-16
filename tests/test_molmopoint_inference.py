"""Synthetic execution/deadline contracts. No pretrained model, GPU or network."""
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from research.molmopoint_identification_v1 import inference as I, supervisor as S
from research.molmopoint_identification_v1.evaluate import validate_completion


class GenerationContract(unittest.TestCase):
    def test_nested_native_metadata_is_losslessly_json_serializable(self):
        array=SimpleNamespace(tolist=lambda:[[1,-1],[2,3]])
        raw={'token_pooling':array,'subpatch_mapping':[array],'image_sizes':[(448,448)]}
        self.assertEqual(json.loads(json.dumps(I.metadata_value(raw))),{
            'token_pooling':[[1,-1],[2,3]],'subpatch_mapping':[[[1,-1],[2,3]]],'image_sizes':[[448,448]]})

    def test_real_generation_wiring_slices_prompt_and_keeps_raw_before_decode(self):
        class Tensor:
            def __init__(self,ids): self.ids=ids
            def __getitem__(self,key): return self
            def to(self,*args): return self
            def tolist(self): return self.ids
        seen, raw = {}, []
        def generate(**kwargs):
            seen.update(kwargs)
            return SimpleNamespace(sequences=Tensor([1,2,3,70,99]))
        model = SimpleNamespace(generate=generate,generation_config=SimpleNamespace(eos_token_id=99))
        processor = SimpleNamespace(post_process_image_text_to_text=lambda *a,**k:['native-special-tokens'])
        torch = SimpleNamespace(bfloat16='bf16',inference_mode=nullcontext,
            autocast=lambda *a,**k:nullcontext(),cuda=SimpleNamespace(synchronize=lambda:None))
        inputs = {'input_ids':Tensor([1,2,3]),'image_token_pooling':Tensor([7])}
        with patch.object(I,'prepare_prompt_inputs',return_value=(inputs,{},['native'])), \
                patch.object(I,'decode_generation',side_effect=ValueError('incomplete point')):
            result=I.native_generate(model,processor,None,{'prompt':'fixed'},10**15,torch,
                ['deadline'],raw_sink=lambda row:raw.append(dict(row)))
        self.assertEqual(result['generated_token_ids'],[70,99])
        self.assertFalse(result['decode_valid'])
        self.assertIn('incomplete point',result['decode_error'])
        self.assertEqual(len(raw),1)
        self.assertNotIn('decode_error',raw[0])
        self.assertEqual(seen['logits_processor'],['native'])
        self.assertEqual(seen['stopping_criteria'],['deadline'])
        self.assertEqual((seen['max_new_tokens'],seen['do_sample'],seen['num_beams']),(1024,False,1))

    def requests(self):
        return [{'case_id':f'board-{i:02d}'} for i in range(1,7)]

    def test_one_generation_each_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'calls'
            calls=[]
            result=I.execute_cases(self.requests(),lambda r,d:calls.append(r) or {'raw':'kept'},out,1000,now=lambda:0)
            self.assertEqual(len(calls),6)
            self.assertEqual(result['generation_requests'],6)
            self.assertEqual(len(list(out.glob('*-admission.json'))),6)
            with self.assertRaises(FileExistsError):
                I.execute_cases(self.requests(),lambda *a:None,out,1000,now=lambda:0)
            self.assertEqual(len(calls),6)

    def test_reject_wrong_count_before_any_call(self):
        for n in (0,5,7):
            with self.assertRaises(ValueError):
                I.execute_cases([{}]*n,lambda *a:self.fail('generation occurred'),'unused',1000)

    def test_admission_closes_during_fsync(self):
        times=iter([0,0,900,900])
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(TimeoutError):
            I.execute_cases(self.requests(),lambda *a:self.fail('late generation'),Path(tmp)/'calls',1000,now=lambda:next(times))

    def test_failed_generation_never_retries_and_admission_remains(self):
        calls=[]
        def fail(*a):
            calls.append(1)
            raise TimeoutError('generation stuck')
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'calls'
            with self.assertRaises(TimeoutError):
                I.execute_cases(self.requests(),fail,out,1000,now=lambda:0)
            self.assertEqual(calls,[1])
            self.assertTrue((out/'board-01-admission.json').exists())
            self.assertFalse((out/'worker.json').exists())


class Lifecycle(unittest.TestCase):
    def test_generated_namespace_roots_must_be_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            name='reviewed-source/research/__init__.py'
            target=root/name
            target.parent.mkdir(parents=True)
            for raw,valid in ((b'',True),(b'unreviewed root code',False)):
                target.write_bytes(raw)
                (root/'runtime-lock.json').write_text(json.dumps({'artifacts':{name:I.sha(raw)}}))
                if valid:
                    S.verify_packet(root)
                else:
                    with self.assertRaisesRegex(ValueError,'executing checkout'):
                        S.verify_packet(root)

    def test_reviewed_runtime_cannot_be_run_from_a_different_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            name='reviewed-source/research/molmopoint_identification_v1/supervisor.py'
            path=root/name
            path.parent.mkdir(parents=True)
            path.write_bytes(b'not the executing source')
            (root/'runtime-lock.json').write_text(json.dumps({'artifacts':{name:I.sha(path.read_bytes())}}))
            with self.assertRaisesRegex(ValueError,'executing checkout'):
                S.verify_packet(root)

    def test_completion_requires_provider_witness_and_unchanged_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'synthetic-data.json').write_bytes(b'{}')
            result=dict(status='provisional_complete',runtime_lock_sha256='pin',scope=S.SCOPE,
                generation_requests=6,gpu_cleanup_verified=True,temporary_environment_removed=True,
                cleanup=dict(groups_absent=True,error=None,interrupted=[]),
                datasets={k:dict(files_checked=n,all_sha256_matched=True)
                          for k,n in {'wheelhouse':177,'model':33,'inputs':9}.items()},
                gpu={'uuid':'synthetic-uuid','name':'RTX PRO 6000'},game_actions=0,scorecards=0,
                output_sha256={'synthetic-data.json':I.sha(b'{}')})
            with patch.object(S.time,'monotonic',return_value=100),patch('builtins.print') as output:
                S.finish(result,root,0,3300)
            marker=output.call_args.args[0]
            self.assertTrue(validate_completion(root,'COMPLETE',marker,'pin'))
            with self.assertRaisesRegex(ValueError,'mounted bytes'):
                validate_completion(root,'COMPLETE',marker,'pin',
                    expected_files={'wheelhouse':177,'model':34,'inputs':9})
            self.assertTrue(validate_completion(root,'COMPLETE',marker,'pin',
                expected_files={'wheelhouse':177,'model':33,'inputs':9}))
            for status,stdout,pin in [('ERROR',marker,'pin'),('COMPLETE','','pin'),('COMPLETE',marker,'other')]:
                with self.assertRaises(ValueError):
                    validate_completion(root,status,stdout,pin)
            (root/'synthetic-data.json').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'output files'):
                validate_completion(root,'COMPLETE',marker,'pin')

    def test_scope_is_six_1024_tokens_and_no_authority_is_refused(self):
        self.assertEqual(S.SCOPE['generation_requests'],6)
        self.assertEqual(S.SCOPE['max_tokens_per_generation'],1024)
        self.assertEqual(S.SCOPE['max_generated_tokens'],6144)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'review-lock.json').write_text('{"artifacts":{}}')
            (root/'protocol.json').write_text(json.dumps({'scope':S.SCOPE,'live_runs_enabled':False}))
            with patch.object(S,'_execute',side_effect=AssertionError('GPU started')):
                with self.assertRaisesRegex(SystemExit,'REVIEW ONLY'):
                    S.run(root)

    def test_receipt_write_overrun_leaves_no_completion_witness(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(S.time,'monotonic',side_effect=[59.9,60.1]):
            with self.assertRaises(RuntimeError):
                S.finish({'status':'provisional_complete'},tmp,0,60)
            self.assertTrue((Path(tmp)/'result.json').exists())
            self.assertFalse((Path(tmp)/'completion-witness.json').exists())
            with self.assertRaises(FileNotFoundError):
                validate_completion(tmp,'COMPLETE','anything','pin')

    def test_post_write_interruption_cannot_certify(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(S.time,'monotonic',side_effect=[59.9,KeyboardInterrupt()]):
                with self.assertRaises(KeyboardInterrupt):
                    S.finish({'status':'provisional_complete'},tmp,0,60)
            with self.assertRaises(FileNotFoundError):
                validate_completion(tmp,'COMPLETE','anything','pin')


if __name__=='__main__':
    unittest.main()
