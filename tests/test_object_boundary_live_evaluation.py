"""Independent replay regressions on synthetic evidence only."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from certification.phase4_multimodal_preflight_v3.images import png
from research.object_discovery_boundaries_v1 import live_evaluation as E, supervisor as S
from research.object_discovery_boundaries_v1.prepare import request_for
from research.object_discovery_boundaries_v1.masks import seed_masks
from research.object_identification_v1.mount_check import canonical


class Replay(unittest.TestCase):
    def setUp(self):
        self.grid=[[0]*64 for _ in range(64)];self.grid[3][2]=1
        self.image=png(self.grid,cell=7);self.request=request_for('board-01',self.image)
        self.admitted=dict(request=self.request,request_sha256=E.sha(canonical(self.request)),
                           call_number=1,admitted_at_monotonic=1)
        self.metadata={'synthetic':'processor metadata'}
        self.encoded={'metadata':self.metadata,'input_ids':[SimpleNamespace(tolist=lambda:[7,8])]}
        self.processor=SimpleNamespace(post_process_image_text_to_text=lambda *a,**k:['synthetic text'])
        self.decoded=dict(points=[{'cell_xy':[2,3]}],native_points=[[0,0,14.,21.]],point_sequence={'complete_points':1})
        self.raw=dict(request=self.request,request_sha256=E.sha(canonical(self.request)),generated_token_ids=[3,99],
            prompt_token_ids=[7,8],eos_token_ids=[99],prompt_tokens=2,completion_tokens=2,finish_reason='stop',
            raw_text_with_special_tokens='synthetic text',metadata=self.metadata,decode_valid=False,points=[],
            generation_parameters=dict(max_new_tokens=4096,do_sample=False,num_beams=1),
            generation_started_at_monotonic=2,call_deadline_monotonic=181,generated_at_monotonic=3,generation_seconds=1)
        self.detail=copy.deepcopy(self.raw)
        self.detail.update(self.decoded,decode_valid=True,case_finalized_at_monotonic=4,
            grid_sha256=self.request['grid_sha256'],objects=seed_masks(self.grid,self.decoded['points']))

    def replay(self,invalid=False):
        with patch.object(E,'decode_inventory',side_effect=ValueError('incomplete') if invalid else None,
                          return_value=self.decoded):
            return E.replay_case(self.request,self.admitted,self.detail,self.raw,None,self.processor,
                                 self.encoded,self.image,[99],1)

    def test_valid_masks_rebuilt_without_reference_access(self):
        row=self.replay();self.assertTrue(row['response_valid']);self.assertEqual(row['objects'][0]['cells'],[[2,3]])
        self.assertIsNone(row['passing_verdict'])

    def test_reported_mask_tampering_is_rejected(self):
        self.detail['objects'][0]['cells']=[[2,3],[3,3]]
        with self.assertRaisesRegex(ValueError,'pixel-mask'):self.replay()

    def test_prompts_and_admission_rebound_hash_do_not_override_frozen_request(self):
        changed=dict(self.request,prompt='human cue')
        self.detail.update(request=changed,request_sha256=E.sha(canonical(changed)))
        with self.assertRaisesRegex(ValueError,'request/admission'):self.replay()

    def test_raw_output_missing_or_changed_is_rejected(self):
        del self.raw['prompt_tokens']
        with self.assertRaisesRegex(ValueError,'incomplete or altered'):self.replay()

    def test_processor_prompt_token_mutation_is_rejected(self):
        self.detail['prompt_token_ids']=self.raw['prompt_token_ids']=[9,9]
        with self.assertRaisesRegex(ValueError,'processor'):self.replay()

    def test_strict_token_types_and_count_contract(self):
        for bad in (True,0,4097):
            with self.subTest(bad=bad):
                self.detail['completion_tokens']=self.raw['completion_tokens']=bad
                with self.assertRaises(ValueError):self.replay()

    def test_generation_parameters_cannot_be_relabelled(self):
        self.detail['generation_parameters']=self.raw['generation_parameters']={'max_new_tokens':1024,'do_sample':False,'num_beams':1}
        with self.assertRaisesRegex(ValueError,'generation contract'):self.replay()

    def test_late_finalize_refused(self):
        self.detail['case_finalized_at_monotonic']=181
        with self.assertRaisesRegex(ValueError,'bounded admission'):self.replay()

    def test_invalid_response_remains_a_case_with_zero_masks(self):
        self.detail.update(decode_valid=False,points=[],objects=[])
        row=self.replay(invalid=True)
        self.assertFalse(row['response_valid']);self.assertEqual(row['objects'],[])

    def test_decoder_claim_does_not_override_replayed_invalidity(self):
        with self.assertRaisesRegex(ValueError,'decode validity'):self.replay(invalid=True)


class Completion(unittest.TestCase):
    def test_requires_provider_witness_staging_and_bound_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'synthetic.json').write_bytes(b'{}')
            result=dict(status='provisional_complete',runtime_lock_sha256='pin',scope=S.SCOPE,generation_requests=6,
                gpu_cleanup_verified=True,temporary_environment_removed=True,
                cleanup=dict(groups_absent=True,error=None,interrupted=[]),
                datasets={k:dict(files_checked=n,all_sha256_matched=True) for k,n in {'wheelhouse':177,'model':34,'inputs':9}.items()},
                agent_input_staging=dict(files_checked=7,all_sha256_matched=True),gpu=dict(uuid='synthetic',name='RTX PRO 6000'),
                game_actions=0,scorecards=0,output_sha256={'synthetic.json':E.sha(b'{}')})
            with patch.object(S.time,'monotonic',return_value=100),patch('builtins.print') as output:S.finish(result,root,0,3300)
            marker=output.call_args.args[0];counts={'wheelhouse':177,'model':34,'inputs':9}
            self.assertTrue(E.validate_completion(root,'COMPLETE',marker,'pin',expected_files=counts))
            for status,text,pin in [('ERROR',marker,'pin'),('COMPLETE','','pin'),('COMPLETE',marker,'wrong')]:
                with self.assertRaises(ValueError):E.validate_completion(root,status,text,pin,expected_files=counts)
            with self.assertRaisesRegex(ValueError,'mounted bytes'):
                E.validate_completion(root,'COMPLETE',marker,'pin',expected_files=dict(counts,model=33))
            (root/'synthetic.json').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'manifest'):
                E.validate_completion(root,'COMPLETE',marker,'pin',expected_files=counts)


if __name__=='__main__':unittest.main()
