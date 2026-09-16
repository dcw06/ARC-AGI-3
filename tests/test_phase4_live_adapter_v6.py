import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from certification.phase4_v6.live_probes import LiveResourceProbes
from certification.phase4_v6.evidence import EvidenceStore, LIMITS, TOTAL
from certification.phase4_v6.monitor import observe_injected, VRAM
from certification.phase4_v6.evaluate import monitor_fields, evaluate


class LiveAdapterTests(unittest.TestCase):
    def test_closed_authority_precedes_all_probes(self):
        with patch('subprocess.run') as run:
            with self.assertRaises(PermissionError):
                LiveResourceProbes(123, Path('/tmp'))
            run.assert_not_called()

    def test_adapter_forwards_frozen_limits_and_owned_pid(self):
        # Only bypass the gate inside this mocked unit test. No actual probes.
        with tempfile.TemporaryDirectory() as directory, \
             patch('certification.phase4_v6.live_probes.require_live_authority'), \
             patch('evaluation.phase4_target.bind_gpu', return_value={'mock': True}) as bind, \
             patch('evaluation.phase4_preflight.sample_gpu', return_value={'mock': True}) as sample, \
             patch('evaluation.phase4_runner.group_rss_bytes', return_value=7) as rss:
            probe = LiveResourceProbes(123, directory)
            probe.bind(); bind.assert_called_once_with(VRAM)
            probe.sample('GPU-test', VRAM); sample.assert_called_once_with('GPU-test', VRAM)
            self.assertEqual(probe.rss(123), 7); rss.assert_called_once_with(123)
            with self.assertRaises(ValueError): probe.rss(456)
            self.assertEqual(probe.scratch(), 0)

    def test_shared_store_enforces_component_budget_and_preserves_old_data(self):
        self.assertEqual(sum(LIMITS.values()), TOTAL)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(LIMITS, {'monitor': 8192}):
            store = EvidenceStore(directory, 'monitor')
            path = store.save('telemetry.json', {'value': 'old'})
            with self.assertRaises(ValueError):
                store.save('telemetry.json', {'value': 'x' * 5000})
            self.assertEqual(json.loads(path.read_text()), {'value': 'old'})
            store.save('failure.json', {'error': 'budget'}, failure_receipt=True)
            with self.assertRaises(ValueError): store.save('../escape.json', {})

    def test_unbudgeted_files_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'unbudgeted').touch()
            with self.assertRaises(ValueError): EvidenceStore(root, 'monitor').save('a.json', {})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'link').symlink_to('/tmp')
            with self.assertRaises(ValueError): EvidenceStore(root, 'monitor').save('a.json', {})

    def test_shared_clock_budgeted_monitor_to_evaluator_fields(self):
        gpu = {'uuid': 'GPU-INJECTED', 'name': 'RTX PRO 6000',
               'used_bytes': 1, 'total_bytes': 96*1024**3}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = observe_injected(123, root/'scratch',
                bind=lambda: {'gpu_uuid': gpu['uuid'], 'max_used_vram_bytes': VRAM,
                              'initial_telemetry': gpu}, sample=lambda *_: gpu,
                rss=lambda _: 1, scratch=lambda: 1, alive=Mock(side_effect=[True, False]),
                ready=lambda: None, clock=Mock(side_effect=[101, 101.25, 101.5]), origin=100,
                evidence_store=EvidenceStore(root/'evidence', 'monitor'))
            telemetry = json.loads((root/'evidence/monitor/telemetry.json').read_text())
            fields = monitor_fields(receipt, telemetry, first_cell_monotonic=100)
            self.assertEqual(fields['monitor_started_seconds'], 1)
            self.assertEqual(fields['gpu_telemetry'][0]['elapsed_seconds'], 1.25)
            result = evaluate(fields, [])
            self.assertFalse(result['passed'])
            self.assertTrue(any('injected' in e for e in result['errors']))
            with self.assertRaises(ValueError):
                monitor_fields(receipt, telemetry, first_cell_monotonic=99)
            bad = copy.deepcopy(telemetry); bad['samples'][0]['elapsed_seconds'] = 0
            with self.assertRaises(ValueError): monitor_fields(receipt, bad, first_cell_monotonic=100)
