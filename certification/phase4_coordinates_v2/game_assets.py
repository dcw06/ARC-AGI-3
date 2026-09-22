"""Stage only immutable manifest-selected development games before installation."""
import hashlib
from pathlib import Path, PurePosixPath
from certification.phase4_v2.package import verify_environment_mount


def stage_games(mount, destination, manifest):
    mount, destination = Path(mount), Path(destination)
    if mount.is_symlink() or not mount.is_dir():
        raise ValueError('invalid game mount')
    selected = {name.removeprefix('environment_files/'): info
                for name, info in manifest['files'].items()
                if name.startswith('environment_files/')}
    if not selected:
        raise ValueError('empty game manifest')
    destination.mkdir(exist_ok=False)
    for name, info in selected.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
            raise ValueError('unsafe game path: '+name)
        source = mount
        for part in relative.parts:
            source = source/part
            if source.is_symlink():
                raise ValueError('game symlink: '+name)
        if not source.resolve().is_relative_to(mount.resolve()):
            raise ValueError('game path escape: '+name)
        if not source.is_file():
            raise ValueError('missing frozen game: '+name)
        if source.stat().st_size != info['bytes']:
            raise ValueError('frozen game size mismatch: '+name)
        with source.open('rb') as stream:
            data = stream.read(info['bytes']+1)
        if len(data) != info['bytes'] or hashlib.sha256(data).hexdigest() != info['sha256']:
            raise ValueError('frozen game hash mismatch: '+name)
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    verify_environment_mount(destination, manifest)
    return destination
