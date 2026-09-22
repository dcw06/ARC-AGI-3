"""Exact stage contracts, usable in the isolated model process."""
import json,hashlib
from pathlib import Path
from certification.phase4_transient_v2.action_contract import response_format,validate_action
CAPS={'control':128,'inventory':2048,'decision':1024,'feedback':1024}
SYSTEM='Read supplied raw integer grids: x is column right, y is row down; grid[y][x]. Separate observed geometry from uncertain rules. Return only the requested JSON. No reset or retries. Give short observable commitments, not a reasoning transcript.'
QUESTIONS={
 'inventory':'Locate up to six visible regions with current-frame row spans [y,xmin,xmax] and bbox [xmin,ymin,xmax,ymax]. Separate silhouettes from internal markings. Give geometric relationships, alternative transformations and ambiguity. List supplied controls and their argument requirements without assuming effects. State at most two uncertain goal hypotheses. Matching geometry does not establish the objective.',
 'decision':'Choose one informative legal action. Declare its intended target as CURRENT-frame row spans, not a stale mask, or none for a nonspatial action. Give two competing hypotheses, a specific observable prediction and distinct alternative, and what stays unresolved. State a subgoal and distinguishing information. Cite earlier call IDs and justify any repeated action.',
 'feedback':'Compare the pre-frame with EVERY returned frame. Report frame index, changed-cell count and bbox ([] if unchanged); dimension change uses count=-1,bbox=[]. Assess both committed predicates, cite evidence frames and update hypotheses and next test. Do not issue an action. Final feedback is required even after progress or terminal observation.'}
