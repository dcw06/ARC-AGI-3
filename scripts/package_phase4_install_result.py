"""Preserve this failed attempt's exact evidence without credentials or caches."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
paths = list((ROOT/'reports/runs/phase4-v6-install-20260917').rglob('*'))
paths += list((ROOT/'notebooks/phase4-v6-install-check-proposal-r1').glob('*'))
paths += [ROOT/name for name in (
    'reports/phase4_v6_install_evaluation.json', 'reports/phase4_v6_install_launch.json',
    'reports/phase4_v6_install_preflight.json', 'reports/phase4_v6_install_authorization_20260917.md',
    'config/phase4_v6_install_execution_lock.json', 'config/phase4_v6_install_compute_ledger.json',
    'config/phase4_v6_install_launch_claim.json')]
archive = ROOT/'evidence/phase4-v6-install-check-failed-v1.zip'
inventory = {}
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as target:
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        if path.is_symlink():
            raise ValueError('symlink in evidence')
        name = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        inventory[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        target.writestr(name, data)
    target.writestr('inventory.json', json.dumps(inventory, indent=2))
with zipfile.ZipFile(archive) as source:
    for name, item in inventory.items():
        data = source.read(name)
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('archive verification failed')
print(json.dumps({'archive': archive.relative_to(ROOT).as_posix(),
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'files_verified': len(inventory)}))
