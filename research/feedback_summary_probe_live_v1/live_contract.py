"""Strict inference-only derivation from the externally sealed CPU diagnostic."""
import json
from pathlib import Path

from research.feedback_probe_v1.source_closure import safe_member
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.feedback_probe_v1.checkpoints import checked_checkpoint
from research.feedback_summary_probe_v1.interface import VARIANTS
from research.feedback_summary_probe_v1.preparation import model_rows, verify_prepared

MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_PROMPT_TOKENS = 8192
MAXIMA = {'checkpoints':8,'policy_conditions':16,'policy_generations':64,'recognition_generations':16,
          'startup_canary':1,'total_generations':81,'prefix_dispatches':36,'continuation_dispatches':64,
          'bootstrap_resets':16,'offline_actions_including_restoration':116,'local_scorecards':16}


def protocol():
    path = Path(__file__).with_name('live_protocol.json')
    value = json.loads(path.read_bytes())
    if (value['comparison_protocol_sha256'] != sha(path.with_name('protocol.json')) or
            value['max_prompt_tokens_per_request'] != MAX_PROMPT_TOKENS or
            canonical(value['prospective_maxima']) != canonical(MAXIMA)):
        raise ValueError('frozen summary live protocol differs')
    return value


def check_checkpoints(checkpoints):
    frozen = protocol()
    if type(checkpoints) is not list or len(checkpoints) != 8 or digest(checkpoints) != frozen['checkpoint_inventory_sha256']:
        raise ValueError('frozen checkpoint inventory or condition order differs')
    for ordinal, checkpoint in enumerate(checkpoints):
        checked_checkpoint(checkpoint, model=MODEL)
        expected = list(VARIANTS if ordinal % 2 == 0 else reversed(VARIANTS))
        if checkpoint.get('order') != expected:
            raise ValueError('checkpoint condition order differs')
    return checkpoints


def verify_inputs(root, pin):
    root = Path(root)
    member = lambda name: safe_member(root, name)
    if sha(member('manifest.json')) != pin:
        raise ValueError('live inference manifest changed')
    manifest = json.loads(member('manifest.json').read_bytes())
    frozen = protocol()
    if (manifest.get('schema') != 'feedback_summary_probe_live_inputs_v1' or
            manifest.get('protocol_sha256') != sha(Path(__file__).with_name('live_protocol.json')) or
            canonical(manifest.get('prospective_maxima')) != canonical(MAXIMA) or
            manifest.get('source_protocol_sha256') != frozen['comparison_protocol_sha256']):
        raise ValueError('live input protocol or maxima differ')
    for name in ('source_CPU_draft_lock_sha256','source_CPU_manifest_sha256'):
        if manifest.get(name) != frozen[name]:
            raise ValueError('CPU provenance differs from frozen source pin')
    if sha(member('checkpoints.json')) != frozen['checkpoint_file_sha256']:
        raise ValueError('frozen checkpoint bytes differ')
    checkpoints = check_checkpoints(json.loads(member('checkpoints.json').read_bytes())['checkpoints'])
    rows = model_rows(checkpoints)
    expected = {'checkpoints.json'} | {row['path'] for row, _ in rows}
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
    if (type(manifest.get('files')) is not dict or set(manifest['files']) != expected or
            actual != expected | {'manifest.json'} or any(path.is_symlink() for path in root.rglob('*')) or
            canonical(manifest.get('model_input_rows')) != canonical([row for row, _ in rows])):
        raise ValueError('inference-only inventory differs')
    for name, expected_hash in manifest['files'].items():
        if sha(member(name)) != expected_hash:
            raise ValueError('inference bytes differ: '+name)
    for row, body in rows:
        if member(row['path']).read_bytes() != canonical(body):
            raise ValueError('request not reconstructed from frozen checkpoint')
    return manifest


def prepare_inputs(prepared, cpu_pin, source, output):
    frozen = protocol()
    prepared, output = Path(prepared), Path(output)
    if cpu_pin != frozen['source_CPU_draft_lock_sha256'] or sha(prepared/'manifest.json') != frozen['source_CPU_manifest_sha256']:
        raise ValueError('CPU snapshot differs from external live protocol pins')
    original = verify_prepared(prepared, cpu_pin, source)
    checkpoints = check_checkpoints(json.loads((prepared/'checkpoints.json').read_bytes())['checkpoints'])
    rows = model_rows(checkpoints)
    members = {'checkpoints.json'} | {row['path'] for row, _ in rows}
    if (canonical(original['model_input_rows']) != canonical([row for row, _ in rows]) or
            set(original['future_inference_allowlist']) != members):
        raise ValueError('CPU request allowlist differs')
    output.mkdir(parents=True, exist_ok=False)
    for name in sorted(members):
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write(safe_member(prepared,name).read_bytes())
    manifest = {'schema':'feedback_summary_probe_live_inputs_v1',
        'protocol_sha256':sha(Path(__file__).with_name('live_protocol.json')),
        'source_protocol_sha256':frozen['comparison_protocol_sha256'],
        'source_CPU_draft_lock_sha256':cpu_pin,'source_CPU_manifest_sha256':sha(prepared/'manifest.json'),
        'files':{name:sha(output/name) for name in sorted(members)},
        'model_input_rows':[row for row,_ in rows],'prospective_maxima':MAXIMA,
        'privacy':'Inference allowlist only; no reference keys, source-run logs or scripted server.'}
    write_new(output/'manifest.json',manifest)
    pin = sha(output/'manifest.json')
    verify_inputs(output,pin)
    return pin
