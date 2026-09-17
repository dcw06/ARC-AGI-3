"""Standalone clean-install probe. No model load, pilot, or execution authority.

Run only in a separately authorized target session. The caller supplies an empty
output directory; a fresh venv is created under temporary scratch and removed.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import threading
import time

SECONDS = 900
LOG_BYTES = 1024**2
MODEL_MANIFESTS = {
    'SHA256SUMS': '44029b360a9c0073e4b0add10703fc3386dc06bf1314f5913a0dad9564144cbb',
    'wheelhouse-manifest.json': 'bc016164d15664c52911fcd11f4e26e72a483e248f3cc9b59ae02b3fce09cc6a',
}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            result.update(block)
    return result.hexdigest()


def verify_wheelhouses(model, environment, manifest, check_deadline):
    for name, expected in MODEL_MANIFESTS.items():
        if (model/name).is_symlink() or digest(model/name) != expected:
            raise ValueError('frozen model wheelhouse manifest mismatch: '+name)
    expected = {}
    for line in (model/'SHA256SUMS').read_text().splitlines():
        if not line:
            continue
        value, name = line.split(maxsplit=1)
        name = name.lstrip('*').removeprefix('./')
        if name in expected or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('invalid wheelhouse inventory path')
        expected[name] = value
    actual = set()
    for path in model.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink in model wheelhouse')
        if path.is_file() and path.name not in MODEL_MANIFESTS:
            actual.add(path.relative_to(model).as_posix())
    if (len(expected) != 179 or len(actual) not in (178, 179)
            or not (set(expected)-actual) <= {'dataset-metadata.json'}
            or actual-set(expected)):
        raise ValueError('model wheelhouse inventory mismatch')
    for name in sorted(actual):
        check_deadline()
        if digest(model/name) != expected[name]:
            raise ValueError('model wheelhouse payload mismatch: '+name)
    wheels = {Path(name).name: info for name, info in manifest['files'].items()
              if name.startswith('wheels/')}
    if len(wheels) != 31 or {p.name for p in environment.iterdir()} != set(wheels):
        raise ValueError('frozen environment wheel inventory mismatch')
    for name, info in wheels.items():
        check_deadline()
        path = environment/name
        if (path.is_symlink() or path.stat().st_size != info['bytes']
                or digest(path) != info['sha256']):
            raise ValueError('environment wheel mismatch: '+name)
    return {'model_payloads': len(actual), 'environment_wheels': len(wheels),
            'model_manifests': MODEL_MANIFESTS}


def command(argv, log, deadline, environment):
    """Bound stdout and kill/reap the owned group on success or failure."""
    errors = []
    process = subprocess.Popen(argv, env=environment, start_new_session=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    def drain():
        try:
            with log.open('ab') as stream:
                while block := process.stdout.read(4096):
                    if stream.tell()+len(block) > LOG_BYTES:
                        raise ValueError('installation probe log budget exhausted')
                    stream.write(block)
        except Exception as exc:
            errors.append(str(exc))
        finally:
            process.stdout.close()
    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    try:
        while process.poll() is None:
            if errors:
                raise RuntimeError(errors[0])
            if time.monotonic() >= deadline-5:
                raise TimeoutError('installation probe deadline')
            time.sleep(.05)
        if process.returncode:
            raise RuntimeError('installation probe command failed; see bounded log')
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)
        thread.join(timeout=2)
        groups = subprocess.run(['ps', '-axo', 'pgid='], capture_output=True,
                                text=True, check=True, timeout=1).stdout.split()
        if str(process.pid) in groups or thread.is_alive() or errors:
            raise RuntimeError('installation probe cleanup/log failure')


RUNTIME_CHECK = '''import importlib.metadata as m, json, platform, subprocess, sys
import arc_agi, arcengine, torch, transformers, vllm, vllm._C
expected={'torch':'2.10.0+cu128','vllm':'0.19.0','transformers':'4.57.6',
          'arc-agi':'0.9.8','arcengine':'0.9.3','numpy':'2.4.4'}
versions={name:m.version(name) for name in expected}
assert versions==expected, versions
assert platform.system()=='Linux' and platform.machine()=='x86_64'
assert sys.version_info[:2]==(3,12)
assert torch.version.cuda=='12.8' and torch.cuda.is_available()
assert torch.cuda.device_count()==1
name=torch.cuda.get_device_name(0)
assert 'RTX PRO 6000' in name, name
x=torch.ones((16,16),device='cuda'); y=x@x; torch.cuda.synchronize()
assert y[0,0].item()==16
driver=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,driver_version',
    '--format=csv,noheader'],text=True,timeout=5).strip()
print(json.dumps({'versions':versions,'python':platform.python_version(),
    'cuda_build':torch.version.cuda,'device':name,'driver_inventory':driver,
    'cuda_tensor_operation_passed':True,'vllm_extension_import_passed':True}))
'''


def run(model, environment, manifest, output):
    started = time.monotonic()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'scope': 'clean_offline_install_and_cuda_smoke_only',
              'model_loaded': False, 'pilot_launched': False, 'phase4_complete': False,
              'provider_reconciliation_required': True, 'error': None}
    def check_deadline():
        if time.monotonic()-started >= SECONDS-10:
            raise TimeoutError('installation probe deadline')
    try:
        if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
                or sys.version_info[:2] != (3, 12)):
            raise ValueError('target Linux x86_64 / Python 3.12 required')
        report['wheelhouses'] = verify_wheelhouses(
            Path(model), Path(environment), manifest, check_deadline)
        with tempfile.TemporaryDirectory(prefix='p4-clean-install-') as folder:
            scratch = Path(folder)
            env = {**os.environ, 'PIP_NO_INDEX': '1', 'PIP_CONFIG_FILE': os.devnull,
                   'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_CACHE_DIR': '1',
                   'PYTHONNOUSERSITE': '1', 'HF_HUB_OFFLINE': '1',
                   'TRANSFORMERS_OFFLINE': '1', 'VLLM_NO_USAGE_STATS': '1',
                   'USE_TF': '0', 'TRANSFORMERS_NO_TF': '1',
                   'XDG_CACHE_HOME': str(scratch/'cache'), 'TMPDIR': str(scratch)}
            env.pop('PYTHONPATH', None)
            log = output/'install.log'
            def execute(argv):
                command(argv, log, started+SECONDS, env)
            execute([sys.executable, '-I', '-m', 'venv', str(scratch/'venv')])
            python = str(scratch/'venv/bin/python')
            # Same ordered installs as the target notebook, in an empty environment.
            base = [python, '-I', '-m', 'pip', 'install', '--no-index', '--no-cache-dir']
            execute(base+['--find-links', str(model), 'vllm==0.19.0',
                         'torch==2.10.0+cu128', 'transformers==4.57.6'])
            execute(base+['--find-links', str(environment), 'arc-agi==0.9.8',
                         'arcengine==0.9.3', 'requests==2.33.1', 'numpy==2.4.4',
                         'pydantic==2.13.2', 'python-dotenv==1.2.2'])
            execute([python, '-I', '-m', 'pip', 'check'])
            execute([python, '-I', '-m', 'pip', 'freeze', '--all'])
            execute([python, '-I', '-c', RUNTIME_CHECK])
        check_deadline()
        # CUDA processes must disappear after the isolated check exits.
        remaining = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid',
            '--format=csv,noheader,nounits'], text=True, timeout=2).strip()
        if remaining:
            raise RuntimeError('GPU process inventory is not empty after cleanup')
        report.update(passed=True, scratch_removed=not scratch.exists(),
                      gpu_cleanup_verified=True)
    except Exception as exc:
        report['error'] = type(exc).__name__+': '+str(exc)[:512]
    report['elapsed_seconds'] = time.monotonic()-started
    if report['elapsed_seconds'] >= SECONDS:
        report.update(passed=False, error=report['error'] or 'probe elapsed ceiling')
    (output/'result.json').write_text(json.dumps(report, indent=2))
    return report
