"""Seal shared pairs and first requests; future branch answers are not inputs."""
from copy import deepcopy
import json
from pathlib import Path

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.feedback_probe_v1.checkpoints import checked_checkpoint
from research.feedback_probe_v1.source_closure import safe_member
from .interface import VARIANTS, candidates, make_request

def protocol(): return json.loads(Path(__file__).with_name('protocol.json').read_bytes())

def derive(checkpoints):
    if type(checkpoints) is not list or len(checkpoints) != 8: raise ValueError('all eight original checkpoints required')
    if len({cp['checkpoint_id'] for cp in checkpoints}) != 8: raise ValueError('duplicate checkpoint')
    rows = []
    for ordinal, cp in enumerate(checkpoints):
        checked_checkpoint(cp, model=protocol()['model'])
        rows.append({'checkpoint_id': cp['checkpoint_id'], 'candidates': candidates(cp, ordinal),
                     'order': list(VARIANTS if ordinal % 2 == 0 else reversed(VARIANTS))})
    return rows

def build(checkpoint_file, output):
    checkpoint_file, output = Path(checkpoint_file), Path(output)
    if sha(checkpoint_file) != protocol()['source_checkpoint_file_sha256']: raise ValueError('external checkpoint pin differs')
    original = json.loads(checkpoint_file.read_bytes())
    checkpoints = original['checkpoints']; rows = derive(checkpoints)
    payload = {'checkpoints.json': original, 'candidate-pairs.json': rows}
    for cp, row in zip(checkpoints, rows):
        for variant in VARIANTS:
            payload['model-inputs/'+cp['checkpoint_id']+'-'+variant+'.json'] = make_request(cp['base_request'], row['candidates'], variant)
    output.mkdir(exist_ok=False)
    for name, value in payload.items():
        path = output/name; path.parent.mkdir(parents=True, exist_ok=True); write_new(path, value)
    module = Path(__file__).parent
    sources = {path.name: sha(path) for path in sorted(module.iterdir()) if path.suffix in ('.py', '.json')}
    manifest = {'schema': 'action_effect_choice_CPU_inputs_v1', 'protocol_sha256': sha(module/'protocol.json'),
        'source_checkpoint_sha256': sha(checkpoint_file), 'module_sources_sha256': sources,
        'files_sha256': {name: sha(output/name) for name in payload}, 'future_inference_allowlist': sorted(payload),
        'proposed_live_maxima': protocol()['proposed_live_maxima'], 'GPU_jobs': 0, 'model_generations': 0,
        'qualification': 'Prospective CPU inputs only; reference branches and later dynamic prompts must remain outside inference staging.'}
    write_new(output/'input-manifest.json', manifest)
    return manifest

def verify(output, pin):
    output = Path(output)
    if sha(safe_member(output,'input-manifest.json')) != pin: raise ValueError('external input manifest pin differs')
    manifest = json.loads((output/'input-manifest.json').read_bytes())
    module = Path(__file__).parent
    sources = {path.name: sha(path) for path in sorted(module.iterdir()) if path.suffix in ('.py', '.json')}
    if manifest['module_sources_sha256'] != sources or manifest['protocol_sha256'] != sha(module/'protocol.json'):
        raise ValueError('CPU sources or protocol changed')
    if (manifest['source_checkpoint_sha256'] != protocol()['source_checkpoint_file_sha256'] or
            sha(output/'checkpoints.json') != protocol()['source_checkpoint_file_sha256']):
        raise ValueError('original checkpoint bytes changed')
    payload = {name: json.loads(safe_member(output,name).read_bytes()) for name in manifest['files_sha256']}
    expected = {'checkpoints.json': payload['checkpoints.json'],
                'candidate-pairs.json': derive(payload['checkpoints.json']['checkpoints'])}
    for cp, row in zip(payload['checkpoints.json']['checkpoints'], expected['candidate-pairs.json']):
        for variant in VARIANTS:
            expected['model-inputs/'+cp['checkpoint_id']+'-'+variant+'.json'] = make_request(cp['base_request'], row['candidates'], variant)
    if (set(manifest['files_sha256']) != set(expected) or manifest['future_inference_allowlist'] != sorted(expected)
            or manifest['proposed_live_maxima'] != protocol()['proposed_live_maxima']):
        raise ValueError('reference leak or input/scope inventory differs')
    actual = {path.relative_to(output).as_posix() for path in output.rglob('*') if path.is_file()}
    if actual != set(expected) | {'input-manifest.json'} or any(path.is_symlink()for path in output.rglob('*')):
        raise ValueError('extra or linked unreviewed input file')
    for name, value in expected.items():
        if sha(output/name) != manifest['files_sha256'][name] or digest(payload[name]) != digest(value):
            raise ValueError('frozen pair or request changed')
    return manifest
