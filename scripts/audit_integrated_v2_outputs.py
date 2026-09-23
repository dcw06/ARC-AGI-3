"""Measure maximum-cardinality output examples with the exact pinned tokenizer."""
import json,sys,hashlib,importlib.metadata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from certification.phase4_integrated_v2.request_contract import schema,validate_shape,CAPS
def maximum(s,stress=False):
 if 'anyOf' in s:return maximum(s['anyOf'][-1],stress)
 if 'enum' in s:return max(s['enum'],key=lambda v:len(str(v)))
 t=s['type']
 if t=='object':return {k:maximum(v,stress) for k,v in s['properties'].items()}
 if t=='array':return [maximum(s['items'],stress) for _ in range(s['maxItems'])]
 if t=='integer':return s.get('maximum',7)
 n=s.get('maxLength',48)
 text=('Q7!z9?x3#v5@k2%j8&b4*d6+f1=m0/w' if stress else 'Visible contour and markings remain uncertain. ')
 return (text*(n//len(text)+1))[:n]
def fixtures():
 out=[]
 for stage in ('inventory','decision','feedback'):
  for stress in (False,True):
   v=maximum(schema(stage,list(range(1,8))),stress)
   if stage=='inventory':
    for i,o in enumerate(v['objects']):o.update(id=f'object_{i:017d}',bbox=[10*i,0,10*i+8,8])
    for i,p in enumerate(v['relationships']):p.update(a=v['objects'][i]['id'],b=v['objects'][i+1]['id'])
    for i,c in enumerate(v['controls']):c.update(action_id=i+1,arguments='x_y' if i==5 else 'empty')
   if stage=='decision':
    v['target'].update(kind='region',spans=[[y,10,18] for y in range(12)])
    for k in ('prediction','alternative'):v[k]['spans']=[[y,10,18] for y in range(12)]
    v['action']={'action_id':6,'action_data':{'x':10,'y':10}}
   if stage=='feedback':
    for i,c in enumerate(v['changes']):c.update(frame_index=i,bbox=[0,0,63,63])
   validate_shape(v,schema(stage,list(range(1,8))))
   out.append({'stage':stage,'variant':'punctuation_stress' if stress else 'realistic_maximum_cardinality','response':v})
 return out
def run():
 from transformers import AutoTokenizer
 from certification.phase4_integrated_v2.tokenizer_binding import verify
 folder=ROOT/'.cache/phase4-tokenizer';verify(folder)
 assert importlib.metadata.version('transformers')=='4.57.6'
 tok=AutoTokenizer.from_pretrained(str(folder),local_files_only=True,trust_remote_code=False)
 rows=[];cases=fixtures()
 for case in cases:
  for formatting in ('compact','normal','pretty'):
   raw=json.dumps(case['response'],**({'separators':(',',':')} if formatting=='compact' else {'indent':2} if formatting=='pretty' else {}))
   count=len(tok.encode(raw,add_special_tokens=False))
   rows.append({'stage':case['stage'],'variant':case['variant'],'formatting':formatting,'tokens':count,'bytes':len(raw.encode()),'cap':CAPS[case['stage']],
                'fits':count+1<=CAPS[case['stage']],'sha256':hashlib.sha256(raw.encode()).hexdigest()})
 # Calibrate offline counting against the one server-counted cap response (v1 inventory).
 import zipfile
 with zipfile.ZipFile(ROOT/'evidence/phase4-integrated-v1-r1-completed.zip') as z:
  v1=json.loads(z.read('download/phase4-integrated-v1/worker/ic1-structured-call-00.json'))
 body=v1['response_content'];assert hashlib.sha256(body.encode()).hexdigest()=='3a645553851309de0f53729517f920c069a7f89a8bbf484c6b34c7f07dfcb7ba'
 calibration={'source':'v1 ic1-structured-call-00 (under the superseded v1 schema)','bytes':len(body.encode()),
  'server_completion_tokens':v1['audit']['server_completion_tokens'],'offline_retokenized':len(tok.encode(body,add_special_tokens=False)),
  'note':'Re-encoding generated text can differ slightly from the generated token sequence; this checks scale, not identity.'}
 report={'rows':rows,'all_fit_with_one_eos_token':all(r['fits'] for r in rows),'calibration':calibration,'model_calls':0,
 'scope':'Every schema array at maximum cardinality; free-text fields at maximum character length. Measures concrete English and punctuation-stress outputs, including pretty printing. Not a theorem over arbitrary Unicode or arbitrary whitespace; runtime guards remain strict.'}
 (ROOT/'reports/phase4_integrated_v2_output_examples.json').write_bytes((json.dumps(cases,indent=2)+'\n').encode())
 (ROOT/'reports/phase4_integrated_v2_output_audit.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
 print(json.dumps(report,indent=2))
if __name__=='__main__':run()
