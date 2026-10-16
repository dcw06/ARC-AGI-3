"""One offline Linux installation rehearsal, CPU execution only; no job launcher.

Receipts are provisional: collection must also verify the reviewed notebook,
provider COMPLETE status and the final cell-output witness. A receipt alone never
certifies lifecycle completion. The provider's pre-cell time cap is not verified.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import tempfile
import time

from certification.direct_publisher_smoke_v1.install import InstallationProcesses
from .mount_check import canonical, find_mount, verify_files


def requirement_pins(raw):
    """Only exact pins and SHA256 are admitted, with no requirement directives."""
    result = {}
    for line in raw.decode('ascii').splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+) --hash=sha256:([a-f0-9]{64})', line)
        if match is None:
            raise ValueError('requirements must contain exact hashed pins only')
        name, version, digest = match.groups()
        name = re.sub('[-_.]+', '-', name).lower()
        if name in result:
            raise ValueError('duplicate pinned package')
        result[name] = {'version': version, 'sha256': digest}
    return result


def install_commands(python, venv, publisher, inputs, requirements):
    """Use host pip to populate an isolated environment without ensurepip."""
    pip = [str(python), '-m', 'pip', '--python', str(Path(venv)/'bin/python')]
    return [
        ('venv creation', [str(python), '-m', 'venv', str(venv), '--without-pip']),
        ('offline hashed installation', [*pip, 'install', '--no-index', '--no-cache-dir',
            '--require-hashes', '--only-binary=:all:', '--find-links', str(publisher),
            '--find-links', str(inputs), '-r', str(requirements)]),
        ('dependency consistency', [*pip, 'check']),
    ]


# This runs under the NEW interpreter with -I. Only reviewed local source is
# added, never the host's site-packages. No pretrained from_pretrained call exists.
REHEARSAL = '''import importlib.metadata as m, json, pathlib, re, sys
root, model, inputs, cache, expected, output = sys.argv[1:]
sys.path.insert(0, root)
expected = json.loads(expected)
actual = {re.sub('[-_.]+', '-', d.metadata['Name']).lower(): d.version for d in m.distributions()}
if actual != expected:
    raise ValueError('isolated installed distribution set/versions differ from all 175 pins')
from research.object_identification_v1.runtime import cpu_check
result = cpu_check(model, cache, inputs, allow_cuda_build=True)
if result['torch_cuda_build'] != '12.8':
    raise ValueError('unexpected CUDA-linked torch wheel')
result['all_175_distribution_versions_matched'] = True
with pathlib.Path(output).open('x') as stream:
    json.dump(result, stream, sort_keys=True)
'''


def validate_completion(result_raw, witness_raw, provider_status, cell_stdout, manifest_sha256):
    """Independent collection rule; a candidate receipt is never sufficient."""
    result, witness = json.loads(result_raw), json.loads(witness_raw)
    marker = 'CPU_INSTALL_CHECK_RETURNED '+hashlib.sha256(witness_raw).hexdigest()
    if (provider_status != 'COMPLETE' or marker not in cell_stdout.splitlines()
            or witness['result_sha256'] != hashlib.sha256(result_raw).hexdigest()
            or result['manifest_sha256'] != manifest_sha256
            or result['status'] != 'checks_passed_pending_provider_completion'):
        raise ValueError('missing, stale or incomplete CPU installation evidence')
    elapsed = witness['elapsed_after_receipt_write_seconds']
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 < elapsed < 1700:
        raise ValueError('CPU installation finalization outside reviewed deadline')
    cleanup, rehearsal = result['cleanup'], result['rehearsal']
    expected_files = {'model': 27, 'inputs': 12, 'publisher_wheels': 177}
    if (set(result['datasets']) != set(expected_files) or any(
            result['datasets'][kind]['files_checked'] != count
            or result['datasets'][kind]['all_sha256_matched'] is not True
            for kind, count in expected_files.items())):
        raise ValueError('mounted bytes not completely verified before installation')
    if (cleanup['groups_absent'] is not True or cleanup['error'] or cleanup['interrupted']
            or result.get('error_type') or result.get('cleanup_error')
            or result['temporary_environment_removed'] is not True
            or result['installed_distributions'] != 175
            or rehearsal['all_175_distribution_versions_matched'] is not True
            or rehearsal['execution_device'] != 'cpu' or rehearsal['cuda_initialized'] is not False
            or rehearsal['torch_cuda_build'] != '12.8'
            or rehearsal['network_attempts'] != 0
            or rehearsal['pretrained_weights_loaded'] is not False
            or result['pretrained_weights_loaded'] is not False
            or result['model_requests'] != 0 or result['game_actions'] != 0):
        raise ValueError('CPU installation execution/cleanup scope not verified')
    return True


def finalize(result, output, started, deadline):
    """Persist a provisional candidate; post-write witness and COMPLETE required."""
    result['elapsed_before_receipt_write_seconds'] = time.monotonic()-started
    destination = Path(output)
    raw = canonical(result)
    with destination.open('xb') as stream:
        stream.write(raw)
    if time.monotonic() >= deadline:
        raise TimeoutError('CPU installation lifecycle exceeded deadline during evidence write')
    if result['status'] != 'checks_passed_pending_provider_completion':
        raise RuntimeError('CPU installation check failed; inspect private receipt and log')
    witness = {'result_sha256': hashlib.sha256(raw).hexdigest(),
               'elapsed_after_receipt_write_seconds': time.monotonic()-started,
               'provider_complete_still_required': True}
    with destination.with_name('completion-witness.json').open('xb') as stream:
        stream.write(canonical(witness))
    if time.monotonic() >= deadline:
        raise TimeoutError('CPU installation lifecycle exceeded deadline during witness write')
    # If any interruption follows, Kaggle ERROR/absent cell witness refuses collection.
    print('CPU_INSTALL_CHECK_RETURNED '+hashlib.sha256(canonical(witness)).hexdigest(), flush=True)
    return result


def run(manifest, *, input_root='/kaggle/input',
        output='/kaggle/working/internvl-cpu-install-verification-v1/result.json'):
    started = time.monotonic()
    deadline = started+manifest['worker_budget_seconds']
    work_deadline = deadline-manifest['cleanup_reserve_seconds']
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.with_name('completion-witness.json').exists():
        raise FileExistsError('preserve previous installation attempt')
    if (sys.platform != 'linux' or sys.version_info[:2] != (3, 12)
            or manifest['schema'] != 'internvl_cpu_install_check_v1'
            or manifest['worker_budget_seconds'] != 1700
            or manifest['cleanup_reserve_seconds'] != 120):
        raise ValueError('CPU installation check requires reviewed Linux/Python 3.12 scope')
    root = Path(__file__).resolve().parents[2]
    trusted = root/'certification/direct_publisher_smoke_v1/trusted_requirements.lock'
    extra = Path(__file__).with_name('runtime_requirements_extra.lock')
    raw_requirements = trusted.read_bytes()+b'\n'+extra.read_bytes()
    pins = requirement_pins(raw_requirements)
    if len(pins) != 175 or len(requirement_pins(trusted.read_bytes())) != 174:
        raise ValueError('expected unchanged 174 pins plus timm')
    result = {'status': 'checks_not_complete', 'datasets': {}, 'model_requests': 0,
              'game_actions': 0, 'pretrained_weights_loaded': False,
              'gpu_runtime_validated': False, 'provider_full_job_cap_verified': False,
              'manifest_sha256': hashlib.sha256(canonical(manifest)).hexdigest(),
              'completion_requires_provider_COMPLETE_and_cell_witness': True}
    processes = InstallationProcesses()
    sandbox = None
    failure = None

    def check():
        if time.monotonic() >= work_deadline:
            raise TimeoutError('CPU installation work deadline reached')

    def alarm(*_):
        raise TimeoutError('CPU installation alarm expired')

    handlers = {s: signal.signal(s, alarm) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGHUP)}
    previous_timer = signal.setitimer(signal.ITIMER_REAL, max(0.001, work_deadline-time.monotonic()))
    try:
        mounts = {}
        for item in manifest['datasets']:
            if item['kind'] in mounts:
                raise ValueError('duplicate dataset kind')
            mount = find_mount(input_root, item['ref'])
            result['datasets'][item['kind']] = verify_files(mount, item['files'], check)
            mounts[item['kind']] = mount
        if set(mounts) != {'model', 'inputs', 'publisher_wheels'}:
            raise ValueError('expected exactly three dataset kinds')
        check()
        sandbox = Path(tempfile.mkdtemp(prefix='internvl-cpu-install-'))
        requirements = sandbox/'requirements.lock'
        requirements.write_bytes(raw_requirements)
        # Never inherit provider secrets, PYTHONPATH or host package configuration.
        env = {'PATH': os.defpath, 'HOME': str(sandbox), 'TMPDIR': str(sandbox),
               'PYTHONNOUSERSITE': '1', 'PIP_CONFIG_FILE': os.devnull,
               'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
               'CUDA_VISIBLE_DEVICES': '', 'NVIDIA_VISIBLE_DEVICES': 'void',
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
               'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HOME': str(sandbox/'hf'),
               'MPLBACKEND': 'Agg', 'TOKENIZERS_PARALLELISM': 'false'}
        log = destination.with_name('installation.log')
        venv = sandbox/'venv'
        for phase, argv in install_commands(sys.executable, venv, mounts['publisher_wheels'],
                                             mounts['inputs'], requirements):
            processes.command(argv, log, work_deadline, env, phase)
        report = sandbox/'rehearsal.json'
        expected = {name: row['version'] for name, row in pins.items()}
        processes.command([str(venv/'bin/python'), '-I', '-c', REHEARSAL,
                           str(root), str(mounts['model']), str(mounts['inputs']),
                           str(sandbox/'hf'), json.dumps(expected), str(report)],
                          log, work_deadline, env, 'pinned CPU model-class rehearsal')
        result['rehearsal'] = json.loads(report.read_bytes())
        result['installed_distributions'] = len(pins)
        check()
    except BaseException as exc:
        failure = exc
        result.update(error_type=type(exc).__name__, error=str(exc)[:1000])
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            cleanup = processes.stop(deadline)
            result['cleanup'] = cleanup
            if not cleanup['groups_absent'] or cleanup['error'] or cleanup['interrupted']:
                raise RuntimeError('installation descendant cleanup not verified')
            if sandbox is not None:
                shutil.rmtree(sandbox)
            result['temporary_environment_removed'] = sandbox is None or not sandbox.exists()
            if not result['temporary_environment_removed'] or time.monotonic() >= deadline:
                raise TimeoutError('CPU installation lifecycle cleanup incomplete or late')
        except BaseException as exc:
            failure = failure or exc
            result['cleanup_error'] = type(exc).__name__+': '+str(exc)[:1000]
        finally:
            for signum, handler in handlers.items():
                signal.signal(signum, handler)
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)
    result['status'] = ('installation_check_failed' if failure is not None
                        else 'checks_passed_pending_provider_completion')
    return finalize(result, destination, started, deadline)
