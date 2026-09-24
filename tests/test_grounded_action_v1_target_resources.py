"""Independent cleanup verdict and pre-query Stage B authority boundary."""
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile

from certification.phase4_integrated_v2.evidence import EvidenceStore
from research.grounded_action_v1.local import ScriptedAdapter, ScriptedService, run
from research.grounded_action_v1.replay import replay_file
from research.grounded_action_v1.target_resources import LiveProbes, independent_cleanup


class TargetResourceTests(unittest.TestCase):
    def test_trajectory_can_use_shared_bounded_evidence_store(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = EvidenceStore(root, 'worker')
            path = root / 'worker/trajectory.json'
            result = run(path, ScriptedService(), lambda arm: ScriptedAdapter(arm),
                         writer=lambda _path, record: store.save('trajectory.json', record))
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(replay_file(path)['calls'], 12)

    def test_missing_authority_precedes_gpu_query(self):
        with patch('subprocess.run') as query:
            with self.assertRaises(PermissionError):
                LiveProbes(123, '/tmp/stage-b-no-authority')
            query.assert_not_called()

    def test_independent_cleanup_requires_empty_gpu_and_absent_groups(self):
        class Probes:
            def __init__(self, pids):
                self.pids = pids
                self.queries = 0

            def sample(self, uuid):
                self.queries += 1
                return {'uuid': uuid}

            def gpu_pids(self):
                self.queries += 1
                return self.pids

        good = Probes([])
        self.assertTrue(independent_cleanup(good, expected_uuid='GPU-TEST',
                                            groups_absent=True, deadline=10,
                                            clock=lambda: 1)['gpu_cleanup_verified'])
        self.assertEqual(good.queries, 2)
        for pids, groups in (([123], True), ([], False)):
            with self.subTest(pids=pids, groups=groups):
                result = independent_cleanup(Probes(pids), expected_uuid='GPU-TEST',
                                             groups_absent=groups, deadline=10, clock=lambda: 1)
                self.assertFalse(result['gpu_cleanup_verified'])
        expired = Probes([])
        self.assertFalse(independent_cleanup(expired, expected_uuid='GPU-TEST',
                                             groups_absent=True, deadline=1,
                                             clock=lambda: 1)['gpu_cleanup_verified'])
        self.assertEqual(expired.queries, 0)


if __name__ == '__main__':
    unittest.main()
