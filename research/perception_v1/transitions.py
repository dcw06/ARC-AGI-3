"""Local record contract only: no environment, dispatch, memory or model calls.

All timestamps are elapsed seconds on one shared monotonic episode clock.
Callers must not reset the origin between steps or mix wall/process clocks.
Chronology checks do not prove durable pre-dispatch retention; that remains
the future runner's responsibility.
"""
import json,math,re
from .fixtures import digest
from certification.phase4_multimodal_preflight_v3.images import check_grid
from certification.phase4_multimodal_preflight_v3.action_contract import validate_action

def observation(value):
    if type(value) is not dict or set(value)!={'frames','levels_completed','state'}:raise ValueError('observation fields')
    if type(value['frames']) is not list or not 1<=len(value['frames'])<=8:raise ValueError('complete bounded frames required')
    for grid in value['frames']:check_grid(grid)
    if type(value['levels_completed']) is not int or value['levels_completed']<0 or type(value['state']) is not str or not 0<len(value['state'])<=64:raise ValueError('progress/state')
def moment(v):
    if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('timestamp')
def changes(before,after):
    if len(before)!=len(after) or len(before[0])!=len(after[0]):return {'shape_changed':True,'changed_cells':None,'bbox':None}
    cells=[(x,y) for y,row in enumerate(after) for x,color in enumerate(row) if before[y][x]!=color]
    return {'shape_changed':False,'changed_cells':len(cells),
        'bbox':[min(x for x,y in cells),min(y for x,y in cells),max(x for x,y in cells),max(y for x,y in cells)] if cells else None}
def commit(*,episode_id,game_id,seed,step,request_sha256,response_sha256,before,action,legal_actions,intended_target,prediction,alternative,at):
    observation(before);moment(at)
    for s in (episode_id,game_id):
        if type(s) is not str or not 0<len(s)<=128:raise ValueError('identity')
    for h in (request_sha256,response_sha256):
        if type(h) is not str or not re.fullmatch('[0-9a-f]{64}',h):raise ValueError('request/response hash')
    if type(seed) is not int or type(step) is not int or step<0:raise ValueError('seed/step')
    validate_action(json.dumps({'action':action}),legal_actions)
    for s in (intended_target,prediction,alternative):
        if type(s) is not str or not 1<=len(s)<=256:raise ValueError('bounded prediction/intent')
    if prediction==alternative:raise ValueError('predictions must distinguish outcomes')
    value={'version':'transition_record_v1','episode_id':episode_id,'game_id':game_id,'seed':seed,'step':step,
        'request_sha256':request_sha256,'response_sha256':response_sha256,'before':before,'before_sha256':digest(before),
        'action':action,'legal_actions':list(legal_actions),'intended_target':intended_target,'prediction':prediction,
        'alternative':alternative,'committed_at':at}
    # Immutable-by-copy intent; caller must retain this before any future dispatch.
    return json.loads(json.dumps(value))
def finalize(intent,*,intent_sha256,dispatch,after,update):
    if digest(intent)!=intent_sha256:raise ValueError('prediction/intent commitment drift')
    if intent.get('version')!='transition_record_v1':raise ValueError('version')
    # Revalidate all fields rather than trust an arbitrary purported commitment.
    args={k:v for k,v in intent.items() if k not in ('version','before_sha256','committed_at')}
    if commit(**args,at=intent['committed_at'])!=intent:raise ValueError('intent binding')
    observation(after)
    if set(dispatch)!={'action','acknowledged','started_at','returned_at'} or dispatch['acknowledged'] is not True or dispatch['action']!=intent['action']:raise ValueError('dispatch binding')
    moment(dispatch['started_at']);moment(dispatch['returned_at'])
    if not intent['committed_at']<=dispatch['started_at']<=dispatch['returned_at']:raise ValueError('dispatch time order')
    if type(update) is not dict or set(update)!={'assessment','evidence_frames','revised_hypothesis'}:raise ValueError('update fields')
    if update['assessment'] not in ('supported','contradicted','unresolved'):raise ValueError('assessment')
    frames=update['evidence_frames']
    if type(frames) is not list or len(set(frames))!=len(frames) or any(type(i) is not int or not 0<=i<len(after['frames']) for i in frames):raise ValueError('evidence frame binding')
    if type(update['revised_hypothesis']) is not str or not 1<=len(update['revised_hypothesis'])<=256:raise ValueError('hypothesis')
    initial=intent['before']['frames'][-1];previous=initial;deltas=[]
    for index,frame in enumerate(after['frames']):
        deltas.append({'index':index,'frame_sha256':digest(frame),'from_before':changes(initial,frame),'from_previous':changes(previous,frame)})
        previous=frame
    return {'intent':intent,'intent_sha256':intent_sha256,'dispatch':dispatch,'after':after,'after_sha256':digest(after),
        'frame_changes':deltas,'level_delta':after['levels_completed']-intent['before']['levels_completed'],
        'model_update':update,'interpretation':'Update is an unverified model claim; progress is an observed counter delta.'}
def verify(record,previous=None):
    expected=finalize(record['intent'],intent_sha256=record['intent_sha256'],dispatch=record['dispatch'],after=record['after'],update=record['model_update'])
    if expected!=record:raise ValueError('record replay mismatch')
    if previous is not None:
        verify(previous)  # Validate the predecessor before trusting its return time.
        a,b=previous['intent'],record['intent']
        if any(a[k]!=b[k] for k in ('episode_id','game_id','seed')) or b['step']!=a['step']+1 or b['before_sha256']!=previous['after_sha256']:
            raise ValueError('episode continuity/fresh observation')
        if previous['dispatch']['returned_at']>b['committed_at']:
            raise ValueError('episode chronology: prediction committed before previous return')
    return True
