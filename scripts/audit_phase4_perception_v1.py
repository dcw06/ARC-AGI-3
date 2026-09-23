"""Freeze exact requests and actual CPU processor/tokenizer budgets, no inference."""
import copy,itertools,json,sys,tempfile,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def run():
    import os,importlib.metadata
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='')
    from transformers import AutoTokenizer,AutoProcessor
    from certification.phase4_perception_v1.cases import generate,canary_request,MODEL
    from certification.phase4_perception_v1.service import expected_prompt,PINNED_PROCESSOR
    from research.perception_v1.scoring import parse
    from research.perception_v1.controls import cases as controls,score
    versions={n:importlib.metadata.version(n) for n in ('torch','torchvision','transformers','pillow')}
    for n,v in {'torch':'2.10.0','torchvision':'0.25.0','transformers':'4.57.6','pillow':'12.2.0'}.items():assert versions[n].split('+')[0]==v
    archive=ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    manifest=json.loads((ROOT/'certification/phase4_perception_v1/tokenizer_manifest.json').read_bytes())
    hashes={n:v['sha256'] for n,v in manifest['files'].items()}|PINNED_PROCESSOR
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(hashes)
        for n,h in hashes.items():
            raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==h;(Path(tmp)/n).write_bytes(raw)
        tokenizer=AutoTokenizer.from_pretrained(tmp,local_files_only=True,trust_remote_code=False)
        processor=AutoProcessor.from_pretrained(tmp,local_files_only=True,trust_remote_code=False)
        rows=generate();summary=[]
        for row in rows:
            req=row['request'];e=expected_prompt(tokenizer,processor,req);row['frozen_local_expectation']=e
            payload=len(json.dumps(req).encode());assert e['expected_prompt_tokens']<=16000 and payload<=262144
            assert e['expected_prompt_tokens']+req['max_tokens']<=65536
            summary.append({'id':row['probe_id'],'request_sha256':row['request_sha256'],'payload_bytes':payload,**e})
        # Maximum schema cardinality/strings, readable English and punctuation-dense stress.
        outputs=[];examples={}
        for label,description in [('english',('Bounded visible region with internal markings. '*2)[:48]),('dense',('!@#$%^&*()-_=+[]{};:,./?'*3)[:48])]:
            ids=[(chr(65+i)+('!@#$%^&*()-_=+[]{};:,./?'*2))[:24] for i in range(6)]
            v={'objects':[{'id':i,'bbox':[12,23,45,56],'colors':[10,11,12],
                'occupancy':[[1,0,1],[0,1,0],[1,0,1]],'has_markings':True,'marking_colors':[10,11,12],
                'description':description} for i in ids],
                'non_object_regions':[{'bbox':[0,0,63,63],'description':description} for _ in range(3)],
                'relations':[{'a':ids[a],'b':ids[b],'same_shape':True,'transform':'mirror_left_right_then_rotate_cw_270'}
                    for a,b in list(itertools.combinations(range(6),2))[:6]]}
            examples[label]=v
            for style,kw in [('compact',{'separators':(',',':')}),('normal',{}),('pretty',{'indent':2})]:
                raw=json.dumps(v,**kw);parse(raw,'stop');n=len(tokenizer.encode(raw,add_special_tokens=False))+1
                assert n<=2048,(label,style,n);outputs.append({'kind':'perception','example':label,'style':style,'tokens_with_eos':n,'cap':2048})
        for c in controls():
            v=copy.deepcopy(c['expected']);v['directional_ids']=list(range(1,8))
            raw=json.dumps(v,indent=2);assert score(c,raw)['valid'];n=len(tokenizer.encode(raw,add_special_tokens=False))+1
            assert n<=512;outputs.append({'kind':'control','example':c['id'],'style':'pretty','tokens_with_eos':n,'cap':512})
        canary=expected_prompt(tokenizer,processor,canary_request(MODEL))
    report={'versions':versions,'cases':summary,'startup_canary':canary,'output_audit':outputs,
        'prompt_token_ceiling_actual_workload':sum(r['expected_prompt_tokens'] for r in summary)+canary['expected_prompt_tokens'],
        'completion_ceiling':sum(r['request']['max_tokens'] for r in rows)+128,'calls_including_canaries':14,
        'model_calls':0,'gpu_runs':0,'limitations':'CPU processor/template audit; representative maximum-schema outputs, not an upper bound on arbitrary Unicode or whitespace.'}
    for path,value in [('certification/phase4_perception_v1/cases.json',rows),('reports/phase4_perception_v1_token_audit.json',report),
                       ('reports/phase4_perception_v1_output_examples.json',examples)]:
        (ROOT/path).write_bytes((json.dumps(value,indent=1)+'\n').encode())
    print(json.dumps(report,indent=2))
if __name__=='__main__':run()
