"""One sequential pass over paired perception and controls; zero environment actions."""
import hashlib,json,time
from types import SimpleNamespace
from certification.phase4_perception_v1.cases import load_cases,request_hash,image_part
# Classified probe outcomes are retained and the pass continues; anything else aborts.
CLASSIFIED=set() # Technical failures stop; invalid model answers remain outcomes.
CONFIGURATION='paired perception v1'

def run_cases(service,store,*,started,deadline,cancel,live,clock=time.monotonic):
    began=clock(); cutoff=min(deadline,began+600)
    state={'status':'running','error':None,'model_inference':live,'environment_actions':0,
        'scorecards':0,'configuration':CONFIGURATION,
        'canary_audit':service.canary_audit,'model_artifact':service.artifact,
        'model_startup_seconds':service.startup_seconds,'preflight':service.preflight,'cases':[],
        'requests_started':0,'request_window_started_seconds':began-started,
        'request_window_cutoff_seconds':cutoff-started}
    store.save('state.json',state)
    try:
        for index,case in enumerate(load_cases()):
            if clock()>=cutoff or cancel.exists():raise TimeoutError('preflight admission closed')
            row={'index':index,'probe_id':case['probe_id'],'request':case['request'],
                 'request_sha256':case['request_sha256'],'status':'started','error':None,
                 'failure_kind':None,'started_seconds':clock()-started}
            state['cases'].append(row);state['requests_started']+=1
            store.save('state.json',state)  # Durable intent before the call; never replay it.
            try:
                result=service.complete(case['request'])
            except Exception as exc:
                evidence=getattr(exc,'response_evidence',None)
                kind=(evidence or {}).get('audit',{}).get('failure_kind')
                row['returned_seconds']=clock()-started
                if evidence is not None:
                    from certification.phase4_perception_v1.response_evidence import checked
                    row.update(checked(evidence))
                if kind in CLASSIFIED:
                    row.update(status='classified_failure',failure_kind=kind,error=type(exc).__name__+': '+str(exc)[:256])
                    store.save('state.json',state);continue
                row['failure_kind']='response_validation' if evidence is not None else 'transport'
                store.save('state.json',state)
                raise
            row['returned_seconds']=clock()-started
            raw=result.content.encode()
            row.update(response_sha256=hashlib.sha256(raw).hexdigest(),response_bytes=len(raw),
                response_content=raw[:32768].decode('utf-8',errors='replace'),response_truncated=len(raw)>32768,
                audit=dict(service.audit_records[-1]))
            store.save('state.json',state)  # Preserve output before validation.
            if len(raw)>32768:raise ValueError('response evidence ceiling')
            if clock()>=cutoff or cancel.exists():raise TimeoutError('preflight completion expired')
            audit=row['audit']
            if (audit['request_sha256']!=request_hash(case['request'])
                or type(result.prompt_tokens) is not int or result.prompt_tokens<=0
                or result.prompt_tokens!=audit['tokenizer_prompt_tokens']
                or result.prompt_tokens!=audit['server_prompt_tokens']
                or type(result.completion_tokens) is not int or not 1<=result.completion_tokens<=case['request']['max_tokens']
                or result.completion_tokens!=audit['server_completion_tokens']
                or result.finish_reason!=audit.get('finish_reason')):
                raise ValueError('probe token audit mismatch')
            from certification.phase4_perception_v1.cases import score
            row['answer']=score(case,result.content,audit.get('finish_reason'))
            row['status']='complete'
            store.save('state.json',state)
        state['status']='complete'
    except Exception as exc:
        state['status']='failed';state['error']=type(exc).__name__+': '+str(exc)[:512]
        if state['cases'] and state['cases'][-1]['status'] not in ('complete','classified_failure'):
            state['cases'][-1].update(status='failed',error=state['error'])
        raise
    finally:
        state['ended_seconds']=clock()-started
        store.save('state.json',state)
    return state

class ScriptedService:
    startup_seconds=0
    artifact={}
    canary_audit={'status':'scripted_not_target'}
    def __init__(self,mode='verified'):
        self.mode=mode;self.calls=0;self.audit_records=[]
        self.preflight={'processor':{'available':True},'mount_inventory':{'processor_files':{}}}
    def complete(self,request):
        from research.perception_v1.fixtures import build,gold
        from research.perception_v1.controls import cases as controls
        from certification.phase4_perception_v1.response_evidence import capture,ResponseValidationError
        row=load_cases()[self.calls];self.calls+=1
        if row['request']!=request:raise ValueError('ordered request allowlist')
        if self.mode=='transport' and self.calls==3:raise ConnectionError('fixture')
        if row['kind']=='perception':
            value=gold(next(c for c in build() if c['id']==row['case_id']))
            if self.mode=='incorrect':value={'objects':[],'non_object_regions':[],'relations':[]}
        elif row['kind']=='control':value=next(c for c in controls() if c['id']==row['case_id'])['expected']
        else:value=row['expected']
        content=json.dumps(value);finish='stop'
        if self.calls==3:
            if self.mode=='invalid':content='{';finish='length'
            if self.mode=='evidence':content='x'*32769
        e=row['frozen_local_expectation'];p=e['expected_prompt_tokens']
        if self.mode=='mismatch' and self.calls==3:p+=1
        audit={'request_sha256':row['request_sha256'],'tokenizer_prompt_tokens':e['expected_prompt_tokens'],
            'server_prompt_tokens':p,'server_completion_tokens':32,'finish_reason':finish,'service_seconds':0,
            'expectation':e,'transport_attempted':True}
        if p!=e['expected_prompt_tokens']:raise ResponseValidationError('fixture mismatch',capture(content,audit))
        self.audit_records.append(audit)
        return SimpleNamespace(content=content,prompt_tokens=p,completion_tokens=32,finish_reason=finish)
