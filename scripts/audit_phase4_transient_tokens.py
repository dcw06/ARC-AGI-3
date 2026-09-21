"""CPU-only exact tokenizer audit of matched archived requests; no model calls."""
import argparse,copy,hashlib,importlib.metadata,json,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_transient_v1.selection import select,FIELD,enforce_payload,encoded

def run(tokenizer_path):
    from transformers import AutoTokenizer
    from certification.phase4_transient_v1.tokenizer_binding import verify
    manifest=verify(tokenizer_path)
    if importlib.metadata.version('transformers')!='4.57.6':raise ValueError('transformers version')
    tokenizer=AutoTokenizer.from_pretrained(str(tokenizer_path),local_files_only=True,trust_remote_code=False)
    spec=json.loads((ROOT/'certification/phase4_transient_v1/protocol.json').read_bytes())
    def count(request):
        enforce_payload(request)
        ids=tokenizer.apply_chat_template(request['messages'],tokenize=True,add_generation_prompt=True,
            truncation=False,**request['chat_template_kwargs'])
        if not ids or len(ids)+request['max_tokens']>65536:raise ValueError('context limit')
        return len(ids)
    receipt=json.loads((ROOT/'reports/phase4_closed_loop_v1_evidence_receipt.json').read_bytes())
    archive=ROOT/receipt['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['archive_sha256']
    rows=[];historical_mismatch=[]
    with zipfile.ZipFile(archive) as z:
        prefix='output/phase4-closed-loop-v1/worker/'
        read=lambda name:json.loads(z.read(prefix+name))
        for ep in read('state.json')['episodes']:
            previous=None
            for name in ep['steps']:
                step=read(name);observed=count(step['request'])
                if observed!=step['audit']['tokenizer_prompt_tokens']:historical_mismatch.append(name)
                control=copy.deepcopy(step['request']);control['messages'][0]['content']=spec['prompts']['control']['text']
                treatment=copy.deepcopy(control);payload=json.loads(treatment['messages'][1]['content'])
                value=select(previous);payload['observation'][FIELD]=value
                treatment['messages'][1]['content']=json.dumps(payload,sort_keys=True,separators=(',',':'))
                # Removing exactly one field restores the serialized control request.
                stripped=copy.deepcopy(treatment);payload['observation'].pop(FIELD)
                stripped['messages'][1]['content']=json.dumps(payload,sort_keys=True,separators=(',',':'))
                assert stripped==control
                rows.append({'record':name,'game_id':ep['game_id'],'field_nonnull':value is not None,
                    'control_tokens':count(control),'treatment_tokens':count(treatment),
                    'control_bytes':len(encoded(control)),'treatment_bytes':len(encoded(treatment)),
                    'control_sha256':hashlib.sha256(encoded(control)).hexdigest(),
                    'treatment_sha256':hashlib.sha256(encoded(treatment)).hexdigest()})
                previous=(read(step['pre']),read(step['post']))
    if historical_mismatch:raise ValueError('tokenizer differs from retained target counts: '+str(historical_mismatch[:3]))
    report={'status':'passed_cpu_tokenizer_audit_not_vllm_validation','transformers':importlib.metadata.version('transformers'),
        'tokenizers':importlib.metadata.version('tokenizers'),'revision':spec['model_binding']['revision'],
        'tokenizer_files':{name:info['sha256'] for name,info in manifest['files'].items()},
        'jinja2':importlib.metadata.version('jinja2'),
        'archive_sha256':receipt['archive_sha256'],'matched_pairs':len(rows),'historical_target_token_counts_matched':len(rows),
        'nonnull_treatments':sum(r['field_nonnull'] for r in rows),
        'max_control_tokens':max(r['control_tokens'] for r in rows),'max_treatment_tokens':max(r['treatment_tokens'] for r in rows),
        'max_treatment_bytes':max(r['treatment_bytes'] for r in rows),
        'max_added_tokens':max(r['treatment_tokens']-r['control_tokens'] for r in rows),
        'context_tokens':65536,'completion_reserve_tokens':128,'truncation':False,
        'scope_limit':'Archived corpus only, not an upper-bound proof for future trajectories. Runtime checks every request; target server/tokenizer parity remains required.',
        'model_calls':0,'gpu_runs':0,'rows':rows}
    (ROOT/'reports/phase4_transient_v1_token_audit.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','tokenizer_files')},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tokenizer',type=Path)
    args=parser.parse_args()
    if args.tokenizer:run(args.tokenizer)
    else:
        with tempfile.TemporaryDirectory(prefix='transient-tokenizer-') as folder:
            with zipfile.ZipFile(ROOT/'evidence/phase4-transient-v1-tokenizer.zip') as z:
                for name in z.namelist():
                    if Path(name).name!=name:raise ValueError('tokenizer archive path')
                z.extractall(folder)
            run(Path(folder))
