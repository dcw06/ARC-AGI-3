from evaluation.m0_profile import inventory_artifact_tree

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


