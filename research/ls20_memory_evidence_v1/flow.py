"""One level-1 episode; engine transitions alone determine completion."""
from copy import deepcopy
import time
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation
from research.verified_feedback_v1.flow import AdmissionClosed
from .live_contract import ACTION_CAP
from .policy import make_request,parse

def run_episode(initial,instructions,engine,complete,sink,*,deadline,now=time.monotonic):
    current=None;history=[];calls=0;reason=error=failure=None;checks=0
    def emit(kind,**values):sink(deepcopy(dict(kind=kind,**values)))
    def check():
        nonlocal checks
        checks+=1;elapsed=now()-deadline
        if elapsed>=0:
            emit('admission_stop',check_index=checks,overrun_seconds=elapsed)
            raise AdmissionClosed('ls20 new-work admission closed')
    try:
        check();emit('bootstrap_intent',seed=0);check()
        current=check_observation(engine.bootstrap())
        if current!=initial:raise ValueError('game does not reproduce the frozen level-1 start')
        emit('initial',observation=current)
        while True:
            if current['levels_completed']>0 or current['state']=='WIN':reason='first_level_complete';break
            if current['state']=='GAME_OVER':reason='game_over';break
            if len(history)>=ACTION_CAP:reason='action_cap';break
            check();step=len(history)
            body=make_request(initial,current,history,instructions)
            emit('request',step=step,body=body,request_sha256=digest(body));check()
            text=complete(deepcopy(body));calls+=1
            emit('response',step=step,text=text);check()
            try:answer=parse(text,current['legal_actions'])
            except (ValueError,TypeError,RecursionError) as exc:
                reason,error='invalid_answer',str(exc);break
            action={key:answer[key] for key in ('action_id','action_data')}
            emit('dispatch_intent',step=step,action=action,before_sha256=digest(current));check()
            after=check_observation(engine.dispatch(deepcopy(action)))
            record=dict(step=step,before=deepcopy(current),after=deepcopy(after),action=action,
                        predicted_visible_change=answer['predicted_visible_change'])
            emit('transition',record=record,transition_sha256=digest(record))
            history.append(record);current=after
    except AdmissionClosed:reason='deadline'
    except BaseException as exc:
        reason,error,failure='exception',type(exc).__name__+': '+str(exc),exc
    try:emit('closed',receipt=engine.close())
    except BaseException as exc:
        reason,error,failure='exception',type(exc).__name__+': '+str(exc),exc
    result=dict(reason=reason,error=error,model_calls=calls,new_dispatches=len(history),
        final_observation=current,level1_passed=bool(current and current['levels_completed']>=1),lifecycle_certified=False)
    emit('summary',**result)
    if failure is not None:raise failure
    return result
