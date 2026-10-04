"""Isolated offline installation check of the downloaded R2 wheelhouse (CPU only; no GPU, no model, no upload).

Run it inside a network namespace with only loopback, e.g. on Linux:

  unshare --user --map-root-user --net python scripts/check_wheelhouse_offline_install.py \
      --wheels ~/.local/share/agi/wheelhouse-r2 --workdir ~/.local/share/agi/wheelhouse-r2-install-check

It refuses to run if the network is reachable (DNS or TCP), unless --allow-network is given for a test.

Steps (each bounded by a timeout, every command and its output retained in the work directory's log):
 1. Re-verify every wheel's size and SHA-256 against the approved download manifest.
 2. Write a hash-pinned lock (name==version --hash=sha256:...) for all 174 artifacts.
 3. Create a fresh virtual environment from the system CPython 3.12 (no site packages, no user config, empty HOME,
    no pip cache) and install with --no-index --require-hashes --only-binary=:all: --find-links <wheels> -r <lock>.
 4. pip check; pip freeze --all compared with the manifest (every artifact installed at its version, nothing else
    apart from pip itself).
 5. CPU import check of torch, transformers, numpy and vllm: versions, CUDA build string, import paths. CUDA
    availability is recorded, not required (this host has no NVIDIA runtime).
 6. Fault checks on one small wheel in separate fresh environments: a corrupted artifact and a missing artifact must
    each be rejected by pip.
The result is written to reports/wheelhouse_r2_offline_install_check.json. GPU checks are recorded as unverified.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_wheelhouse import APPROVED_MANIFEST_SHA256, load_manifest  # noqa: E402
MANIFEST = ROOT / 'reports/wheelhouse_download_manifest.json'
RESULT = ROOT / 'reports/wheelhouse_r2_offline_install_check.json'
SYSTEM_PYTHON = '/usr/bin/python3.12'
INSTALL_TIMEOUT = 3600
STEP_TIMEOUT = 900
EXPECTED_MANIFEST = APPROVED_MANIFEST_SHA256
EVIDENCE = ROOT / 'reports/wheelhouse_r2_offline_install_evidence'
IMPORT_CHECK = r'''
import importlib, json, sys
out = {'python': sys.version.split()[0], 'prefix': sys.prefix, 'modules': {}}
for name in ('numpy', 'torch', 'transformers', 'vllm'):
    try:
        m = importlib.import_module(name)
        out['modules'][name] = {'version': getattr(m, '__version__', None), 'file': getattr(m, '__file__', None)}
    except Exception as e:
        out['modules'][name] = {'error': f'{type(e).__name__}: {e}'}
try:
    import torch
    out['torch_cuda_build'] = torch.version.cuda
    out['torch_cuda_available'] = bool(torch.cuda.is_available())
except Exception as e:
    out['torch_cuda_build'] = f'error: {e}'
print('IMPORT_CHECK ' + json.dumps(out, sort_keys=True))
'''


class CheckError(Exception):
    pass


def parse_name_version(filename):
    name, version = filename[:-4].split('-')[:2]
    return name, version


def lock_lines(manifest):
    lines = []
    for a in sorted(manifest['artifacts'], key=lambda a: a['filename']):
        name, version = parse_name_version(a['filename'])
        lines.append(f"{name}=={version} --hash=sha256:{a['sha256']}")
    return lines


def network_reachable(timeout=3.0):
    """True if DNS or a direct TCP connection works (the check must run with neither)."""
    try:
        socket.getaddrinfo('pypi.org', 443)
        return True
    except OSError:
        pass
    try:
        with socket.create_connection(('151.101.0.223', 443), timeout=timeout):
            return True
    except OSError:
        return False


def verify_wheels(manifest, wheels):
    bad = []
    for a in manifest['artifacts']:
        path = wheels / a['filename']
        if not path.is_file() or path.stat().st_size != a['size']:
            bad.append(a['filename'])
            continue
        h = hashlib.sha256()
        with open(path, 'rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                h.update(block)
        if h.hexdigest() != a['sha256']:
            bad.append(a['filename'])
    return bad


def clean_env(work):
    home = work / 'home'
    home.mkdir(parents=True, exist_ok=True)
    (work / 'tmp').mkdir(exist_ok=True)
    return {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'TMPDIR': str(work / 'tmp'), 'LANG': 'C.UTF-8',
            'PIP_CONFIG_FILE': '/dev/null', 'PIP_NO_INPUT': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
            'PYTHONNOUSERSITE': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
            'VLLM_NO_USAGE_STATS': '1', 'DO_NOT_TRACK': '1'}


def install_command(python, wheels, lock):
    return [python, '-I', '-m', 'pip', 'install', '--no-index', '--no-cache-dir', '--require-hashes',
            '--only-binary=:all:', '--find-links', str(wheels), '-r', str(lock)]


def run(argv, env, log, timeout):
    started = time.monotonic()
    with open(log, 'a', encoding='utf-8') as stream:
        stream.write(f'\n$ {" ".join(argv)}\n')
        stream.flush()
        try:
            proc = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                  timeout=timeout)
        except subprocess.TimeoutExpired as error:
            stream.write(f'TIMEOUT after {timeout} s\n')
            raise CheckError(f'timed out: {argv[:4]}') from error
        stream.write(proc.stdout)
        stream.write(f'[exit {proc.returncode} in {time.monotonic() - started:.1f} s]\n')
    return proc.returncode, proc.stdout


def compare_freeze(freeze_text, manifest):
    from packaging.utils import canonicalize_name
    installed = {}
    for line in freeze_text.splitlines():
        if '==' in line:
            name, version = line.split('==', 1)
            installed[canonicalize_name(name)] = version.strip()
    expected = {canonicalize_name(n): v for n, v in (parse_name_version(a['filename'])
                                                       for a in manifest['artifacts'])}
    from packaging.version import Version
    mismatched = sorted(n for n, v in expected.items() if n in installed and Version(installed[n]) != Version(v))
    missing = sorted(set(expected) - set(installed))
    extra = sorted(set(installed) - set(expected) - {'pip'})
    return {'expected': len(expected), 'installed': len(installed), 'missing': missing,
            'version_mismatch': mismatched, 'extra': extra, 'pip': installed.get('pip')}


def fault_checks(manifest, wheels, work, env, log):
    small = min((a for a in manifest['artifacts'] if a['filename'].endswith('-py3-none-any.whl')),
                key=lambda a: a['size'])
    name, version = parse_name_version(small['filename'])
    results = {'artifact': small['filename']}
    for case in ('corrupted', 'missing'):
        folder = work / f'fault-{case}'
        (folder / 'wheels').mkdir(parents=True)  # folder is new: work is a fresh exclusive directory
        if case == 'corrupted':
            data = bytearray((wheels / small['filename']).read_bytes())
            data[len(data) // 2] ^= 0xFF
            (folder / 'wheels' / small['filename']).write_bytes(bytes(data))
        lock = folder / 'lock.txt'
        lock.write_text(f"{name}=={version} --hash=sha256:{small['sha256']}\n", encoding='utf-8')
        code, _ = run([SYSTEM_PYTHON, '-m', 'venv', str(folder / 'venv')], env, log, STEP_TIMEOUT)
        if code != 0:
            raise CheckError(f'venv for the {case} fault check failed')
        code, out = run(install_command(str(folder / 'venv/bin/python'), folder / 'wheels', lock), env, log,
                        STEP_TIMEOUT)
        results[case] = {'pip_exit': code, 'rejected': code != 0,
                         'reason': 'hash mismatch' if 'HASHES' in out.upper() or 'hash' in out.lower()
                         else ('no matching distribution' if 'No matching distribution' in out else 'other')}
        remove_inside(work, folder / 'venv')
    return results


def check_paths(wheels, parent):
    """Refuse unsafe parents: the filesystem root, the home directory, the repository and its ancestors, or any
    directory overlapping the wheels."""
    repo = ROOT.resolve()
    if not parent.is_dir():
        raise SystemExit(f'refused: {parent} is not an existing directory')
    if parent == Path(parent.anchor) or parent == Path.home().resolve():
        raise SystemExit(f'refused: {parent} is the filesystem root or the home directory')
    if parent == repo or repo in parent.parents or parent in repo.parents:
        raise SystemExit(f'refused: {parent} is the repository, inside it, or one of its ancestors')
    if parent == wheels or wheels in parent.parents or parent in wheels.parents:
        raise SystemExit(f'refused: {parent} overlaps the wheel directory {wheels}')
    if wheels == repo or repo in wheels.parents:
        raise SystemExit(f'refused: the wheel directory {wheels} is inside the repository')


def remove_inside(work, target):
    """Recursively remove target only if it lies strictly inside the exclusive work directory."""
    work, target = work.resolve(), target.resolve()
    if work not in target.parents:
        raise CheckError(f'refused to remove {target}: not inside {work}')
    shutil.rmtree(target, ignore_errors=True)


def retain_evidence(work, result):
    """Copy the log and lock into the repository and bind them by SHA-256 in the result."""
    folder = EVIDENCE / work.name
    folder.mkdir(parents=True, exist_ok=False)
    files = {}
    for name in ('install-check.log', 'requirements.lock'):
        source = work / name
        if source.is_file():
            data = source.read_bytes()
            (folder / name).write_bytes(data)
            files[name] = hashlib.sha256(data).hexdigest()
    shown = folder.relative_to(ROOT) if folder.is_relative_to(ROOT) else folder
    return {'folder': str(shown), 'files_sha256': files}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--wheels', required=True)
    parser.add_argument('--workdir-parent', required=True,
                        help='an existing directory; a fresh exclusive child is created in it and only that child '
                             'is ever written or cleaned')
    parser.add_argument('--keep-venv', action='store_true')
    parser.add_argument('--allow-network', action='store_true', help='tests only')
    args = parser.parse_args(argv)
    wheels, parent = Path(args.wheels).resolve(), Path(args.workdir_parent).resolve()
    # All validation happens before any filesystem change.
    manifest = load_manifest(MANIFEST, EXPECTED_MANIFEST)  # recomputed digest, counts, totals, names, duplicates
    check_paths(wheels, parent)
    if network_reachable() and not args.allow_network:
        raise SystemExit('refused: the network is reachable; run inside an isolated network namespace')
    work = Path(tempfile.mkdtemp(prefix='install-check-', dir=parent))  # fresh, exclusively ours
    log = work / 'install-check.log'
    env = clean_env(work)
    result = {'schema': 'wheelhouse_offline_install_check_v1', 'manifest_sha256': manifest['manifest_sha256'],
              'started': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
              'network_isolated': not network_reachable(), 'host_python': SYSTEM_PYTHON,
              'scope': 'CPU-only offline installation; GPU startup, inference and cleanup are not verified here'}
    try:
        bad = verify_wheels(manifest, wheels)
        result['wheels_verified'] = {'count': manifest['artifact_count'] - len(bad), 'of': manifest['artifact_count'],
                                     'bad': bad}
        if bad:
            raise CheckError('wheel verification failed')
        lock = work / 'requirements.lock'
        lines = lock_lines(manifest)
        lock.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        result['lock'] = {'lines': len(lines), 'sha256': hashlib.sha256(lock.read_bytes()).hexdigest()}
        code, _ = run([SYSTEM_PYTHON, '-m', 'venv', str(work / 'venv')], env, log, STEP_TIMEOUT)
        if code != 0:
            raise CheckError('venv creation failed')
        python = str(work / 'venv/bin/python')
        code, out = run([python, '-I', '-m', 'pip', '--version'], env, log, STEP_TIMEOUT)
        result['pip_version'] = out.strip()
        started = time.monotonic()
        code, _ = run(install_command(python, wheels, lock), env, log, INSTALL_TIMEOUT)
        result['install'] = {'exit': code, 'seconds': round(time.monotonic() - started, 1)}
        if code != 0:
            raise CheckError('offline installation failed')
        code, out = run([python, '-I', '-m', 'pip', 'check'], env, log, STEP_TIMEOUT)
        result['pip_check'] = {'exit': code, 'output': out.strip()[-2000:]}
        code, out = run([python, '-I', '-m', 'pip', 'freeze', '--all'], env, log, STEP_TIMEOUT)
        result['freeze'] = compare_freeze(out, manifest)
        code, out = run([python, '-I', '-c', IMPORT_CHECK], env, log, STEP_TIMEOUT)
        line = next((l for l in out.splitlines() if l.startswith('IMPORT_CHECK ')), None)
        result['imports'] = json.loads(line[len('IMPORT_CHECK '):]) if line else {'error': out.strip()[-2000:]}
        result['faults'] = fault_checks(manifest, wheels, work, env, log)
        imports = result['imports'].get('modules', {})
        result['passed'] = bool(
            result['pip_check']['exit'] == 0
            and not (result['freeze']['missing'] or result['freeze']['version_mismatch'] or result['freeze']['extra'])
            and all('version' in imports.get(m, {}) for m in ('numpy', 'torch', 'transformers', 'vllm'))
            and result['faults']['corrupted']['rejected'] and result['faults']['missing']['rejected'])
    except CheckError as error:
        result['passed'] = False
        result['error'] = str(error)
    finally:
        if not args.keep_venv:
            remove_inside(work, work / 'venv')
        result['finished'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        result['log'] = str(log)
        result['not_established'] = ['GPU runtime (CUDA initialisation, model startup, inference, cancellation, '
                                     'cleanup)', 'licence and redistribution review', 'team-owned upload',
                                     'exact target image (this host: WSL Ubuntu 24.04, CPython 3.12.3; target '
                                     'CPython 3.12.13)']
        result['work_directory'] = str(work)
        result['evidence'] = retain_evidence(work, result)
        RESULT.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        print(json.dumps({k: result.get(k) for k in ('passed', 'network_isolated', 'install', 'error')}))
    return 0 if result.get('passed') else 1


if __name__ == '__main__':
    sys.exit(main())
