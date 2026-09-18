import copy
import unittest
from certification.phase4_v14.evaluate import evaluate
from certification.phase4_v14.replay import load


class TargetReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.rows = load()

    def check_rejected(self, report):
        result = evaluate(report, self.rows)
        self.assertFalse(result['passed'])
        self.assertFalse(result['development_model_lifecycle_passed'])
        self.assertIsNone(result['capacity_candidate'])
        self.assertIsNone(result['C_admit'])

    def test_original_passes(self):
        result = evaluate(self.report, self.rows)
        self.assertTrue(result['passed'], result['errors'])
        self.assertEqual(result['capacity_candidate']['C_admit_candidate'],22358)

    def test_independent_cleanup_alone(self):
        for value in (False, None, 0, 1, 'true'):
            with self.subTest(value=value):
                self.check_rejected({**self.report,'independent_gpu_cleanup_verified':value})
        report = dict(self.report); del report['independent_gpu_cleanup_verified']
        self.check_rejected(report)

    def test_worker_bindings(self):
        for key in ('action_output_contract','policy_parent'):
            for value in ('wrong',None):
                report = {**self.report,'worker':dict(self.report['worker'])}
                if value is None: del report['worker'][key]
                else: report['worker'][key]=value
                self.check_rejected(report)

    def test_client_bindings(self):
        for index in (0,109):
            for key in ('action_output_contract','parent'):
                for value in ('wrong',None):
                    report=copy.deepcopy(self.report)
                    client=report['worker']['clients'][index]
                    if value is None: del client[key]
                    else: client[key]=value
                    self.check_rejected(report)

    def test_historical_policy_failures_remain_rejected(self):
        report=copy.deepcopy(self.report)
        report['worker']['clients'][0]['result']['policy_failures']=1
        self.check_rejected(report)


if __name__=='__main__':unittest.main()
