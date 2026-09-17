import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certification.phase4_v6 import target_install_probe as probe
from certification.phase4_v6.build_install_probe import build


class InstallProbeTests(unittest.TestCase):
    def test_missing_frozen_artifacts_fail_before_install(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(probe, 'command') as command:
            root = Path(folder)
            result = probe.run(root/'missing', root/'missing', {}, root/'output')
            self.assertFalse(result['passed'])
            self.assertFalse(result['model_loaded'])
            command.assert_not_called()
            self.assertEqual(json.loads((root/'output/result.json').read_text()), result)

    def test_manifest_mismatch_is_not_a_clean_install(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'SHA256SUMS').write_text('not the frozen wheelhouse')
            with self.assertRaisesRegex(ValueError, 'manifest mismatch'):
                probe.verify_wheelhouses(root, root, {}, lambda: None)

    def test_probe_proposal_binds_notebook_without_authorizing_a_pilot(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'proposal'
            lock = build(output)
            for name, digest in lock['artifacts'].items():
                self.assertEqual(hashlib.sha256((output/name).read_bytes()).hexdigest(), digest)
            notebook = json.loads((output/'profile.ipynb').read_text())
            ast.parse(notebook['cells'][1]['source'])
            ast.parse(probe.RUNTIME_CHECK)
            metadata = json.loads((output/'kernel-metadata.json').read_text())
            self.assertEqual(metadata['model_sources'], [])
            self.assertFalse(metadata['enable_internet'])
            budget = json.loads((output/'budget-proposal.json').read_text())
            self.assertEqual(budget['authorized_seconds'], 0)
            self.assertEqual(budget['pilot_authorized_seconds'], 0)
            with self.assertRaises(FileExistsError):
                build(output)
