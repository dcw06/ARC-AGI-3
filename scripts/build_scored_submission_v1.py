"""Build a private, one-hour, scored E1S-R review candidate. Does not authenticate, upload or approve."""
import argparse
import ast
import base64
import hashlib
import json
import lzma
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def build(output, bindings):
    from research.stagnation_supervision_runtime_v2.notebook import source_names
    names,_ = source_names(ROOT)
    names = set(names)|{p.relative_to(ROOT).as_posix() for p in (ROOT/'agent').glob('*.py')}
    names |= {'config/e1_feature_manifests.yaml','config/operational_primary.yaml','config/m0_launch_spec_q3vl30.json'}
    raw = {name:(ROOT/name).read_bytes() for name in sorted(names)}
    protocol_name = 'research/stagnation_supervision_runtime_v2/protocol.json'
    protocol = json.loads(raw[protocol_name])
    protocol['model']['kaggle_source'] = bindings['model_source']
    protocol['model']['mounted_path'] = bindings['model_mount']
    raw[protocol_name] = (json.dumps(protocol,sort_keys=True,indent=1)+'\n').encode()
    spec = {'schema':'scored_baseline_one_hour_v1','source_approved':False,
            'attempt_id':'scored-e1sr-'+uuid.uuid4().hex,
            'authorized_seconds':3600,'internal_seconds':3300,'study_cutoff_seconds':3000,
            'maximum_games':110,'maximum_policy_generations':8800,'maximum_canaries':1,
            'maximum_actions_per_game':80,'maximum_scorecards':1,'maximum_scored_submissions':1,
            'automatic_retries':0, 'account':bindings['kernel'].split('/')[0],
            'permission_outcome':'pending_scored_scope_review'}
    raw['config/scored_submission_v1.json'] = (json.dumps(spec,sort_keys=True,indent=1)+'\n').encode()
    hashes = {n:sha(v) for n,v in raw.items()}
    packed = base64.b85encode(lzma.compress(json.dumps({n:base64.b64encode(v).decode() for n,v in raw.items()},
                                                       sort_keys=True).encode(),preset=9)).decode()
    code = f'''import base64, hashlib, json, lzma, pathlib, shutil, sys, tempfile, time
started = time.monotonic()
source = pathlib.Path(tempfile.mkdtemp(prefix='arc3-scored-source-'))
try:
    payload = json.loads(lzma.decompress(base64.b85decode({packed!r})))
    bindings = {hashes!r}
    if set(payload) != set(bindings):
        raise ValueError('scored source inventory mismatch')
    for name,value in payload.items():
        data = base64.b64decode(value,validate=True)
        if hashlib.sha256(data).hexdigest() != bindings[name]:
            raise ValueError('scored source drift: '+name)
        path = source/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
    sys.path.insert(0,str(source))
    from agent.scored_runtime import entry
    result = entry(source,started)
    print(json.dumps(result,sort_keys=True))
finally:
    if source.exists():
        shutil.rmtree(source)
'''
    notebook = {'nbformat':4,'nbformat_minor':4,'metadata':{'kernelspec':{'name':'python3','language':'python','display_name':'Python 3'}},
                'cells':[{'cell_type':'markdown','metadata':{},'source':'# E1S-R one-hour scored submission — review candidate\nNo approval or submission is granted by this file.'},
                         {'cell_type':'code','metadata':{},'source':code,'execution_count':None,'outputs':[]}]}
    metadata = {'id':bindings['kernel'],'title':bindings['kernel'].split('/')[1], 'code_file':'submission.ipynb',
                'language':'python','kernel_type':'notebook','is_private':True,
                'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
                'dataset_sources':[protocol['dataset']['ref']+'/1',bindings['model_source']],
                'model_sources':[],'competition_sources':['arc-prize-2026-arc-agi-3'],
                **protocol['kaggle_image']}
    artifacts = {'submission.ipynb':notebook,'kernel-metadata.json':metadata}
    lock = {'schema':'scored_baseline_review_v1','source_approved':False,'gpu_authorized':False,
            'source_bindings':hashes, 'private_bindings':bindings, 'specification':spec,
            'artifact_hashes':{n:sha((json.dumps(v,sort_keys=True,indent=1)+'\n').encode()) for n,v in artifacts.items()}}
    output.mkdir(parents=True,exist_ok=False)
    for name,value in {**artifacts,'review-lock.json':lock}.items():
        (output/name).write_text(json.dumps(value,sort_keys=True,indent=1)+'\n',encoding='utf-8')
    for name,data in raw.items():
        if name.endswith('.py'):
            compile(data,name,'exec')
    compile(code,'scored notebook','exec')
    print(json.dumps({'review_lock_sha256':sha((output/'review-lock.json').read_bytes()),
                      'source_files':len(raw),'notebook_bytes':(output/'submission.ipynb').stat().st_size,
                      'gpu_enabled':False,'source_approved':False}))
    return lock

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--private-bindings',type=Path,required=True)
    args = parser.parse_args()
    build(args.output,json.loads(args.private_bindings.read_bytes()))
