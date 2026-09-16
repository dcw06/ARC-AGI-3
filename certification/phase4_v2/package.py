"""Standard-library-only allowlisted offline artifact packaging and verification."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(environments, wheels, root=ROOT):
    """Select only frozen development directories, never arbitrary game discovery."""
    pairs = json.loads((root / 'config/e1_experiment_protocol.yaml').read_text())['development_game_seed_pairs']
    files = {}
    for pair in pairs:
        base, version = pair['game_id'].split('-', 1)
        folder = environments / base / version
        for name in (base + '.py', 'metadata.json'):
            if not (folder / name).is_file():
                raise FileNotFoundError(f'missing frozen development artifact: {pair["game_id"]}/{name}')
        for p in sorted(folder.rglob('*')):
            if p.is_symlink() or not p.resolve().is_relative_to(environments.resolve()):
                raise ValueError('artifact symlink/escape')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                files['environment_files/' + p.relative_to(environments).as_posix()] = p
    dependencies = sorted(wheels.glob('*.whl'))
    if not dependencies:
        raise FileNotFoundError('offline dependency wheels missing')
    # Complete dependency closure is checked by offline pip --dry-run before target freeze.
    for p in dependencies:
        if p.is_symlink():
            raise ValueError('wheel symlink')
        files['wheels/' + p.name] = p
    return files


def build(environments, wheels, output, root=ROOT):
    files = inventory(Path(environments), Path(wheels), root)
    manifest = {'schema_version': 1, 'scope': '15_allowlisted_development_games_only',
        'dependency_resolution_verified': False,
        'files': {n: {'sha256': sha(p), 'bytes': p.stat().st_size} for n, p in files.items()}}
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, p in files.items():
            archive.writestr(name, p.read_bytes())
        archive.writestr('manifest.json', json.dumps(manifest, sort_keys=True))
    verify(output, expected_sha256=sha(Path(output)))
    return {'archive_sha256': sha(Path(output)), **manifest}


def verify(archive_path, *, expected_sha256):
    if sha(Path(archive_path)) != expected_sha256:
        raise ValueError('archive hash mismatch')
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate archive members')
        manifest = json.loads(archive.read('manifest.json'))
        if set(names) != set(manifest['files']) | {'manifest.json'}:
            raise ValueError('unexpected archive inventory')
        for name, info in manifest['files'].items():
            p = Path(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:
                raise ValueError('unsafe archive path')
            data = archive.read(name)
            if len(data) != info['bytes'] or hashlib.sha256(data).hexdigest() != info['sha256']:
                raise ValueError('artifact hash mismatch: ' + name)
    return manifest


def verify_environment_mount(environments, manifest):
    environments = Path(environments)
    expected = {n.removeprefix('environment_files/'): v
                for n, v in manifest['files'].items() if n.startswith('environment_files/')}
    found = {}
    for path in environments.rglob('*'):
        if path.is_symlink():
            raise ValueError('environment symlink')
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            found[path.relative_to(environments).as_posix()] = path
    if set(found) != set(expected):
        raise ValueError('environment mount inventory differs from package')
    for name, path in found.items():
        if path.stat().st_size != expected[name]['bytes'] or sha(path) != expected[name]['sha256']:
            raise ValueError('environment mount hash mismatch: ' + name)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environments', type=Path, required=True)
    parser.add_argument('--wheels', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    if args.manifest.exists():
        raise FileExistsError('manifest already exists')
    result = build(args.environments, args.wheels, args.output)
    with args.manifest.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'archive_sha256': result['archive_sha256'], 'files': len(result['files'])}))
