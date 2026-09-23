"""Pinned CPU tokenizer audit: exact fixture requests plus adaptive stress inputs."""
import argparse,copy,hashlib,importlib.metadata,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from certification.phase4_integrated_v2.request_contract import make_request,validate_request,digest
def run(folder):
 from transformers import AutoTokenizer
 from certification.phase4_integrated_v2.tokenizer_binding import verify
 manifest=verify(folder);versions={k:importlib.metadata.version(k) for k in ('transformers','tokenizers','jinja2')}
 assert versions=={'transformers':'4.57.6','tokenizers':'0.22.2','jinja2':'3.1.6'}
 tok=AutoTokenizer.from_pretrained(str(folder),local_files_only=True,trust_remote_code=False)
 requests={}
 with zipfile.ZipFile(ROOT/'evidence/phase4-integrated-v2-local.zip') as z:
  for name in z.namelist():
   if name.startswith(('correct/worker/','cap/worker/')) and '-call-' in name:
    r=json.loads(z.read(name))['request'];requests[name]=r
 from certification.phase4_grounding_v1.cases import canary_request
 from certification.phase4_integrated_v2.request_contract import protocol
 requests['canary']=canary_request(protocol()['model_binding']['model_id'])
 initial=json.loads((ROOT/'reports/integrated_case_v1/initial_observation.json').read_bytes())
 requests['initial_inventory']=make_request('inventory',initial,{})
 # Maximum admitted frame count; history filler demonstrates rejection rather
 # than asserting all theoretically valid response combinations fit in context.
 stress={**initial,'frames':[initial['frames'][-1]]*8}
 requests['eight_frame_feedback']=make_request('feedback',stress,{'pre_grid':initial['frames'][-1],'history':[]})
 stress_history={'history':[{'call_id':f'stress-{i}','answer':{'text':'indeterminate '*512}} for i in range(16)]}
 requests['bounded_history_stress']=make_request('decision',initial,stress_history)
 rows=[]
 for name,r in requests.items():
  ids=tok.apply_chat_template(r['messages'],tokenize=True,add_generation_prompt=True,truncation=False,**r['chat_template_kwargs'])
  size=max(len(json.dumps(r).encode()),len(json.dumps(r,separators=(',',':')).encode()))
  admissible=len(ids)<=60000 and len(ids)+r['max_tokens']<=65536 and size<=196608
  rows.append({'id':name,'request_sha256':digest(r),'prompt_tokens':len(ids),'completion_cap':r['max_tokens'],'bytes':size,'admissible':admissible})
  if name not in ('eight_frame_feedback','bounded_history_stress'):assert admissible,name
 # Worst-case accumulated history: every prior answer is the maximum-size, most
 # token-dense valid output, built exactly as worker.run_cases composes contexts.
 examples=json.loads((ROOT/'reports/phase4_integrated_v2_output_examples.json').read_bytes())
 worst={}
 for case in examples:
  raw=json.dumps(case['response'],sort_keys=True,separators=(',',':'))
  n=len(tok.encode(raw,add_special_tokens=False))
  if n>worst.get(case['stage'],(0,None))[0]:worst[case['stage']]=(n,case['response'])
 grid=initial['frames'][-1];history=[{'call_id':'ic2-structured-call-00','stage':'inventory','answer':worst['inventory'][1]}]
 accumulated=[];cursor=1
 def measure(stage,frames,context):
  r=make_request(stage,{**initial,'frames':[grid]*frames},context)
  ids=tok.apply_chat_template(r['messages'],tokenize=True,add_generation_prompt=True,truncation=False,**r['chat_template_kwargs'])
  size=max(len(json.dumps(r).encode()),len(json.dumps(r,separators=(',',':')).encode()))
  return {'prompt_tokens':len(ids),'bytes':size,'admissible':len(ids)<=60000 and len(ids)+r['max_tokens']<=65536 and size<=196608}
 for step in range(8):
  dec=f'ic2-structured-call-{cursor:02d}';cursor+=1
  accumulated.append({'step':step,'stage':'decision','history_entries':len(history),**measure('decision',1,{'history':history})})
  history.append({'call_id':dec,'stage':'decision','answer':worst['decision'][1]})
  context={'history':history,'pre_grid':grid,'pre_levels':initial['levels_completed'],'decision_call_id':dec,'decision':worst['decision'][1]}
  row={'step':step,'stage':'feedback','history_entries':len(history),**measure('feedback',1,context)}
  row['max_admissible_returned_frames']=max([f for f in range(1,9) if measure('feedback',f,context)['admissible']],default=0)
  accumulated.append(row)
  history.append({'call_id':f'ic2-structured-call-{cursor:02d}','stage':'feedback','answer':worst['feedback'][1]});cursor+=1
 accumulated_summary={'answer_tokens_used':{k:v[0] for k,v in worst.items()},'rows':accumulated,
  'largest_one_frame_prompt':max(r['prompt_tokens'] for r in accumulated),
  'all_one_frame_requests_admissible':all(r['admissible'] for r in accumulated),
  'min_admissible_returned_frames_final_feedback':min(r['max_admissible_returned_frames'] for r in accumulated if r['stage']=='feedback'),
  'scope':'Worst-case valid answers at maximum cardinality/length (punctuation-stress where denser), compact as serialized in requests; frames are copies of the initial grid. Not a bound for grids that tokenize more densely.'}
 report={'versions':versions,'accumulated_history_worst_case':accumulated_summary,'tokenizer_manifest_sha256':hashlib.sha256((ROOT/'certification/phase4_integrated_v2/tokenizer_manifest.json').read_bytes()).hexdigest(),
  'rows':rows,'adaptive_rule':'Every actual request is tokenized before inference; >60000 prompt tokens or 196608 bytes fails closed with no truncation/retry. Stress cases are not a guarantee all histories fit.',
  'study_prompt_ceiling':1500000,'generated_ceiling_including_canary':27776,'max_completions':26,'model_calls':0,'gpu_runs':0}
 (ROOT/'reports/phase4_integrated_v2_token_audit.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);run(p.parse_args().tokenizer)
