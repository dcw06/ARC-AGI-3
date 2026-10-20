"""Closed, answer-free live inputs bound to the retained CPU preparation."""
from copy import deepcopy
import json
from pathlib import Path

from research.action_effect_choice_v1.preparation import derive, verify
from research.action_effect_choice_v1.interface import VARIANTS, make_request
from research.feedback_probe_v1.source_closure import safe_member
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new

MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_PROMPT_TOKENS = 8192
MAXIMA = {'checkpoints': 8, 'policy_conditions': 16, 'policy_generations': 32,
          'startup_canary': 1, 'total_generations': 33, 'prefix_dispatches': 36,
          'continuation_dispatches': 32, 'bootstrap_resets': 16,
          'offline_actions_including_restoration': 84, 'local_scorecards': 16}


def protocol():
    path = Path(__file__).with_name('live_protocol.json')
    value = json.loads(path.read_bytes())
    if (value['comparison_protocol_sha256'] != sha(path.with_name('protocol.json')) or
            value['comparison_protocol_sha256'] != sha(path.parent.parent/'action_effect_choice_v1/protocol.json') or
            canonical(value['prospective_maxima']) != canonical(MAXIMA) or
            value['max_prompt_tokens_per_request'] != MAX_PROMPT_TOKENS):
        raise ValueError('frozen live/scientific protocol differs')
    return value


def check_checkpoints(checkpoints):
    if digest(checkpoints) != protocol()['checkpoint_inventory_sha256']:
        raise ValueError('original checkpoint inventory differs')
    rows = derive(checkpoints)
    return [dict(deepcopy(cp), order=row['order']) for cp, row in zip(checkpoints, rows)]


def expected_inputs(checkpoints):
    rows = derive(checkpoints)
    result = {'candidate-pairs.json': rows}
    for cp, row in zip(checkpoints, rows):
        for variant in VARIANTS:
            result['model-inputs/'+cp['checkpoint_id']+'-'+variant+'.json'] = make_request(cp['base_request'], row['candidates'], variant)
    return result


def verify_inputs(root, pin):
    root = Path(root)
    member = lambda name: safe_member(root, name)
    if sha(member('manifest.json')) != pin: raise ValueError('live manifest changed')
    manifest = json.loads(member('manifest.json').read_bytes())
    frozen = protocol()
    if (manifest.get('schema') != 'action_effect_choice_live_inputs_v1' or
            manifest.get('protocol_sha256') != sha(Path(__file__).with_name('live_protocol.json')) or
            manifest.get('source_CPU_manifest_sha256') != frozen['source_CPU_manifest_sha256'] or
            canonical(manifest.get('prospective_maxima')) != canonical(MAXIMA) or
            sha(member('checkpoints.json')) != frozen['checkpoint_file_sha256']):
        raise ValueError('live input provenance/protocol/checkpoint differs')
    original = json.loads(member('checkpoints.json').read_bytes())
    check_checkpoints(original['checkpoints'])
    expected = expected_inputs(original['checkpoints'])
    expected['checkpoints.json'] = original
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if (set(manifest.get('files', {})) != set(expected) or actual != set(expected) | {'manifest.json'} or
            any(p.is_symlink() for p in root.rglob('*'))):
        raise ValueError('extra, missing or linked inference input')
    for name, value in expected.items():
        if sha(member(name)) != manifest['files'][name] or member(name).read_bytes() != canonical(value):
            raise ValueError('frozen inference bytes differ: '+name)
    return manifest


def prepare_inputs(prepared, cpu_pin, source, output):
    prepared, output = Path(prepared), Path(output)
    frozen = protocol()
    if cpu_pin != frozen['source_CPU_archive_sha256']:
        raise ValueError('sealed CPU source archive identity differs')
    original = verify(prepared, frozen['source_CPU_manifest_sha256'])
    output.mkdir(parents=True, exist_ok=False)
    for name in sorted(original['future_inference_allowlist']):
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(safe_member(prepared, name).read_bytes())
    write_new(output/'manifest.json', {
        'schema': 'action_effect_choice_live_inputs_v1',
        'protocol_sha256': sha(Path(__file__).with_name('live_protocol.json')),
        'source_CPU_manifest_sha256': frozen['source_CPU_manifest_sha256'],
        'files': {name: sha(output/name) for name in original['future_inference_allowlist']},
        'prospective_maxima': MAXIMA,
        'privacy': 'Frozen CPU inference allowlist only; no branch labels, future states or scripted answers.'})
    pin = sha(output/'manifest.json')
    verify_inputs(output, pin)
    return pin
