"""One sequential pass over 56 coordinate prompts; never instantiate a game/scorecard."""
import hashlib,json,time
from types import SimpleNamespace
from certification.phase4_coordinates_v2.cases import load_cases,request_hash
from certification.phase4_coordinates_v2.action_contract import validate_action,request_legal_actions

def run_cases(service,store,*,started,deadline,cancel,live,clock=time.monotonic):
    began=clock(); cutoff=min(deadline,began+480)
    state={'status':'running','error':None,'model_inference':live,'environment_actions':0,
        'scorecards':0,'configuration':'fixed-model paired coordinate diagnostic v1',
        'canary_audit':service.canary_audit,'model_artifact':service.artifact,
        'model_startup_seconds':service.startup_seconds,'cases':[],
        'requests_started':0,'request_window_started_seconds':began-started,
        'request_window_cutoff_seconds':cutoff-started}
    store.save('state.json',state)
    try:
        for index,case in enumerate(load_cases()):
            if clock()>=cutoff or cancel.exists():raise TimeoutError('diagnostic admission closed')
            row={'index':index,'case_id':case['case_id'],'game_id':case['game_id'],'source_group':case['source_group'],'request':case['request'],
                 'request_sha256':case['request_sha256'],'status':'started','error':None,
                 'started_seconds':clock()-started}
            state['cases'].append(row);state['requests_started']+=1
            store.save('state.json',state)  # Durable intent before the call; never replay it.
            try:
                result=service.complete(case['request'])
            except Exception as exc:
                row['failure_kind']='response_validation' if hasattr(exc,'response_evidence') else 'transport'
                if hasattr(exc,'response_evidence'):
                    from certification.phase4_coordinates_v2.response_evidence import checked
                    evidence=checked(exc.response_evidence)
                    row.update(evidence)
                    row['received_evidence_request_matches']=evidence.get('audit',{}).get('request_sha256')==case['request_sha256']
                    row['returned_seconds']=clock()-started
                    store.save('state.json',state)
                raise
            row['returned_seconds']=clock()-started
            raw=result.content.encode()
            row.update(response_sha256=hashlib.sha256(raw).hexdigest(),response_bytes=len(raw),
                response_content=raw[:8192].decode('utf-8',errors='replace'),response_truncated=len(raw)>8192,
                audit=dict(service.audit_records[-1]))
            store.save('state.json',state)  # Preserve invalid output before validation.
            if len(raw)>8192:raise ValueError('response evidence ceiling')
            if clock()>=cutoff or cancel.exists():raise TimeoutError('diagnostic completion expired')
            audit=row['audit']
            if (audit['request_sha256']!=request_hash(case['request'])
                or type(result.prompt_tokens) is not int or result.prompt_tokens<=0
                or result.prompt_tokens!=audit['tokenizer_prompt_tokens']
                or result.prompt_tokens!=audit['server_prompt_tokens']
                or type(result.completion_tokens) is not int or not 1<=result.completion_tokens<=128
                or result.completion_tokens!=audit['server_completion_tokens']):
                raise ValueError('diagnostic token audit mismatch')
            from certification.phase4_coordinates_v2.answers import score
            row['diagnostic']=score(case,result.content)
            row['status']='complete'
            store.save('state.json',state)
        state['status']='complete'
    except Exception as exc:
        state['status']='failed';state['error']=type(exc).__name__+': '+str(exc)[:512]
        if state['cases'] and state['cases'][-1]['status']!='complete':
            state['cases'][-1].update(status='failed',error=state['error'])
        raise
    finally:
        state['ended_seconds']=clock()-started
        store.save('state.json',state)
    return state

class ScriptedService:
    """Local fixture: correct, incorrect, malformed or transport-failing outputs."""
    startup_seconds=0
    artifact={}
    canary_audit={'status':'scripted_not_target'}
    def __init__(self,mode='correct'):self.audit_records=[];self.mode=mode;self.calls=0
    def complete(self,request):
        from certification.phase4_coordinates_v2.score import truth
        from certification.phase4_coordinates_v2.response_evidence import capture,ResponseValidationError
        case=next(c for c in load_cases() if c['request']==request)
        self.calls+=1
        if self.mode=='transport':raise ConnectionError('scripted transport failure')
        value={'color':truth(case)[0]}
        if self.mode=='transposed':value['color']=truth(case)[1]
        if self.mode=='other':value['color']=next(v for v in range(16) if v not in truth(case))
        if self.mode=='incorrect':
            if 'color' in value:value['color']=(value['color']+1)%16
            else:value['count']=(value['count']+1)%4097
        content='{' if self.mode=='malformed' else json.dumps(value)
        audit={'request_sha256':request_hash(request),'tokenizer_prompt_tokens':10,
            'server_prompt_tokens':10,'server_completion_tokens':29,'service_seconds':0}
        if self.mode=='mismatch':
            audit['server_prompt_tokens']=11
            raise ResponseValidationError('scripted mismatch',capture(content,audit))
        self.audit_records.append(audit)
        return SimpleNamespace(content=content,prompt_tokens=10,completion_tokens=29)
