"""Prompt changes must agree at preparation, staging and independent replay."""
import json
import unittest

from tests.test_object_boundary_preparation import Preparation
from research.object_discovery_boundaries_v1.prepare import prepare, requests_for, PROMPT
from research.object_discovery_boundaries_v1.prompts import DETAILED_PROFILE, DETAILED_PROMPT, select_prompt
from research.object_discovery_boundaries_v1.evaluation import verified_preparation
from research.object_discovery_boundaries_v1.reference_audit import canonical, digest
from research.object_discovery_boundaries_v1.supervisor import stage_agent_inputs


class PromptProfiles(unittest.TestCase):
    def setUp(self):
        fixture=Preparation('test_inputs_have_one_generic_prompt_no_reference_metadata')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.base=fixture.base
        self.legacy=fixture.prep
        self.detailed=self.base/'detailed'
        prepare(self.base/'source',self.detailed,prompt_profile=DETAILED_PROFILE)

    def test_exact_detailed_prompt_and_4096_token_cap_on_all_six(self):
        requests=requests_for(self.detailed/'inputs',prompt_profile=DETAILED_PROFILE)
        self.assertEqual(len(requests),6)
        self.assertEqual({r['prompt'] for r in requests},{DETAILED_PROMPT})
        self.assertTrue(all(r['max_new_tokens']==4096 for r in requests))
        self.assertTrue(all(r['max_prompt_characters']==4096 for r in requests))
        self.assertTrue(DETAILED_PROMPT.startswith('Examine this pixel-based game image'))
        self.assertTrue(DETAILED_PROMPT.endswith('do not repeat the inventory or continue counting.'))
        self.assertEqual(DETAILED_PROMPT.count('\n1.'),1)
        self.assertEqual(DETAILED_PROMPT.count('\n8.'),1)
        for i in range(1,7):
            name=f'board-{i:02d}.png'
            self.assertEqual((self.detailed/'inputs'/name).read_bytes(),(self.legacy/'inputs'/name).read_bytes())

    def test_legacy_requests_are_unchanged(self):
        self.assertEqual({r['prompt'] for r in requests_for(self.legacy/'inputs')},{PROMPT})
        self.assertTrue(all('max_prompt_characters' not in r for r in requests_for(self.legacy/'inputs')))
        self.assertEqual(select_prompt('legacy_whole_v1',PROMPT),PROMPT)
        for profile in ('',None,'detailed_whole_v3'):
            with self.assertRaises(ValueError):select_prompt(profile,PROMPT)

    def test_wrong_profile_and_changed_user_instruction_refuse(self):
        with self.assertRaisesRegex(ValueError,'contract differs'):
            requests_for(self.detailed/'inputs')
        with self.assertRaisesRegex(ValueError,'contract differs'):
            requests_for(self.legacy/'inputs',prompt_profile=DETAILED_PROFILE)
        path=self.detailed/'inputs/requests.jsonl'
        rows=[json.loads(line) for line in path.read_bytes().splitlines()]
        rows[0]['prompt']+=' Also point to the blue square.'
        path.write_bytes(b''.join(canonical(r) for r in rows))
        with self.assertRaisesRegex(ValueError,'contract differs'):
            requests_for(self.detailed/'inputs',prompt_profile=DETAILED_PROFILE)

    def test_preparation_and_runtime_staging_use_bound_profile(self):
        verified_preparation(self.detailed)
        protocol=json.loads((self.detailed/'protocol.json').read_bytes())
        self.assertEqual(protocol['prompt_profile'],DETAILED_PROFILE)
        self.assertIn('research/object_discovery_boundaries_v1/prompts.py',protocol['source_sha256'])
        inputs=self.detailed/'inputs'
        rows=[dict(name=p.name,bytes=p.stat().st_size,sha256=digest(p.read_bytes())) for p in inputs.iterdir()]
        destination=self.base/'staged'
        stage_agent_inputs(inputs,destination,rows,lambda:None,prompt_profile=DETAILED_PROFILE)
        self.assertEqual(requests_for(destination,prompt_profile=DETAILED_PROFILE),
                         requests_for(inputs,prompt_profile=DETAILED_PROFILE))
        with self.assertRaisesRegex(ValueError,'contract differs'):
            stage_agent_inputs(inputs,self.base/'wrong-profile',rows,lambda:None)

    def test_exact_long_prompt_passes_actual_adapter_and_worker_wiring(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from research.object_discovery_boundaries_v1 import inference as worker
        from research.molmopoint_identification_v1.adapter import prepare_prompt_inputs
        seen=[]
        model=SimpleNamespace(config=SimpleNamespace(model_type='molmo_point'),
            build_logit_processor_from_inputs=lambda value:['native-constraint'])
        def template(messages,**options):
            seen.append(messages[0]['content'][0]['text'])
            return dict(input_ids='synthetic',metadata=dict(token_pooling='synthetic',
                subpatch_mapping='synthetic',image_sizes=[(448,448)]))
        processor=SimpleNamespace(apply_chat_template=template)
        image=SimpleNamespace(size=(448,448))
        with self.assertRaisesRegex(ValueError,'bounded pointing prompt'):
            prepare_prompt_inputs(model,processor,image,DETAILED_PROMPT)
        output=prepare_prompt_inputs(model,processor,image,DETAILED_PROMPT,max_prompt_characters=4096)
        self.assertEqual(seen,[DETAILED_PROMPT])
        self.assertEqual(output[0],{'input_ids':'synthetic'})
        for limit in (True,0,1001,4097,999999):
            with self.assertRaises(ValueError):
                prepare_prompt_inputs(model,processor,image,DETAILED_PROMPT,max_prompt_characters=limit)
        with self.assertRaisesRegex(ValueError,'bounded pointing prompt'):
            prepare_prompt_inputs(model,processor,image,'x'*4097,max_prompt_characters=4096)
        class ReachedRealAdapter(Exception):pass
        def adapter(*args,**kwargs):
            actual=prepare_prompt_inputs(*args,**kwargs)
            self.assertEqual(kwargs['max_prompt_characters'],4096)
            self.assertEqual(actual[2],['native-constraint'])
            raise ReachedRealAdapter
        request=requests_for(self.detailed/'inputs',prompt_profile=DETAILED_PROFILE)[0]
        with patch.object(worker,'prepare_prompt_inputs',side_effect=adapter):
            with self.assertRaises(ReachedRealAdapter):
                worker.native_generate(model,processor,image,request,float('inf'),None,None)

    def test_character_bound_is_frozen_with_the_new_request(self):
        path=self.detailed/'inputs/requests.jsonl'
        rows=[json.loads(line) for line in path.read_bytes().splitlines()]
        del rows[0]['max_prompt_characters']
        path.write_bytes(b''.join(canonical(r) for r in rows))
        with self.assertRaisesRegex(ValueError,'contract differs'):
            requests_for(self.detailed/'inputs',prompt_profile=DETAILED_PROFILE)


if __name__=='__main__':unittest.main()
