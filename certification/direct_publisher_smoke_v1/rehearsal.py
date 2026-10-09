"""Scripted CPU rehearsals of the smoke-test control code. GPU disabled: no GPU query is made, CUDA is hidden, the
model server is the scripted stub and installation uses fixture wheels in the publisher dataset layout. These rehearsals are
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

from certification.direct_publisher_smoke_v1.binding import load_protocol
from certification.direct_publisher_smoke_v1.host import tree_sha256
from certification.direct_publisher_smoke_v1.run import run

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


def fixture_bundle(folder, inputs):
    """Flat publisher fixture; trusted hash-pinned lock stays outside the mount."""
    folder = Path(folder)
    folder.mkdir(parents=True)
    inputs = Path(inputs)
    inputs.mkdir(parents=True)
    wheels = {'fixturea-1.0-py3-none-any.whl': wheel('fixturea', '1.0', ['fixtureb==1.0']),
              'fixtureb-1.0-py3-none-any.whl': wheel('fixtureb', '1.0')}
    lock, plain, artifacts = '', '', []
    for name, data in sorted(wheels.items()):
        (folder / name).write_bytes(data)
        lock += f"{name.split('-')[0]}=={name.split('-')[1]} --hash=sha256:{hashlib.sha256(data).hexdigest()}\n"
        plain += f"{name.split('-')[0]}=={name.split('-')[1]}\n"
        artifacts.append({'filename': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (folder / 'requirements.lock').write_bytes(plain.encode())
    (inputs / 'trusted_requirements.lock').write_bytes(lock.encode())
    (folder / 'README.md').write_bytes(b'Flat publisher fixture; CPU control evidence only.\n')
    digest = lambda name: hashlib.sha256((folder / name).read_bytes()).hexdigest()  # noqa: E731
    sums = ''.join(f'{digest(n)}  {n}\n' for n in sorted(wheels))
    (folder / 'SHA256SUMS').write_bytes(sums.encode())
    artifact_sha = hashlib.sha256(json.dumps(artifacts, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    proposal = {'dataset': {'ref': 'rehearsal/fixture-publisher', 'version': 1},
                'trusted_artifacts_sha256': artifact_sha,
                'trusted_requirements_sha256': hashlib.sha256(lock.encode()).hexdigest(),
                'wheel_count': len(wheels), 'integrity_budget_seconds': 180,
                'publisher_metadata_sha256': {n: digest(n) for n in ('README.md', 'SHA256SUMS', 'requirements.lock')}}
    (inputs / 'proposal.json').write_bytes((json.dumps(proposal, indent=2) + '\n').encode())
    (inputs / 'trusted_manifest.json').write_bytes((json.dumps({'artifacts': artifacts}) + '\n').encode())
    return {'dataset': dict(proposal['dataset'], publisher_metadata_sha256=proposal['publisher_metadata_sha256']),
            'bundle': {'approved_manifest_sha256': artifact_sha,
                       'requirements_lock_sha256': proposal['trusted_requirements_sha256'], 'wheel_count': len(wheels)}}


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
    protocol['dataset'] = copy.deepcopy(bundle_pins['dataset'])
    protocol['bundle'] = copy.deepcopy(bundle_pins['bundle'])
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
    pins = fixture_bundle(work / 'bundle', work / 'inputs')
    tree = fixture_model(work / 'model')
    behaviour = spec.get('behaviour', 'normal')
    overrides = {}
    if name == 'bundle_file_tampered':
        target = work / 'bundle/fixtureb-1.0-py3-none-any.whl'
        target.write_bytes(target.read_bytes() + b'tampered')
    if name == 'sha256sums_binding_mismatch':
        overrides['dataset__publisher_metadata_sha256'] = dict(pins['dataset']['publisher_metadata_sha256'],
                                                              SHA256SUMS='0' * 64)
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
                 workdir=work / 'work', server_argv=argv, on_cleanup=on_cleanup, trusted_inputs=work / 'inputs')
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
