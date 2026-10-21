"""One bounded, private ls20 VLM episode; no route is available to the policy."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from certification.direct_publisher_smoke_v1.accounting import Clock,Ledger
from certification.direct_publisher_smoke_v1.client import Client
from research.initial_geometry_assistance_v1.live_io import Journal,sha,write_new
from research.initial_geometry_assistance_v1.live_resources import environment
from research.initial_geometry_assistance_v1.model_io import TokenAudit,validate_reply
from research.verified_feedback_live_v1.engine import FeedbackEngine
from .flow import run_episode
from .live_contract import MODEL,MAX_PROMPT_TOKENS,ACTION_CAP,verify_inputs

WORKER_SECONDS=3300
ADMISSION_SECONDS=3000

def canary():
    return dict(model=MODEL,messages=[dict(role='user',content='Reply with the single word: ok')],
                max_tokens=16,temperature=0,seed=0,chat_template_kwargs={'enable_thinking':False})

def request_plan():
    return [dict(id=identity,kind='canary' if identity=='canary' else 'policy',method='POST',
                 path='/v1/chat/completions',timeout_seconds=30,max_issues=1)
            for identity in ['canary']+['ls20/instructed/'+str(step) for step in range(ACTION_CAP)]]

class DurableLedger(Ledger):
    def __init__(self,clock,sink):super().__init__(request_plan(),41,clock);self.sink=sink
    def admit(self,identity):
        item,entry=super().admit(identity)
        self.sink({**entry,'request_kind':entry['kind'],'kind':'HTTP_admission'})
        if not self.clock.admission_open():raise TimeoutError('HTTP admission expired while journaling')
        return item,entry

def study(config,output,*,token_audit,engine_factory=None):
    output,inputs=Path(output),Path(config['inputs'])
    verify_inputs(inputs,config['input_manifest_sha256'])
    initial=json.loads((inputs/'initial.json').read_bytes())
    instructions=(inputs/'instructions.txt').read_text(encoding='utf-8')
    clock=Clock(dict(internal_seconds=WORKER_SECONDS,admission_cutoff_seconds=ADMISSION_SECONDS),config['started'])
    journal=Journal(output/'transport.jsonl');ledger=DurableLedger(clock,journal)
    client=Client('127.0.0.1',config['port'],ledger,clock,MODEL)
    resets=dispatches=closes=0;episodes=[];error=None
    def complete(identity,body):
        count=token_audit(body)
        if type(count) is not int or not 0<count<=MAX_PROMPT_TOKENS:raise ValueError('native prompt cap before HTTP exceeded')
        journal(dict(kind='HTTP_request',id=identity,body=body,native_prompt_tokens=count))
        status,raw=client.call(identity,body)
        journal(dict(kind='HTTP_response',id=identity,status=status,raw=raw.decode('utf-8')))
        if status!=200:raise ValueError('model HTTP status differs')
        return validate_reply(body,json.loads(raw),count)
    def effect(operation):
        nonlocal resets,dispatches,closes
        if operation=='bootstrap':
            if resets>=1:raise ValueError('reset cap')
            resets+=1
        elif operation=='dispatch':
            if dispatches>=ACTION_CAP:raise ValueError('action cap')
            dispatches+=1
        elif operation=='close':
            if closes>=1:raise ValueError('scorecard close cap')
            closes+=1
        else:raise ValueError('engine operation differs')
        journal(dict(kind='engine_admission',episode='ls20-instructed',operation=operation,
                     bootstrap_attempts=resets,dispatch_attempts=dispatches,close_attempts=closes))
    try:
        if complete('canary',canary()).strip()!='ok':raise ValueError('canary differs')
        deadline=config['started']+ADMISSION_SECONDS
        if deadline-time.monotonic()<120:raise TimeoutError('episode headroom below 120 seconds')
        events=Journal(output/'ls20-instructed.jsonl');step=0
        def response(body):
            nonlocal step
            value=complete('ls20/instructed/'+str(step),body);step+=1;return value
        try:
            engine=(engine_factory(effect) if engine_factory else FeedbackEngine(config['game_python'],
                'ls20-9607627b',config['games'],output/'recordings',output/'engine.log',deadline,
                cleanup_deadline=config['started']+WORKER_SECONDS,
                env=dict(environment(),PYTHONPATH=str(Path(__file__).resolve().parents[2])),on_effect=effect))
            episodes.append(run_episode(initial,instructions,engine,response,events,deadline=deadline))
        finally:events.close()
        clock.check('worker final evidence')
    except BaseException as exc:error=type(exc).__name__+': '+str(exc);raise
    finally:
        try:write_new(output/'worker-result.json',dict(schema='ls20_instruction_worker_v1',error=error,
            episodes=episodes,ledger=ledger.summary(),bootstrap_attempts=resets,dispatch_attempts=dispatches,
            close_attempts=closes,lifecycle_certified=False))
        finally:journal.close()
    return episodes

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();config=json.loads(args.config.read_bytes())
    if sha(args.config)!=os.environ.pop('LS20_INSTRUCTION_V1_CONFIG_SHA256'):raise ValueError('worker config pin differs')
    if not sys.version.startswith('3.12.'):raise ValueError('Python version differs')
    if any(importlib.metadata.version(k)!=v for k,v in config['model_host_packages'].items()):raise ValueError('model packages differ')
    verify_inputs(config['inputs'],config['input_manifest_sha256'])
    with (args.output/'vllm.log').open('ab') as log:
        process=subprocess.Popen(config['server_argv'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=environment())
        deadline=min(config['started']+ADMISSION_SECONDS,time.monotonic()+900)
        while True:
            if process.poll() is not None:raise RuntimeError('vLLM startup failed')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('model startup deadline')
            try:
                with socket.create_connection(('127.0.0.1',config['port']),timeout=min(1,remaining)):break
            except OSError:time.sleep(min(0.5,max(0,deadline-time.monotonic())))
        study(config,args.output,token_audit=TokenAudit(config['model_path']))

if __name__=='__main__':main()
