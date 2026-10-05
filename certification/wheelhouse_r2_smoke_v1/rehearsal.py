"""Scripted CPU rehearsals of the smoke-test control code. GPU disabled: no GPU query is made, CUDA is hidden, the
model server is the scripted stub and installation uses fixture wheels in the R2 bundle layout. These rehearsals are
NOT GPU compatibility evidence."""
import base64
import copy
import hashlib
import io
import json
import os
import socket
import tempfile
import zipfile
from pathlib import Path

from certification.wheelhouse_r2_smoke_v1.binding import load_protocol
from certification.wheelhouse_r2_smoke_v1.host import tree_sha256
from certification.wheelhouse_r2_smoke_v1.run import run

STUB = Path(__file__).with_name('rehearsal_stub.py')
SERVED = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'


def wheel(name, version, requires=()):
    """A minimal valid pure-Python wheel (bytes)."""
    files = {f'{name}/__init__.py': f'__version__ = "{version}"\n'.encode(),
             f'{name}-{version}.dist-info/METADATA': (f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n'
                                                      + ''.join(f'Requires-Dist: {r}\n' for r in requires)).encode(),
             f'{name}-{version}.dist-info/WHEEL': b'Wheel-Version: 1.0\nGenerator: rehearsal\nRoot-Is-Purelib: true\n'
                                                  b'Tag: py3-none-any\n'}
    record = ''.join(f'{path},sha256={base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()},'
                     f'{len(data)}\n' for path, data in files.items())
    files[f'{name}-{version}.dist-info/RECORD'] = (record + f'{name}-{version}.dist-info/RECORD,,\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        for path, data in files.items():
            info = zipfile.ZipInfo(path, (2026, 1, 1, 0, 0, 0))
            z.writestr(info, data)
    return buffer.getvalue()


def fixture_bundle(folder):
    """Fixture bundle in the R2 layout: wheels/, requirements.lock, README.md, bundle-manifest.json, SHA256SUMS
    (non-circular, as in the R2 plan). Returns its bound hashes."""
    folder = Path(folder)
    (folder / 'wheels').mkdir(parents=True)
    wheels = {'fixturea-1.0-py3-none-any.whl': wheel('fixturea', '1.0', ['fixtureb==1.0']),
              'fixtureb-1.0-py3-none-any.whl': wheel('fixtureb', '1.0')}
    lock = ''
    for name, data in sorted(wheels.items()):
        (folder / 'wheels' / name).write_bytes(data)
        lock += f"{name.split('-')[0]}=={name.split('-')[1]} --hash=sha256:{hashlib.sha256(data).hexdigest()}\n"
    (folder / 'requirements.lock').write_text(lock)
    (folder / 'README.md').write_text('Fixture bundle for scripted CPU rehearsals (not R2).\n')
    payload = sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file())
    digest = lambda name: hashlib.sha256((folder / name).read_bytes()).hexdigest()  # noqa: E731
    manifest = {'files': [{'path': n, 'size': (folder / n).stat().st_size, 'sha256': digest(n)} for n in payload]}
    (folder / 'bundle-manifest.json').write_text(json.dumps(manifest, indent=1))
    sums = ''.join(f'{digest(n)}  {n}\n' for n in sorted(payload + ['bundle-manifest.json']))
    (folder / 'SHA256SUMS').write_text(sums)
    return {'sha256sums_sha256': digest('SHA256SUMS'), 'bundle_manifest_sha256': digest('bundle-manifest.json'),
            'requirements_lock_sha256': digest('requirements.lock'), 'wheel_count': len(wheels)}


def fixture_model(folder):
    folder = Path(folder)
    folder.mkdir(parents=True)
    (folder / 'config.json').write_text('{"fixture": true}\n')
    (folder / 'model-00001-of-00001.bin').write_bytes(b'\0' * 1024)
    return tree_sha256(folder)['tree_sha256']


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def rehearsal_protocol(bundle_pins, model_dir, model_tree, port, behaviour, **overrides):
    """The frozen protocol with fixture bindings and shortened limits, labelled as a rehearsal."""
    protocol = copy.deepcopy(load_protocol())
    protocol['rehearsal'] = {'evidence_class': 'scripted_cpu_rehearsal', 'behaviour': behaviour}
    protocol['dataset'] = {'ref': 'rehearsal/fixture-bundle', 'version': 'rehearsal',
                           'sha256sums_sha256': bundle_pins['sha256sums_sha256'],
                           'bundle_manifest_sha256': bundle_pins['bundle_manifest_sha256']}
    protocol['bundle'] = {'approved_manifest_sha256': 'fixture',
                          'requirements_lock_sha256': bundle_pins['requirements_lock_sha256'],
                          'wheel_count': bundle_pins['wheel_count']}
    protocol['runtime'].update(packages={'fixturea': '1.0', 'fixtureb': '1.0'}, imports=['fixturea', 'fixtureb'])
    protocol['runtime'].pop('torch_cuda_build')
    protocol['model'].update(mounted_path=str(model_dir), tree_sha256=model_tree, required_files=['config.json'],
                             shard_glob='model-*.bin', shard_count=1)
    protocol['server'].update(port=port, terminate_grace_seconds=2, kill_grace_seconds=2)
    protocol['limits'].update(internal_seconds=600, cleanup_reserve_seconds=60, admission_cutoff_seconds=540,
                              installation_seconds=180, model_verification_seconds=30, startup_ceiling_seconds=8)
    for item in protocol['requests']:
        item['timeout_seconds'] = min(item['timeout_seconds'], 5)
    for key, value in overrides.items():
        section, field = key.split('__')
        protocol[section][field] = value
    return protocol


