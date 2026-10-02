"""R3 launch blockers: generated cache arguments, retained runtime config, target lifecycle replay."""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from research.stagnation_supervision_v1.closed_loop import server_config as C, target_evaluate as T

ROOT = Path(__file__).resolve().parents[1]


class ServerConfiguration(unittest.TestCase):
    def owner(self):
        from certification.phase4_integrated_v2.model_process import load_operational_primary
        rows = []
        owner = C.model_owner(load_operational_primary(ROOT), lambda value: rows.append(copy.deepcopy(value)))
        argv, _ = owner._argv_and_env()
        owner.process = SimpleNamespace(pid=1234)
        return owner, rows, argv

    def test_actual_operational_argv_has_only_an_explicit_disable(self):
        owner, rows, argv = self.owner()
        self.assertEqual(argv.count(C.DISABLE), 1)
        self.assertNotIn('--enable-prefix-caching', argv)
        self.assertEqual(rows[-1]['argv'], argv)
        self.assertEqual(rows[-1]['status'], 'launch_requested')

    def test_runtime_metrics_are_retained_and_verified_before_canary(self):
        owner, rows, _ = self.owner()
        raw = C.rehearsal_record()['metrics_body'].encode()
        with mock.patch.object(C, 'urlopen', return_value=io.BytesIO(raw)) as query:
            owner._completion_canary()
        query.assert_called_once_with('http://127.0.0.1:8000/metrics', timeout=5)
        self.assertEqual([r['status'] for r in rows], ['launch_requested', 'received', 'verified'])
        C.validate(rows[-1], mode='live')

    def test_configuration_failures_retain_received_bytes(self):
        good = C.rehearsal_record()['metrics_body']
        for text in ('', good.replace('False', 'True'), good + good, good.replace('engine="0"', 'engine="1"'),
                     'vllm:prefix_cache_hits_total 0\n', good.replace('False', 'false'), 'x' * (C.LIMIT + 1)):
            with self.subTest(text=text[:80]):
                owner, rows, _ = self.owner()
                with mock.patch.object(C, 'urlopen', return_value=io.BytesIO(text.encode())):
                    with self.assertRaises(ValueError):
                        owner._completion_canary()
                self.assertEqual(rows[-2]['status'], 'received')
                self.assertEqual(rows[-1]['status'], 'failed')
                self.assertEqual(rows[-1]['metrics_body'], text[:C.LIMIT])

    def test_absent_or_conflicting_inherited_flags_are_rejected(self):
        for flags in ([], [C.DISABLE], ['--enable-prefix-caching', C.DISABLE], ['--enable-prefix-caching=True']):
            with self.assertRaises(ValueError):
                C.cache_disabled_argv(flags)


class TargetLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_stagnation_supervision_v1_connected import connected
        from research.stagnation_supervision_v1.closed_loop import bridge as B
        _, _, _, _, detail = connected(details=True)
        cls.output = Path(detail['output'])
        with mock.patch.dict('os.environ', {'SSV_REHEARSAL': '1', 'SSV_REHEARSAL_GROUPS': 'b1-ar25',
                                         'SSV_REHEARSAL_ACTIONS': '12'}):
            cls.spec = B.session_run_spec('1', 'rehearsal')

    def result(self, folder):
        return T.evaluate_target(folder, self.spec, mode='rehearsal', session='1', internal_seconds=1500)

    def test_valid_connected_rehearsal_requires_both_verdicts(self):
        result = self.result(self.output)
        self.assertTrue(result['trajectory_complete'], result['problems'])
        self.assertTrue(result['lifecycle_verified'], result['problems'])
        self.assertTrue(result['technically_complete'])
        self.assertFalse(result['target_accepted'])  # injected GPU never becomes live evidence

    def test_valid_trajectories_do_not_mask_failed_lifecycle_receipts(self):
        mutations = (
            ('monitor/monitor-result.json', 'status', 'failed'),
            ('monitor/monitor-result.json', 'sampling_interval_seconds', .25),
            ('monitor/monitor-result.json', 'error', 'monitor failed'),
            ('control/gpu-cleanup.json', 'gpu_cleanup_verified', False),
            ('control/gpu-cleanup.json', 'remaining_gpu_pids', 1),
            ('control/gpu-cleanup.json', 'gpu_uuid', 'GPU-WRONG'),
            ('control/gpu-cleanup.json', 'checked_monotonic', 0),
            ('control/notebook-cost.json', 'elapsed_seconds', 1501),
            ('control/notebook-cost.json', 'elapsed_seconds', float('nan')),
            ('control/notebook-cost.json', 'internal_seconds', 99999),
            ('control/notebook-cost.json', 'first_cell_cleanup_verified', False),
            ('control/first-cell-supervisor-cleanup.json', 'groups', {}),
            ('control/first-cell-supervisor-cleanup.json', 'drain_finished', False),
            ('control/outer.json', 'scratch_removed', False),
            ('control/outer.json', 'worker_completed_seconds', 1201),
            ('control/outer.json', 'first_cell_monotonic', 0),
            ('control/monitor-ready-ack.json', 'nonce', 'bad'),
            ('worker/host-status.json', 'startup_seconds', 901),
            ('worker/canary.json', 'response_content', 'not JSON'),
            ('worker/model-ready.json', 'artifact', {}),
            ('worker/server-configuration.json', 'status', 'failed'),
            ('worker/worker-result.json', 'calls', 0),
        )
        for relative, key, value in mutations:
            with self.subTest(relative=relative, key=key), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / 'output'
                shutil.copytree(self.output, folder)
                path = folder / relative
                data = json.loads(path.read_bytes())
                data[key] = value
                path.write_text(json.dumps(data))
                result = self.result(folder)
                self.assertTrue(result['trajectory_complete'])
                self.assertFalse(result['lifecycle_verified'], result)
                self.assertFalse(result['technically_complete'])

    def test_missing_receipts_and_relabeling_rehearsal_as_live_fail_closed(self):
        result = T.evaluate_target(self.output, self.spec, mode='live', session='1')
        self.assertFalse(result['target_accepted'])
        for relative in ('control/notebook-cost.json', 'monitor/telemetry.json', 'worker/server-configuration.json'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / 'output'
                shutil.copytree(self.output, folder)
                (folder / relative).unlink()
                self.assertFalse(self.result(folder)['technically_complete'])
