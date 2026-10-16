"""Read mounted bytes with stdlib only; no installs, model imports or inference."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import signal
import sys
import time

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()

def verify_files(root, inventory, check):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('expected a mounted directory, not a symlink')
    expected = {}
    for row in inventory:
        name = row['name']
        if (type(name) is not str or not name or name in ('.', '..')
                or '/' in name or '\\' in name or Path(name).name != name
                or name in expected or not re.fullmatch('[a-f0-9]{64}', row['sha256'])
                or (row['bytes'] is not None and (type(row['bytes']) is not int or row['bytes'] < 0))):
            raise ValueError('unsafe or duplicate expected filename/hash/size')
        expected[name] = row
    actual = set()
    for path in root.rglob('*'):
        check()
        if path.is_symlink():
            raise ValueError('symlink in dataset')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(expected):
        raise ValueError('dataset file inventory differs')
    total = 0
    for name in sorted(expected):
        row = expected[name]
        path = root/name
        check()
        size = path.stat().st_size
        if row['bytes'] is not None and size != row['bytes']:
            raise ValueError('file size differs: '+name)
        digest = hashlib.sha256()
        count = 0
        with path.open('rb') as stream:
            while True:
                check()
                block = stream.read(8*1024*1024)
                check()
                if not block:
                    break
                count += len(block)
                digest.update(block)
        if count != size or digest.hexdigest() != row['sha256']:
            raise ValueError('file bytes differ: '+name)
        total += size
    check()
    return {'files_checked': len(expected), 'bytes_checked': total, 'all_sha256_matched': True}

def find_mount(input_root, ref):
    owner, slug = ref.split('/')
    candidates = [Path(input_root)/slug, Path(input_root)/'datasets'/owner/slug]
    found = [path for path in candidates if path.is_dir()]
    if len(found) != 1:
        raise ValueError('expected exactly one mount for '+ref)
    return found[0]

def run(manifest, input_root='/kaggle/input', output='/kaggle/working/internvl-cpu-byte-verification/result.json'):
    started = time.monotonic()
    deadline = started+manifest['worker_budget_seconds']
    result = {'status': 'byte_verification_not_complete', 'datasets': {},
              'manifest_sha256': hashlib.sha256(canonical(manifest)).hexdigest(),
              'model_requests': 0, 'game_actions': 0, 'package_installs': 0,
              'pretrained_weights_loaded': False, 'gpu_runtime_validated': False,
              'provider_full_job_cap_verified': False,
              'session_completion_requires_provider_status': True,
              'host': {'python': sys.version.split()[0], 'machine': platform.machine(),
                       'system': platform.system(), 'libc': list(platform.libc_ver())}}
    def check():
        if time.monotonic() >= deadline:
            raise TimeoutError('CPU byte-verification worker deadline exceeded')
    def alarm(*_):
        raise TimeoutError('CPU byte-verification alarm expired')
    previous = signal.signal(signal.SIGALRM, alarm)
    signal.alarm(manifest['worker_budget_seconds'])
    destination = Path(output)
    try:
        if destination.exists():
            raise FileExistsError('preserve previous verification result')
        if manifest['schema'] != 'internvl_cpu_dataset_bytes_v1':
            raise ValueError('unknown byte-check manifest')
        for item in manifest['datasets']:
            check()
            mount = find_mount(input_root, item['ref'])
            checked = verify_files(mount, item['files'], check)
            checked.update(ref=item['ref'], intended_version=item['version'], mount=str(mount),
                           provider_attachment_version_verified=False)
            result['datasets'][item['kind']] = checked
        result['installed_host_versions'] = {}
        for name in ('torch', 'torchvision', 'transformers', 'timm'):
            try:
                result['installed_host_versions'][name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                result['installed_host_versions'][name] = None
        check()
        result['status'] = 'mounted_bytes_match_no_runtime_or_model_validation'
    except BaseException as error:
        result['status'] = 'byte_verification_failed'
        result['error_type'] = type(error).__name__
        raise
    finally:
        try:
            result['elapsed_to_evidence_write_seconds'] = time.monotonic()-started
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write(canonical(result))
            check()  # any late write makes the CPU session fail
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
    return result
