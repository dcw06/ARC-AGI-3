"""Competition binding survives reviewed packaging; no provider calls or GPU."""
import json
import unittest

from certification.direct_publisher_smoke_v1 import binding as B, notebook as N
from tests.test_direct_publisher_smoke import FixtureRoot, put


class CompetitionBindingTests(unittest.TestCase):
    def test_review_and_launch_retain_arc3_competition_without_enabling_review_gpu(self):
        fixture = FixtureRoot(self)
        review = json.loads((fixture.root / fixture.lock).parent.joinpath('kernel-metadata.json').read_bytes())
        launch = json.loads(N.launch_artifacts(fixture.root)['kernel-metadata.json'])
        for metadata in (review, launch):
            self.assertEqual(metadata['competition_sources'], ['arc-prize-2026-arc-agi-3'])
            self.assertTrue(metadata['is_private'])
            self.assertFalse(metadata['enable_internet'])
        self.assertFalse(review['enable_gpu'])
        self.assertFalse(review['enable_tpu'])
        self.assertTrue(launch['enable_gpu'])
        self.assertEqual(launch['machine_shape'], 'NvidiaRtxPro6000')

    def test_missing_or_different_competition_refuses_packaging(self):
        for competition in (None, {}, {'ref': 'another-competition'}):
            fixture = FixtureRoot(self)
            if competition is None: fixture.protocol.pop('competition', None)
            else: fixture.protocol['competition'] = competition
            put(fixture.root, B.PROTOCOL, fixture.protocol)
            with self.assertRaisesRegex(ValueError, 'competition binding'):
                N.review_notebook(fixture.root)

    def test_launch_refuses_review_metadata_that_dropped_competition(self):
        fixture = FixtureRoot(self)
        folder = (fixture.root / fixture.lock).parent
        metadata_path = folder / 'kernel-metadata.json'
        metadata = json.loads(metadata_path.read_bytes())
        metadata['competition_sources'] = []
        metadata_path.write_bytes(N.encode(metadata))
        lock = B.read_json(fixture.root, fixture.lock)
        lock['artifacts']['kernel-metadata.json'] = B.sha256(metadata_path)
        put(fixture.root, fixture.lock, lock)
        fixture.update(B.PERMISSION, review_lock_sha256=fixture.sha(fixture.lock))
        fixture.authorize()
        with self.assertRaisesRegex(ValueError, 'input bindings differ'):
            N.launch_artifacts(fixture.root)


if __name__ == '__main__':
    unittest.main()
