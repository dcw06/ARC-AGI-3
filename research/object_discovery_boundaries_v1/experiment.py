"""Externally frozen evaluation inputs. Evaluators never create their own freeze."""
import json
from pathlib import Path
import re

from .reference_audit import digest

ROOT = Path(__file__).resolve().parents[2]
SOURCE_NAMES = (
    'research/object_discovery_boundaries_v1/experiment.py',
    'research/object_discovery_boundaries_v1/scoring.py',
    'research/object_discovery_boundaries_v1/masks.py',
    'research/object_discovery_boundaries_v1/reference_audit.py',
    'research/object_discovery_boundaries_v1/prepare.py',
    'research/object_discovery_boundaries_v1/evaluation.py',
    'research/object_discovery_boundaries_v1/sam21.py',
    'research/object_discovery_boundaries_v1/granularity.py',
    'research/object_discovery_boundaries_v1/granularity_backends.py',
    'research/object_discovery_boundaries_v1/granularity_runtime.py',
    'research/object_discovery_boundaries_v1/granularity_worker.py',
    'certification/phase4_multimodal_preflight_v3/images.py',
    'scripts/evaluate_granularity_segmentation.py',
    'scripts/evaluate_object_boundaries.py',
    'scripts/freeze_object_boundary_experiment.py',
)


def source_pins():
    return {name: digest((ROOT/name).read_bytes()) for name in SOURCE_NAMES}


def verified_references(references, manifest_path, manifest_sha256, *,
                        input_manifest, input_kind, levels=('whole',), match_iou=.5):
    """Check the external anchor, reference bytes, policy and sources before use.

    The digest must come from the reviewed experiment record, not a digest
    calculated from whichever manifest happens to accompany an output folder.
    This is an integrity check, not an owner approval or a preregistration claim.
    """
    if type(manifest_sha256) is not str or not re.fullmatch('[0-9a-f]{64}', manifest_sha256):
        raise ValueError('externally frozen experiment manifest SHA256 required')
    path = Path(manifest_path)
    raw_manifest=path.read_bytes()
    if path.is_symlink() or digest(raw_manifest) != manifest_sha256:
        raise ValueError('experiment manifest differs from external freeze')
    frozen = json.loads(raw_manifest)
    if frozen.get('schema') != 'object_boundary_experiment_v1' or not frozen.get('experiment_id'):
        raise ValueError('frozen experiment schema/identity required')
    if (type(match_iou) not in (int, float) or frozen.get('match_iou') != match_iou or
            frozen.get('levels') != list(levels)):
        raise ValueError('scoring policy differs from frozen experiment')
    if frozen.get('evaluation_source_sha256') != source_pins():
        raise ValueError('evaluation source differs from frozen experiment')
    inputs = Path(input_manifest)
    if (input_kind not in ('seed_inputs', 'preparation') or inputs.is_symlink() or
            frozen.get('input_manifest_sha256', {}).get(input_kind) != digest(inputs.read_bytes())):
        raise ValueError('input manifest differs from frozen experiment')
    reference_path = Path(references)
    if reference_path.is_symlink():
        raise ValueError('reference symlink refused')
    raw = reference_path.read_bytes()
    if digest(raw) != frozen.get('reference_sha256'):
        raise ValueError('reviewed reference differs from frozen experiment')
    return json.loads(raw), dict(experiment_manifest_sha256=manifest_sha256,
        experiment_id=frozen['experiment_id'], reference_sha256=digest(raw),
        evaluation_source_sha256=frozen['evaluation_source_sha256'])
