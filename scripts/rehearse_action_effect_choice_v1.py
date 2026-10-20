"""Owned CPU-only real-engine rehearsal with scripted replies and hidden reference branches."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.engine_bridge import BridgeEngine
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha,write_new
from research.initial_geometry_assistance_v1.live_resources import environment
from research.initial_geometry_assistance_v1.policy import request_for
from research.action_effect_choice_v1.preparation import verify
from research.action_effect_choice_v1.interface import VARIANTS,make_request,parse_choice,EFFECTS
from research.action_effect_choice_v1.flow import run_case,reference_branch,terminal
from research.action_effect_choice_v1.scoring import branch_key,score,effect_size

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','game-environment','game-python','output','recordings'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--input-pin',required=True);parser.add_argument('--game-pin',required=True)
    args=parser.parse_args()
    interfaces={line.split(':')[0].strip()for line in Path('/proc/net/dev').read_text().splitlines()[2:]if':'in line}
    if(sys.platform!='linux'or interfaces!={'lo'}or os.getpgrp()!=os.getpid()or os.environ.get('ACTION_EFFECT_CPU_OWNED')!='1'):
        raise ValueError('external ownership/watchdog and isolated loopback-only CPU namespace required')
    verify(args.inputs,args.input_pin);verify_game_environment(args.game_environment,args.game_pin)
    args.output.mkdir(exist_ok=False)
    checkpoints=json.loads((args.inputs/'checkpoints.json').read_bytes())['checkpoints']
    pairs=json.loads((args.inputs/'candidate-pairs.json').read_bytes())
    started=time.monotonic();deadline=started+1000
    effects={phase:{op:0 for op in ('bootstrap','dispatch','close')}for phase in ('play','replay','reference')}
    requests=[];results=[];scored=[];references={};serial=0
    def engine(cp,name,phase):
        def effect(op):effects[phase][op]+=1
        return BridgeEngine(args.game_python,cp['game_id'],args.game_environment/'environment_files',args.recordings/name,
            args.output/(name+'-engine.log'),deadline,
            env=dict(environment(),PYTHONPATH=str(ROOT),CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void'),on_effect=effect)
    def branches(cp,pair,path):
        nonlocal serial
        identity=cp['checkpoint_id']+'/'+digest([record['action']for record in path])
        if identity not in references:
            records={}
            for label in ('A','B'):
                serial+=1;name='reference-'+str(serial).zfill(3);events=[]
                records[label]=reference_branch(cp,pair,label,engine(cp,name,'reference'),events.append,
                    path=path,deadline=deadline)
                write_new(args.output/(name+'.json'),events)
            references[identity]=records
        return references[identity]
    for cp,row in zip(checkpoints,pairs):
        pair=row['candidates']
        initial_refs=branches(cp,pair,[])
        for variant in row['order']:
            name=cp['checkpoint_id']+'-'+variant;events=[];texts=[];bodies=[]
            def complete(body):
                decision=len(texts);choice=('A'if variant==VARIANTS[0]else'B')if decision==0 else('B'if variant==VARIANTS[0]else'A')
                text=json.dumps({'candidate_predictions':{'A':'unknown','B':'unknown'},'selected_candidate':choice,
                    'observed_previous_change':'not_applicable'if decision==0 else'unknown',
                    'previous_prediction_check':'not_applicable'if decision==0 else'unknown'})
                bodies.append(deepcopy(body));texts.append(text)
                requests.append({'id':name+'/'+str(decision),'body':deepcopy(body),'request_sha256':digest(body)})
                return text
            result=run_case(cp,pair,variant,engine(cp,name+'-play','play'),complete,events.append,deadline=deadline)
            write_new(args.output/(name+'-events.json'),events)
            if result['reason']in('invalid_answer','deadline','exception'):raise ValueError('scripted flow failed')
            replay_events=[];index=[0]
            def replay_complete(body):
                position=index[0];index[0]+=1
                if digest(body)!=digest(bodies[position]):raise ValueError('rebuilt replay request differs')
                return texts[position]
            replay_result=run_case(cp,pair,variant,engine(cp,name+'-replay','replay'),replay_complete,replay_events.append,deadline=deadline)
            if digest(events)!=digest(replay_events)or result!=replay_result:raise ValueError('full deterministic game replay differs')
            transitions=[event['record']for event in events if event['kind']=='transition']
            for decision,text in enumerate(texts):
                before=cp['current']if decision==0 else transitions[decision-1]['after']
                reference=branches(cp,pair,transitions[:decision])
                key=branch_key(before,pair,reference)
                chosen=parse_choice(text,first=decision==0)['selected_candidate']
                if digest(reference[chosen]['after'])!=digest(transitions[decision]['after']):
                    raise ValueError('selected reference branch differs from actual full outcome')
                prior=None if decision==0 else parse_choice(texts[decision-1],first=True)
                scored.append({'id':name+'/'+str(decision),'score':score(text,key,first=decision==0,
                    previous_forecast=None if prior is None else prior['candidate_predictions'][prior['selected_candidate']],
                    previous_observed=None if decision==0 else('yes'if transitions[decision-1]['before']['grid']!=before['grid']else'no'),
                    previous_effect=None if decision==0 else effect_size(transitions[decision-1]['before'],before))})
            results.append(result)
        # Audit every first-choice / prior-forecast combination without inference.
        for label in ('A','B'):
            branch=initial_refs[label]
            if terminal(branch['after'])or any(action['action_id']not in branch['after']['legal_actions']for action in pair.values()):continue
            record={'step':len(cp['prefix']),'before':branch['before'],'after':branch['after'],
                'action':branch['action'],'predicted_visible_change':'unknown'}
            base=request_for(cp['initial'],cp['initial_case']['geometry']['reviewed'],branch['after'],
                cp['prefix']+[record],len(cp['prefix'])+1,cp['base_request']['model'])
            for variant in VARIANTS:
                for forecast in EFFECTS:
                    prior={'candidate_predictions':{'A':'unknown','B':'unknown'},'selected_candidate':label,
                        'observed_previous_change':'not_applicable','previous_prediction_check':'not_applicable'}
                    prior['candidate_predictions'][label]=forecast
                    body=make_request(base,pair,variant,prior)
                    requests.append({'id':cp['checkpoint_id']+'/'+variant+'/CPU-next-input/'+label+'/'+forecast,
                                     'body':body,'request_sha256':digest(body)})
    verify(args.inputs,args.input_pin)
    first_opportunities=[{'checkpoint_id':cp['checkpoint_id'],
        'different_visible_effects':len(set(branch_key(cp['current'],row['candidates'],branches(cp,row['candidates'],[])).values()))>1}
        for cp,row in zip(checkpoints,pairs)]
    write_new(args.output/'reference-keys-PRIVATE.json',references)
    write_new(args.output/'request-audit-PRIVATE.json',requests)
    write_new(args.output/'scripted-scores-PRIVATE.json',scored)
    if time.monotonic()>=deadline:raise TimeoutError('CPU rehearsal deadline')
    receipt={'passed':True,'input_manifest_sha256':args.input_pin,'conditions':len(results),
        'scripted_completions':sum(row['model_calls']for row in results),'game_replays':len(results),
        'reference_branches':effects['reference']['bootstrap'],'request_variations':len(requests),
        'effects':effects,'first_choice_effect_separation':first_opportunities,
        'elapsed_seconds':time.monotonic()-started,'GPU_jobs':0,'neural_generations':0,'provider_writes':0,
        'qualification':'Scripted choices and forecasts test software only. Engine-derived reference labels and future input audits stay outside inference staging. Full independent live evaluator and bounded launcher are not implemented.'}
    write_new(args.output/'CPU-rehearsal.json',receipt)
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
