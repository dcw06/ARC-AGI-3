"""Dataset model bindings and the existing binary-digest tree contract; CPU only."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from certification.direct_publisher_smoke_v1 import binding as B, host, notebook as N
from tests.test_direct_publisher_smoke import FixtureRoot, put


class ModelDatasetTests(unittest.TestCase):
    def protocol(self):
        value = copy.deepcopy(B.load_protocol())
        value['model'].update(source_kind='dataset', kaggle_source='fixture/model-snapshot/3')
        return value

    def test_dataset_model_review_and_launch_pin_both_versions_without_model_attachment(self):
        fixture = FixtureRoot(self)
        fixture.protocol['model'].update(source_kind='dataset', kaggle_source='fixture/model-snapshot/3')
        put(fixture.root, B.PROTOCOL, fixture.protocol)
        N.build_review(fixture.root / 'notebooks/direct-publisher-smoke-v1-review-r2', root=fixture.root)
        fixture.lock = B.review_lock(fixture.root)
        fixture.update(B.PERMISSION, review_lock_sha256=fixture.sha(fixture.lock),
                       protocol_sha256=fixture.sha(B.PROTOCOL))
        fixture.authorize()
        expected = [fixture.protocol['dataset']['ref'] + '/1', 'fixture/model-snapshot/3']
        review = json.loads((fixture.root / fixture.lock).parent.joinpath('kernel-metadata.json').read_bytes())
        launch = json.loads(N.launch_artifacts(fixture.root)['kernel-metadata.json'])
        self.assertFalse(review['enable_gpu'])
        for metadata in (review, launch):
            self.assertEqual(metadata['dataset_sources'], expected)
            self.assertEqual(metadata['model_sources'], [])
            self.assertTrue(metadata['is_private'])
            self.assertFalse(metadata['enable_internet'])
        self.assertEqual(launch['machine_shape'], 'NvidiaRtxPro6000')

    def test_legacy_model_source_is_preserved_and_wheel_version_is_pinned(self):
        protocol = B.load_protocol()
        self.assertEqual(N.input_sources(protocol), {
            'dataset_sources': [protocol['dataset']['ref'] + '/1'],
            'model_sources': [protocol['model']['kaggle_source']]})

    def test_invalid_or_unversioned_model_dataset_is_rejected(self):
        for ref in ('fixture/model-snapshot', 'fixture/model-snapshot/0',
                    'fixture/model-snapshot/latest', 'fixture/model-snapshot/1/extra'):
            with self.subTest(ref=ref):
                protocol = self.protocol()
                protocol['model']['kaggle_source'] = ref
                with self.assertRaisesRegex(ValueError, 'version-pinned'):
                    N.input_sources(protocol)

    def test_source_kind_and_dataset_collision_are_rejected(self):
        protocol = self.protocol()
        protocol['model']['source_kind'] = 'fallback'
        with self.assertRaisesRegex(ValueError, 'source kind'):
            N.input_sources(protocol)
        protocol = self.protocol()
        protocol['model']['kaggle_source'] = protocol['dataset']['ref'] + '/2'
        with self.assertRaisesRegex(ValueError, 'distinct'):
            N.input_sources(protocol)

    def test_manifest_binary_digest_reconstruction_matches_actual_host_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = []
            for name, content in (('nested/a.json', b'config'), ('weights.bin', b'fixture weights')):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                rows.append({'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
            binary, ascii_hex = hashlib.sha256(b'arc3-artifact-tree-v1\0'), hashlib.sha256(b'arc3-artifact-tree-v1\0')
            for row in sorted(rows, key=lambda row: row['path']):
                name = row['path'].encode()
                prefix = len(name).to_bytes(4, 'big') + name + row['bytes'].to_bytes(8, 'big')
                binary.update(prefix + bytes.fromhex(row['sha256']))
                ascii_hex.update(prefix + row['sha256'].encode())
            actual = host.tree_sha256(root)
            self.assertEqual(actual['tree_sha256'], binary.hexdigest())
            self.assertNotEqual(binary.hexdigest(), ascii_hex.hexdigest())


if __name__ == '__main__':
    unittest.main()
