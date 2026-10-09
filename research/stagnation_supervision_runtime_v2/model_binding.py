"""Runtime v2 model binding (hand-written).

The frozen Track 3 model identity is unchanged: Qwen/Qwen3-VL-30B-A3B-Instruct-FP8 at revision d9748a51, served by
vLLM 0.19.0 as instruct/non-thinking with the m0 launch specification, the same six tokenizer/chat-template files
(byte-identical, checked by the derivation) and the same required-file and four-shard layout. Only the attachment
container changes: the R4/R6 packages bound the Kaggle Model qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1
(81 files, tree 052ab27f...), while the verified runtime consumes a version-pinned dataset-backed snapshot of the
upstream revision (20 files, tree b480ad92...). The private dataset reference and mount path stay REPLACE_WITH_
placeholders until a privately bound successor review; with placeholders the mount resolution refuses.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'research/stagnation_supervision_runtime_v2/protocol.json'


def tree_digest(rows):
    """arc3-artifact-tree-v1 over (path, size, binary SHA-256) rows, as host tree hashing computes it."""
    digest = hashlib.sha256(b'arc3-artifact-tree-v1\0')
    for row in sorted(rows, key=lambda r: r['path']):
        path = row['path'].encode()
        digest.update(len(path).to_bytes(4, 'big') + path + row['bytes'].to_bytes(8, 'big') + bytes.fromhex(row['sha256']))
    return digest.hexdigest()


def model_section(root=ROOT):
    model = json.loads((Path(root) / PROTOCOL).read_bytes())['model']
    rows = model['files']
    if (tree_digest(rows) != model['tree_sha256'] or len(rows) != model['file_count']
            or sum(r['bytes'] for r in rows) != model['bytes'] or len({r['path'] for r in rows}) != len(rows)):
        raise ValueError('model snapshot inventory does not reproduce its pinned tree digest')
    return model


def expected_artifact(root=ROOT):
    """The identity the model host must verify and the game worker must accept (tree, file count, bytes)."""
    model = model_section(root)
    return {'tree_sha256': model['tree_sha256'], 'file_count': model['file_count'], 'bytes': model['bytes']}


def bind_primary(root, primary):
    """The frozen operational primary with only the model location and tree pin replaced by the verified binding."""
    from research.stagnation_supervision_runtime_v2.publisher_host import model_mount
    model = model_section(root)
    if (tuple(model['required_files']) != tuple(primary.required_files) or model['shard_glob'] != primary.shard_glob
            or model['shard_count'] != primary.shard_count or model['revision'] != primary.binding.revision
            or model['model_id'] != primary.binding.model_id):
        raise ValueError('model identity or layout differs from the frozen Track 3 binding')
    mount = model_mount(model)  # placeholders, ambiguity or a wrong layout refuse here, before any hashing
    return replace(primary, model_path=Path(mount['mounted_path']), model_tree_sha256=model['tree_sha256'])
