"""Synthetic manifests only; production must retain the hash independently."""
from pathlib import Path
from research.object_discovery_boundaries_v1.experiment import source_pins
from research.object_discovery_boundaries_v1.reference_audit import canonical,digest


def frozen(references,*,seed_inputs=None,preparation=None):
    manifest=dict(schema='object_boundary_experiment_v1',experiment_id='SYNTHETIC-TEST-ONLY',
        reference_sha256=digest(Path(references).read_bytes()),levels=['whole'],match_iou=.5,
        evaluation_source_sha256=source_pins(),input_manifest_sha256={kind:digest((Path(folder)/name).read_bytes())
            for kind,folder,name in [('seed_inputs',seed_inputs,'manifest.json'),
                                     ('preparation',preparation,'preparation-manifest.json')] if folder is not None})
    path=Path(references).with_suffix('.experiment.json');raw=canonical(manifest);path.write_bytes(raw)
    return dict(experiment_manifest=path,experiment_manifest_sha256=digest(raw))
