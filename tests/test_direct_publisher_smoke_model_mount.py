"""CPU regressions for the model-root failure after the successful RTX check."""
import copy
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1 import host, run as R
from certification.direct_publisher_smoke_v1.binding import load_protocol


class ModelMountTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.input = self.base / 'input'
        self.input.mkdir()
        self.canonical = self.input / 'datasets/fixture/model-snapshot'
        self.legacy = self.input / 'model-snapshot'
        self.model = {
            'source_kind': 'dataset', 'kaggle_source': 'fixture/model-snapshot/3',
            'mounted_path': str(self.canonical), 'required_files': ['config.json'],
            'shard_count': 1, 'shard_glob': 'model-*.safetensors',
        }
        # create=True lets the original reproduction run against the pre-fix host.
        root_patch = patch.object(host, 'INPUT_ROOT', self.input, create=True)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def snapshot(self, path):
        path.mkdir(parents=True)
        (path / 'config.json').write_bytes(b'{}')
        (path / 'model-00001-of-00001.safetensors').write_bytes(b'CPU fixture, not real weights')
        self.model['tree_sha256'] = host.tree_sha256(path)['tree_sha256']

    def test_original_reproduction_missing_configured_path_with_legacy_mount(self):
        self.snapshot(self.legacy)
        self.assertFalse(self.canonical.exists())
        result = host.verify_model(self.model)
        self.assertEqual(result['tree_sha256'], self.model['tree_sha256'])
        self.assertEqual(result['mounted_path'], str(self.legacy))
        self.assertEqual(result['configured_path'], str(self.canonical))
        self.assertEqual(result['files'], 2)

    def test_canonical_mount_and_legacy_configured_path(self):
        self.snapshot(self.canonical)
        self.model['mounted_path'] = str(self.legacy)
        result = host.verify_model(self.model)
        self.assertEqual(result['mounted_path'], str(self.canonical))
        self.assertFalse(result['provider_attachment_version_verified'])
        self.assertEqual(result['requested_version'], 3)

    def test_bound_layout_alias_is_resolved_without_hashing_the_link(self):
        self.snapshot(self.legacy)
        self.canonical.parent.mkdir(parents=True)
        self.canonical.symlink_to(self.legacy, target_is_directory=True)
        result = host.verify_model(self.model)
        self.assertEqual(result['mounted_path'], str(self.legacy))
        self.assertTrue(result['mount_candidates'][0]['is_symlink'])
        with self.assertRaisesRegex(ValueError, 'real directory'):
            host.tree_sha256(self.canonical)  # Generic tree validation remains strict.

    def test_distinct_layouts_are_ambiguous_even_when_bytes_match(self):
        self.snapshot(self.legacy)
        self.snapshot(self.canonical)
        with self.assertRaisesRegex(host.HostMismatch, 'unambiguous mount'):
            host.verify_model(self.model)

    def test_missing_mount_reports_both_checked_paths(self):
        with self.assertRaisesRegex(host.HostMismatch, 'found 0 real directories') as caught:
            host.verify_model(self.model)
        for path in (self.canonical, self.legacy):
            self.assertIn(str(path), str(caught.exception))

    def test_configured_path_cannot_select_another_dataset(self):
        self.snapshot(self.legacy)
        self.model['mounted_path'] = str(self.input / 'unrelated-model')
        with self.assertRaisesRegex(host.HostMismatch, 'bound dataset'):
            host.verify_model(self.model)

    def test_alias_to_another_root_is_rejected_even_with_matching_bytes(self):
        for target in (self.input / 'unrelated-model', self.base / 'outside-input'):
            with self.subTest(target=target):
                self.snapshot(target)
                self.canonical.parent.mkdir(parents=True, exist_ok=True)
                self.canonical.symlink_to(target, target_is_directory=True)
                try:
                    with self.assertRaisesRegex(host.HostMismatch, 'real bound directory'):
                        host.verify_model(self.model)
                finally:
                    self.canonical.unlink()

    def test_broken_alias_is_not_silently_ignored(self):
        self.snapshot(self.legacy)
        self.canonical.parent.mkdir(parents=True)
        self.canonical.symlink_to(self.base / 'missing', target_is_directory=True)
        with self.assertRaisesRegex(host.HostMismatch, 'broken model dataset mount alias'):
            host.verify_model(self.model)

    def test_unpinned_and_unsafe_dataset_references_are_rejected(self):
        for source in ('fixture/model-snapshot', 'fixture/model-snapshot/0',
                       'fixture/model-snapshot/latest', 'fixture/../3', 'fixture/model-snapshot/3/extra'):
            with self.subTest(source=source):
                self.model['kaggle_source'] = source
                with self.assertRaisesRegex(host.HostMismatch, 'version-pinned'):
                    host.verify_model(self.model)

    def test_unsupported_source_kind_is_rejected(self):
        self.model['source_kind'] = 'fallback'
        with self.assertRaisesRegex(host.HostMismatch, 'source kind'):
            host.verify_model(self.model)

    def test_selected_mount_still_requires_pinned_bytes_and_layout(self):
        self.snapshot(self.legacy)
        weights = self.legacy / 'model-00001-of-00001.safetensors'
        weights.write_bytes(b'altered bytes')
        with self.assertRaisesRegex(host.HostMismatch, 'SHA-256 differs'):
            host.verify_model(self.model)
        self.model['tree_sha256'] = host.tree_sha256(self.legacy)['tree_sha256']
        self.model['shard_count'] = 2
        with self.assertRaisesRegex(host.HostMismatch, 'model layout'):
            host.verify_model(self.model)

    def test_internal_links_remain_forbidden(self):
        self.snapshot(self.legacy)
        (self.legacy / 'linked-config.json').symlink_to(self.legacy / 'config.json')
        with self.assertRaisesRegex(ValueError, 'tree contains a symlink'):
            host.verify_model(self.model)

    def test_legacy_kaggle_model_path_is_preserved(self):
        self.snapshot(self.legacy)
        self.model.pop('source_kind')
        self.model['mounted_path'] = str(self.legacy)
        self.assertEqual(host.verify_model(self.model)['mounted_path'], str(self.legacy))

    def test_deadline_after_last_model_read_cannot_pass(self):
        self.snapshot(self.legacy)
        self.model['mounted_path'] = str(self.legacy)
        # Zero-length files previously did not invoke any deadline callback.
        for path in self.legacy.iterdir():
            path.write_bytes(b'')
        self.model['tree_sha256'] = host.tree_sha256(self.legacy)['tree_sha256']
        def expired():
            raise TimeoutError('model verification deadline reached')
        with self.assertRaisesRegex(TimeoutError, 'model verification'):
            host.verify_model(self.model, expired)
        calls = []
        def final_check():
            calls.append(True)
            if len(calls) == 4:  # initial check, two empty entries, final tree check
                raise TimeoutError('deadline after final model read')
        with self.assertRaisesRegex(TimeoutError, 'final model read'):
            host.verify_model(self.model, final_check)

    def test_server_receives_the_path_whose_bytes_were_verified(self):
        self.snapshot(self.legacy)
        protocol = copy.deepcopy(load_protocol())
        protocol['model'] = dict(protocol['model'], **self.model)
        with patch.object(R.host, 'host_facts', return_value={}), \
             patch.object(R, 'verify_bundle', return_value={}), \
             patch.object(R, 'install', return_value={'python': sys.executable}), \
             patch.object(R, 'ModelServer') as server:
            server.return_value.start.side_effect = RuntimeError('scripted stop before starting a server')
            server.return_value.stop.return_value = {'groups_absent': True}
            result = R.run('rehearsal', protocol, self.base / 'evidence', time.monotonic(),
                           bundle=self.base / 'bundle', workdir=self.base / 'work')
        self.assertEqual(result['failed_stage'], 'server_start')
        self.assertEqual(result['stages']['model_artifact']['mounted_path'], str(self.legacy))
        argv = server.call_args.args[0]
        self.assertEqual(argv[argv.index('--model') + 1], str(self.legacy))
        self.assertEqual(result['ledger']['issued'], 0)


if __name__ == '__main__':
    unittest.main()
