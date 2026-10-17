"""External reference freeze regressions. Synthetic data, no model or network."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.object_discovery_boundaries_v1.experiment import verified_references
from research.object_discovery_boundaries_v1.reference_audit import canonical,digest
from tests.object_boundary_experiment_fixture import frozen


class FrozenReferences(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.inputs=self.root/'inputs';self.inputs.mkdir()
        (self.inputs/'manifest.json').write_text('{}')
        self.refs=self.root/'references.json';self.refs.write_text('{"frames":[]}')
        self.authority=frozen(self.refs,seed_inputs=self.inputs)

    def verify(self,**kwargs):
        return verified_references(self.refs,self.authority['experiment_manifest'],
            self.authority['experiment_manifest_sha256'],input_manifest=self.inputs/'manifest.json',
            input_kind='seed_inputs',**kwargs)

    def test_exact_freeze_passes_and_output_records_external_anchor(self):
        refs,record=self.verify()
        self.assertEqual(refs,{'frames':[]})
        self.assertEqual(record['experiment_manifest_sha256'],self.authority['experiment_manifest_sha256'])

    def test_changed_reference_and_rebound_manifest_refused_by_external_hash(self):
        self.refs.write_text('{"frames":[{"changed_mask":true}]}')
        with self.assertRaisesRegex(ValueError,'reference differs'):self.verify()
        path=self.authority['experiment_manifest'];manifest=json.loads(path.read_bytes())
        manifest['reference_sha256']=digest(self.refs.read_bytes());path.write_bytes(canonical(manifest))
        with self.assertRaisesRegex(ValueError,'manifest differs'):self.verify()

    def test_source_drift_input_drift_and_policy_drift_refuse(self):
        with patch('research.object_discovery_boundaries_v1.experiment.source_pins',return_value={}):
            with self.assertRaisesRegex(ValueError,'evaluation source differs'):self.verify()
        with self.assertRaisesRegex(ValueError,'scoring policy differs'):self.verify(match_iou=.6)
        with self.assertRaisesRegex(ValueError,'scoring policy differs'):self.verify(levels=('parts',))
        (self.inputs/'manifest.json').write_text('{"rehashed":true}')
        with self.assertRaisesRegex(ValueError,'input manifest differs'):self.verify()

    def test_missing_or_malformed_external_anchor_refuses(self):
        for bad in (None,'',True,'self-derived','a'*63):
            self.authority['experiment_manifest_sha256']=bad
            with self.assertRaisesRegex(ValueError,'externally frozen'):self.verify()


if __name__=='__main__':unittest.main()
