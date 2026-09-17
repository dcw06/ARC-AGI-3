import copy
import json
import math
from pathlib import Path
import unittest
import zipfile

from certification.phase4_v1.lifecycle import validate_freeze
from certification.phase4_v6.evaluate import evaluate_local_smoke
from certification.phase4_v6.pilot import run


class LocalSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        with zipfile.ZipFile(root/'evidence/phase4-v3-terminal-lifecycle-evidence-portable.zip') as archive:
            cls.template = json.loads(archive.read('run/supervisor.json'))
        _, cls.rows = validate_freeze()

    def report(self):
        report = copy.deepcopy(self.template)
        report.update(scope='local_development_pilot', elapsed_seconds=120, lifecycle_seconds=300)
        return report

    def test_local_pass_preserves_failed_historical_timing_verdict(self):
        report = self.report()
        result = evaluate_local_smoke(report, self.rows)
        self.assertTrue(result['passed'], result['errors'])
        self.assertFalse(result['historical_v3_evaluation']['passed'])
        self.assertEqual(result['historical_v3_evaluation']['errors'],
                         ['resource limit/evidence: elapsed_seconds'])
        self.assertEqual(report['elapsed_seconds'], 120)
        self.assertFalse(result['target_gpu_certified'])
        self.assertFalse(result['phase4_complete'])

    def test_invalid_or_exhausted_deadline_rejected(self):
        for seconds, elapsed in [(300, 300), (300, -1), (300, math.nan),
                                 (300, math.inf), (300, True), (301, 120),
                                 (math.inf, 120), (True, 0), (60, 60)]:
            with self.subTest(seconds=seconds, elapsed=elapsed):
                report = self.report()
                report['elapsed_seconds'] = elapsed
                result = evaluate_local_smoke(report, self.rows, seconds=seconds)
                self.assertFalse(result['passed'])
                self.assertIn('local CPU smoke deadline/evidence', result['errors'])

    def test_other_failures_remain_failures(self):
        for changes in ({'cleanup_verified': False}, {'admission_canceled': True},
                        {'peak_rss_bytes': 5*1024**3}, {'scope': 'live_development_pilot'},
                        {'status': 'failed'}, {'error': 'worker failure'},
                        {'lifecycle_seconds': 90}, {'worker': None}):
            with self.subTest(changes=changes):
                report = self.report()
                report.update(changes)
                self.assertFalse(evaluate_local_smoke(report, self.rows)['passed'])
        report = self.report()
        report['worker']['clients'].pop()
        self.assertFalse(evaluate_local_smoke(report, self.rows)['passed'])
        report = self.report()
        report['worker']['model_inference'] = True
        self.assertFalse(evaluate_local_smoke(report, self.rows)['passed'])

    def test_runner_rejects_budget_above_local_ceiling(self):
        with self.assertRaisesRegex(ValueError, 'local CPU smoke deadline'):
            run('unused', 'unused', seconds=301)
