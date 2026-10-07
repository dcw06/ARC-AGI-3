"""Offline installation verification: bundle integrity against the bound checksums, a hash-pinned offline install
into a fresh virtual environment, then pip check, exact versions, imports and the torch CUDA build."""
import hashlib
import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from certification.direct_publisher_smoke_v1.server import ModelServer, defer_startup_signals


class InstallFailed(RuntimeError):
    pass


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(bundle, dataset, bundle_pins, check=lambda: None, *, inputs=None):
    """Verify the flat publisher mount against reviewed local inputs, not an R2 manifest."""
    from certification.direct_publisher_smoke_v1.preflight import PACKAGE, load_inputs, verify_mounted
    inputs = Path(inputs) if inputs is not None else PACKAGE
    proposal, _, _ = load_inputs(inputs)
    expected = {'ref': proposal['dataset']['ref'], 'version': proposal['dataset']['version'],
                'publisher_metadata_sha256': proposal['publisher_metadata_sha256']}
    if dataset != expected:
        raise InstallFailed('dataset differs from the trusted intake binding')
    expected_pins = {'approved_manifest_sha256': proposal['trusted_artifacts_sha256'],
                     'requirements_lock_sha256': proposal['trusted_requirements_sha256'],
                     'wheel_count': proposal['wheel_count']}
    if bundle_pins != expected_pins:
        raise InstallFailed('trusted installation pins differ from the protocol')

    def checked_now():
        check()  # combined installation deadline covers every streamed hash chunk
        return time.monotonic()
    return verify_mounted(bundle, package=inputs, now=checked_now)


class InstallationProcesses:
    """Retain ownership even when command startup never returns to its caller.

    Linux subreaper mode lets this notebook reap orphaned grandchildren itself;
    waitpid is scoped to each owned group, never to unrelated child processes.
    The previous subreaper setting is restored after all lifecycle groups stop.
    """
    def __init__(self, terminate_grace=1, kill_grace=2):
        self.groups = []
        self.terminate_grace, self.kill_grace = terminate_grace, kill_grace
        self.previous_subreaper = None

    def _adopt_descendants(self):
        if self.previous_subreaper is not None:
            return
        if sys.platform != 'linux':
            raise InstallFailed('installation process ownership requires Linux')
        libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        if libc.prctl(37, ctypes.byref(previous), 0, 0, 0) != 0:  # PR_GET_CHILD_SUBREAPER
            raise OSError(ctypes.get_errno(), 'cannot read child subreaper setting')
        self.previous_subreaper = previous.value
        if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
            raise OSError(ctypes.get_errno(), 'cannot adopt installation descendants')

    def _stop_group(self, entry, deadline):
        old = entry.get('cleanup', {})
        if old.get('groups_absent'):
            # Verified absence is terminal for this owner. A later reuse of its
            # numeric PGID must not let final cleanup signal an unrelated group.
            return dict(old)
        interruptions = []
        for _ in range(2):
            try:
                receipt = entry['group'].stop(deadline, self.terminate_grace, self.kill_grace)
                break
            except BaseException as exc:
                interruptions.append(f'cleanup: {type(exc).__name__}: {str(exc)[:120]}')
        else:
            receipt = {'ownership': entry['group'].ownership, 'pgid': entry['group'].pgid,
                       'groups_absent': False, 'error': 'process cleanup interrupted twice'}
        for key in ('sigterm_sent', 'sigkill_sent'):
            receipt[key] = receipt.get(key, False) or old.get(key, False)
        receipt['interrupted'] = old.get('interrupted', []) + interruptions + receipt.get('interrupted', [])
        entry['cleanup'] = receipt
        return receipt

    def command(self, argv, log, deadline, env, what):
        if deadline <= time.monotonic():
            raise InstallFailed(f'{what}: installation deadline reached')
        with defer_startup_signals():
            self._adopt_descendants()
            group = ModelServer(argv, env, log, None, None, inherit_env=False)
            entry = {'phase': what, 'group': group}
            self.groups.append(entry)  # register the owner before entering Popen
        with Path(log).open('ab') as stream:
            stream.write(f'\n$ {" ".join(map(str, argv))}\n'.encode())
            stream.flush()
            offset = stream.tell()
        try:
            group.start()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InstallFailed(f'{what}: installation deadline reached')
            try:
                code = group.process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise InstallFailed(f'{what}: installation deadline reached') from exc
        finally:
            # Even KeyboardInterrupt or an alarm before assignment must reach this.
            cleanup = self._stop_group(entry, deadline)
        if not cleanup['groups_absent'] or cleanup.get('interrupted'):
            raise InstallFailed(f'{what}: process-group cleanup not verified without interruption')
        if deadline <= time.monotonic():
            raise InstallFailed(f'{what}: installation deadline reached during process cleanup')
        # A file avoids pipe EOF hangs when imported code leaves a child behind.
        with Path(log).open('rb') as stream:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(offset, stream.tell() - 2 * 1024 * 1024))
            output = stream.read().decode('utf-8', errors='replace')
        if code:
            raise InstallFailed(f'{what} exited {code}: {output.strip()[-300:]}')
        return subprocess.CompletedProcess(argv, code, stdout=output, stderr='')

    def stop(self, deadline):
        receipts = [{'phase': entry['phase'], **self._stop_group(entry, deadline)} for entry in self.groups]
        error = None
        if self.previous_subreaper is not None:
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(36, self.previous_subreaper, 0, 0, 0) != 0:
                error = 'could not restore child subreaper setting'
            else:
                self.previous_subreaper = None
        return {'groups': receipts, 'groups_absent': all(r['groups_absent'] for r in receipts),
                'interrupted': [message for r in receipts for message in r.get('interrupted', [])],
                'error': error}


