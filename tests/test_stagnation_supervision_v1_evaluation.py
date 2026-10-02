"""Stagnation supervision v1 (Track 3): held-out detector evaluation under the frozen trigger spec."""
import json
import unittest

from research.stagnation_supervision_v1 import evaluate as E, fixtures as F, thresholds as S

RESULTS = json.loads(E.RESULTS.read_text(encoding='utf-8'))


class HeldOutEvaluation(unittest.TestCase):
    def test_results_reproduce_from_the_frozen_spec(self):
        fresh = E.report(F.generate('evaluation'), S.load())
        self.assertEqual(json.loads(json.dumps(fresh)), RESULTS)
        self.assertEqual(RESULTS['spec_params'], S.load()['params'])
        self.assertEqual(RESULTS['evaluation_fixtures_sha256'], F.digest('evaluation'))
        self.assertEqual(RESULTS['spec_development_fixtures_sha256'], F.digest('development'))

    def test_report_refuses_the_development_partition(self):
        with self.assertRaises(ValueError):
            E.report(F.generate('development'), S.load())

    def test_every_error_is_retained(self):
        for name, d in RESULTS['detectors'].items():
            m = d['metrics']
            false = [e for e in d['errors'] if e['kind'] == 'false_intervention']
            missed = [e for e in d['errors'] if e['kind'] == 'missed_positive']
            self.assertEqual(len(false), m['false_triggers'], name)
            self.assertEqual(len(missed), m['positive_trajectories'] - m['detected_positive_trajectories'], name)
            self.assertEqual(m['triggers'], m['correct_triggers'] + m['false_triggers'])


if __name__ == '__main__':
    unittest.main()
