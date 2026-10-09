"""Runtime v2 split installation (hand-written successor of certification/phase4_integrated_v2/prepare.py).

Model interpreter: the verified runtime's path, unchanged from the GPU-run control-interface v2 probe:
  * `publisher_install.verify_bundle`: the flat version-pinned publisher mount must hold exactly the 174 trusted
    wheels (size and streamed SHA-256) plus the three bound publisher metadata files, whose package/version pins
    must equal the trusted hash-pinned lock;
  * `publisher_install.install`: a fresh `--without-pip` venv populated by host pip with `--no-index
    --no-cache-dir --require-hashes --only-binary=:all:` from the trusted lock, then `pip check`, exact versions,
    imports and the torch CUDA build. Every command owns its process group.
  Retained from R4 (they pass on the same bytes): the torch wheel contract and the isolation/metadata check that
  the model interpreter has exactly the pinned model packages and no game package.
Game interpreter: the unchanged R4 path (verified in earlier GPU-session installs on the CPython 3.12.13 image): the
  31 competition arc_agi_3 wheels verified against reports/phase4_v2_offline_package.json, a `--without-pip`
  venv managed by host pip (`HeadlessEnvironment`, which asserts CPython 3.12, Linux, x86_64), the exact R4 pins,
  dependency check and the isolated game import check (no torch, vllm or transformers).
Both share the R4 first-cell installation deadline (450 s from the first cell). A larger value is accepted only in
an explicit CPU rehearsal (`SSV_REHEARSAL=1`), where it is recorded and never becomes target timing evidence.
"""
import base64
import gzip
import json
import os
from pathlib import Path
import sys
import time

from certification.phase4_integrated_v2.evidence import EvidenceStore

PROTOCOL = 'research/stagnation_supervision_runtime_v2/protocol.json'
MODEL_METADATA_EXTRA = """
assert {n:m.version(n) for n in ('torch','vllm','transformers','numpy')} == {
    'torch':'2.10.0','vllm':'0.19.0','transformers':'4.57.6','numpy':'2.2.6'}
assert importlib.util.find_spec('arcengine') is None
assert importlib.util.find_spec('arc_agi') is None
"""


def _retain(output, scratch, receipt):
    evidence = Path(scratch) / 'install-evidence'
    if evidence.exists():
        for role in ('game', 'model'):
            folder = evidence / role
            if folder.exists():
                data = {p.name: base64.b64encode(p.read_bytes()).decode() for p in folder.iterdir() if p.is_file()}
                packed = gzip.compress(json.dumps(data, sort_keys=True).encode())
                EvidenceStore(output, 'logs').save('install-' + role + '.json',
                                                   {'encoding': 'gzip-base64-json', 'data': base64.b64encode(packed).decode()})
    EvidenceStore(output, 'control').save('installation.json', receipt)


def prepare(scratch, output, wheelhouse, game_wheels, manifest, started, *, root, install_seconds=None):
    """Install and check both interpreters on the shared first-cell clock; returns {'model': python, 'game': python}."""
    from certification.phase4_v6.clean_environment import ENVIRONMENT_PINS, verify_environment_wheels
    from certification.phase4_v6.headless_environment import HeadlessEnvironment
    from certification.phase4_v6.target_install_probe_r3 import verify_torch_contract
    from certification.phase4_v6.target_install_probe_r5 import GAME_CHECK, ISOLATION_CHECK
    from research.stagnation_supervision_runtime_v2.publisher_install import (
        InstallationProcesses, _run, install, verify_bundle)
    scratch, output = Path(scratch), Path(output)
    protocol = json.loads((Path(root) / PROTOCOL).read_bytes())
    seconds = protocol['limits']['installation_seconds']
    if install_seconds is not None:
        if os.environ.get('SSV_REHEARSAL') != '1' or type(install_seconds) is not int or install_seconds <= 0:
            raise PermissionError('an installation-time override is rehearsal-only')
        seconds = install_seconds
    deadline = started + seconds

    def check():
        if time.monotonic() >= deadline - 10:
            raise TimeoutError('installation deadline')

    receipt = {'passed': False, 'scope': 'runtime_v2_split_install', 'runtime_binding': protocol['scope'],
               'installation_seconds': seconds, 'override': install_seconds is not None, 'error': None,
               'evidence_class': 'cpu_rehearsal_not_target_timing' if install_seconds is not None else 'first_cell'}
    processes = InstallationProcesses(30, 10)
    evidence = scratch / 'install-evidence'
    try:
        check()
        receipt['model_bundle'] = verify_bundle(wheelhouse, protocol['dataset'], protocol['bundle'], check)
        receipt['torch_contract'] = verify_torch_contract(wheelhouse)
        receipt['game_wheels'] = verify_environment_wheels(game_wheels, manifest)
        check()
        (evidence / 'model').mkdir(parents=True, exist_ok=False)
        (scratch / 'model').mkdir(exist_ok=False)
        runtime = protocol['runtime']['model']
        log = evidence / 'model' / 'install.log'
        model = install(wheelhouse, scratch / 'model' / 'venv', runtime, deadline, log, python=sys.executable,
                        processes=processes)
        receipt['model_install'] = {k: model.get(k) for k in ('install_seconds', 'versions', 'imports', 'torch_cuda_build')}
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
        env.update(PYTHONNOUSERSITE='1', CUDA_VISIBLE_DEVICES='', VLLM_NO_USAGE_STATS='1', USE_TF='0',
                   TRANSFORMERS_NO_TF='1')
        _run([model['python'], '-I', '-c', ISOLATION_CHECK + MODEL_METADATA_EXTRA], log, deadline, env,
             'model metadata and isolation', processes)
        check()
        runner = HeadlessEnvironment(scratch / 'game', evidence / 'game', host_python=sys.executable,
                                     seconds=max(0, deadline - time.monotonic()))
        runner.deadline = deadline  # one absolute deadline shared with the model interpreter's work
        runner.env.update(VLLM_NO_USAGE_STATS='1', USE_TF='0', TRANSFORMERS_NO_TF='1', CUDA_VISIBLE_DEVICES='')
        runner.bootstrap()
        runner.execute('resolve_game', runner.pip() + ['install', '--dry-run', '--no-index', '--only-binary=:all:',
                                                       '--find-links', str(Path(game_wheels).resolve()),
                                                       '--report', str(runner.output / 'resolution.json'),
                                                       *ENVIRONMENT_PINS])
        runner.install('install_game', game_wheels, ENVIRONMENT_PINS)
        runner.check()
        runner.execute('game_imports', [runner.python, '-I', '-c', GAME_CHECK])
        check()
        receipt['passed'] = True
        receipt['interpreters'] = {'model': model['python'], 'game': runner.python}
        return dict(receipt['interpreters'])
    except Exception as exc:
        receipt['error'] = type(exc).__name__ + ': ' + str(exc)[:512]
        raise
    finally:
        cleanup = processes.stop(max(deadline, time.monotonic() + 15))
        receipt['model_process_cleanup'] = {'groups_absent': cleanup['groups_absent'], 'error': cleanup['error'],
                                            'interrupted': cleanup['interrupted'], 'groups': len(cleanup['groups'])}
        if not cleanup['groups_absent'] or cleanup['error'] or cleanup['interrupted']:
            receipt['passed'] = False
            receipt['error'] = receipt['error'] or 'installation process cleanup not verified'
        receipt['elapsed_seconds'] = time.monotonic() - started
        _retain(output, scratch, receipt)
        if receipt['error'] and sys.exc_info()[0] is None:
            raise RuntimeError(receipt['error'])
