import copy,unittest
from unittest.mock import Mock
from tests.test_phase4_multimodal_preflight_v3 import FakeTokenizer,FakeProcessor,rows
from certification.phase4_multimodal_preflight_v3.service import audited_probe
from certification.phase4_multimodal_preflight_v3.response_evidence import ResponseValidationError

class ProcessorFailureTests(unittest.TestCase):
    def test_missing_usage_is_not_a_measured_disagreement(self):
        from types import SimpleNamespace
        with self.assertRaises(ResponseValidationError) as cm:
            audited_probe(FakeTokenizer(),FakeProcessor(),rows()['I2']['request'],
                lambda _:SimpleNamespace(content='{}',prompt_tokens=None,completion_tokens=3,finish_reason='stop'))
        a=cm.exception.response_evidence['audit']
        self.assertEqual(a['failure_kind'],'usage_validation_failure');self.assertTrue(a['transport_attempted'])

    def failure(self,processor):
        complete=Mock()
        with self.assertRaises(ResponseValidationError) as cm:
            audited_probe(FakeTokenizer(),processor,rows()['I2']['request'],complete)
        complete.assert_not_called()
        return cm.exception.response_evidence

    def test_execution_failure_is_not_count_disagreement(self):
        p=Mock(side_effect=ValueError('Only returning PyTorch tensors is currently supported.'))
        evidence=self.failure(p);a=evidence['audit']
        self.assertEqual((a['failure_kind'],a['failure_stage'],a['exception_type'],a['transport_attempted']),
            ('processor_execution_failure','processor_execution','ValueError',False))
        self.assertNotIn('server_prompt_tokens',a);self.assertEqual(evidence['response_bytes'],0)

    def test_actual_offline_count_disagreement_retains_both_counts(self):
        a=self.failure(FakeProcessor(full_offset=1))['audit']
        self.assertEqual(a['failure_kind'],'token_accounting_mismatch')
        self.assertEqual(a['failure_stage'],'offline_count_comparison')
        self.assertNotEqual(a['expectation']['manual_prompt_tokens'],a['expectation']['processor_full_prompt_tokens'])

    def test_transport_failure_retains_attempt_identity(self):
        with self.assertRaises(ResponseValidationError) as cm:
            audited_probe(FakeTokenizer(),FakeProcessor(),rows()['I2']['request'],Mock(side_effect=ConnectionError('fixture')))
        a=cm.exception.response_evidence['audit']
        self.assertEqual((a['failure_stage'],a['exception_type'],a['transport_attempted']),('transport','ConnectionError',True))

    def test_evaluator_rejects_fabricated_mismatch_and_missing_provenance(self):
        from certification.phase4_multimodal_preflight_v3.evaluate import check_row
        plan=rows()['I2'];ev=self.failure(Mock(side_effect=ValueError('fixture')))
        row={'probe_id':'I2','request':plan['request'],'request_sha256':plan['request_sha256'],
            'status':'classified_failure','failure_kind':'processor_execution_failure',**ev}
        check_row(plan,row,{})
        for field,value in [('transport_attempted',True),('failure_stage','server_count_validation'),('exception_type',None)]:
            changed=copy.deepcopy(row);changed['audit'][field]=value
            with self.assertRaises(ValueError):check_row(plan,changed,{})
        changed=copy.deepcopy(row);changed['failure_kind']=changed['audit']['failure_kind']='token_accounting_mismatch'
        with self.assertRaises(ValueError):check_row(plan,changed,{})

if __name__=='__main__':unittest.main()
