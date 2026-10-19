"""Package mutation and interrupted finalization checks; no compute authority."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from research.feedback_probe_v1.live_package import check_runtime
from research.feedback_probe_v1.live_runtime import finalize

ROOT = Path(__file__).resolve().parents[1]


def runtime():
    value = json.loads((ROOT/'research/feedback_probe_v1/runtime_template.json').read_bytes())
    value['kernel_id'] = 'daichongwei06/unit-test'
    value['model']['kaggle_source'] = 'daichongwei06/unit-test-model/1'
    value['model']['mounted_path'] = '/kaggle/input/datasets/daichongwei06/unit-test-model'
    return value


class ProbePackageChecks(unittest.TestCase):
    def test_private_bindings_cannot_change_verified_runtime(self):
        original = runtime()
        check_runtime(original)
        for key, field, changed in [('kaggle_image', 'docker_image', 'mutable-image:latest'),
                                    ('model', 'revision', 'other-revision'),
                                    ('model', 'tree_sha256', '0'*64),
                                    ('dataset', 'version', 2), ('runtime', 'gpu_count', 2),
                                    ('model_host_packages', 'vllm', 'other-version')]:
            with self.subTest(field=field):
                value = deepcopy(original)
                value[key][field] = changed
                with self.assertRaises(ValueError):
                    check_runtime(value)
        value = deepcopy(original)
        value['server_argv'].append('--unreviewed-setting')
        with self.assertRaises(ValueError):
            check_runtime(value)

    def test_placeholder_foreign_account_or_wrong_mount_cannot_be_sealed(self):
        for change in ('placeholder', 'foreign', 'mount', 'version'):
            value = runtime()
            if change == 'placeholder':
                value['kernel_id'] = '<PRIVATE_NOTEBOOK>'
            elif change == 'foreign':
                value['kernel_id'] = 'someoneelse/unit-test'
            elif change == 'version':
                value['model']['kaggle_source'] = 'daichongwei06/unit-test-model/2'
            else:
                value['model']['mounted_path'] += '-wrong'
            with self.subTest(change=change), self.assertRaises(ValueError):
                check_runtime(value)

    def test_finalization_write_overrun_leaves_no_return_witness(self):
        with tempfile.TemporaryDirectory() as folder:
            root, ticks = Path(folder), [59.9]
            def writer(path, value):
                path.write_text(json.dumps(value))
                ticks[0] = 60.1
            with self.assertRaises(TimeoutError):
                finalize(root, {'started_monotonic': 0, 'error': None}, deadline=60,
                         now=lambda: ticks[0], writer=writer)
            self.assertFalse(json.loads((root/'provisional-result.json').read_bytes())['lifecycle_finalized'])
            self.assertFalse((root/'return-witness.json').exists())

    def test_interrupt_after_either_write_never_emits_success_marker(self):
        for name in ('provisional-result.json', 'return-witness.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root, markers = Path(folder), []
                def writer(path, value):
                    path.write_text(json.dumps(value))
                    if path.name == name:
                        raise KeyboardInterrupt('injected after write')
                with self.assertRaises(KeyboardInterrupt):
                    finalize(root, {'started_monotonic': 0, 'error': None}, deadline=60,
                             now=lambda: 59.9, writer=writer, emit=lambda *args, **kwargs: markers.append(args))
                self.assertEqual(markers, [])
                self.assertFalse(json.loads((root/'provisional-result.json').read_bytes())['lifecycle_finalized'])

    def test_overrun_during_marker_is_not_a_passing_return(self):
        with tempfile.TemporaryDirectory() as folder:
            root, ticks = Path(folder), [59.9]
            def marker(*args, **kwargs):
                ticks[0] = 60.1
            with self.assertRaises(TimeoutError):
                finalize(root, {'started_monotonic': 0, 'error': None}, deadline=60,
                         now=lambda: ticks[0], emit=marker)
            witness = json.loads((root/'return-witness.json').read_bytes())
            self.assertTrue(witness['provider_COMPLETE_and_exact_return_marker_required'])
            self.assertFalse(json.loads((root/'provisional-result.json').read_bytes())['lifecycle_finalized'])
