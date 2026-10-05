"""Offline installation verification: bundle integrity against the bound checksums, a hash-pinned offline install
into a fresh virtual environment, then pip check, exact versions, imports and the torch CUDA build."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


class InstallFailed(RuntimeError):
    pass


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(bundle, dataset, bundle_pins, check=lambda: None):
    """Integrity of the attached bundle: SHA256SUMS and bundle-manifest.json match the bound hashes, every listed
    file matches, no file is unlisted, the lock matches the protocol and holds the expected number of wheels."""
    bundle = Path(bundle)
    sums_path = bundle / 'SHA256SUMS'
    if file_sha256(sums_path) != dataset['sha256sums_sha256']:
        raise InstallFailed('SHA256SUMS differs from the bound hash')
    if file_sha256(bundle / 'bundle-manifest.json') != dataset['bundle_manifest_sha256']:
        raise InstallFailed('bundle-manifest.json differs from the bound hash')
    listed = {}
    for line in sums_path.read_text(encoding='utf-8').splitlines():
        digest, _, name = line.partition('  ')
        if len(digest) != 64 or not name or name in listed or name.startswith('/') or '..' in Path(name).parts:
            raise InstallFailed(f'malformed SHA256SUMS line: {line[:120]!r}')
        listed[name] = digest
    present = {p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file()} - {'SHA256SUMS'}
    if present != set(listed):
        raise InstallFailed(f'file set differs from SHA256SUMS: extra {sorted(present - set(listed))[:5]}, '
                            f'missing {sorted(set(listed) - present)[:5]}')
    bad = []
    for name, digest in sorted(listed.items()):
        check()
        if file_sha256(bundle / name) != digest:
            bad.append(name)
    if bad:
        raise InstallFailed(f'{len(bad)} file(s) differ from SHA256SUMS: {bad[:5]}')
    lock = bundle / 'requirements.lock'
    if file_sha256(lock) != bundle_pins['requirements_lock_sha256']:
        raise InstallFailed('requirements.lock differs from the protocol')
    lines = [x for x in lock.read_text(encoding='utf-8').splitlines() if x.strip()]
    wheels = [n for n in listed if n.startswith('wheels/') and n.endswith('.whl')]
    if len(lines) != bundle_pins['wheel_count'] or len(wheels) != bundle_pins['wheel_count']:
        raise InstallFailed(f'expected {bundle_pins["wheel_count"]} wheels; lock has {len(lines)}, bundle {len(wheels)}')
    return {'files_verified': len(listed), 'wheels': len(wheels), 'sha256sums_sha256': dataset['sha256sums_sha256'],
            'requirements_lock_sha256': bundle_pins['requirements_lock_sha256']}


def _run(argv, log, deadline, env, what):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise InstallFailed(f'{what}: installation deadline reached')
    with Path(log).open('ab') as stream:
        stream.write(f'\n$ {" ".join(map(str, argv))}\n'.encode())
        stream.flush()
        try:
            result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, env=env, timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise InstallFailed(f'{what}: installation deadline reached') from exc
    if result.returncode:
        raise InstallFailed(f'{what} exited {result.returncode}')
    return result


PACKAGE_CHECK = '''import importlib, importlib.metadata as m, json, sys
expected = json.loads(sys.argv[1])
report = {"versions": {}, "imports": {}}
for name in expected["packages"]:
    report["versions"][name] = m.version(name)
for name in expected["imports"]:
    module = importlib.import_module(name)
    report["imports"][name] = getattr(module, "__file__", None)
if "torch" in expected["imports"]:
    import torch
    report["torch_cuda_build"] = torch.version.cuda
print(json.dumps(report))
'''


def install(bundle, venv, runtime, deadline, log, python=sys.executable, environment=None):
    """Hash-pinned offline install into a new virtual environment, then pip check, versions, imports and the torch
    CUDA build. No index, no cache, binary wheels only, no network configuration."""
    bundle, venv = Path(bundle), Path(venv)
    env = {k: v for k, v in (environment or os.environ).items()
           if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL')}
    env.update(PIP_NO_INDEX='1', PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1',
               PYTHONNOUSERSITE='1', CUDA_VISIBLE_DEVICES=env.get('CUDA_VISIBLE_DEVICES', ''))
    receipt = {'passed': False}
    begin = time.monotonic()
    _run([python, '-m', 'venv', str(venv)], log, deadline, env, 'venv creation')
    vpython = str(venv / 'bin' / 'python')
    _run([vpython, '-m', 'pip', 'install', '--no-index', '--no-cache-dir', '--require-hashes', '--only-binary=:all:',
          '--find-links', str(bundle / 'wheels'), '-r', str(bundle / 'requirements.lock')],
         log, deadline, env, 'offline install')
    receipt['install_seconds'] = round(time.monotonic() - begin, 3)
    _run([vpython, '-m', 'pip', 'check'], log, deadline, env, 'pip check')
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise InstallFailed('package checks: installation deadline reached')
    try:
        checked = subprocess.run([vpython, '-I', '-c', PACKAGE_CHECK, json.dumps(runtime)], capture_output=True,
                                 text=True, env=env, timeout=remaining)
    except subprocess.TimeoutExpired as exc:
        raise InstallFailed('package checks: installation deadline reached') from exc
    with Path(log).open('a', encoding='utf-8') as stream:
        stream.write(checked.stdout + checked.stderr)
    if checked.returncode:
        raise InstallFailed('package import check failed: ' + checked.stderr.strip()[-300:])
    report = json.loads(checked.stdout.strip().splitlines()[-1])
    receipt.update(report)
    mismatched = {n: v for n, v in report['versions'].items() if v != runtime['packages'][n]}
    if mismatched:
        raise InstallFailed(f'version mismatch (no upgrade attempted): {mismatched}')
    if 'torch_cuda_build' in runtime and report.get('torch_cuda_build') != runtime['torch_cuda_build']:
        raise InstallFailed(f"torch CUDA build {report.get('torch_cuda_build')} != {runtime['torch_cuda_build']}")
    receipt.update(passed=True, python=vpython)
    return receipt
