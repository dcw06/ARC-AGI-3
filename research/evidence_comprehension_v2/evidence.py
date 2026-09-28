"""Failure-safe run evidence for evidence comprehension v2: one append-only call log, a byte budget, a manifest.

v1 kept one file per call. The shared output store (certification/phase4_integrated_v2/evidence.py) walks and
stats the whole output tree under its lock on every write, and the resource monitor writes several times a
second, so with one file per call each scan grew with the run: in a CPU rehearsal of v2's 8,004 calls the
worker's per-call slot rose from 13 ms to 450 ms by call 2,700 (host-side time stayed at about 3 ms). v2
therefore appends each call as one line of `calls.jsonl` instead, keeping the tree to a few files.

Guarantees are v1's:
- each call is durable before the next starts: the line is written and fsynced, then the manifest (the
  call log's SHA-256, byte length and line count, and each other file's SHA-256 and size) is atomically
  replaced;
- a crash between the two leaves a log longer than the manifest says, and a torn line fails parsing, so
  partial evidence is retained but can never be mistaken for complete evidence;
- a byte budget with a reserve keeps room for the final run index.

The runner's interface is unchanged: `writer(folder / 'calls/NNNNN.json', record)` appends call NNNNN (which must
be the next call) and `writer(folder / 'run.json', index)` replaces the index. `load_verified` returns the
same structure as v1's: the index with `calls` in order.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

from research.evidence_comprehension_v1.evidence import (  # noqa: F401  (unchanged helpers, re-exported)
    EvidenceError, StorageExhausted, atomic_write, encode)

MANIFEST = 'manifest.json'
CALLS = 'calls.jsonl'
VERSION = 'evidence_comprehension_evidence_v2'
_CALL_PATH = re.compile(r'calls/(\d{5})\.json')


class RunEvidence:
    """Callable writer for the runner: writer(absolute_path, value, reserve_bytes=0)."""

    def __init__(self, folder, budget_bytes=64 * 1024**2, lock_root=None):
        self.folder = Path(folder)
        self.budget = budget_bytes
        self.lock_path = Path(lock_root) / '.evidence.lock' if lock_root is not None else None
        if (self.folder / MANIFEST).exists() or (self.folder / CALLS).exists():
            raise FileExistsError('run evidence folder already used')
        self.files = {}
        self.calls = {'sha256': hashlib.sha256().hexdigest(), 'bytes': 0, 'lines': 0}
        self._hash = hashlib.sha256()
        self.sequence = 0

    def _used(self, excluding=None):
        return self.calls['bytes'] + sum(v['bytes'] for k, v in self.files.items() if k != excluding)

    def __call__(self, path, value, reserve_bytes=0):
        relative = Path(path).resolve().relative_to(self.folder.resolve()).as_posix()
        if relative in (MANIFEST, CALLS) or '..' in relative.split('/'):
            raise ValueError('reserved or unsafe evidence path')
        call = _CALL_PATH.fullmatch(relative)
        raw = encode(value)
        if call:
            if int(call.group(1)) != self.calls['lines']:
                raise ValueError('calls must be appended in order')
            line = raw + b'\n'
            if self._used() + len(line) + reserve_bytes > self.budget:
                raise StorageExhausted(f'evidence budget {self.budget} bytes exhausted writing {relative}')
        elif self._used(relative) + len(raw) + reserve_bytes > self.budget:
            raise StorageExhausted(f'evidence budget {self.budget} bytes exhausted writing {relative}')
        with self._locked():
            self.folder.mkdir(parents=True, exist_ok=True)
            if call:
                with (self.folder / CALLS).open('ab') as stream:
                    stream.write(line)
                    stream.flush()
                    os.fsync(stream.fileno())
                self._hash.update(line)
                self.calls = {'sha256': self._hash.hexdigest(), 'bytes': self.calls['bytes'] + len(line),
                              'lines': self.calls['lines'] + 1}
            else:
                atomic_write(self.folder / relative, raw)
                self.files[relative] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            self.sequence += 1
            atomic_write(self.folder / MANIFEST, encode({'version': VERSION, 'sequence': self.sequence,
                                                         'calls': self.calls, 'files': self.files}))

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
    """Reassemble the run: index plus every logged call; reject missing, extra, truncated or mismatched evidence."""
    folder = Path(folder)
    try:
        manifest = json.loads((folder / MANIFEST).read_bytes())
    except (OSError, ValueError) as exc:
        raise EvidenceError('manifest missing or unreadable') from exc
    if (manifest.get('version') != VERSION or not isinstance(manifest.get('files'), dict)
            or not isinstance(manifest.get('calls'), dict)):
        raise EvidenceError('manifest version')
    on_disk = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} - {MANIFEST}
    if any(name.endswith('.tmp') for name in on_disk):
        raise EvidenceError('interrupted write left a temporary file')
    expected = set(manifest['files']) | ({CALLS} if manifest['calls'].get('lines') else set())
    if on_disk != expected:
        raise EvidenceError(f'file inventory mismatch: missing {sorted(expected - on_disk)[:3]}, '
                            f'extra {sorted(on_disk - expected)[:3]}')
    if set(manifest['files']) != {'run.json'}:
        raise EvidenceError('unexpected run evidence file')
    for name, row in manifest['files'].items():
        path = folder / name
        if path.is_symlink():
            raise EvidenceError('symlinked evidence: ' + name)
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise EvidenceError('truncated or mismatched evidence: ' + name)
    calls = []
    if manifest['calls'].get('lines'):
        path = folder / CALLS
        if path.is_symlink():
            raise EvidenceError('symlinked evidence: ' + CALLS)
        raw = path.read_bytes()
        if len(raw) != manifest['calls']['bytes'] or hashlib.sha256(raw).hexdigest() != manifest['calls']['sha256']:
            raise EvidenceError('truncated or mismatched evidence: ' + CALLS)
        if not raw.endswith(b'\n'):
            raise EvidenceError('torn call log line')
        try:
            calls = [json.loads(line) for line in raw[:-1].split(b'\n')]
        except ValueError as exc:
            raise EvidenceError('unreadable call log line') from exc
        if len(calls) != manifest['calls']['lines']:
            raise EvidenceError('call log line count differs from the manifest')
    for n, call in enumerate(calls):
        if not isinstance(call, dict) or call.get('index') != n:
            raise EvidenceError(f'call {n} carries index {call.get("index") if isinstance(call, dict) else None}')
    index = json.loads((folder / 'run.json').read_bytes())
    if index.get('calls_recorded') != len(calls):
        raise EvidenceError('run index disagrees with the retained calls')
    return {**index, 'calls': calls}


# ------------------------------------------------------------------ test utilities (consistent forgeries)

def _rewrite(folder, calls, files):
    folder = Path(folder)
    raw = b''.join(encode(c) + b'\n' for c in calls)
    (folder / CALLS).write_bytes(raw)
    for name, value in files.items():
        (folder / name).write_bytes(encode(value))
    manifest = json.loads((folder / MANIFEST).read_bytes())
    manifest['calls'] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'lines': len(calls)}
    for name in files:
        data = (folder / name).read_bytes()
        manifest['files'][name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    (folder / MANIFEST).write_bytes(encode(manifest))


def forge(folder, name, mutate):
    """Change one retained record (`calls/NNNNN.json` or `run.json`) and re-hash it into the manifest."""
    folder = Path(folder)
    calls = load_unverified_calls(folder)
    index = json.loads((folder / 'run.json').read_bytes())
    call = _CALL_PATH.fullmatch(name)
    if call:
        mutate(calls[int(call.group(1))])
    elif name == 'run.json':
        mutate(index)
    else:
        raise ValueError(name)
    _rewrite(folder, calls, {'run.json': index})


def truncate(folder, keep):
    """Keep only the first `keep` calls, consistently re-hashed (the index is left for the caller to adjust)."""
    _rewrite(folder, load_unverified_calls(folder)[:keep], {})


def load_unverified_calls(folder):
    path = Path(folder) / CALLS
    return [json.loads(line) for line in path.read_bytes().splitlines()] if path.exists() else []
