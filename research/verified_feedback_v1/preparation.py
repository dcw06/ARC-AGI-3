"""Seal CPU preparation inputs; no outcomes, later prompts or execution authority."""
from pathlib import Path
import json

from research.action_effect_choice_v2.interface import candidates
from research.feedback_probe_v1.checkpoints import checked_checkpoint
from research.feedback_probe_v1.source_closure import safe_member, source_inventory
from research.initial_geometry_assistance_v1.geometry import canonical
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from .interface import CONDITIONS, make_request

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINTS = ['research/verified_feedback_v1/protocol.json', 'research/verified_feedback_v1/preparation.py',
              'research/verified_feedback_v1/flow.py', 'scripts/prepare_verified_feedback_v1.py']


def protocol():
    result = json.loads(Path(__file__).with_name('protocol.json').read_bytes())
    if result.get('live_enabled') is not False or result.get('conditions') != list(CONDITIONS):
        raise ValueError('CPU-only protocol or conditions differ')
    return result


def payload(original):
    frozen = protocol()
    checkpoints = original['checkpoints']
    if type(checkpoints) is not list or len(checkpoints) != 8 or len({c['checkpoint_id'] for c in checkpoints}) != 8:
        raise ValueError('all eight unique original checkpoints required')
    result = {'checkpoints.json': original}; rows = []
    for ordinal, cp in enumerate(checkpoints):
        checked_checkpoint(cp, model=frozen['model'])
        pair = candidates(cp, ordinal)
        order = list(CONDITIONS if ordinal % 2 == 0 else reversed(CONDITIONS))
        rows.append({'checkpoint_id': cp['checkpoint_id'], 'candidates': pair, 'order': order})
        for condition in CONDITIONS:
            result['model-inputs/'+cp['checkpoint_id']+'-'+condition+'.json'] = make_request(
                cp['base_request'], pair, condition, study_decision_index=0,
                restored_prefix_length=len(cp['prefix']), trajectory_id=cp['checkpoint_id']+'-'+condition)
    if sum(len(cp['prefix']) for cp in checkpoints)*2 != frozen['planning_ceiling_not_authorization']['prefix_dispatches']:
        raise ValueError('frozen restoration-action plan differs')
    result['candidate-pairs.json'] = rows
    return result


def build(checkpoints, output):
    checkpoints, output = Path(checkpoints), Path(output)
    if sha(checkpoints) != protocol()['source_checkpoint_file_sha256']:
        raise ValueError('external original checkpoint pin differs')
    content = payload(json.loads(checkpoints.read_bytes()))
    sources = source_inventory(ROOT, ENTRYPOINTS)
    output.mkdir(exist_ok=False)
    for name, value in content.items():
        path = output/name; path.parent.mkdir(parents=True, exist_ok=True); write_new(path, value)
    manifest = {'schema': 'verified_feedback_CPU_inputs_v1', 'live_enabled': False,
        'protocol_sha256': sha(Path(__file__).with_name('protocol.json')),
        'source_checkpoint_sha256': sha(checkpoints), 'source_entrypoints': ENTRYPOINTS,
        'sources_sha256': sources, 'files_sha256': {name: sha(output/name) for name in content},
        'inference_file_allowlist': sorted(content), 'model_generations': 0, 'GPU_jobs': 0, 'provider_writes': 0,
        'qualification': 'First-decision inputs only. Future executed receipts are built from actual event journals, not precomputed labels or retained pilot answers. No live runner or approval.'}
    write_new(output/'input-manifest.json', manifest)
    return manifest


def verify(output, pin):
    output = Path(output)
    member = lambda name: safe_member(output, name)
    if sha(member('input-manifest.json')) != pin:
        raise ValueError('external prepared-input manifest pin differs')
    manifest = json.loads(member('input-manifest.json').read_bytes())
    if (manifest.get('schema') != 'verified_feedback_CPU_inputs_v1' or manifest.get('live_enabled') is not False or
            manifest.get('source_entrypoints') != ENTRYPOINTS or
            manifest.get('sources_sha256') != source_inventory(ROOT, ENTRYPOINTS) or
            manifest.get('protocol_sha256') != sha(Path(__file__).with_name('protocol.json')) or
            manifest.get('source_checkpoint_sha256') != protocol()['source_checkpoint_file_sha256'] or
            sha(member('checkpoints.json')) != protocol()['source_checkpoint_file_sha256']):
        raise ValueError('CPU sources, protocol or original checkpoints changed')
    expected = payload(json.loads(member('checkpoints.json').read_bytes()))
    actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
    if (set(manifest['files_sha256']) != set(expected) or manifest['inference_file_allowlist'] != sorted(expected) or
            actual != set(expected) | {'input-manifest.json'} or any(p.is_symlink() for p in output.rglob('*'))):
        raise ValueError('extra, missing or linked input; future labels/receipts not allowed')
    for name, value in expected.items():
        if sha(member(name)) != manifest['files_sha256'][name] or member(name).read_bytes() != canonical(value):
            raise ValueError('frozen first request or candidate pairing differs: '+name)
    return manifest
