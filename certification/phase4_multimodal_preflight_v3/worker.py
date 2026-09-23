"""One sequential pass over the four preflight probes; never instantiate a game/scorecard."""
import hashlib,json,time
from types import SimpleNamespace
from certification.phase4_multimodal_preflight_v3.cases import load_cases,request_hash,image_part
# Classified probe outcomes are retained and the pass continues; anything else aborts.
CLASSIFIED={'dependency_missing','image_rejected_by_server','server_rejected','token_accounting_mismatch','processor_execution_failure'}
CONFIGURATION='multimodal image-input preflight v3'

def run_cases(service,store,*,started,deadline,cancel,live,clock=time.monotonic):
    began=clock(); cutoff=min(deadline,began+300)
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
                    from certification.phase4_multimodal_preflight_v3.response_evidence import checked
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
                response_content=raw[:8192].decode('utf-8',errors='replace'),response_truncated=len(raw)>8192,
                audit=dict(service.audit_records[-1]))
            store.save('state.json',state)  # Preserve output before validation.
            if len(raw)>8192:raise ValueError('response evidence ceiling')
            if clock()>=cutoff or cancel.exists():raise TimeoutError('preflight completion expired')
            audit=row['audit']
            if (audit['request_sha256']!=request_hash(case['request'])
                or type(result.prompt_tokens) is not int or result.prompt_tokens<=0
                or result.prompt_tokens!=audit['tokenizer_prompt_tokens']
                or result.prompt_tokens!=audit['server_prompt_tokens']
                or type(result.completion_tokens) is not int or not 1<=result.completion_tokens<=64
                or result.completion_tokens!=audit['server_completion_tokens']
                or result.finish_reason!=audit.get('finish_reason')):
                raise ValueError('probe token audit mismatch')
            from certification.phase4_multimodal_preflight_v3.probes import score
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
    """Local fixture covering each outcome class; counts follow the frozen provisional arithmetic."""
    startup_seconds=0
    artifact={}
    canary_audit={'status':'scripted_not_target'}
    def __init__(self,mode='verified'):
        self.audit_records=[];self.mode=mode;self.calls=0
        processor_ok=mode!='dependency'
        self.preflight={'mount_inventory':{'file_count':3,'files':[],'processor_files':{
            'preprocessor_config.json':{'present':processor_ok,'sha256':None,'matches_pinned':processor_ok},
            'video_preprocessor_config.json':{'present':True,'sha256':None,'matches_pinned':True}}},
            'processor':{'available':processor_ok,'error':None if processor_ok else 'missing mounted file: preprocessor_config.json','versions':{}}}
    def complete(self,request):
        from certification.phase4_multimodal_preflight_v3.response_evidence import capture,ResponseValidationError
        case=next(c for c in load_cases() if c['request']==request)
        probe=case['probe_id'];self.calls+=1;image=image_part(request) is not None;digest=request_hash(request)
        if self.mode=='transport':raise ConnectionError('scripted transport failure')
        if image and self.mode=='dependency':
            raise ResponseValidationError('scripted',capture('',{'failure_kind':'dependency_missing','request_sha256':digest,'failure_stage':'processor_availability','exception_type':'ProcessorUnavailable','transport_attempted':False}))
        if image and self.mode=='rejected':
            raise ResponseValidationError('scripted',capture('{"error":"image input not supported"}',
                {'failure_kind':'image_rejected_by_server','request_sha256':digest,'http_status':400,'failure_stage':'transport','exception_type':'ServerRejectedError','transport_attempted':True}))
        if image and self.mode=='processor':
            raise ResponseValidationError('scripted processor failure',capture('',{'failure_kind':'processor_execution_failure',
                'request_sha256':digest,'failure_stage':'processor_execution','exception_type':'ValueError','transport_attempted':False}))
        # Frozen local template counts (image templates already include the 3 vision markers).
        template=case['frozen_local_expectation']['template_tokens'];expectation={'template_tokens':template}
        if image:
            arithmetic=dict(case['image']['provisional_arithmetic'])
            if self.mode=='arithmetic' and probe in ('I2','I3'):  # target processor differs from the document
                arithmetic.update(grid_thw=[1,62,62],processed_height=992,processed_width=992,image_tokens=961)
            expectation.update(input_width=case['image']['input_width'],input_height=case['image']['input_height'],
                image_grid_thw=arithmetic['grid_thw'],processed_height=arithmetic['processed_height'],
                processed_width=arithmetic['processed_width'],image_tokens_processor=arithmetic['image_tokens'],
                manual_prompt_tokens=template-1+arithmetic['image_tokens'],processor_full_prompt_tokens=template-1+arithmetic['image_tokens'])
            expected=template-1+arithmetic['image_tokens']
        else:expected=template
        expectation['expected_prompt_tokens']=expected
        server=expected
        if self.mode=='mismatch' and probe=='I2':server=expected+1
        if self.mode=='not_consumed' and image:server=template-1  # server dropped the image
        value=dict(case['expected'])
        if self.mode=='incorrect':value['color']=((value['color'] or 0)+1)%16
        if self.mode=='identical' and probe in ('I2','I3'):value={'quadrant':'top_left','color':8}
        content='{' if self.mode=='invalid' and probe=='I2' else json.dumps(value)
        audit={'transport_attempted':True,'request_sha256':digest,'tokenizer_prompt_tokens':expected,'server_prompt_tokens':server,
            'server_completion_tokens':9,'finish_reason':'stop','service_seconds':0,'expectation':expectation,
            'frozen_local_expected_prompt_tokens':case.get('frozen_local_expectation',{}).get('expected_prompt_tokens')}
        if server!=expected:
            raise ResponseValidationError('scripted mismatch',capture(content,{**audit,'failure_kind':'token_accounting_mismatch','failure_stage':'server_count_validation','exception_type':'ValueError'}))
        self.audit_records.append(audit)
        return SimpleNamespace(content=content,prompt_tokens=server,completion_tokens=9,finish_reason='stop')
