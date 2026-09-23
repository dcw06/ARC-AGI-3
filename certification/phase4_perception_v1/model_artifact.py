import hashlib
import time
from pathlib import Path
from evaluation.m0_profile import ArtifactInventory
from certification.phase4_perception_v1.startup import marker


def inventory_artifact_tree(root, *, clock=time.monotonic, emit=marker):
    """Same artifact-tree-v1 digest, with cumulative progress every 10 seconds.

    Progress is emitted only after a read returns; a stuck read leaves its stage
    begin/last-progress marker, never a misleading heartbeat claiming progress.
    """
    base = Path(root).resolve()
    if not base.is_dir():
        raise ValueError('artifact root must be a directory')
    digest = hashlib.sha256(b'arc3-artifact-tree-v1\0')
    count = total = read_bytes = 0
    last = clock()
    for path in sorted(base.rglob('*'), key=lambda item: item.relative_to(base).as_posix()):
        if path.is_symlink():
            raise ValueError('artifact tree contains a symlink')
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix().encode()
        size = path.stat().st_size
        file_digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                file_digest.update(chunk)
                read_bytes += len(chunk)
                now = clock()
                if now - last >= 10:
                    emit('artifact_hash', 'progress', bytes_read=read_bytes, files_completed=count)
                    last = now
        digest.update(len(relative).to_bytes(4, 'big'))
        digest.update(relative)
        digest.update(size.to_bytes(8, 'big'))
        digest.update(file_digest.digest())
        count += 1
        total += size
    if not count:
        raise ValueError('artifact tree is empty')
    emit('artifact_hash', 'complete', bytes_read=read_bytes, files_completed=count)
    return ArtifactInventory(digest.hexdigest(), count, total)

def verify_artifact(primary):
    path = primary.model_path
    if path.is_symlink():
        raise ValueError("model root must not be a symlink")
    inventory = inventory_artifact_tree(path)
    if inventory.tree_sha256 != primary.model_tree_sha256:
        raise ValueError("model artifact SHA-256 mismatch")
    if (any(not (path / name).is_file() for name in primary.required_files)
            or len(list(path.glob(primary.shard_glob))) != primary.shard_count):
        raise ValueError("model artifact layout mismatch")
    return {"tree_sha256": inventory.tree_sha256, "bytes": inventory.total_bytes,
            "file_count": inventory.file_count}

