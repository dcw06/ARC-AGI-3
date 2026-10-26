import copy
import hashlib
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from scripts.demo_ls20_discovery_windows_w1 import verify_bundle

ROOT=Path(__file__).parents[1]


class ReplayTests(unittest.TestCase):
    def test_both_pinned_mac_versions_replay_all_40_attempts(self):
        validator=Draft202012Validator(json.loads((ROOT/'research/ls20_discovery_windows/schema.json').read_text()))
        for suffix in ('fixed','original'):
            path=ROOT/f'reports/ls20_windows_w1_v1/trace_{suffix}.json'
            bundle=json.loads(path.read_text())
            summary=json.loads((path.parent/f'summary_{suffix}.json').read_text())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),summary['trace_sha256'])
            self.assertEqual(len(verify_bundle(bundle)),20)
            for case in bundle['cases']:
                validator.validate(case['handoff'])
                for step in case['steps']:
                    validator.validate(step['prediction'])

    def test_replacing_before_with_future_evidence_is_rejected(self):
        bundle=json.loads((ROOT/'reports/ls20_windows_w1_v1/trace_fixed.json').read_text())
        step=bundle['cases'][0]['steps'][0]
        step['before']=copy.deepcopy(step['after'])
        with self.assertRaises(ValueError): verify_bundle(bundle)

    def test_splicing_different_episodes_is_rejected(self):
        bundle=json.loads((ROOT/'reports/ls20_windows_w1_v1/trace_fixed.json').read_text())
        bundle['cases'][0]['steps'][1]['before']=copy.deepcopy(bundle['cases'][1]['steps'][0]['before'])
        with self.assertRaises(ValueError): verify_bundle(bundle)

    def test_swapping_producer_commit_is_rejected(self):
        bundle=json.loads((ROOT/'reports/ls20_windows_w1_v1/trace_fixed.json').read_text())
        bundle['m1_producer_commit']='c920f5d69ceb50239325738f9a188bb055ebdebd'
        with self.assertRaises(ValueError): verify_bundle(bundle)


if __name__=='__main__': unittest.main()
