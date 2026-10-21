"""Externally frozen eight-checkpoint inputs and exact inference allowlist."""
from copy import deepcopy
import json
from pathlib import Path
from research.verified_feedback_v1.preparation import verify
from research.verified_feedback_v1.interface import CONDITIONS,make_request
from research.action_effect_choice_v2.interface import candidates
from research.feedback_probe_v1.checkpoints import checked_checkpoint
from research.feedback_probe_v1.source_closure import safe_member
from research.initial_geometry_assistance_v1.geometry import canonical,digest
from research.initial_geometry_assistance_v1.live_io import sha,write_new

MODEL='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_PROMPT_TOKENS=8192
MAXIMA={'checkpoints':8,'policy_conditions':16,'policy_generations':32,'startup_canary':1,'total_generations':33,
        'prefix_dispatches':36,'continuation_dispatches':32,'bootstrap_resets':16,
        'offline_actions_including_restoration':84,'local_scorecards':16}

def protocol():
    path=Path(__file__).with_name('live_protocol.json');value=json.loads(path.read_bytes())
    if(value['comparison_protocol_sha256']!=sha(path.with_name('protocol.json'))or
       value['comparison_protocol_sha256']!=sha(path.parent.parent/'verified_feedback_v1/protocol.json')or
       canonical(value['prospective_maxima'])!=canonical(MAXIMA)or value['checkpoint_ordinals']!=list(range(8))or
       value['max_prompt_tokens_per_request']!=8192 or value['max_new_tokens_per_generation']!=256):
        raise ValueError('frozen feedback protocol differs')
    return value

def derive(checkpoints):
    return [dict(checkpoint_id=cp['checkpoint_id'],candidates=candidates(cp,i),
        order=list(CONDITIONS if i%2==0 else reversed(CONDITIONS)))for i,cp in enumerate(checkpoints)]

def check_checkpoints(checkpoints):
    if digest(checkpoints)!=protocol()['checkpoint_inventory_sha256']:
        raise ValueError('externally frozen checkpoint inventory differs')
    if len(checkpoints)!=8 or sum(len(cp['prefix'])for cp in checkpoints)!=18:
        raise ValueError('eight-checkpoint restoration plan differs')
    result=[]
    for cp,row in zip(checkpoints,derive(checkpoints)):
        checked_checkpoint(cp,model=MODEL);result.append(dict(deepcopy(cp),order=row['order']))
    return result

def expected_inputs(checkpoints):
    checked=check_checkpoints(checkpoints);rows=derive(checked);result={'candidate-pairs.json':rows}
    for cp,row in zip(checked,rows):
        for condition in CONDITIONS:
            result['model-inputs/'+cp['checkpoint_id']+'-'+condition+'.json']=make_request(cp['base_request'],
                row['candidates'],condition,study_decision_index=0,restored_prefix_length=len(cp['prefix']),
                trajectory_id=cp['checkpoint_id']+'-'+condition)
    return result

def verify_inputs(root,pin):
    root=Path(root);member=lambda name:safe_member(root,name)
    if sha(member('manifest.json'))!=pin:raise ValueError('external live manifest pin differs')
    manifest=json.loads(member('manifest.json').read_bytes());frozen=protocol()
    if(manifest.get('schema')!='verified_feedback_live_inputs_v1'or
       manifest.get('protocol_sha256')!=sha(Path(__file__).with_name('live_protocol.json'))or
       manifest.get('source_CPU_manifest_sha256')!=frozen['source_CPU_manifest_sha256']or
       canonical(manifest.get('prospective_maxima'))!=canonical(MAXIMA)or
       sha(member('checkpoints.json'))!=frozen['checkpoint_file_sha256']):raise ValueError('live input provenance differs')
    original=json.loads(member('checkpoints.json').read_bytes())
    expected=expected_inputs(original['checkpoints']);expected['checkpoints.json']=original
    actual={p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()}
    if(set(manifest.get('files',{}))!=set(expected)or actual!=set(expected)|{'manifest.json'}or
       any(p.is_symlink()for p in root.rglob('*'))):raise ValueError('extra/missing/linked live input')
    for name,value in expected.items():
        if sha(member(name))!=manifest['files'][name]or member(name).read_bytes()!=canonical(value):
            raise ValueError('frozen condition or request differs: '+name)
    return manifest

def prepare_inputs(prepared,cpu_pin,source,output):
    prepared,output=Path(prepared),Path(output);frozen=protocol()
    if cpu_pin!=frozen['source_CPU_archive_sha256']:raise ValueError('external CPU archive identity differs')
    verify(prepared,frozen['source_CPU_manifest_sha256'])
    original=json.loads(safe_member(prepared,'checkpoints.json').read_bytes())
    if sha(prepared/'checkpoints.json')!=frozen['checkpoint_file_sha256']:raise ValueError('original checkpoint bytes differ')
    payload=expected_inputs(original['checkpoints']);payload['checkpoints.json']=original
    output.mkdir(parents=True,exist_ok=False)
    for name,value in payload.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);write_new(path,value)
    write_new(output/'manifest.json',{'schema':'verified_feedback_live_inputs_v1',
        'protocol_sha256':sha(Path(__file__).with_name('live_protocol.json')),
        'source_CPU_manifest_sha256':frozen['source_CPU_manifest_sha256'],
        'files':{name:sha(output/name)for name in payload},'prospective_maxima':MAXIMA,
        'privacy':'Original exposed cases and first prompts only; no executed receipts, future prompts or references.'})
    pin=sha(output/'manifest.json');verify_inputs(output,pin);return pin
