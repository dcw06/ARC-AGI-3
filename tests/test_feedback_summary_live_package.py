"""Package mutation and interrupted finalization checks; no compute authority."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from research.feedback_summary_probe_live_v1.live_package import check_runtime, creation_title, validate_creation_binding, validate_target_binding
from research.feedback_summary_probe_live_v1.live_operator import validate_send
from research.feedback_summary_probe_live_v1.live_runtime import finalize

ROOT = Path(__file__).resolve().parents[1]


def runtime():
    value = json.loads((ROOT/'research/feedback_summary_probe_live_v1/runtime_template.json').read_bytes())
    value['kernel_id'] = 'daichongwei06/unit-test'
    value['model']['kaggle_source'] = 'daichongwei06/unit-test-model/1'
    value['model']['mounted_path'] = '/kaggle/input/datasets/daichongwei06/unit-test-model'
    return value


class ProbePackageChecks(unittest.TestCase):
    def test_creation_title_reproduces_exact_bound_slug(self):
        target = 'daichongwei06/arc3-feedback-summary-probe-diagnostic-v1'
        title = creation_title(target)
        self.assertEqual(title.lower().replace(' ', '-'), target.split('/')[1])
        validate_creation_binding({'slug': target, 'new_title': title})
        with self.assertRaisesRegex(ValueError, 'different bound slug'):
            validate_creation_binding({'slug': target, 'new_title': 'ARC3 Feedback Probe Checkpoint Diagnostic V1'})

    def test_ambiguous_creation_slug_is_refused_before_save(self):
        for slug in ('arc3--probe', '-arc3-probe', 'arc3-probe-', 'arc3_probe', 'arc3-PrObE'):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                creation_title('daichongwei06/'+slug)

    def test_original_mismatch_refuses_at_send_boundary_before_any_SDK_use(self):
        fields = {'slug': 'daichongwei06/arc3-feedback-summary-probe-diagnostic-v1',
                  'new_title': 'ARC3 Feedback Probe Checkpoint Diagnostic V1'}
        with self.assertRaisesRegex(ValueError, 'different bound slug'):
            validate_send({}, {'save_fields': fields}, None, 'a'*64)

    def test_review_preflight_and_send_must_name_the_same_target(self):
        slug = 'daichongwei06/arc3-feedback-summary-probe-diagnostic-v1'
        fields = {'slug': slug, 'new_title': creation_title(slug)}
        lock = {'kernel_id': slug, 'save_fields': fields}
        metadata = {'id': slug, 'title': fields['new_title']}
        validate_target_binding(lock, metadata)
        for target in ('review', 'metadata', 'title'):
            changed_lock, changed_metadata = deepcopy(lock), deepcopy(metadata)
            if target == 'review': changed_lock['kernel_id'] += '-other'
            elif target == 'metadata': changed_metadata['id'] += '-other'
            else: changed_metadata['title'] += ' Other'
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_target_binding(changed_lock, changed_metadata)

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
