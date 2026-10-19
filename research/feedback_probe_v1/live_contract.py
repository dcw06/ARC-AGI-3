"""Frozen checkpoint inference inputs, with evaluator reference keys excluded."""
import json
from pathlib import Path, PurePosixPath

from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from .checkpoints import checked_checkpoint
from .interface import VARIANTS, policy_request, recognition_request

MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_PROMPT_TOKENS = 8192
MAXIMA = {'checkpoints': 8, 'policy_conditions': 16, 'policy_generations': 64,
          'recognition_generations': 8, 'startup_canary': 1, 'total_generations': 73,
          'prefix_dispatches': 36, 'continuation_dispatches': 64, 'bootstrap_resets': 16,
          'offline_actions_including_restoration': 116, 'local_scorecards': 16}


def protocol():
    path = Path(__file__).with_name('live_protocol.json')
    value = json.loads(path.read_bytes())
    if (value['comparison_protocol_sha256'] != sha(path.with_name('protocol.json')) or
            value['max_prompt_tokens_per_request'] != MAX_PROMPT_TOKENS or
            canonical(value['prospective_maxima']) != canonical(MAXIMA)):
        raise ValueError('frozen live diagnostic protocol differs')
    return value


def check_checkpoints(checkpoints):
    frozen = protocol()
    if (type(checkpoints) is not list or len(checkpoints) != 8 or
            digest(checkpoints) != frozen['checkpoint_inventory_sha256']):
        raise ValueError('frozen checkpoint inventory or condition order differs')
    for ordinal, checkpoint in enumerate(checkpoints):
        checked_checkpoint(checkpoint, model=MODEL)
        expected = list(VARIANTS if ordinal % 2 == 0 else reversed(VARIANTS))
        if checkpoint.get('order') != expected:
            raise ValueError('checkpoint condition order differs')
    return checkpoints


def _model_rows(checkpoints):
    rows = []
    for checkpoint in checkpoints:
        identity = checkpoint['checkpoint_id']
        for kind in (*VARIANTS, 'recognition'):
            body = (recognition_request(checkpoint['base_request']) if kind == 'recognition' else
                    policy_request(checkpoint['base_request'], kind))
            rows.append(({'checkpoint_id': identity, 'kind': kind,
                          'path': 'model-inputs/'+identity+'-'+kind+'.json',
                          'request_sha256': digest(body)}, body))
    return rows


def _member(root, name):
    relative = PurePosixPath(name)
    if (type(name) is not str or '\\' in name or ':' in name or relative.is_absolute() or
            not relative.parts or '..' in relative.parts or '.' in relative.parts):
        raise ValueError('unsafe inference input member')
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise ValueError('unsafe/missing inference input member')
    return path


def verify_inputs(root, pin):
    root = Path(root)
    if root.is_symlink() or sha(_member(root, 'manifest.json')) != pin:
        raise ValueError('live inference manifest changed')
    manifest = json.loads((root/'manifest.json').read_bytes())
    if (manifest.get('schema') != 'feedback_probe_live_inputs_v1' or
            manifest.get('protocol_sha256') != sha(Path(__file__).with_name('live_protocol.json')) or
            canonical(manifest.get('prospective_maxima')) != canonical(MAXIMA) or
            manifest.get('source_protocol_sha256') != protocol()['comparison_protocol_sha256']):
        raise ValueError('live input protocol or maxima binding differs')
    for field in ('source_CPU_draft_lock_sha256', 'source_CPU_manifest_sha256'):
        value = manifest.get(field)
        if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('live input CPU provenance pin differs')
    checkpoints_path = _member(root, 'checkpoints.json')
    if sha(checkpoints_path) != protocol()['checkpoint_file_sha256']:
        raise ValueError('frozen checkpoint bytes differ')
    checkpoints = check_checkpoints(json.loads(checkpoints_path.read_bytes())['checkpoints'])
    rows = _model_rows(checkpoints)
    expected = {'checkpoints.json'} | {row['path'] for row, _ in rows}
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if (type(manifest.get('files')) is not dict or set(manifest['files']) != expected or
            actual != expected | {'manifest.json'} or
            any(p.is_symlink() for p in root.rglob('*')) or
            canonical(manifest.get('model_input_rows')) != canonical([row for row, _ in rows])):
        raise ValueError('inference-only input inventory differs')
    for name, expected_hash in manifest['files'].items():
        if sha(_member(root, name)) != expected_hash:
            raise ValueError('live inference input bytes differ: '+name)
    for row, body in rows:
        if _member(root, row['path']).read_bytes() != canonical(body):
            raise ValueError('model input not reconstructed from frozen checkpoint')
    return manifest


def prepare_inputs(prepared, cpu_pin, source, output):
    """Derive a deterministic inference allowlist from a verified CPU preparation."""
    from .preparation import verify_prepared
    prepared, output = Path(prepared), Path(output)
    original = verify_prepared(prepared, cpu_pin, source)
    checkpoints = check_checkpoints(json.loads((prepared/'checkpoints.json').read_bytes())['checkpoints'])
    if canonical(original['prospective_maxima']) != canonical(MAXIMA):
        raise ValueError('CPU preparation exceeds frozen live schedule')
    rows = _model_rows(checkpoints)
    members = {'checkpoints.json'} | {row['path'] for row, _ in rows}
    if canonical(original['model_input_rows']) != canonical([row for row, _ in rows]):
        raise ValueError('CPU model input schedule differs')
    output.mkdir(parents=True, exist_ok=False)
    for name in sorted(members):
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(_member(prepared, name).read_bytes())
    manifest = {'schema': 'feedback_probe_live_inputs_v1',
                'protocol_sha256': sha(Path(__file__).with_name('live_protocol.json')),
                'source_protocol_sha256': protocol()['comparison_protocol_sha256'],
                'source_CPU_draft_lock_sha256': cpu_pin,
                'source_CPU_manifest_sha256': sha(prepared/'manifest.json'),
                'files': {name: sha(output/name) for name in sorted(members)},
                'model_input_rows': [row for row, _ in rows], 'prospective_maxima': MAXIMA,
                'privacy': 'Inference allowlist only: frozen checkpoints and model inputs; no reference keys.'}
    write_new(output/'manifest.json', manifest)
    pin = sha(output/'manifest.json')
    verify_inputs(output, pin)
    return pin
