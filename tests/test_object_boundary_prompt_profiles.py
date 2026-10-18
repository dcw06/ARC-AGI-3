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
        self.assertTrue(DETAILED_PROMPT.startswith('Examine this pixel-based game image'))
        self.assertTrue(DETAILED_PROMPT.endswith('do not repeat the inventory or continue counting.'))
        self.assertEqual(DETAILED_PROMPT.count('\n1.'),1)
        self.assertEqual(DETAILED_PROMPT.count('\n8.'),1)
        for i in range(1,7):
            name=f'board-{i:02d}.png'
            self.assertEqual((self.detailed/'inputs'/name).read_bytes(),(self.legacy/'inputs'/name).read_bytes())

    def test_legacy_requests_are_unchanged(self):
        self.assertEqual({r['prompt'] for r in requests_for(self.legacy/'inputs')},{PROMPT})
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


if __name__=='__main__':unittest.main()
