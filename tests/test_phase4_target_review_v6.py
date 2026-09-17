"""Target evidence rejection tests; no hardware or authority bypass."""
import unittest
from unittest.mock import patch

from certification.phase4_v6.evaluate import evaluate


class TargetReviewTests(unittest.TestCase):
    def test_evaluator_overrun_revokes_success_and_capacity(self):
        from certification.phase4_v6.pilot import enforce_finalization_deadline
        report = {'status': 'worker_completed_pending_independent_evaluation'}
        result = {'passed': True, 'errors': [], 'capacity_candidate': {'rate': 123}}
        with patch('certification.phase4_v6.pilot.time.monotonic', return_value=400):
            enforce_finalization_deadline(report, result, started=100, seconds=300)
        self.assertFalse(result['passed'])
        self.assertIsNone(result['capacity_candidate'])
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['elapsed_seconds'], 300)

    def test_known_cache_overrides_stay_inside_monitored_scratch(self):
        from pathlib import Path
        import tempfile
        from certification.phase4_v6.scratch import worker_environment
        with tempfile.TemporaryDirectory() as folder:
            original = {'VLLM_CACHE_ROOT': '/outside', 'HF_HOME': '/outside',
                        'HF_HUB_OFFLINE': '1'}
            env = worker_environment(original, folder)
            self.assertEqual(original['VLLM_CACHE_ROOT'], '/outside')
            self.assertEqual(env['HF_HUB_OFFLINE'], '1')
            for key, value in env.items():
                if key not in ('HF_HUB_OFFLINE', 'PYTHONDONTWRITEBYTECODE'):
                    self.assertTrue(Path(value).is_relative_to(Path(folder).resolve()))
                    self.assertTrue(Path(value).is_dir())

    def test_cleanup_receipt_and_uncanceled_lifecycle_required_for_capacity(self):
        report = {
            'gpu_cleanup_verified': True,
            'resource_evidence_class': 'live_resource_monitor',
            'gpu_telemetry': [], 'gpu_binding': {'gpu_uuid': 'fixture'},
            'monitor_started_seconds': 0, 'worker_started_seconds': 1,
            'worker_stopped_seconds': 2, 'monitor_ended_seconds': 3,
            'elapsed_seconds': 4, 'worker': {},
        }
        cases = ({}, {'gpu_cleanup_verified': False},
                 {'gpu_cleanup_verified': None}, {'admission_canceled': True})
        for changes in cases:
            with self.subTest(changes=changes), patch(
                    'certification.phase4_v6.evaluate.evaluate_v4',
                    return_value={'errors': []}), patch(
                    'certification.phase4_v6.evaluate.validate_telemetry'), patch(
                    'certification.phase4_v6.evaluate.capacity_from_worker',
                    return_value={'fixture': True}):
                result = evaluate({**report, **changes}, [])
                self.assertEqual(result['passed'], not changes)
                if changes:
                    self.assertIsNone(result['capacity_candidate'])
                    self.assertFalse(result['development_model_lifecycle_passed'])
