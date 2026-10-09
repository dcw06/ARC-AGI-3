# Derived by scripts/build_evidence_memory_v1_sessions.py from research/control_interface_action_selection_v2/rehearsal.py at 5a21dd3 (origin/wheelhouse-replacement-audit); edit the derivation.
"""Fixture installation plus local scripted HTTP, timeout/cancellation and cleanup. Zero GPU/model calls.
The study phase talks to research/evidence_memory_v1/successor/stub.py (scripted answers, vLLM counters)."""
import copy
import json
from pathlib import Path
import sys
import time

from certification.direct_publisher_smoke_v1 import host
from certification.direct_publisher_smoke_v1 import rehearsal as fixtures
from . import binding, run

# Rehearsal limits: the frozen limits shortened for CPU fixtures (the study admission rule is unchanged).
REHEARSAL_LIMITS = {'internal_seconds': 360, 'admission_cutoff_seconds': 240, 'cleanup_reserve_seconds': 60,
                    'installation_seconds': 120, 'startup_ceiling_seconds': 15, 'model_verification_seconds': 15}


def rehearsal_limits(root, **overrides):
    return {**binding.load_protocol(root)['limits'], **REHEARSAL_LIMITS, **overrides}


def scenario(root, folder, fault='none', latency=0.0, **limits):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    inputs = folder / 'trusted'
    bundle = folder / 'bundle'
    pins = fixtures.fixture_bundle(bundle, inputs)
    model = folder / 'model'
    tree = fixtures.fixture_model(model)
    protocol = copy.deepcopy(binding.load_protocol(root))
    protocol['dataset'], protocol['bundle'] = pins['dataset'], pins['bundle']
    protocol['runtime'].update(packages={'fixturea': '1.0', 'fixtureb': '1.0'}, imports=['fixturea', 'fixtureb'])
    protocol['runtime'].pop('torch_cuda_build')
    protocol['model'].update(mounted_path=str(model), tree_sha256=tree, required_files=['config.json'],
                             shard_glob='model-*.bin', shard_count=1)
    protocol['model'].pop('source_kind')  # isolated fixture tree, not a real Kaggle dataset mount
    protocol['server'].update(port=fixtures.free_port(), terminate_grace_seconds=2, kill_grace_seconds=2)
    protocol['limits'] = rehearsal_limits(root, **limits)
    for item in protocol['requests']:
        item['timeout_seconds'] = 5
    # -m uses the fixture venv's interpreter without installing any research/game packages.
    argv = lambda py: [py, '-m', 'research.evidence_memory_v1.successor.stub',
        '--port', str(protocol['server']['port']), '--served', protocol['server']['served_model_name'],
        '--root', str(root), '--package', binding.PACKAGE, '--fault', fault, '--latency', str(latency)]
    protocol['server']['env']['PYTHONPATH'] = str(root)
    return run.run('rehearsal', protocol, folder / 'evidence', time.monotonic(), bundle=bundle,
        workdir=folder / 'work', python=sys.executable, trusted_inputs=inputs, server_argv=argv,
        experiment_root=root, model_check=lambda check: host.verify_model(protocol['model'], check))
