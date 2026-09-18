import hashlib
import json
import unittest
from unittest.mock import patch
from agent.e1_policy import E1Policy, CompletionResult, _strict_object
from certification.phase4_v11.policy_evidence import PolicyEvidence, ObservedPolicy


class PolicyEvidenceTests(unittest.TestCase):
    def test_real_parser_exception_retained_and_reraised(self):
        evidence=PolicyEvidence('client')
        policy=object.__new__(ObservedPolicy);policy.evidence=evidence
        def propose(_):
            evidence.received({'messages':[]},CompletionResult('```json\n{}\n```'), 'request-1')
            return _strict_object('```json\n{}\n```')
        with patch.object(E1Policy,'propose',side_effect=propose):
            with self.assertRaisesRegex(ValueError,'strict JSON'):policy.propose(None)
        row=evidence.summary()['examples'][0]
        self.assertEqual(row['category'],'malformed_json')
        self.assertEqual(row['completion']['request_id'],'request-1')
        self.assertEqual(row['completion']['request_sha256'],hashlib.sha256(json.dumps({'messages':[]},sort_keys=True).encode()).hexdigest())

    def test_success_identity_and_stale_response_reset(self):
        evidence=PolicyEvidence('client');policy=object.__new__(ObservedPolicy);policy.evidence=evidence
        evidence.received({},CompletionResult('old'), 'old-request')
        sentinel=object()
        with patch.object(E1Policy,'propose',return_value=sentinel):self.assertIs(policy.propose(None),sentinel)
        self.assertIsNone(evidence.last)
        exc=ValueError('action is not currently legal')
        with patch.object(E1Policy,'propose',side_effect=exc):
            with self.assertRaises(ValueError) as caught:policy.propose(None)
        self.assertIs(caught.exception,exc)
        self.assertEqual(evidence.summary()['examples'][0]['category'],'illegal_action')
        self.assertIsNone(evidence.summary()['examples'][0]['completion'])

    def test_bounds_counts_and_hash_of_full_response(self):
        evidence=PolicyEvidence('client');text='x'*10000
        for i in range(80):
            evidence.begin();evidence.received({},CompletionResult(text),'request-'+str(i))
            evidence.rejected(ValueError('ACTION6 coordinate invalid'))
        result=evidence.summary()
        self.assertEqual(result['policy_failures'],80)
        self.assertEqual(result['categories'],{'invalid_action_data':80})
        self.assertEqual(len(result['examples']),8)
        self.assertEqual(result['examples_omitted'],72)
        sample=result['examples'][0]['completion']
        self.assertEqual(len(sample['response_prefix']),1024)
        self.assertTrue(sample['response_truncated'])
        self.assertEqual(sample['response_sha256'],hashlib.sha256(text.encode()).hexdigest())
        self.assertLess(len(json.dumps(result).encode()),16000)

    def test_bad_completion_diagnostics_do_not_raise(self):
        evidence=PolicyEvidence('client');evidence.received({},None,'request')
        self.assertEqual(evidence.last['invalid_completion_type'],'NoneType')
