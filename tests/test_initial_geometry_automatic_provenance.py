"""Raw-evidence admission regressions; synthetic arrays, no model inference."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from research.initial_geometry_assistance_v1.automatic_replay import (
    confined, offline_cpu, reconstruct_objects, replay_source, sha, verify_provenance)
from research.initial_geometry_assistance_v1.geometry import canonical
from research.initial_geometry_assistance_v1.prepare import AUTOMATIC_SHA, build_inputs

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/'research/initial_geometry_assistance_v1/protocol.json'
HAS_ARRAYS = importlib.util.find_spec('numpy') is not None and importlib.util.find_spec('torch') is not None


class ProvenanceTests(unittest.TestCase):
    def test_protocol_freezes_actual_automatic_artifact(self):
        protocol = json.loads(PROTOCOL.read_bytes())
        self.assertEqual(protocol.get('automatic_masks_sha256'), AUTOMATIC_SHA)
        path = PROTOCOL.with_name('automatic_provenance.json')
        self.assertEqual(protocol['automatic_provenance_manifest_sha256'], sha(path.read_bytes()))
        self.assertEqual(json.loads(path.read_bytes())['automatic_masks_sha256'], AUTOMATIC_SHA)
        self.assertTrue((ROOT/protocol['automatic_replay_producer']).is_file())

    def test_protocol_or_manifest_rebinding_refused_before_evidence_read(self):
        protocol = json.loads(PROTOCOL.read_bytes())
        protocol['automatic_provenance_manifest_sha256'] = '0'*64
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, 'provenance manifest differs'):
            verify_provenance(Path(folder), protocol)

    def test_missing_raw_roots_refused_despite_true_claims(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base/'sam-comparison-evaluation-r1.json').write_bytes(canonical({
                'source_deployment_verified': True, 'masks_replayed_without_model_inference': True}))
            with self.assertRaises((ValueError, FileNotFoundError)):
                verify_provenance(base, json.loads(PROTOCOL.read_bytes()))

    def test_no_traversal_in_evidence_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('../elsewhere', '/absolute', 'C:/absolute', 'foo\\bar'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    confined(Path(folder), name)

    def test_prepare_requires_replay_even_with_all_old_flags_true(self):
        claimed = {'source_deployment_verified': True, 'masks_replayed_without_model_inference': True}
        source = {'replay_verified': True, 'lifecycle_certified': True, 'deployment_guard_passed': True}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'inputs'
            with patch('research.initial_geometry_assistance_v1.prepare.pinned', side_effect=[{}, claimed, source]), \
                    patch('research.initial_geometry_assistance_v1.prepare.replay_comparison',
                          side_effect=ValueError('raw evidence does not replay')) as replay:
                with self.assertRaisesRegex(ValueError, 'raw evidence does not replay'):
                    build_inputs('refs', 'auto', 'source', 'images', output,
                                 control_root=folder, molmopoint_checkpoint='checkpoint', sam_acquisition='receipt')
                replay.assert_called_once()
            self.assertFalse(output.exists())

    def test_replayed_and_stored_artifact_must_agree_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'inputs'
            with patch('research.initial_geometry_assistance_v1.prepare.pinned', side_effect=[{}, {'claimed': True}, {}]), \
                    patch('research.initial_geometry_assistance_v1.prepare.replay_comparison', return_value={'claimed': False}):
                with self.assertRaisesRegex(ValueError, 'differs from evidence replay'):
                    build_inputs('refs', 'auto', 'source', 'images', output,
                                 control_root=folder, molmopoint_checkpoint='checkpoint', sam_acquisition='receipt')
            self.assertFalse(output.exists())

    def test_deployment_is_checked_again_not_taken_from_collection_flags(self):
        # The old collection's flag is deliberately true while actual validation fails.
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            coll = base/'gpu-attempt1-terminal-collection-r1'
            coll.mkdir()
            (coll/'collection-manifest.json').write_bytes(canonical({}))
            (coll/'collection.json').write_bytes(canonical({'provider_status': 'COMPLETE', 'deployment_guard_passed': True,
                                                           'target_identity_matches': True, 'expected_version': 1}))
            (coll/'saved-package-snapshot.json').write_bytes(canonical({'metadata': {}, 'source': '{}'}))
            with patch('research.object_discovery_boundaries_v1.deployment.authority_from', return_value={}), \
                    patch('research.object_discovery_boundaries_v1.operations.validate_saved',
                          side_effect=ValueError('saved source altered')) as validate:
                with self.assertRaisesRegex(ValueError, 'saved source altered'):
                    replay_source(base, 'checkpoint', {})
                validate.assert_called_once()

    def test_swallowed_network_attempt_fails_replay(self):
        original = socket.create_connection
        with self.assertRaisesRegex(ValueError, 'attempted networking'):
            with offline_cpu():
                try:
                    socket.create_connection(('127.0.0.1', 1))
                except PermissionError:
                    pass
        self.assertIs(socket.create_connection, original)


@unittest.skipUnless(HAS_ARRAYS, 'requires retained CPU numpy/torch interpreter')
class RawSAMTests(unittest.TestCase):
    @staticmethod
    def fixture():
        import numpy as np
        from research.object_discovery_boundaries_v1.sam21 import point_prompts
        points = [{'pixel_xy': [70., 140.], 'cell_xy': [10, 20]}]
        arrays = {'pred_masks': np.ones((1, 1, 3, 256, 256), dtype=np.float32),
                  'iou_scores': np.array([[[.1, .8, .2]]], dtype=np.float32),
                  'original_sizes': np.array([[448, 448]]),
                  'input_points': np.array(point_prompts(points)['input_points'], dtype=np.float32)*(1024/448),
                  'input_labels': np.ones((1, 1, 1), dtype=np.int64)}
        arrays['pred_masks'][0, 0, 0] = -1
        arrays['pred_masks'][0, 0, 2] = -1
        return points, arrays

    def test_masks_come_from_logits_and_predicted_quality(self):
        points, arrays = self.fixture()
        objects = reconstruct_objects(points, arrays)
        self.assertEqual(len(objects[0]['cells']), 4096)
        self.assertEqual(objects[0]['selected_candidate_index'], 1)
        arrays['iou_scores'][0, 0, 0] = .9
        changed = reconstruct_objects(points, arrays)
        self.assertEqual(changed[0]['cells'], [])
        self.assertTrue(changed[0]['empty_mask'])

    def test_ties_use_earliest_candidate(self):
        points, arrays = self.fixture()
        arrays['iou_scores'][0, 0] = .5
        self.assertEqual(reconstruct_objects(points, arrays)[0]['selected_candidate_index'], 0)

    def test_nonfinite_logits_or_scores_refused(self):
        for key in ('pred_masks', 'iou_scores'):
            points, arrays = self.fixture()
            arrays[key].flat[0] = float('nan')
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'raw shape/values'):
                reconstruct_objects(points, arrays)

    def test_seed_or_board_coordinate_binding_refused(self):
        for key in ('original_sizes', 'input_points', 'input_labels'):
            points, arrays = self.fixture()
            arrays[key].flat[0] = 0 if key == 'input_labels' else 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                reconstruct_objects(points, arrays)

    def test_unknown_arrays_and_wrong_precision_refused(self):
        points, arrays = self.fixture()
        arrays['reference_mask'] = arrays['pred_masks']
        with self.assertRaisesRegex(ValueError, 'raw inventory'):
            reconstruct_objects(points, arrays)
        del arrays['reference_mask']
        arrays['pred_masks'] = arrays['pred_masks'].astype('float64')
        with self.assertRaisesRegex(ValueError, 'FP32'):
            reconstruct_objects(points, arrays)


if __name__ == '__main__':
    unittest.main()