def _run(argv, log, deadline, env, what, processes=None):
    owned = processes is None
    processes = processes if processes is not None else InstallationProcesses()
    try:
        return processes.command(argv, log, deadline, env, what)
    finally:
        if owned:
            cleanup = processes.stop(deadline)
            if sys.exc_info()[0] is None and (not cleanup['groups_absent'] or cleanup['error']):
                raise InstallFailed('installation process cleanup not verified')


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


def install(bundle, venv, runtime, deadline, log, python=sys.executable, environment=None, requirements=None,
            processes=None):
    """Hash-pinned offline install into a new virtual environment, then pip check, versions, imports and the torch
    CUDA build. No index, no cache, binary wheels only, no network configuration."""
    bundle, venv = Path(bundle), Path(venv)
    env = {k: v for k, v in (environment or os.environ).items()
           if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL')}
    env.update(PIP_NO_INDEX='1', PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1',
               PYTHONNOUSERSITE='1', CUDA_VISIBLE_DEVICES=env.get('CUDA_VISIBLE_DEVICES', ''))
    owned = processes is None
    processes = processes if processes is not None else InstallationProcesses()
    try:
        return _install(bundle, venv, runtime, deadline, log, python, env, requirements, processes)
    finally:
        if owned:
            cleanup = processes.stop(deadline)
            if sys.exc_info()[0] is None and (not cleanup['groups_absent'] or cleanup['error']):
                raise InstallFailed('installation process cleanup not verified')


def _install(bundle, venv, runtime, deadline, log, python, env, requirements, processes):
    receipt = {'passed': False}
    begin = time.monotonic()
    _run([python, '-m', 'venv', str(venv)], log, deadline, env, 'venv creation', processes)
    vpython = str(venv / 'bin' / 'python')
    _run([vpython, '-m', 'pip', 'install', '--no-index', '--no-cache-dir', '--require-hashes', '--only-binary=:all:',
          '--find-links', str(bundle), '-r', str(requirements or Path(__file__).with_name('trusted_requirements.lock'))],
         log, deadline, env, 'offline install', processes)
    receipt['install_seconds'] = round(time.monotonic() - begin, 3)
    _run([vpython, '-m', 'pip', 'check'], log, deadline, env, 'pip check', processes)
    checked = _run([vpython, '-I', '-c', PACKAGE_CHECK, json.dumps(runtime)], log, deadline, env,
                   'package checks', processes)
    report = json.loads(checked.stdout.strip().splitlines()[-1])
    receipt.update(report)
    mismatched = {n: v for n, v in report['versions'].items() if v != runtime['packages'][n]}
    if mismatched:
        raise InstallFailed(f'version mismatch (no upgrade attempted): {mismatched}')
    if 'torch_cuda_build' in runtime and report.get('torch_cuda_build') != runtime['torch_cuda_build']:
        raise InstallFailed(f"torch CUDA build {report.get('torch_cuda_build')} != {runtime['torch_cuda_build']}")
    if time.monotonic() >= deadline:
        raise InstallFailed('package checks: installation deadline reached')
    receipt.update(passed=True, python=vpython)
    return receipt
