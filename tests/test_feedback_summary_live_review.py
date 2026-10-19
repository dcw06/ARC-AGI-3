"""Additional 81-request scientific separation and authority regressions."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.initial_geometry_assistance_v1.geometry import digest
from research.feedback_summary_probe_live_v1.live_evaluation import audit_study
from research.feedback_summary_probe_live_v1.live_runtime import SCOPE,check_authority
from research.feedback_summary_probe_v1.interface import recognition_request
from tests.feedback_summary_live_fixture import create,protocol_patches
from tests.test_feedback_probe_audit_v1 import ScriptEngine
import tests.test_feedback_summary_live_operator as operator_checks


class LiveReviewChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.inputs,cls.output,_=create(cls.folder.name,invalid_recognition=True)

    def audit(self,output):
        with ExitStack() as stack:
            protocol_patches(stack)
            return audit_study(output,self.inputs,token_audit=lambda _:100,
                               replay_factory=lambda cp,variant:ScriptEngine(cp))

    def test_invalid_recognition_never_gates_or_coaches_policy(self):
        result=self.audit(self.output)
        self.assertEqual(result['generations'],81)
        self.assertEqual(result['recognition_generations'],16)
        self.assertEqual(result['policy_generations'],64)
        self.assertEqual(result['continuation_dispatches'],64)
        self.assertTrue(all(not row['score']['valid'] for row in result['recognition']))
        self.assertTrue(all(not row['score']['all_fields_correct'] for row in result['recognition']))
        self.assertEqual({row['variant'] for row in result['recognition']},{'recent_raw','recent_summary'})

    def test_old_73_request_authority_is_not_relabelled_as_81(self):
        pin,authority,_,_=operator_checks.ProbeOperatorChecks.fixture()
        check_authority(authority,pin)
        authority['scope']=dict(SCOPE,generations=73,counted_HTTP_requests=73,recognition_generations=8)
        with self.assertRaises(PermissionError):check_authority(authority,pin)
        authority['scope']=dict(SCOPE)
        authority['proofs']['compute_authorization']['scope']=dict(SCOPE,generations=73)
        authority['compute_authorization']=digest(authority['proofs']['compute_authorization'])
        with self.assertRaises(PermissionError):check_authority(authority,pin)

    def test_recognition_expected_summary_is_independently_checked(self):
        def wrong(base,variant):
            body=recognition_request(base,variant)
            if variant=='recent_summary':
                part=body['messages'][1]['content'][-2]
                value=json.loads(part['text'])
                value['transitions'][-1]['changed_cell_count']+=1
                part['text']=json.dumps(value,sort_keys=True,separators=(',',':'))
            return body
        with patch('research.feedback_summary_probe_live_v1.live_evaluation.recognition_request',side_effect=wrong):
            with self.assertRaisesRegex(ValueError,'summary differs'):
                self.audit(self.output)


if __name__=='__main__':unittest.main()
