"""Generate the frozen probe inventory with pinned-tokenizer local expectations (no model calls)."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from certification.phase4_multimodal_preflight_v2.cases import generate,text_only
OUTPUT=ROOT/'certification/phase4_multimodal_preflight_v2/cases.json'

def expectation(tokenizer,row):
    """Template tokens with the pinned tokenizer; image tokens from the provisional arithmetic only."""
    request=row['request'];kwargs=request['chat_template_kwargs']
    ids=tokenizer.apply_chat_template(request['messages'],tokenize=True,add_generation_prompt=True,truncation=False,**kwargs)
    value={'template_tokens':len(ids),'source':'pinned tokenizer template + provisional resize arithmetic; verified on target, never assumed'}
    if 'image' in row:
        pad=tokenizer.convert_tokens_to_ids('<|image_pad|>')
        if ids.count(pad)!=1:raise ValueError('placeholder count')
        base=tokenizer.apply_chat_template(text_only(request)['messages'],tokenize=True,add_generation_prompt=True,truncation=False,**kwargs)
        if len(ids)-len(base)!=3:raise ValueError('vision marker delta')
        value['expected_prompt_tokens']=len(ids)-1+row['image']['provisional_arithmetic']['image_tokens']
    else:value['expected_prompt_tokens']=len(ids)
    return value

def build(tokenizer_folder):
    from transformers import AutoTokenizer
    from certification.phase4_multimodal_preflight_v2.tokenizer_binding import verify
    verify(tokenizer_folder)
    tokenizer=AutoTokenizer.from_pretrained(str(tokenizer_folder),local_files_only=True,trust_remote_code=False)
    rows=generate()
    for row in rows:row['frozen_local_expectation']=expectation(tokenizer,row)
    OUTPUT.write_text(json.dumps(rows,indent=1)+'\n',newline='\n')
    return [{'probe':r['probe_id'],'request_sha256':r['request_sha256'],**r['frozen_local_expectation'],
        **({'png_bytes':r['image']['png_bytes'],**r['image']['provisional_arithmetic']} if 'image' in r else {})} for r in rows]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True)
    print(json.dumps(build(p.parse_args().tokenizer),indent=1))
