"""Offline pinned-tokenizer audit for the exact coordinate inventory and canary."""
import argparse,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from certification.phase4_coordinates_v2.cases import load,encoded,request_hash
from certification.phase4_grounding_v1.cases import canary_request
from certification.phase4_coordinates_v2.tokenizer_binding import verify
def run(folder):
    from transformers import AutoTokenizer
    manifest=verify(folder)
    versions={n:importlib.metadata.version(n) for n in ('transformers','tokenizers','jinja2')}
    assert versions=={'transformers':'4.57.6','tokenizers':'0.22.2','jinja2':'3.1.6'}
    tokenizer=AutoTokenizer.from_pretrained(str(folder),local_files_only=True,trust_remote_code=False)
    cases=load();rows=[]
    for case in cases+[{'case_id':'startup-canary','request':canary_request(cases[0]['request']['model'])}]:
        request=case['request'];tokens=tokenizer.apply_chat_template(request['messages'],tokenize=True,add_generation_prompt=True,truncation=False,**request['chat_template_kwargs'])
        size=max(len(json.dumps(request).encode()),len(json.dumps(request,separators=(',',':')).encode()))
        assert len(tokens)+128<=65536 and size<=65536
        rows.append({'case_id':case['case_id'],'request_sha256':request_hash(request),'prompt_tokens':len(tokens),
            'serialized_bytes':size,'completion_cap':128,'context_headroom_tokens':65536-len(tokens)-128})
    report={'status':'offline_token_audit_passed_not_live_vllm_validation','versions':versions,'tokenizer_manifest':manifest,'cases':rows,
        'calls':len(cases),'canary_calls':1,'total_inference_ceiling':len(rows),'maximum_generated_tokens':len(rows)*128,
        'total_prompt_tokens':sum(r['prompt_tokens'] for r in rows),'largest_prompt_tokens':max(r['prompt_tokens'] for r in rows),'model_calls':0}
    (ROOT/'reports/phase4_coordinates_v2_token_audit.json').write_bytes(encoded(report));print(json.dumps({k:v for k,v in report.items() if k not in ('cases','tokenizer_manifest')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);run(p.parse_args().tokenizer)
