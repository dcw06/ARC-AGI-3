"""Pinned local tokenizer audit; no model-service or GPU access."""
import argparse,hashlib,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from certification.phase4_grounding_v1.cases import load_cases,request_hash,canary_request
from certification.phase4_grounding_v1.tokenizer_binding import verify

def run(folder):
    from transformers import AutoTokenizer
    manifest=verify(folder)
    assert importlib.metadata.version('transformers')=='4.57.6'
    assert importlib.metadata.version('tokenizers')=='0.22.2'
    tokenizer=AutoTokenizer.from_pretrained(str(folder),local_files_only=True,trust_remote_code=False)
    rows=[]
    cases=load_cases()
    for case in cases+[{'case_id':'startup-canary','request':canary_request(cases[0]['request']['model'])}]:
        request=case['request'];ids=tokenizer.apply_chat_template(request['messages'],tokenize=True,
            add_generation_prompt=True,truncation=False,**request['chat_template_kwargs'])
        size=max(len(json.dumps(request).encode()),len(json.dumps(request,separators=(',',':')).encode()))
        assert 0<len(ids)<=65408 and size<=65536
        rows.append({'case_id':case['case_id'],'request_sha256':request_hash(request),'prompt_tokens':len(ids),
            'completion_cap':128,'max_serialized_bytes':size})
    report={'status':'passed_pinned_cpu_tokenizer_not_target_vllm','transformers':importlib.metadata.version('transformers'),
        'tokenizers':importlib.metadata.version('tokenizers'),'jinja2':importlib.metadata.version('jinja2'),
        'tokenizer_files':manifest,'cases':rows,'diagnostic_calls':12,'canary_calls':1,'maximum_total_completions':13,
        'maximum_diagnostic_prompt_tokens':max(r['prompt_tokens'] for r in rows[:-1]),
        'total_diagnostic_prompt_tokens':sum(r['prompt_tokens'] for r in rows[:-1]),
        'total_prompt_tokens_including_canary':sum(r['prompt_tokens'] for r in rows),'maximum_generated_tokens_including_canary':13*128,
        'model_calls':0}
    (ROOT/'reports/phase4_grounding_v1_token_audit.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','tokenizer_files')}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tokenizer',type=Path,required=True);run(parser.parse_args().tokenizer)
