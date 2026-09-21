"""Fresh-state closed-loop episodes. No fallback, reset, resampling or retry."""
import time
from agent.action import ActionDecision
from agent.state import GameRuntimeState
from arcengine import GameState
from certification.phase4_v1.lifecycle import journal_record
from certification.phase4_transient_v1.contract import protocol,request_for,pack,digest
from certification.phase4_transient_v1.action_contract import validate_action
from certification.phase4_transient_v1.response_evidence import capture

def run_cases(service,store,adapter_factory,*,started,deadline,cancel,live,clock=time.monotonic):
    began=clock();cutoff=min(deadline,began+1200)
    state={'status':'running','error':None,'model_inference':live,'configuration':protocol()['configuration'],
        'canary_audit':service.canary_audit,'model_artifact':service.artifact,'model_startup_seconds':service.startup_seconds,
        'request_window_started_seconds':began-started,'request_window_cutoff_seconds':cutoff-started,
        'requests_started':0,'dispatch_attempts':0,'episodes':[]}
    def save():store.save('state.json',state)
    def check():
        if clock()>=cutoff or cancel.exists():raise TimeoutError('closed-loop admission/completion deadline')
    def retain(obs):
        data=pack(obs);name='obs-'+digest(data)+'.json'
        from certification.phase4_transient_v1.selection import select
        select((data,data))  # Validate even bootstrap/final records and every returned frame.
        if not (store.root/'worker'/name).exists():store.save(name,data)
        return name
    save();initial={}
    try:
        for row in protocol()['schedule']:
            check();adapter=adapter_factory(row);client=None
            ep={**row,'status':'running','error':None,'steps':[],'scorecard_id':None,
                'scorecard_receipt':None,'client_closed':False,'started_seconds':clock()-started}
            state['episodes'].append(ep);save()
            try:
                ep['scorecard_id']=adapter.open_scorecard(tags=['closed-loop-development-v1',row['arm']]);save()
                if not ep['scorecard_id']:raise ValueError('missing scorecard identity')
                check();client=adapter.bootstrap(row['game_id']);check()
                if client.observation.game_id!=row['game_id']:raise ValueError('wrong game')
                runtime=GameRuntimeState(client.observation,action_budget_limit=20)
                ep['initial_observation']=retain(client.observation);save()
                key=(row['game_id'],row['pair_index']);fingerprint=client.observation.canonical_hash
                if key in initial and initial[key]!=fingerprint:raise ValueError('paired initial state mismatch')
                initial[key]=fingerprint
                ep['terminal_reason']='action_cap'
                previous_transition=None
                for index in range(20):
                    check()
                    if runtime.observation.state in (GameState.WIN,GameState.GAME_OVER):break
                    if state['requests_started']>=120:raise ValueError('global request budget')
                    step={'episode_id':row['episode_id'],'step':index,'decision_id':row['episode_id']+f'-{index}',
                        'pre':retain(runtime.observation),'request':request_for(runtime,row['arm'],row['request_seed'],previous_transition),
                        'status':'request_started','started_seconds':clock()-started}
                    step['request_sha256']=digest(step['request'])
                    name=row['episode_id']+f'-step-{index:02d}.json'
                    ep['steps'].append(name);state['requests_started']+=1
                    store.save(name,step);save()
                    try:
                        result=service.complete(step['request'])
                    except Exception as exc:
                        if hasattr(exc,'response_evidence'):step.update(exc.response_evidence)
                        step.update(status='failed',error=type(exc).__name__+': '+str(exc)[:256])
                        store.save(name,step);raise
                    audit=dict(service.audit_records[-1]);step.update(capture(result.content,audit))
                    step['returned_seconds']=clock()-started;store.save(name,step)
                    check()
                    if (step['response_truncated'] or audit['request_sha256']!=step['request_sha256']
                        or type(result.prompt_tokens) is not int or not 0<result.prompt_tokens<=65408
                        or type(audit['tokenizer_prompt_tokens']) is not int
                        or type(audit['server_prompt_tokens']) is not int
                        or result.prompt_tokens!=audit['tokenizer_prompt_tokens'] or result.prompt_tokens!=audit['server_prompt_tokens']
                        or type(result.completion_tokens) is not int or not 1<=result.completion_tokens<=128
                        or type(audit['server_completion_tokens']) is not int
                        or result.completion_tokens!=audit['server_completion_tokens']):raise ValueError('token audit')
                    action=validate_action(result.content,runtime.observation.available_actions)['action']
                    decision=ActionDecision(**action,source='closed_loop_model',decision_id=step['decision_id'])
                    if state['dispatch_attempts']>=120:raise ValueError('dispatch budget')
                    step.update(action=action,status='dispatch_entered',dispatch_seconds=clock()-started)
                    state['dispatch_attempts']+=1;runtime.counters.conservative_spent_actions+=1
                    store.save(name,step);save();check()
                    post=adapter.dispatch(client,decision)
                    # Retain acknowledgement/observation before checking late returns.
                    step.update(post=retain(post),status='acknowledged',ack_seconds=clock()-started,
                        journal=journal_record(client.journal)[-1])
                    store.save(name,step);check()
                    from certification.phase4_transient_v1.selection import select
                    select((pack(runtime.observation),pack(post)))
                    previous_transition=(pack(runtime.observation),pack(post))
                    runtime.replace_observation(post,action_id=decision.action_id,action_data=decision.action_data,transition_id=decision.decision_id)
                if runtime.observation.state==GameState.WIN:ep['terminal_reason']='win'
                elif runtime.observation.state==GameState.GAME_OVER:ep['terminal_reason']='game_over'
                ep['final_observation']=retain(runtime.observation);ep['status']='complete'
            except Exception as exc:
                ep.update(status='failed',error=type(exc).__name__+': '+str(exc)[:512]);raise
            finally:
                errors=[]
                if client is not None:
                    try:adapter.finalize_client(client);ep['client_closed']=client.closed
                    except Exception as exc:errors.append('client finalization: '+str(exc)[:128])
                    ep['client_journal']=journal_record(client.journal)
                if ep['scorecard_id']:
                    try:
                        ep['scorecard_receipt']=adapter.close_scorecard()
                        if ep['scorecard_receipt'].get('card_id')!=ep['scorecard_id']:raise ValueError('scorecard receipt identity')
                    except Exception as exc:errors.append('scorecard finalization: '+str(exc)[:128])
                ep['lifecycle_journal']=journal_record(adapter.lifecycle_journal)
                ep['ended_seconds']=clock()-started
                if errors:ep.update(status='failed',error='; '.join(errors))
                save()
                if errors:raise RuntimeError(ep['error'])
            check()
        state['status']='complete'
    except Exception as exc:
        state.update(status='failed',error=type(exc).__name__+': '+str(exc)[:512]);raise
    finally:
        state['ended_seconds']=clock()-started;save()
    return state
