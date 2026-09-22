"""Standard-library local monitor handshake; no GPU readiness claim."""
import json
import os
from pathlib import Path

KIND = 'local_cpu_monitor_ready'


def publish_local_ready():
    """Called by a local monitor after its own initialization succeeds."""
    path = Path(os.environ['P4_READY_PATH'])
    value = {'kind': KIND, 'nonce': os.environ['P4_READY_NONCE'],
             'worker_pid': int(os.environ['P4_WORKER_PID']), 'monitor_pid': os.getpid()}
    temporary = path.with_suffix('.tmp')
    with temporary.open('x') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_local_ready(path, *, nonce, worker_pid, monitor_pid):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
        raise ValueError('invalid monitor-ready file')
    value = json.loads(path.read_text())
    expected = {'kind': KIND, 'nonce': nonce,
                'worker_pid': worker_pid, 'monitor_pid': monitor_pid}
    if (value != expected or type(value.get('worker_pid')) is not int
            or type(value.get('monitor_pid')) is not int):
        raise ValueError('monitor-ready identity/schema mismatch')
    return value
