"""Verify an externally pinned CPU snapshot before scripted checks or token audit."""
import json
from pathlib import Path, PurePosixPath
from research.initial_geometry_assistance_v1.live_io import sha


def verify_prepared(root, lock_pin, source):
    root, source = Path(root), Path(source)
    if sha(root/'draft-lock.json') != lock_pin:
        raise ValueError('CPU draft lock differs from external pin')
    lock = json.loads((root/'draft-lock.json').read_bytes())
    if lock['live_launch_package'] is not False or sha(root/'manifest.json') != lock['manifest_sha256']:
        raise ValueError('prepared manifest or no-launch scope differs')
    for name, expected in lock['sources'].items():
        if sha(source/name) != expected: raise ValueError('prepared source changed: '+name)
    manifest = json.loads((root/'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or (root/name).is_symlink() or sha(root/name) != expected:
            raise ValueError('prepared artifact changed/unsafe: '+name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'manifest.json', 'draft-lock.json'}:
        raise ValueError('unexpected prepared files')
    return manifest
