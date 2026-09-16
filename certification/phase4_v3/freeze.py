"""Local v3 source snapshot verification; grants no GPU authority."""
import hashlib
import json
from pathlib import Path
from evaluation.phase4_execution import source_names, verify_lock
from certification.phase4_v1.lifecycle import validate_freeze

ROOT = Path(__file__).resolve().parents[2]


def names(root=ROOT):
    result = set(source_names(root))
    for revision in ('phase4_v1', 'phase4_v2', 'phase4_v3'):
        result.update(p.relative_to(root).as_posix()
                      for p in (root / 'certification' / revision).glob('*.py'))
    result.update({'certification/phase4_v3/protocol.json',
                   'certification/phase4_v1/lock.json', 'certification/phase4_v1/workload.json',
                   'certification/phase4_v1/budget.json', 'certification/phase4_v1/contract.json',
                   'reports/phase4_v2_offline_package.json'})
    return sorted(result)


def verify_snapshot(root=ROOT):
    verify_lock(root)
    validate_freeze(root)
    path = root / 'certification/phase4_v3/source_snapshot.json'
    lock = json.loads(path.read_text())
    if set(lock.get('bindings', {})) != set(names(root)):
        raise ValueError('incomplete v3 source snapshot')
    for name, digest in lock['bindings'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError('v3 source drift: ' + name)
    return hashlib.sha256(path.read_bytes()).hexdigest()
