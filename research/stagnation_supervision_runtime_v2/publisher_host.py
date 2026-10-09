# Derived from certification/direct_publisher_smoke_v1/host.py at 5a21dd3 by scripts/derive_stagnation_supervision_runtime_v2.py; edit the derivation, not this file.
"""Host, GPU and model-artifact facts. GPU queries go through an injectable `query` (nvidia-smi in the live path);
the rehearsal does not query any GPU and records these checks as not exercised."""
import csv
import hashlib
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

INPUT_ROOT = Path('/kaggle/input')


class HostMismatch(RuntimeError):
    pass


def host_facts(runtime):
    libc, version = platform.libc_ver()
    facts = {'python': platform.python_version(), 'executable': sys.executable, 'machine': platform.machine(),
             'libc': libc, 'glibc': version, 'kernel': platform.release()}
    problems = []
    if not facts['python'].startswith(runtime['python'] + '.'):
        problems.append(f"python {facts['python']} is not {runtime['python']}.x")
    if facts['machine'] != runtime['machine']:
        problems.append(f"machine {facts['machine']}")
    if libc != 'glibc' or tuple(map(int, version.split('.'))) < tuple(map(int, runtime['glibc_minimum'].split('.'))):
        problems.append(f"glibc {version or 'unknown'} below {runtime['glibc_minimum']}")
    facts['matches'] = not problems
    facts['problems'] = problems
    if problems:
        raise HostMismatch('; '.join(problems))
    return facts


def nvidia_smi(fields, kind='gpu', timeout=5):
    flag = '--query-gpu=' if kind == 'gpu' else '--query-compute-apps='
    result = subprocess.run(['nvidia-smi', flag + ','.join(fields), '--format=csv,noheader,nounits'],
                            capture_output=True, text=True, check=True, timeout=timeout)
    if len(result.stdout) > 16384:
        raise ValueError('nvidia-smi output too large')
    return [[v.strip() for v in row] for row in csv.reader(result.stdout.strip().splitlines()) if row]


def gpu_facts(runtime, query=nvidia_smi):
    rows = query(['uuid', 'name', 'driver_version', 'memory.total', 'memory.used'])
    if len(rows) != runtime['gpu_count'] or any(len(r) != 5 for r in rows):
        raise HostMismatch(f'expected {runtime["gpu_count"]} GPU, found {len(rows)}')
    uuid, name, driver, total, used = rows[0]
    if runtime['gpu_name_contains'] not in name:
        raise HostMismatch(f'GPU {name!r} is not {runtime["gpu_name_contains"]}')
    return {'uuid': uuid, 'name': name, 'driver_version': driver, 'memory_total_mib': int(total),
            'memory_used_mib': int(used)}


def gpu_sample(uuid, query=nvidia_smi):
    rows = query(['uuid', 'memory.used', 'utilization.gpu'])
    row = next((r for r in rows if r and r[0] == uuid), None)
    if row is None:
        raise HostMismatch('bound GPU missing from telemetry')
    return {'memory_used_mib': int(row[1]), 'utilization_percent': int(row[2]), 'at': time.monotonic()}


def gpu_cleanup(uuid, groups_absent, query=nvidia_smi):
    """Independent post-termination check: owned groups gone and no compute process left on the bound GPU."""
    receipt = {'groups_absent': groups_absent, 'gpu_processes': None, 'gpu_cleanup_verified': False, 'error': None}
    try:
        processes = [r for r in query(['gpu_uuid', 'pid'], kind='apps') if r and r[0] == uuid]
        receipt['gpu_processes'] = len(processes)
        receipt['gpu_cleanup_verified'] = groups_absent and not processes
    except Exception as exc:
        receipt['error'] = f'{type(exc).__name__}: {str(exc)[:200]}'
    return receipt


