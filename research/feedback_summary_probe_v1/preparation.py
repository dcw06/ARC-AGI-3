"""Seal new checkpoint requests without changing the completed experiment."""
from copy import deepcopy
import json
from pathlib import Path

from research.feedback_probe_v1.checkpoints import checked_checkpoint
from research.feedback_probe_v1.preparation import verify_prepared as verify_original
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha
from .audit import audit_recognition_request
from .interface import VARIANTS, policy_request, recognition_request

MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'


def protocol():
    path = Path(__file__).with_name('protocol.json')
    return json.loads(path.read_bytes())


def derive_checkpoints(original):
    if type(original) is not list or len(original) != 8:
        raise ValueError('requires all eight frozen checkpoints')
    result = deepcopy(original)
    for ordinal, checkpoint in enumerate(result):
        checked_checkpoint(checkpoint, model=MODEL)
        checkpoint['order'] = list(VARIANTS if ordinal % 2 == 0 else reversed(VARIANTS))
    return result


def model_rows(checkpoints):
    rows = []
    for checkpoint in checkpoints:
        for variant in VARIANTS:
            for kind in ('recognition', 'policy'):
                identity = checkpoint['checkpoint_id']
                body = (recognition_request(checkpoint['base_request'], variant) if kind == 'recognition'
                        else policy_request(checkpoint['base_request'], variant))
                if kind == 'recognition':
                    audit_recognition_request(checkpoint, variant, body)
                row = {'checkpoint_id': identity, 'variant': variant, 'kind': kind,
                       'path': f'model-inputs/{identity}-{variant}-{kind}.json',
                       'request_sha256': digest(body)}
                rows.append((row, body))
    return rows


def verify_prepared(root, lock_pin, source):
    root = Path(root)
    manifest = verify_original(root, lock_pin, source)
    frozen = protocol()
    if (manifest.get('schema') != 'feedback_summary_probe_CPU_inputs_v1' or
            manifest.get('protocol_sha256') != sha(Path(__file__).with_name('protocol.json')) or
            digest(manifest.get('prospective_maxima')) != digest(frozen['prospective_maxima'])):
        raise ValueError('summary-probe CPU protocol differs')
    for name in ('source_review_lock_sha256', 'source_evaluation_sha256',
                 'source_run_evidence_sha256', 'source_input_manifest_sha256'):
        if manifest.get(name) != frozen[name]:
            raise ValueError('source provenance differs: '+name)
    original = json.loads((root/'source-checkpoints.json').read_bytes())['checkpoints']
    if sha(root/'source-checkpoints.json') != frozen['source_checkpoint_file_sha256']:
        raise ValueError('source checkpoints differ from external frozen bytes')
    expected = derive_checkpoints(original)
    actual = json.loads((root/'checkpoints.json').read_bytes())['checkpoints']
    if digest(actual) != digest(expected) or digest(original) != manifest['source_checkpoint_inventory_sha256']:
        raise ValueError('checkpoint selection or paired order changed')
    rows = model_rows(actual)
    if digest(manifest['model_input_rows']) != digest([row for row, _ in rows]):
        raise ValueError('frozen request inventory changed')
    for row, body in rows:
        if digest(json.loads((root/row['path']).read_bytes())) != digest(body):
            raise ValueError('prepared request differs from observed checkpoint')
    allowlist = {'checkpoints.json'} | {row['path'] for row, _ in rows}
    if set(manifest['future_inference_allowlist']) != allowlist:
        raise ValueError('reference data or extra files in future inference allowlist')
    return manifest
