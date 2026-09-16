"""Standard-library-only review/compute gate. Never creates authorization."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = 'certification/phase4_v4'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root=ROOT):
    # This module and the shared inventory helper import only the standard library.
    from evaluation.phase4_execution import source_names
    names = set(source_names(root))
    for revision in ('phase4_v1', 'phase4_v2', 'phase4_v3', 'phase4_v4'):
        folder = root / 'certification' / revision
        names.update(p.relative_to(root).as_posix() for p in folder.glob('*.py'))
        names.update(p.relative_to(root).as_posix() for p in folder.glob('*.json')
                     if p.name not in ('compute_ledger.json', 'execution_lock.json'))
    names.update({'config/phase4_execution_lock_v2.json', 'reports/phase4_v2_offline_package.json'})
    return sorted(names)


def authority(root=ROOT):
    folder = root / FOLDER
    protocol = json.loads((folder / 'protocol.json').read_text())
    ledger = json.loads((folder / 'compute_ledger.json').read_text())
    # Explicitly fail before importing agent, torch, arcengine, or starting install.
    if (protocol.get('execution_ready') is not True or
            ledger.get('authorized_seconds') != 28800 or not ledger.get('approval_reference')):
        raise PermissionError('v4 is review-only: execution readiness and separate approval required')
    lock_path = folder / 'execution_lock.json'
    lock = json.loads(lock_path.read_text())
    required = {f'{FOLDER}/{n}' for n in ('authority.py', 'protocol.json', 'service.py',
        'worker.py', 'supervisor.py', 'run_target.py', 'evaluate.py', 'build_notebook.py')}
    if (not required <= set(lock.get('bindings', {}))
            or set(lock['bindings']) != set(inventory(root))):
        raise PermissionError('incomplete reviewed execution lock')
    for name, digest in lock['bindings'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path) != digest:
            raise PermissionError('execution source drift')
    events = ledger.get('events', [])
    if (len(events) != 1 or events[0].get('kind') != 'reserve'
            or events[0].get('seconds') != 28800
            or events[0].get('execution_lock_sha256') != sha(lock_path)
            or not events[0].get('attempt_id')):
        raise PermissionError('one bound reservation required; consumed attempts cannot run')
    return events[0]
