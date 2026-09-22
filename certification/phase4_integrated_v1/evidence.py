"""Single shared cross-process budget for the frozen 128 MiB output envelope."""
import fcntl
import json
import os
import time
from pathlib import Path

MIB = 1024**2
LIMITS = {'control':4*MIB,'monitor':16*MIB,'worker':88*MIB,'evaluation':12*MIB,'logs':8*MIB}
TOTAL = 128*MIB


class EvidenceStore:
    """Every producer must use this writer; uncontrolled logs remain forbidden.

    Atomic replacement peak counts both old and temporary files. A component's
    last 4 KiB is reserved for a bounded failure receipt, not more telemetry.
    """
    def __init__(self, root, component):
        if component not in LIMITS:
            raise ValueError('unknown evidence component')
        self.root, self.component = Path(root), component
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise ValueError('symlink evidence root')

    def save(self, name, value, *, failure_receipt=False):
        return self.write(name, json.dumps(value, sort_keys=True, allow_nan=False).encode(),
                          failure_receipt=failure_receipt)

    def write(self, name, data, *, failure_receipt=False):
        if Path(name).name != name or name in ('', '.', '..') or not name.endswith('.json'):
            raise ValueError('invalid evidence filename')
        if failure_receipt and name != 'failure.json':
            raise ValueError('reserved bytes only for failure.json')
        if self.component=='worker' and len(data)>MIB: raise ValueError('worker record ceiling')
        if not isinstance(data, bytes):
            raise TypeError('evidence payload must be bytes')
        if failure_receipt and len(data) > 2048:
            raise ValueError('oversized failure receipt')
        lock_path = self.root / '.evidence.lock'
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+b') as lock:
            begin=time.monotonic()
            fcntl.flock(lock, fcntl.LOCK_EX)
            locked=time.monotonic()
            sizes = {component: 0 for component in LIMITS}
            total = 0
            for entry in self.root.rglob('*'):
                if entry.is_symlink():
                    raise ValueError('symlink in evidence store')
                if entry.is_file():
                    relative = entry.relative_to(self.root)
                    if entry != lock_path and relative.parts[0] not in LIMITS:
                        raise ValueError('unbudgeted evidence file')
                    size = entry.stat().st_size
                    total += size
                    if entry != lock_path:
                        sizes[relative.parts[0]] += size
            scanned=time.monotonic()
            ceiling = LIMITS[self.component] - (0 if failure_receipt else 4096)
            if sizes[self.component] + len(data) > ceiling or total + len(data) > TOTAL:
                raise ValueError('aggregate/component evidence budget exhausted')
            folder = self.root / self.component
            folder.mkdir(exist_ok=True)
            path = folder / name
            temporary = path.with_suffix('.tmp')
            write_started=time.monotonic()
            with temporary.open('xb') as stream:
                stream.write(data); stream.flush()
                flushed=time.monotonic()
                os.fsync(stream.fileno())
                synced=time.monotonic()
            os.replace(temporary, path)
            self.last_write_timings={'lock_seconds':locked-begin,'scan_seconds':scanned-locked,
                'write_seconds':flushed-write_started,'fsync_seconds':synced-flushed,
                'replace_seconds':time.monotonic()-synced}
            return path
