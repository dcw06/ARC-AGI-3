"""Replay order, requests, journals, frames and outcomes without worker verdicts."""
import hashlib,json,math
from pathlib import Path
from agent.state import GameRuntimeState
from agent.action import ActionDecision,serialize_action
from arcengine import GameState
from certification.phase4_integrated_v1.contract import pack,unpack,protocol,digest,baseline_request,make_request
from certification.phase4_integrated_v1.request_contract import parse,cells
from certification.phase4_integrated_v1.predicates import changes,verdict

def evaluate_trajectories(worker,folder,*,seconds=3300):
 folder=Path(folder);expected={'state.json'};calls=dispatches=prompts=0;summaries=[];cards=set()
 frozen=json.loads((Path(__file__).resolve().parents[2]/'reports/integrated_case_v1/initial_observation.json').read_bytes())
 def read(name):
  if Path(name).name!=name or not name.endswith('.json'):raise ValueError('unsafe evidence reference')
  p=folder/name
  if p.is_symlink() or p.stat().st_size>1048576:raise ValueError('record size/type')
  expected.add(name);return json.loads(p.read_bytes())
 def observation(name):
  v=read(name)
  if name!='obs-'+digest(v)+'.json':raise ValueError('observation content address')
  return unpack(v)
 def require(ok,msg):
  if not ok:raise ValueError(msg)
 def stamp(t):
  require(type(t) in (int,float) and math.isfinite(t) and 0<=t<seconds,'timestamp');return t
 def journal(e,kind):require(e['kind']==kind and e['status']=='acknowledged','journal status')
 require(len(worker['episodes'])==2,'incomplete pair')
 last=worker['request_window_started_seconds']
 for row,ep in zip(protocol()['schedule'],worker['episodes']):
  require(all(ep.get(k)==v for k,v in row.items()),'schedule binding')
  require(ep['status']=='complete' and ep['error'] is None and ep['client_closed'] is True,'episode finalization')
  require(ep['scorecard_id'] and ep['scorecard_id'] not in cards,'card isolation');cards.add(ep['scorecard_id'])
  require(ep['scorecard_receipt']['card_id']==ep['scorecard_id'],'card receipt')
  life=ep['lifecycle_journal'];require(len(life)==2,'local card lifecycle');journal(life[0],'scorecard_open');journal(life[1],'scorecard_close')
  require(life[0]['fields']['card_id']==ep['scorecard_id'] and life[1]['prepared_fields']['card_id']==ep['scorecard_id'],'card journal binding')
  require(last<=stamp(ep['started_seconds'])<=stamp(ep['ended_seconds'])<=worker['ended_seconds'],'episode timeline')
  last=ep['ended_seconds'];obs=observation(ep['initial_observation']);initial=obs.levels_completed
  require(obs.canonical_hash==frozen['canonical_hash'] and obs.full_reset is True,'frozen initial state')
  runtime=GameRuntimeState(obs,action_budget_limit=8);history=[];cursor=0;when=ep['started_seconds'];invalid=False;actions=[];feedback_scores=[];geometry=None
  entries=ep['client_journal'];require(len(entries)==len(ep['steps'])+1,'journal inventory');journal(entries[0],'bootstrap_reset')
  require(entries[0]['fields']['observation_hash']==obs.canonical_hash and entries[0]['fields']['guid']==obs.guid
   and entries[0]['prepared_fields']['requested_game_id']==row['game_id'] and entries[0]['prepared_fields']['scorecard_id']==ep['scorecard_id'],'bootstrap binding')
  def call(stage,current,context):
   nonlocal cursor,when,calls,prompts
   require(cursor<len(ep['calls']),'missing stage')
   name=ep['calls'][cursor];record=read(name);cid=ep['episode_id']+f'-call-{cursor:02d}';cursor+=1;calls+=1
   require(name==cid+'.json' and record['id']==cid and record['stage']==stage,'stage order/identity')
   require(pack(observation(record['pre']))==pack(current),'call observation')
   request=baseline_request(runtime) if stage=='control' else make_request(stage,pack(current),context)
   require(record['request']==request and record['request_sha256']==digest(request),'request reconstruction')
   raw=record['response_content'].encode();require(record['status']=='received' and record['response_truncated'] is False and len(raw)<=32768
      and len(raw)==record['response_bytes'] and hashlib.sha256(raw).hexdigest()==record['response_sha256'],'response retention')
   a=record['audit'];p=a['server_prompt_tokens'];c=a['server_completion_tokens']
   require(type(p) is int and 0<p<=60000 and type(a['tokenizer_prompt_tokens']) is int and a['tokenizer_prompt_tokens']==p
      and type(c) is int and 1<=c<=request['max_tokens'] and a['request_sha256']==digest(request),'token audit')
   require(0<=stamp(a['service_seconds'])<=120,'service deadline')
   require(when<=stamp(record['started_seconds'])<=stamp(record['returned_seconds'])<worker['request_window_cutoff_seconds'],'call deadline')
   when=record['returned_seconds'];prompts+=p
   try:value=parse(stage,record['response_content'],current.available_actions,current.latest_frame.tolist())
   except (ValueError,KeyError,TypeError):value=None
   require(record['model_valid']==(value is not None),'model validity claim')
   return cid,value,name
  if row['arm']=='structured':
   cid,value,_=call('inventory',obs,{})
   invalid=value is None
   if not invalid:
    history.append({'call_id':cid,'stage':'inventory','answer':value})
    from certification.phase4_integrated_v1.geometry import evaluate_inventory
    geometry=evaluate_inventory(value)
  require(len(ep['steps'])<=8 and len(set(ep['steps']))==len(ep['steps']),'action cap/duplicate')
  for i,name in enumerate(ep['steps']):
   require(not invalid and obs.state not in (GameState.WIN,GameState.GAME_OVER) and obs.levels_completed==initial,'action after stop')
   stage='control' if row['arm']=='control' else 'decision';cid,value,callname=call(stage,obs,{'history':history})
   require(value is not None,'dispatch from invalid decision')
   if stage=='decision':history.append({'call_id':cid,'stage':stage,'answer':value})
   s=read(name);a=value['action'];did=ep['episode_id']+f'-{i}'
   require(s['episode_id']==ep['episode_id'] and s['step']==i and s['decision_id']==did and s['decision_call']==callname
      and s['status']=='acknowledged' and s['action']==a and pack(observation(s['pre']))==pack(obs),'step/action binding')
   require(when<=stamp(s['dispatch_seconds'])<=stamp(s['ack_seconds'])<worker['request_window_cutoff_seconds'],'dispatch time');when=s['ack_seconds']
   e=entries[i+1];journal(e,'action');require(e==s['journal'],'journal copy')
   wire=serialize_action(ActionDecision(**a,source='integrated_model',decision_id=did),game_id=obs.game_id,guid=obs.guid,legal_actions=obs.available_actions)
   f=e['prepared_fields'];require(f['decision_id']==did and f['action_id']==a['action_id'] and f['pre_state_hash']==obs.canonical_hash and f['payload_sha256']==wire.payload_sha256,'wire binding')
   post=observation(s['post']);require(post.guid==obs.guid and post.game_id==obs.game_id and not post.full_reset
      and e['fields']['post_state_hash']==post.canonical_hash and obs.levels_completed<=post.levels_completed<=post.win_levels and post.win_levels==obs.win_levels,'post/progress binding')
   runtime.counters.conservative_spent_actions+=1;runtime.replace_observation(post,action_id=a['action_id'],action_data=a['action_data'],transition_id=did)
   dispatches+=1;actions.append(a)
   if stage=='decision':
    fid,feedback,fn=call('feedback',post,{'history':history,'pre_grid':obs.latest_frame.tolist(),'pre_levels':obs.levels_completed,'decision_call_id':cid,'decision':value})
    require(s['feedback_call']==fn,'feedback binding');invalid=feedback is None
    frames=[g.tolist() for g in post.frames];before=obs.latest_frame.tolist()
    truth=[{'frame_index':j,**changes(before,g)} for j,g in enumerate(frames)]
    primary=verdict(value['prediction'],before,frames,obs.levels_completed,post.levels_completed)
    alternative=verdict(value['alternative'],before,frames,obs.levels_completed,post.levels_completed)
    hit=None if a['action_id']!=6 else (a['action_data']['x'],a['action_data']['y']) in cells(value['target']['spans'])
    feedback_scores.append({'step':i,'declared_target_hit':hit,'changes':truth,'primary_truth':primary,'alternative_truth':alternative,
       'feedback_changes_exact':None if invalid else feedback['changes']==truth,'feedback_verdicts_exact':None if invalid else (feedback['primary']==primary and feedback['alternative']==alternative),
       'visible_object_grounding':'requires_current_frame_adjudication','behavioral_use':'requires_rubric_adjudication'})
    if not invalid:history.append({'call_id':fid,'stage':'feedback','answer':feedback})
   obs=post
  # A final invalid decision has a retained call but no dispatch.
  if cursor<len(ep['calls']):
   require(not invalid and len(ep['steps'])<8 and obs.levels_completed==initial and obs.state not in (GameState.WIN,GameState.GAME_OVER),'extra call')
   _,value,_=call('control' if row['arm']=='control' else 'decision',obs,{'history':history});require(value is None,'unexecuted valid decision');invalid=True
  require(cursor==len(ep['calls']) and len(set(ep['calls']))==cursor,'call inventory')
  reason='invalid_output' if invalid else 'win' if obs.state==GameState.WIN else 'game_over' if obs.state==GameState.GAME_OVER else 'progress' if obs.levels_completed>initial else 'action_cap'
  require(ep['terminal_reason']==reason and (reason!='action_cap' or len(actions)==8),'stop reason')
  require(pack(observation(ep['final_observation']))==pack(obs) and when<=ep['ended_seconds'],'final state')
  summaries.append({'arm':row['arm'],'actions':len(actions),'calls':cursor,'level_delta':obs.levels_completed-initial,'terminal_reason':reason,
     'adjacent_repeats':sum(a==b for a,b in zip(actions,actions[1:])),'feedback':feedback_scores,'initial_geometry':geometry,'intent_for_control':'unobserved'})
 require(calls==worker['requests_started'] and dispatches==worker['dispatch_attempts'] and prompts==worker['prompt_tokens'] and calls<=25 and dispatches<=16 and prompts<=1500000,'total budgets')
 if (folder/'model-ready.json').exists():expected.add('model-ready.json')
 require({p.name for p in folder.iterdir() if p.is_file()}==expected,'evidence inventory')
 return {'episodes':summaries,'calls':calls,'actions':dispatches,'prompt_tokens':prompts,'interpretation':'Single inspected scaffold case; no automatic policy promotion; human rubric adjudication remains separate.'}
