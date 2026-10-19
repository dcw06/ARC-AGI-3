"""Verify an externally pinned CPU snapshot before scripted checks or token audit."""
import json
from pathlib import Path
from research.initial_geometry_assistance_v1.live_io import sha
from .source_closure import safe_member, verify_source_inventory


def verify_prepared(root, lock_pin, source):
    root, source = Path(root), Path(source)
    if sha(safe_member(root, 'draft-lock.json')) != lock_pin:
        raise ValueError('CPU draft lock differs from external pin')
    lock = json.loads((root/'draft-lock.json').read_bytes())
    if lock['live_launch_package'] is not False or sha(safe_member(root, 'manifest.json')) != lock['manifest_sha256']:
        raise ValueError('prepared manifest or no-launch scope differs')
    verify_source_inventory(source, lock['sources'])
    manifest = json.loads((root/'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        if sha(safe_member(root, name)) != expected:
            raise ValueError('prepared artifact changed/unsafe: '+name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'manifest.json', 'draft-lock.json'}:
        raise ValueError('unexpected prepared files')
    return manifest
