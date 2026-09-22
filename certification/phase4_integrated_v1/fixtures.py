"""Scripted responses and synthetic transitions from retained initial pixels."""
import copy,json,os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from arcengine import GameState
from agent.framework_adapter import LocalFrameworkAdapter
from certification.phase4_integrated_v1.request_contract import digest
from certification.phase4_integrated_v1.predicates import changes,verdict
ROOT=Path(__file__).resolve().parents[2]
def initial():return json.loads((ROOT/'reports/integrated_case_v1/initial_observation.json').read_bytes())
class FakeArcade:
 def __init__(self,row):self.row=row
 def open_scorecard(self,tags=None):return 'fixture-'+self.row['episode_id']
 def close_scorecard(self,card):
  if os.environ.get('INTEGRATED_FIXTURE')=='cleanup':raise RuntimeError('injected close failure')
  return SimpleNamespace(model_dump=lambda:{'card_id':card})
 def make(self,game_id,**kwargs):
  row=self.row;base=initial()
  class Env:
   count=0
   def observation(self):
    g=copy.deepcopy(base['frames'][-1]);g[0][0]=(g[0][0]+self.count)%16
    if os.environ.get('INTEGRATED_FIXTURE')=='initial' and row['arm']=='structured':g[0][1]=1
    frames=[g]
    if self.count:frames=[base['frames'][-1],g]
    return SimpleNamespace(game_id=game_id,guid='fixture-'+row['episode_id'],frame=[np.array(f,dtype=np.uint8) for f in frames],
      state=GameState.NOT_FINISHED,levels_completed=int(self.count>=2 and os.environ.get('INTEGRATED_FIXTURE')!='cap'),win_levels=base['win_levels'],available_actions=base['available_actions'],full_reset=self.count==0)
   def step(self,action,data=None,reasoning=None):self.count+=1;return self.observation()
  e=Env();e.observation_space=e.observation();return e
def adapter_factory(row):return LocalFrameworkAdapter(FakeArcade(row),seed_by_game={row['game_id']:0})
def prediction(kind):return dict(kind=kind,frame='final',spans=[[0,0,0]],x=0,y=0,color=9,dx=0,dy=0)
def response(request):
 p=json.loads(request['messages'][1]['content']);stage=p.get('stage','control')
 if stage=='control':return {'action':{'action_id':1,'action_data':{}}}
 if stage=='inventory':return {'objects':[],'relationships':[],'controls':[{'action_id':a,'arguments':'x_y' if a==6 else 'empty','effect':'unknown'} for a in p['observation']['available_actions']],
  'hypotheses':[],'ambiguities':'Scripted intentionally incomplete inventory; not model evidence.'}
 if stage=='decision':return {'action':{'action_id':1,'action_data':{}},'target':{'kind':'none','label':'nonspatial','spans':[]},
  'hypotheses':[{'id':'h1','claim':'cell changes','status':'hypothesized'},{'id':'h2','claim':'cell unchanged','status':'hypothesized'}],
  'prediction':prediction('any_cell_change'),'alternative':prediction('no_cell_change'),'unresolved':'other effects',
  'subgoal':'test control','information':'cell change versus unchanged','evidence_ids':[h['call_id'] for h in p['context']['history']],
  'repeat_justification':'test repeatability'}
 c=p['context'];o=p['observation'];d=c['decision'];frames=o['frames']
 return {'changes':[{'frame_index':i,**changes(c['pre_grid'],g)} for i,g in enumerate(frames)],
  'primary':verdict(d['prediction'],c['pre_grid'],frames,c['pre_levels'],o['levels_completed']),
  'alternative':verdict(d['alternative'],c['pre_grid'],frames,c['pre_levels'],o['levels_completed']),
  'hypotheses':[],'evidence_frames':list(range(len(frames))),'next_test':'test conditional change'}
class ScriptedService:
 startup_seconds=0;artifact={};canary_audit={'status':'scripted_not_target'}
 def __init__(self):self.audit_records=[]
 def complete(self,request):
  mode=os.environ.get('INTEGRATED_FIXTURE','correct');value=response(request)
  stage=json.loads(request['messages'][1]['content']).get('stage')
  if mode=='transport':raise RuntimeError('injected transport')
  if mode=='incorrect' and stage=='feedback':value['primary']='contradicted';value['changes'][0]['count']=999
  content='{}' if mode=='invalid' and stage=='decision' else json.dumps(value)
  p=11 if mode=='mismatch' else 10
  self.audit_records.append({'request_sha256':digest(request),'tokenizer_prompt_tokens':10,'server_prompt_tokens':p,'server_completion_tokens':29,'service_seconds':0})
  return SimpleNamespace(content=content,prompt_tokens=p,completion_tokens=29)
