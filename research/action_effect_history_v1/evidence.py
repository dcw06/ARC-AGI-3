"""Failure-safe run evidence: atomic checkpoints, a byte budget, and a hash manifest.

Each file is written to a temporary name, fsynced and renamed; the manifest (every file's SHA-256
and size) is then rewritten the same way. A crash between the two leaves a detectable mismatch,
so partial evidence is retained but can never be mistaken for complete evidence.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path

MANIFEST = 'manifest.json'
VERSION = 'action_effect_history_evidence_v1'


class StorageExhausted(OSError):
    pass


class EvidenceError(ValueError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def atomic_write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


class RunEvidence:
    """Callable writer for the runner: writer(absolute_path, value)."""

    def __init__(self, folder, budget_bytes=64 * 1024**2, lock_root=None):
        self.folder = Path(folder)
        self.budget = budget_bytes
        # Share the output tree's evidence lock so concurrent scanners (the monitor's store)
        # never observe a temporary file mid-rename.
        self.lock_path = Path(lock_root) / '.evidence.lock' if lock_root is not None else None
        self.files = {}
        self.sequence = 0
        if (self.folder / MANIFEST).exists():
            raise FileExistsError('run evidence folder already used')

    def __call__(self, path, value):
        relative = Path(path).resolve().relative_to(self.folder.resolve()).as_posix()
        if relative == MANIFEST or '..' in relative.split('/'):
            raise ValueError('reserved or unsafe evidence path')
        raw = encode(value)
        used = sum(v['bytes'] for k, v in self.files.items() if k != relative)
        if used + len(raw) > self.budget:
            raise StorageExhausted(f'evidence budget {self.budget} bytes exhausted writing {relative}')
        with self._locked():
            atomic_write(self.folder / relative, raw)
            self.files[relative] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            self.sequence += 1
            atomic_write(self.folder / MANIFEST, encode({'version': VERSION, 'sequence': self.sequence,
                                                         'files': self.files}))

    @contextlib.contextmanager
    def _locked(self):
        if self.lock_path is None:
            yield
            return
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield


def load_verified(folder):
    """Reassemble the run report; reject missing, extra, truncated, mismatched or duplicate files."""
    folder = Path(folder)
    try:
        manifest = json.loads((folder / MANIFEST).read_bytes())
    except (OSError, ValueError) as exc:
        raise EvidenceError('manifest missing or unreadable') from exc
    if manifest.get('version') != VERSION or not isinstance(manifest.get('files'), dict):
        raise EvidenceError('manifest version')
    on_disk = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} - {MANIFEST}
    if any(name.endswith('.tmp') for name in on_disk):
        raise EvidenceError('interrupted write left a temporary file')
    if on_disk != set(manifest['files']):
        raise EvidenceError(f'file inventory mismatch: missing {sorted(set(manifest["files"]) - on_disk)[:3]}, '
                            f'extra {sorted(on_disk - set(manifest["files"]))[:3]}')
    for name, row in manifest['files'].items():
        path = folder / name
        if path.is_symlink():
            raise EvidenceError('symlinked evidence: ' + name)
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise EvidenceError('truncated or mismatched evidence: ' + name)
    index = json.loads((folder / 'run.json').read_bytes())
    ids = [e['episode_id'] for e in index['episodes']]
    if len(ids) != len(set(ids)):
        raise EvidenceError('duplicate episode ids in index')
    episode_files = {n for n in manifest['files'] if n.startswith('episodes/')}
    if episode_files != {f'episodes/{i}.json' for i in ids}:
        raise EvidenceError('episode files do not match the index')
    episodes = [json.loads((folder / f'episodes/{i}.json').read_bytes()) for i in ids]
    for summary, episode in zip(index['episodes'], episodes):
        if (episode['episode_id'] != summary['episode_id'] or episode['status'] != summary['status']
                or episode['stop_reason'] != summary['stop_reason']):
            raise EvidenceError('episode file disagrees with index: ' + summary['episode_id'])
    return {**index, 'episodes': episodes}