SCENARIOS = {
    'nominal': {'expect_passed': True, 'expect_stage': None},
    'bundle_file_tampered': {'expect_passed': False, 'expect_stage': 'bundle_integrity'},
    'sha256sums_binding_mismatch': {'expect_passed': False, 'expect_stage': 'bundle_integrity'},
    'version_mismatch': {'expect_passed': False, 'expect_stage': 'installation'},
    'model_tree_mismatch': {'expect_passed': False, 'expect_stage': 'model_artifact'},
    'server_exits_early': {'expect_passed': False, 'expect_stage': 'server_ready', 'behaviour': 'exit_early'},
    'startup_ceiling': {'expect_passed': False, 'expect_stage': 'server_ready', 'behaviour': 'never_ready'},
    'wrong_served_model': {'expect_passed': False, 'expect_stage': 'startup_probe_S2', 'behaviour': 'wrong_model'},
    'request_timeout': {'expect_passed': False, 'expect_stage': 'startup_probe_S3', 'behaviour': 'slow_completion'},
    'not_idle_after_cancel': {'expect_passed': False, 'expect_stage': 'cancellation_C2_idle',
                              'behaviour': 'stay_busy'},
    'server_ignores_sigterm': {'expect_passed': True, 'expect_stage': None, 'behaviour': 'ignore_sigterm',
                               'expect_sigkill': True},
    'child_ignores_sigterm': {'expect_passed': True, 'expect_stage': None, 'behaviour': 'child_ignores_sigterm',
                              'expect_sigkill': True},
}


def scenario(name, base, on_cleanup=None):
    """Run one scenario in a fresh directory under `base`; returns (expectation check, result)."""
    spec = SCENARIOS[name]
    work = Path(tempfile.mkdtemp(prefix=f'{name}-', dir=base))
    pins = fixture_bundle(work / 'bundle')
    tree = fixture_model(work / 'model')
    behaviour = spec.get('behaviour', 'normal')
    overrides = {}
    if name == 'bundle_file_tampered':
        target = work / 'bundle/wheels/fixtureb-1.0-py3-none-any.whl'
        target.write_bytes(target.read_bytes() + b'tampered')
    if name == 'sha256sums_binding_mismatch':
        overrides['dataset__sha256sums_sha256'] = '0' * 64
    if name == 'model_tree_mismatch':
        overrides['model__tree_sha256'] = 'f' * 64
    port = free_port()
    protocol = rehearsal_protocol(pins, work / 'model', tree, port, behaviour, **overrides)
    if name == 'version_mismatch':
        protocol['runtime']['packages']['fixturea'] = '2.0'
    argv = lambda py: [py, str(STUB), '--port', str(port), '--served', SERVED, '--behaviour', behaviour]  # noqa
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    import time
    result = run('rehearsal', protocol, work / 'evidence', time.monotonic(), bundle=work / 'bundle',
                 workdir=work / 'work', server_argv=argv, on_cleanup=on_cleanup)
    stopped = result['cleanup']['server']
    check = {'passed_as_expected': result['passed'] == spec['expect_passed'],
             'stage_as_expected': result['failed_stage'] == spec['expect_stage'],
             'groups_absent': stopped.get('groups_absent') is True,
             'gpu_never_queried': result['stages'].get('gpu', '').startswith('not_exercised'),
             'evidence_class_rehearsal': result['evidence_class'] == 'scripted_cpu_rehearsal'
             and result['gpu_compatibility_evidence'] is False,
             'within_request_cap': result['ledger']['issued'] <= protocol['limits']['maximum_model_requests']}
    if spec.get('expect_sigkill'):
        check['sigkill_needed_and_sent'] = stopped.get('sigkill_sent') is True
    return {'scenario': name, 'behaviour': behaviour, 'expected': spec, 'checks': check,
            'as_expected': all(check.values()), 'failed_stage': result['failed_stage'], 'error': result['error'],
            'requests_issued': result['ledger']['issued'], 'by_kind': result['ledger']['by_kind'],
            'cleanup': stopped, 'evidence_dir': str(work / 'evidence')}, result
