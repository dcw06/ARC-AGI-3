"""Owned offline CPU game/token rehearsal; scripted replies are not model results."""
import argparse
from copy import deepcopy
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import sys
import time
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.engine_bridge import BridgeEngine
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import Journal,sha,write_new
from research.initial_geometry_assistance_v1.live_resources import environment
from research.initial_geometry_assistance_v1.model_io import TokenAudit
from research.verified_feedback_v1.preparation import verify
from research.verified_feedback_v1.flow import run_case
from research.verified_feedback_v1.interface import CONDITIONS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','game-environment','game-python','output','recordings'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--input-pin',required=True);parser.add_argument('--game-pin',required=True)
    args=parser.parse_args()
    interfaces={line.split(':')[0].strip()for line in Path('/proc/net/dev').read_text().splitlines()[2:]if':'in line}
    if(sys.platform!='linux'or interfaces!={'lo'}or os.getpgrp()!=os.getpid()
       or os.environ.get('VERIFIED_FEEDBACK_CPU_OWNED')!='1' or os.environ.get('CUDA_VISIBLE_DEVICES')!=''):
        raise ValueError('owned, GPU-disabled, isolated CPU namespace/watchdog required')
    if metadata.version('transformers')!='4.57.6':raise ValueError('pinned native tokenizer differs')
    verify(args.inputs,args.input_pin);verify_game_environment(args.game_environment,args.game_pin)
    args.output.mkdir(exist_ok=False)
    checkpoints=json.loads((args.inputs/'checkpoints.json').read_bytes())['checkpoints']
    pairs=json.loads((args.inputs/'candidate-pairs.json').read_bytes())
    started=time.monotonic();deadline=started+700
    effects={op:0 for op in ('bootstrap','dispatch','close')};requests=[];results=[]
    def effect(op):effects[op]+=1
    def engine(cp,name):
        return BridgeEngine(args.game_python,cp['game_id'],args.game_environment/'environment_files',
            args.recordings/name,args.output/(name+'-engine.log'),deadline,
            env=dict(environment(),PYTHONPATH=str(ROOT),CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void'),on_effect=effect)
    for cp,row in zip(checkpoints,pairs):
        first_bodies=[]
        for condition in row['order']:
            name=cp['checkpoint_id']+'-'+condition;bodies=[];texts=[];events=[]
            journal=Journal(args.output/(name+'-play.jsonl'))
            def sink(event):journal(event);events.append(deepcopy(event))
            def complete(body):
                first=not bodies
                reply={'candidate_predictions':{'A':'none'if first else'unknown','B':'none'if first else'unknown'},
                    'selected_candidate':'A'if first else'B','observed_previous_change':'not_applicable'if first else'unknown',
                    'previous_prediction_check':'not_applicable'if first else'unknown'}
                text=json.dumps(reply);bodies.append(deepcopy(body));texts.append(text)
                requests.append({'id':name+'/'+str(len(bodies)-1),'body':deepcopy(body),'request_sha256':digest(body)})
                return text
            try:result=run_case(cp,row['candidates'],condition,engine(cp,name+'-play'),complete,sink,deadline=deadline)
            finally:journal.close()
            if result['reason']in('invalid_answer','deadline','exception'):raise ValueError('scripted CPU flow failed')
            first_bodies.append(bodies[0]);replayed=[];position=[0]
            replay_journal=Journal(args.output/(name+'-replay.jsonl'))
            def replay_sink(event):replay_journal(event);replayed.append(deepcopy(event))
            def replay_complete(body):
                index=position[0];position[0]+=1
                if digest(body)!=digest(bodies[index]):raise ValueError('rebuilt CPU request differs')
                return texts[index]
            try:again=run_case(cp,row['candidates'],condition,engine(cp,name+'-replay'),replay_complete,replay_sink,deadline=deadline)
            finally:replay_journal.close()
            if digest(events)!=digest(replayed)or result!=again:raise ValueError('independent CPU trajectory replay differs')
            results.append(result)
        if first_bodies[0]!=first_bodies[1]:raise ValueError('first-decision inputs differ by condition')
    archive=ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if sha(archive)!='af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
        raise ValueError('processor fixture differs')
    counts=[]
    with tempfile.TemporaryDirectory(prefix='verified-feedback-native-')as directory:
        with zipfile.ZipFile(archive)as bundle:
            for name in bundle.namelist():
                if Path(name).name!=name:raise ValueError('unsafe processor fixture')
                (Path(directory)/name).write_bytes(bundle.read(name))
        import torch
        torch.set_num_threads(2);native=TokenAudit(directory)
        for request in requests:
            count=native(request['body'])
            if type(count)is not int or not 0<count<=8192:raise ValueError('native prompt token bound differs')
            counts.append({'id':request['id'],'request_sha256':request['request_sha256'],'prompt_tokens':count})
    verify(args.inputs,args.input_pin)
    if time.monotonic()>=deadline:raise TimeoutError('CPU rehearsal deadline')
    write_new(args.output/'requests-PRIVATE.json',requests)
    write_new(args.output/'native-tokens-PRIVATE.json',counts)
    receipt={'passed':True,'input_manifest_sha256':args.input_pin,'conditions':len(results),
        'scripted_completions':sum(r['model_calls']for r in results),'independent_game_replays':len(results),
        'second_phases_reached':sum(r['model_calls']==2 for r in results),
        'stop_reasons':{reason:sum(r['reason']==reason for r in results)for reason in{r['reason']for r in results}},
        'effects_including_replay':effects,'native_counts':len(counts),'maximum_native_prompt_tokens':max(r['prompt_tokens']for r in counts),
        'transformers_version':metadata.version('transformers'),'elapsed_seconds':time.monotonic()-started,
        'requests_sha256':sha(args.output/'requests-PRIVATE.json'),'native_token_receipt_sha256':sha(args.output/'native-tokens-PRIVATE.json'),
        'GPU_jobs':0,'neural_generations':0,'provider_writes':0,
        'qualification':'Scripted policy and actual offline game/token replay only. No neural improvement, forecast-accuracy result, production lifecycle certification or authority.'}
    write_new(args.output/'CPU-rehearsal.json',receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