def tree_sha256(root, check=lambda: None):
    """arc3-artifact-tree-v1 digest (relative path, size and content hash of every file, in path order)."""
    base = Path(root).resolve()
    if Path(root).is_symlink() or not base.is_dir():
        raise ValueError('artifact root must be a real directory')
    check()
    digest = hashlib.sha256(b'arc3-artifact-tree-v1\0')
    count = total = 0
    for path in sorted(base.rglob('*'), key=lambda p: p.relative_to(base).as_posix()):
        check()
        if path.is_symlink():
            raise ValueError('artifact tree contains a symlink')
        if not path.is_file():
            continue
        relative, size, file_digest = path.relative_to(base).as_posix().encode(), path.stat().st_size, hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                file_digest.update(chunk)
                check()
        digest.update(len(relative).to_bytes(4, 'big') + relative + size.to_bytes(8, 'big') + file_digest.digest())
        count, total = count + 1, total + size
    if not count:
        raise ValueError('artifact tree is empty')
    check()  # Empty files and the last read must also obey the model-verification deadline.
    return {'tree_sha256': digest.hexdigest(), 'files': count, 'bytes': total}


def model_mount(model):
    """Select only the reviewed model dataset's two supported Kaggle mount layouts.

    A root alias may point to the other layout of that same dataset. Distinct
    directories, broken aliases and links to other roots are refused; internal
    symlinks remain forbidden by tree_sha256. Version identity still depends on
    the version-pinned attachment and the complete trusted tree digest.
    """
    configured = Path(model['mounted_path'])
    kind = model.get('source_kind', 'model')
    if kind == 'model':
        return {'configured_path': str(configured), 'mounted_path': str(configured)}
    if kind != 'dataset':
        raise HostMismatch('unsupported model source kind')
    source = model['kaggle_source']
    if not isinstance(source, str) or not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*', source):
        raise HostMismatch('version-pinned model dataset reference required')
    owner, name, version = source.split('/')
    candidates = [INPUT_ROOT / 'datasets' / owner / name, INPUT_ROOT / name]
    if configured not in candidates:
        raise HostMismatch('configured model path does not name the bound dataset')
    observations, found = [], set()
    for candidate in candidates:
        present, alias = candidate.exists(), candidate.is_symlink()
        resolved = candidate.resolve() if present else None
        observations.append({'path': str(candidate), 'exists': present, 'is_directory': candidate.is_dir(),
                             'is_symlink': alias, 'resolved_path': str(resolved) if resolved else None})
        if alias and not present:
            raise HostMismatch(f'broken model dataset mount alias: {candidate}')
        if present:
            if not candidate.is_dir() or resolved not in candidates or resolved.is_symlink():
                raise HostMismatch(f'model dataset mount must resolve to a real bound directory: {candidate}')
            found.add(resolved)
    if len(found) != 1:
        paths = ', '.join(str(path) for path in candidates)
        raise HostMismatch(f'model dataset {owner}/{name} version {version}: expected one unambiguous mount; '
                           f'found {len(found)} real directories; checked {paths}')
    return {'configured_path': str(configured), 'mounted_path': str(found.pop()),
            'dataset_ref': f'{owner}/{name}', 'requested_version': int(version),
            'provider_attachment_version_verified': False, 'mount_candidates': observations}


def verify_model(model, check=lambda: None):
    mount = model_mount(model)
    path = Path(mount['mounted_path'])
    tree = tree_sha256(path, check)
    if tree['tree_sha256'] != model['tree_sha256']:
        raise HostMismatch('model artifact tree SHA-256 differs from the pin')
    missing = [n for n in model['required_files'] if not (path / n).is_file()]
    shards = len(list(path.glob(model['shard_glob'])))
    if missing or shards != model['shard_count']:
        raise HostMismatch(f'model layout: missing {missing}, {shards} shards')
    check()
    return dict(tree, **mount)


def dataset_mount(ref, version, base=Path('/kaggle/input')):
    """The attached bundle directory for the bound dataset ref (both Kaggle mount layouts are accepted)."""
    owner, name = ref.split('/', 1)
    candidates = [base / 'datasets' / owner / name, base / name]
    found = [c for c in candidates if c.is_dir()]
    if len(found) != 1:
        raise HostMismatch(f'dataset {ref} (version {version}) must have exactly one unambiguous mount')
    return found[0]


def environment_without_gpu():
    return dict(os.environ, CUDA_VISIBLE_DEVICES='')
