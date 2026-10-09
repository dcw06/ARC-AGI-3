# Derived from research/control_interface_action_selection_v2/rehearsal.py (5a21dd3) by scripts/build_progress_subgoal_v1_runtime2.py; edit the derivation.
"""Fixture installation plus local scripted HTTP, timeout/cancellation and cleanup. Zero GPU/model calls.

The complete frozen questionnaire (all 5,852 scheduled calls, built from the frozen question set) runs through the
derived lifecycle against the scripted stub. The stub's answers are scripted (research.progress_subgoal_v1.fake_server
rules, or the keys for `oracle`); labels from a rehearsal are not results. Returns (result, declared protocol): the
declared protocol is what an independent evaluation of the rehearsal must use."""
import copy
import os
from pathlib import Path
import sys
import time

from certification.direct_publisher_smoke_v1 import host
from certification.direct_publisher_smoke_v1 import rehearsal as fixtures
from . import binding, questionnaire as QN, run

FAULTS = ('none', 'timeout_once', 'consecutive_timeouts', 'not_idle', 'http_error', 'token_mismatch',
          'admission_cutoff')
POLICIES = ('scripted', 'oracle')
# The reviewed rehearsal timing (research/progress_subgoal_v1/worker.py: 2 s calls, 3 s idle verification).
TIMING = {'timeout_seconds': 2.0, 'teardown_seconds': 1, 'verify_seconds': 3.0, 'margin_seconds': 4}
LIMITS = {'internal_seconds': 1500, 'admission_cutoff_seconds': 1200, 'cleanup_reserve_seconds': 300,
          'installation_seconds': 180, 'startup_ceiling_seconds': 120, 'model_verification_seconds': 10}
# admission_cutoff: the stub adds latency so the frozen admission rule stops the schedule inside withheld pass 1.
CUTOFF_LIMITS = dict(LIMITS, internal_seconds=400, admission_cutoff_seconds=100)
CUTOFF_LATENCY_SECONDS = 0.03
# The fixture installation needs a host interpreter with pip (>= 22.3) to manage the fresh venv; a rehearsal harness
# whose own interpreter has no pip names one here (CPU rehearsal only; the live path always uses its own).
HOST_PYTHON_ENV = 'PSV1R2_REHEARSAL_HOST_PYTHON'


def declared_protocol(root, pins, model, tree, port, fault):
    protocol = copy.deepcopy(binding.load_protocol(root))
    protocol['dataset'], protocol['bundle'] = pins['dataset'], pins['bundle']
    protocol['runtime'].update(packages={'fixturea': '1.0', 'fixtureb': '1.0'}, imports=['fixturea', 'fixtureb'])
    protocol['runtime'].pop('torch_cuda_build')
    protocol['model'].update(mounted_path=str(model), tree_sha256=tree, required_files=['config.json'],
                             shard_glob='model-*.bin', shard_count=1)
    protocol['model'].pop('source_kind')  # isolated fixture tree, not a real Kaggle dataset mount
    protocol['server'].update(port=port, terminate_grace_seconds=2, kill_grace_seconds=2)
    protocol['limits'].update(CUTOFF_LIMITS if fault == 'admission_cutoff' else LIMITS)
    protocol['experiment']['call_timing'] = dict(TIMING)
    for item in protocol['requests']:
        item['timeout_seconds'] = (TIMING['timeout_seconds'] if item['kind'] == QN.KIND
                                   else QN.IDLE_READ_TIMEOUT_SECONDS if item['kind'] == QN.IDLE_KIND else 5)
    protocol['server']['env']['PYTHONPATH'] = str(root)
    return protocol


def scenario(root, folder, fault='none', policy='scripted'):
    if fault not in FAULTS or policy not in POLICIES:
        raise ValueError('rehearsal scenario')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    inputs = folder / 'trusted'
    bundle = folder / 'bundle'
    pins = fixtures.fixture_bundle(bundle, inputs)
    model = folder / 'model'
    tree = fixtures.fixture_model(model)
    protocol = declared_protocol(root, pins, model, tree, fixtures.free_port(), fault)
    latency = CUTOFF_LATENCY_SECONDS if fault == 'admission_cutoff' else 0.0
    # -m uses the fixture venv's interpreter without installing any research/game packages.
    argv = lambda py: [py, '-m', 'research.progress_subgoal_v1_runtime2.rehearsal_stub',
        '--port', str(protocol['server']['port']), '--served', protocol['server']['served_model_name'],
        '--questionnaire-fault', fault, '--policy', policy, '--latency', str(latency), '--root', str(root)]
    result = run.run('rehearsal', protocol, folder / 'evidence', time.monotonic(), bundle=bundle,
        workdir=folder / 'work', python=os.environ.get(HOST_PYTHON_ENV) or sys.executable, trusted_inputs=inputs,
        server_argv=argv,
        experiment_root=root, model_check=lambda check: host.verify_model(protocol['model'], check))
    return result, protocol
