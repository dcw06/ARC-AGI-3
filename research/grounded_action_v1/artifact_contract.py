"""Frozen Stage B model artifact identity shared by host and game worker."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def expected_artifact(root=ROOT):
    from certification.phase4_integrated_v2.model_process import load_operational_primary

    root = Path(root)
    primary = load_operational_primary(root)
    profile = json.loads((root / 'reports/m0_profiles/m0-q3vl30-instruct.json').read_bytes())
    artifact = profile['artifact']
    count = artifact['file_count']
    size = profile['measurements']['offline_artifact_bytes']
    if (artifact['tree_sha256'] != primary.model_tree_sha256 or
            type(count) is not int or count <= 0 or
            type(size) is not int or size <= 0):
        raise ValueError('pinned model artifact identity drift')
    return {'tree_sha256': artifact['tree_sha256'], 'file_count': count,
            'bytes': size}
