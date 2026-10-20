"""Externally pinned, answer-free four-condition pilot inputs and fixed maxima."""
from copy import deepcopy
import json
from pathlib import Path

from research.action_effect_choice_v2.preparation import verify
from research.action_effect_choice_v2.interface import VARIANTS, candidates, make_request
from research.feedback_probe_v1.checkpoints import checked_checkpoint
from research.feedback_probe_v1.source_closure import safe_member
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new

MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_PROMPT_TOKENS = 8192
MAXIMA = {'checkpoints': 2, 'policy_conditions': 4, 'policy_generations': 8,
          'startup_canary': 1, 'total_generations': 9, 'prefix_dispatches': 8,
          'continuation_dispatches': 8, 'bootstrap_resets': 4,
          'offline_actions_including_restoration': 20, 'local_scorecards': 4}


def protocol():
    path=Path(__file__).with_name('live_protocol.json');value=json.loads(path.read_bytes())
    if (value['comparison_protocol_sha256']!=sha(path.with_name('protocol.json')) or
            value['comparison_protocol_sha256']!=sha(path.parent.parent/'action_effect_choice_v2/protocol.json') or
            canonical(value['prospective_maxima'])!=canonical(MAXIMA) or
            value['checkpoint_ordinals']!=[0,1] or value['max_prompt_tokens_per_request']!=8192 or
            value['max_new_tokens_per_generation']!=256):
        raise ValueError('frozen pilot protocol differs')
    return value


def check_checkpoints(checkpoints):
    frozen=protocol()
    if digest(checkpoints)!=frozen['checkpoint_inventory_sha256']:
        raise ValueError('externally frozen ordinal-selected pilot checkpoints differ')
    if len(checkpoints)!=2 or sum(len(cp['prefix'])for cp in checkpoints)!=4:
        raise ValueError('pilot restoration plan differs')
    result=[]
    for i,cp in enumerate(checkpoints):
        checked_checkpoint(cp,model=MODEL)
        result.append(dict(deepcopy(cp),order=list(VARIANTS if i%2==0 else reversed(VARIANTS))))
    return result


def expected_inputs(checkpoints):
    checked=check_checkpoints(checkpoints)
    rows=[dict(checkpoint_id=cp['checkpoint_id'],candidates=candidates(cp,i),order=cp['order'])for i,cp in enumerate(checked)]
    result={'candidate-pairs.json':rows}
    for cp,row in zip(checked,rows):
        for variant in VARIANTS:
            result['model-inputs/'+cp['checkpoint_id']+'-'+variant+'.json']=make_request(
                cp['base_request'],row['candidates'],variant,study_decision_index=0,restored_prefix_length=len(cp['prefix']))
    return result


def verify_inputs(root,pin):
    root=Path(root);member=lambda name:safe_member(root,name)
    if sha(member('manifest.json'))!=pin:raise ValueError('live manifest changed')
    manifest=json.loads(member('manifest.json').read_bytes());frozen=protocol()
    if (manifest.get('schema')!='action_effect_choice_live_inputs_v2' or
            manifest.get('protocol_sha256')!=sha(Path(__file__).with_name('live_protocol.json')) or
            manifest.get('source_CPU_manifest_sha256')!=frozen['source_CPU_manifest_sha256'] or
            canonical(manifest.get('prospective_maxima'))!=canonical(MAXIMA) or
            sha(member('checkpoints.json'))!=frozen['checkpoint_file_sha256']):
        raise ValueError('pilot input protocol/provenance differs')
    original=json.loads(member('checkpoints.json').read_bytes())
    expected=expected_inputs(original['checkpoints']);expected['checkpoints.json']=original
    actual={p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()}
    if (set(manifest.get('files',{}))!=set(expected) or actual!=set(expected)|{'manifest.json'} or
            any(p.is_symlink()for p in root.rglob('*'))):raise ValueError('extra, missing or linked pilot input')
    for name,value in expected.items():
        if sha(member(name))!=manifest['files'][name]or member(name).read_bytes()!=canonical(value):
            raise ValueError('frozen pilot request differs: '+name)
    return manifest


def prepare_inputs(prepared,cpu_pin,source,output):
    prepared,source,output=map(Path,(prepared,source,output));frozen=protocol()
    if cpu_pin!=frozen['source_CPU_archive_sha256']:raise ValueError('CPU archive identity differs')
    verify(prepared,frozen['source_CPU_manifest_sha256'])
    original=json.loads(safe_member(prepared,'checkpoints.json').read_bytes())
    selected={'checkpoints':[original['checkpoints'][i]for i in frozen['checkpoint_ordinals']]}
    if sha(prepared/'checkpoints.json')!=frozen['original_eight_checkpoint_file_sha256']:
        raise ValueError('original eight-checkpoint file differs')
    payload=expected_inputs(selected['checkpoints']);payload['checkpoints.json']=selected
    output.mkdir(parents=True,exist_ok=False)
    for name,value in payload.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);write_new(path,value)
    write_new(output/'manifest.json',{'schema':'action_effect_choice_live_inputs_v2',
        'protocol_sha256':sha(Path(__file__).with_name('live_protocol.json')),
        'source_CPU_manifest_sha256':frozen['source_CPU_manifest_sha256'],
        'files':{name:sha(output/name)for name in payload},'prospective_maxima':MAXIMA,
        'privacy':'First two externally frozen original cases only; no references, scripted answers or future prompts.'})
    pin=sha(output/'manifest.json');verify_inputs(output,pin);return pin
