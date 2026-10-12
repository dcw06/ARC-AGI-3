"""The artifact lock must cover the bytes actually written on the current platform."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_scored_submission_v1 import build

class ArtifactBytes(unittest.TestCase):
    def test_saved_artifacts_match_their_lock_and_stay_gpu_disabled(self):
        bindings = {'kernel':'REPLACE_WITH_ACCOUNT/arc3-e1sr-scored-one-hour-v1',
                    'model_source':'REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1',
                    'model_mount':'/kaggle/input/datasets/REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET'}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'review'
            lock = build(folder,bindings)
            for name,digest in lock['artifact_hashes'].items():
                self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(),digest)
                self.assertNotIn(b'\r\n',(folder/name).read_bytes())
            self.assertEqual(json.loads((folder/'review-lock.json').read_bytes()),lock)
            metadata = json.loads((folder/'kernel-metadata.json').read_bytes())
            for field in ('enable_gpu','enable_tpu','enable_internet'):
                self.assertIs(metadata[field],False)
            self.assertIs(lock['source_approved'],False)
            self.assertIs(lock['gpu_authorized'],False)
