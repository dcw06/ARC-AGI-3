import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from certification.phase4_v6.monitor import observe_injected, VRAM, RAM


class MonitorTests(unittest.TestCase):
    def run_probe(self, **overrides):
        gpu = {'uuid': 'GPU-fixture', 'name': 'RTX PRO 6000',
               'total_bytes': 96 * 1024**3, 'used_bytes': 1}
        ready = Mock()
        args = dict(bind=lambda: {'gpu_uuid': gpu['uuid'], 'max_used_vram_bytes': VRAM,
                                 'initial_telemetry': gpu}, sample=lambda *_: gpu,
                    rss=lambda _: 1, scratch=lambda: 1, alive=Mock(side_effect=[True, False]),
                    ready=ready, clock=lambda: 1, sleep=lambda _: None)
        args.update(overrides)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'monitor'
            receipt = observe_injected(123, output, **args)
            self.assertEqual(json.loads((output / 'monitor-result.json').read_text()), receipt)
            telemetry = json.loads((output / 'telemetry.json').read_text()) if (output / 'telemetry.json').exists() else None
        return receipt, ready, telemetry

    def test_readiness_after_initial_validated_durable_sample(self):
        result, ready, telemetry = self.run_probe()
        self.assertEqual(result['status'], 'injected_monitor_completed')
        ready.assert_called_once()
        self.assertEqual(len(telemetry['samples']), 1)
        self.assertFalse(result['target_gpu_certified'])

    def test_bad_binding_never_ready(self):
        result, ready, _ = self.run_probe(bind=lambda: {})
        self.assertEqual(result['status'], 'failed')
        ready.assert_not_called()

    def test_initial_probe_failures_never_ready(self):
        for change in (dict(sample=lambda *_: {}), dict(rss=lambda _: RAM+1),
                       dict(scratch=lambda: True), dict(sample=Mock(side_effect=OSError('missing GPU')))):
            result, ready, _ = self.run_probe(**change)
            self.assertEqual(result['status'], 'failed')
            ready.assert_not_called()

    def test_late_gpu_identity_drift_is_terminal(self):
        gpu = {'uuid': 'GPU-fixture', 'name': 'RTX PRO 6000',
               'total_bytes': 96 * 1024**3, 'used_bytes': 1}
        sample = Mock(side_effect=[gpu, {**gpu, 'uuid': 'changed'}])
        result, ready, telemetry = self.run_probe(sample=sample, alive=lambda: True)
        self.assertEqual(result['status'], 'failed')
        ready.assert_called_once()
        self.assertEqual(sample.call_count, 2)
        self.assertEqual(len(telemetry['samples']), 1)

    def test_sampling_gap_fails_before_ready(self):
        result, ready, _ = self.run_probe(clock=Mock(side_effect=[0, 2, 2]))
        self.assertEqual(result['status'], 'failed')
        ready.assert_not_called()

    def test_full_evidence_retains_failure_receipt(self):
        result, ready, telemetry = self.run_probe(alive=lambda: True, evidence_bytes=8192)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('evidence', result['error'])
        self.assertIsNotNone(telemetry)
        self.assertGreater(result['samples_attempted'], len(telemetry['samples']))
