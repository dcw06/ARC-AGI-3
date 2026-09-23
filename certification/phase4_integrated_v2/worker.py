"""Two isolated episodes; explicit inventory -> decision -> dispatch -> feedback."""
import json,time
from pathlib import Path
from agent.action import ActionDecision
from agent.state import GameRuntimeState
from arcengine import GameState
from certification.phase4_v1.lifecycle import journal_record
from certification.phase4_integrated_v2.contract import protocol,pack,digest,baseline_request,make_request
from certification.phase4_integrated_v2.request_contract import parse
from certification.phase4_integrated_v2.response_evidence import capture

def run_cases(service,store,adapter_factory,*,started,deadline,cancel,live,clock=time.monotonic):
    began=clock();cutoff=min(deadline,began+1200)
    spec=protocol();expected=json.loads((Path(__file__).resolve().parents[2]/'reports/integrated_case_v1/initial_observation.json').read_bytes())
    state={'status':'running','error':None,'model_inference':live,'configuration':spec['configuration'],
           'canary_audit':service.canary_audit,'model_artifact':service.artifact,'model_startup_seconds':service.startup_seconds,
           'request_window_started_seconds':began-started,'request_window_cutoff_seconds':cutoff-started,
           'requests_started':0,'dispatch_attempts':0,'prompt_tokens':0,'episodes':[]}
    def save():store.save('state.json',state)
    def check():
        if clock()>=cutoff or cancel.exists():raise TimeoutError('integrated absolute admission/completion deadline')
    def retain(obs):
        value=pack(obs);name='obs-'+digest(value)+'.json'
        if not (store.root/'worker'/name).exists():store.save(name,value)
        return name
    def call(ep,stage,obs,context,runtime):
        check()
        if state['requests_started']>=25:raise ValueError('global inference ceiling')
        request=baseline_request(runtime) if stage=='control' else make_request(stage,pack(obs),context)
        cid=ep['episode_id']+f'-call-{len(ep["calls"]):02d}'
        name=cid+'.json';row={'id':cid,'stage':stage,'pre':retain(obs),'request':request,'request_sha256':digest(request),
                              'started_seconds':clock()-started,'status':'request_started'}
        ep['calls'].append(name);state['requests_started']+=1;store.save(name,row);save()
        try:
            result=service.complete(request);audit=dict(service.audit_records[-1])
            row.update(capture(result.content,audit),returned_seconds=clock()-started,status='received')
            store.save(name,row) # Received evidence survives late returns and token validation.
            check()
            p,c=audit.get('server_prompt_tokens'),audit.get('server_completion_tokens')
            if (row['response_truncated'] or type(p) is not int or not 0<p<=60000
                or type(c) is not int or not 1<=c<=request['max_tokens']
                or type(audit.get('tokenizer_prompt_tokens')) is not int or audit['tokenizer_prompt_tokens']!=p
                or result.prompt_tokens!=p or result.completion_tokens!=c or audit['request_sha256']!=row['request_sha256']):raise ValueError('token/response audit')
            state['prompt_tokens']+=p
            if state['prompt_tokens']>1500000:raise ValueError('total prompt ceiling')
            try:
                if audit.get('finish_reason')!='stop':raise ValueError('completion did not finish with stop')
                value=parse(stage,result.content,obs.available_actions,obs.latest_frame.tolist());row['model_valid']=True
            except (ValueError,KeyError,TypeError) as exc:
                value=None;row.update(model_valid=False,model_error=str(exc)[:256])
            store.save(name,row);save();return cid,value,name
        except Exception as exc:
            if hasattr(exc,'response_evidence'):row.update(exc.response_evidence)
            row.update(status='technical_failure',error=type(exc).__name__+': '+str(exc)[:256]);store.save(name,row);raise
    save()
    try:
        for schedule in spec['schedule']:
            check();adapter=adapter_factory(schedule);client=None
            ep={**schedule,'status':'running','error':None,'calls':[],'steps':[],'client_closed':False,
                'scorecard_id':None,'scorecard_receipt':None,'started_seconds':clock()-started}
            state['episodes'].append(ep);save()
            try:
                ep['scorecard_id']=adapter.open_scorecard(tags=['integrated-development-v1',schedule['arm']]);save()
                if not ep['scorecard_id']:raise ValueError('local card identity')
                check();client=adapter.bootstrap(schedule['game_id']);obs=client.observation;check()
                ep['initial_observation']=retain(obs);save()
                if obs.canonical_hash!=expected['canonical_hash'] or obs.full_reset is not True:raise ValueError('frozen initial state mismatch')
                runtime=GameRuntimeState(obs,action_budget_limit=8);base=obs.levels_completed;history=[];inventory=None
                ep['terminal_reason']='action_cap'
                if schedule['arm']=='structured':
                    cid,inventory,_=call(ep,'inventory',obs,{},runtime)
                    if inventory is None:ep['terminal_reason']='invalid_output'
                    else:history.append({'call_id':cid,'stage':'inventory','answer':inventory})
                for index in range(8):
                    check()
                    if ep['terminal_reason']=='invalid_output':break
                    if obs.state in (GameState.WIN,GameState.GAME_OVER) or obs.levels_completed>base:break
                    stage='control' if schedule['arm']=='control' else 'decision'
                    cid,decision,call_name=call(ep,stage,obs,{'history':history},runtime)
                    if decision is None:ep['terminal_reason']='invalid_output';break
                    if stage=='decision':history.append({'call_id':cid,'stage':'decision','answer':decision})
                    action=decision['action'];did=ep['episode_id']+f'-{index}'
                    step={'episode_id':ep['episode_id'],'step':index,'decision_id':did,'decision_call':call_name,
                          'pre':retain(obs),'action':action,'status':'dispatch_entered','dispatch_seconds':clock()-started}
                    name=did+'-step.json';ep['steps'].append(name);state['dispatch_attempts']+=1
                    if state['dispatch_attempts']>16:raise ValueError('dispatch ceiling')
                    store.save(name,step);save();check()
                    act=ActionDecision(**action,source='integrated_model',decision_id=did)
                    runtime.counters.conservative_spent_actions+=1
                    post=adapter.dispatch(client,act)
                    step.update(post=retain(post),status='acknowledged',ack_seconds=clock()-started,journal=journal_record(client.journal)[-1])
                    store.save(name,step);check()
                    runtime.replace_observation(post,action_id=act.action_id,action_data=act.action_data,transition_id=did)
                    if stage=='decision':
                        fid,feedback,feedback_name=call(ep,'feedback',post,{'history':history,'pre_grid':obs.latest_frame.tolist(),
                            'pre_levels':obs.levels_completed,'decision_call_id':cid,'decision':decision},runtime)
                        step['feedback_call']=feedback_name;store.save(name,step)
                        if feedback is None:ep['terminal_reason']='invalid_output'
                        else:history.append({'call_id':fid,'stage':'feedback','answer':feedback})
                    obs=post
                    if ep['terminal_reason']=='invalid_output':break
                if ep['terminal_reason']!='invalid_output':
                    ep['terminal_reason']='win' if obs.state==GameState.WIN else 'game_over' if obs.state==GameState.GAME_OVER else 'progress' if obs.levels_completed>base else 'action_cap'
                ep['final_observation']=retain(obs);ep['status']='complete'
            except Exception as exc:
                ep.update(status='failed',error=type(exc).__name__+': '+str(exc)[:512]);raise
            finally:
                errors=[]
                if client is not None:
                    try:adapter.finalize_client(client);ep['client_closed']=client.closed
                    except Exception as exc:errors.append(str(exc)[:128])
                    ep['client_journal']=journal_record(client.journal)
                if ep['scorecard_id']:
                    try:ep['scorecard_receipt']=adapter.close_scorecard()
                    except Exception as exc:errors.append(str(exc)[:128])
                ep['lifecycle_journal']=journal_record(adapter.lifecycle_journal);ep['ended_seconds']=clock()-started
                if errors:ep.update(status='failed',error='; '.join(errors))
                save()
                if errors:raise RuntimeError('episode finalization failure')
        state['status']='complete'
    except Exception as exc:
        state.update(status='failed',error=type(exc).__name__+': '+str(exc)[:512]);raise
    finally:state['ended_seconds']=clock()-started;save()
    return state