def protocol():return json.loads(Path(__file__).with_name('protocol.json').read_bytes())
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def obj(p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def arr(v,n,low=0):return {'type':'array','items':v,'minItems':low,'maxItems':n}
def integer(lo=0,hi=63):return {'type':'integer','minimum':lo,'maximum':hi}
def enum(*v):return {'type':'string','enum':list(v)}
TEXT={'type':'string','maxLength':512};ID={'type':'string','minLength':1,'maxLength':64}
SPANS=arr(arr(integer(),3,3),128);BOX=arr(integer(),4,4)
HYP=obj({'id':ID,'claim':TEXT,'status':enum('observed','hypothesized','uncertain')})
PRED=obj({'kind':enum('no_cell_change','any_cell_change','exact_color_at','exact_translation_of_mask','level_counter_increase'),
 'frame':enum('final','any_returned'),'spans':SPANS,'x':integer(),'y':integer(),'color':integer(0,15),'dx':integer(-63,63),'dy':integer(-63,63)})
def schema(stage,legal):
 if stage=='inventory':return obj({'objects':arr(obj({'id':ID,'bbox':BOX,'spans':SPANS,'silhouette':TEXT,'markings':TEXT}),6),
  'relationships':arr(obj({'a':ID,'b':ID,'transforms':arr(enum('translation','rotate_cw_90','rotate_cw_180','rotate_cw_270','reflection','uncertain'),8,1),'claim':TEXT}),6),
  'controls':arr(obj({'action_id':integer(1,7),'arguments':enum('empty','x_y'),'effect':TEXT}),7),'hypotheses':arr(HYP,2),'ambiguities':TEXT})
 if stage=='decision':return obj({'action':response_format(legal)['json_schema']['schema']['properties']['action'],
  'target':obj({'kind':enum('region','location','none'),'label':TEXT,'spans':SPANS}),
  'hypotheses':arr(HYP,2),'prediction':PRED,'alternative':PRED,'unresolved':TEXT,'subgoal':TEXT,
  'information':TEXT,'evidence_ids':arr(ID,17),'repeat_justification':TEXT})
 if stage=='feedback':return obj({'changes':arr(obj({'frame_index':integer(0,7),'count':integer(-1,4096),'bbox':arr(integer(),4)}),8,1),
  'primary':enum('supported','contradicted','unresolved'),'alternative':enum('supported','contradicted','unresolved'),
  'hypotheses':arr(HYP,2),'evidence_frames':arr(integer(0,7),8),'next_test':TEXT})
 raise ValueError('stage')
def validate_shape(v,s):
 if 'anyOf' in s:
  for sub in s['anyOf']:
   try:validate_shape(v,sub);return
   except ValueError:pass
  raise ValueError('schema alternative')
 t=s.get('type')
 if t=='object':
  if type(v) is not dict or set(v)!=set(s.get('properties',{})):raise ValueError('object fields')
  for k,sub in s.get('properties',{}).items():validate_shape(v[k],sub)
 elif t=='array':
  if type(v) is not list or not s.get('minItems',0)<=len(v)<=s['maxItems']:raise ValueError('array bound')
  for item in v:validate_shape(item,s['items'])
 elif t=='integer':
  if type(v) is not int or not s.get('minimum',-10**9)<=v<=s.get('maximum',10**9):raise ValueError('integer bound')
 elif t=='string':
  if type(v) is not str or not s.get('minLength',0)<=len(v)<=s.get('maxLength',4096):raise ValueError('string bound')
 if 'enum' in s and v not in s['enum']:raise ValueError('enum')
def cells(spans,w=64,h=64):
 out=set()
 for y,x0,x1 in spans:
  if not 0<=y<h or not 0<=x0<=x1<w:raise ValueError('out-of-frame span')
  row={(x,y) for x in range(x0,x1+1)}
  if out&row:raise ValueError('overlapping span')
  out|=row
 return out
def parse(stage,content,legal,grid):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('duplicate key')
   d[k]=v
  return d
 v=json.loads(content,object_pairs_hook=pairs)
 if stage=='control':return validate_action(json.dumps(v),legal)
 validate_shape(v,schema(stage,legal));h,w=len(grid),len(grid[0])
 if stage=='inventory':
  ids=[o['id'] for o in v['objects']]
  if len(set(ids))!=len(ids):raise ValueError('duplicate object id')
  for o in v['objects']:
   cells(o['spans'],w,h);x0,y0,x1,y1=o['bbox']
   if not 0<=x0<=x1<w or not 0<=y0<=y1<h:raise ValueError('bbox bounds')
 if stage=='decision':
  t=v['target'];pts=cells(t['spans'],w,h)
  if (t['kind']=='none')!=(not pts):raise ValueError('target mask')
  if v['action']['action_id']==6 and not pts:raise ValueError('click needs target')
  for p in (v['prediction'],v['alternative']):
   pts=cells(p['spans'],w,h)
   if p['kind'] in ('no_cell_change','any_cell_change','exact_translation_of_mask') and not pts:raise ValueError('empty predicate mask')
   if p['kind']=='exact_color_at' and (p['x']>=w or p['y']>=h):raise ValueError('predicate point')
 return v
def check_grid(g):
 if type(g) is not list or not 1<=len(g)<=64 or type(g[0]) is not list or not 1<=len(g[0])<=64:raise ValueError('grid shape')
 if any(type(r) is not list or len(r)!=len(g[0]) or any(type(c) is not int or not 0<=c<=15 for c in r) for r in g):raise ValueError('grid values')
def enforce_payload(r):
 if max(len(json.dumps(r).encode()),len(json.dumps(r,separators=(',',':')).encode()))>196608:raise ValueError('request byte limit')
def make_request(stage,observation,context):
 if stage not in QUESTIONS:raise ValueError('stage')
 if not 1<=len(observation['frames'])<=8:raise ValueError('returned-frame admission bound')
 for g in observation['frames']:check_grid(g)
 visible={k:observation[k] for k in ('frames','available_actions','state','levels_completed','win_levels')}
 p={'stage':stage,'instruction':QUESTIONS[stage],'observation':visible,'context':context}
 r={'model':protocol()['model_binding']['model_id'],'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(p,sort_keys=True,separators=(',',':'))}],
 'temperature':0,'seed':0,'max_tokens':CAPS[stage],'chat_template_kwargs':{'enable_thinking':False},
 'response_format':{'type':'json_schema','json_schema':{'name':'integrated_'+stage+'_v1','strict':True,'schema':schema(stage,observation['available_actions'])}}}
 enforce_payload(r);return r
def validate_request(r):
 enforce_payload(r);p=json.loads(r['messages'][1]['content'])
 if 'stage' not in p:
  from certification.phase4_transient_v2.request_contract import validate_request as baseline
  baseline(r)
  if r['seed']!=0 or r['messages'][0]['content']!=protocol()['prompts']['control']['text']:raise ValueError('baseline drift')
  return 'control'
 stage=p['stage']
 if stage not in QUESTIONS or set(p)!={'stage','instruction','observation','context'}:raise ValueError('stage envelope')
 if r!=make_request(stage,p['observation'],p['context']):raise ValueError('structured request drift')
 return stage
