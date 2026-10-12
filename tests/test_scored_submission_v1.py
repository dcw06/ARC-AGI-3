"""CPU regressions for the new scored package; no account, model or GPU calls."""
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.scored_runtime import certify

class Finalization(unittest.TestCase):
    def receipt(self):
        return {'error':None,'groups_absent':True,'gpu_cleanup_verified':True,
                'source_and_dependencies_removed':True}

    def test_late_evidence_write_never_certifies_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            receipt=self.receipt()
            with patch('agent.scored_runtime.time.monotonic',side_effect=[3299.9,3300.1]):
                certify(root,receipt,0,nullcontext)
            self.assertFalse(receipt['passed'])
            self.assertTrue((root/'scored-finalization-pending.json').exists())
            self.assertFalse(json.loads((root/'scored-lifecycle.json').read_bytes())['passed'])

    def test_source_removal_failure_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt={**self.receipt(),'source_and_dependencies_removed':False}
            with patch('agent.scored_runtime.time.monotonic',return_value=100):
                certify(Path(tmp),receipt,0,nullcontext)
            self.assertFalse(receipt['passed'])
            self.assertTrue((Path(tmp)/'scored-finalization-pending.json').exists())

    def test_interruption_after_success_write_leaves_refusal_barrier(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('agent.scored_runtime.time.monotonic',side_effect=[100,KeyboardInterrupt()]):
                with self.assertRaises(KeyboardInterrupt):
                    certify(Path(tmp),self.receipt(),0,nullcontext)
            self.assertTrue((Path(tmp)/'scored-finalization-pending.json').exists())

    def test_success_requires_post_write_and_post_removal_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt=self.receipt()
            with patch('agent.scored_runtime.time.monotonic',side_effect=[100,101,102]):
                certify(Path(tmp),receipt,0,nullcontext)
            self.assertTrue(receipt['passed'])
            self.assertFalse((Path(tmp)/'scored-finalization-pending.json').exists())
