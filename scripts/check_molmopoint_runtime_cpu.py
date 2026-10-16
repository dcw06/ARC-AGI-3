"""CPU compatibility rehearsal with tiny random parameters, never pretrained weights."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.molmopoint_identification_v1.adapter import MODEL,REVISION,prepare_prompt_inputs
from research.molmopoint_identification_v1.inference import requests_for,metadata_value


def check(model_folder, preparation, output):
    os.environ.update(CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void',
        HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    attempts=[]
    def refuse(*args,**kwargs):
        attempts.append(True)
        raise PermissionError('CPU rehearsal network disabled')
    socket.socket.connect=refuse
    socket.create_connection=refuse
    def expired(*args):
        raise TimeoutError('CPU rehearsal exceeded 240 seconds')
    signal.signal(signal.SIGALRM,expired)
    signal.alarm(240)
    import torch, transformers, accelerate
    from PIL import Image
    from transformers import AutoConfig,AutoModelForImageTextToText,AutoProcessor
    assert transformers.__version__=='4.57.1'
    assert accelerate.__version__=='1.12.0'
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.manual_seed(0)
    pin=json.loads((ROOT/'research/molmopoint_identification_v1/model_pin.json').read_bytes())
    hashes={}
    for row in pin['files']:
        if row['name'].endswith('.safetensors'):
            continue
        raw=(Path(model_folder)/row['name']).read_bytes()
        assert len(raw)==row['bytes']
        if 'git_blob_sha1' in row:
            assert hashlib.sha1(('blob '+str(len(raw))+'\0').encode()+raw).hexdigest()==row['git_blob_sha1']
        if 'upstream_sha256' in row:
            assert hashlib.sha256(raw).hexdigest()==row['upstream_sha256']
        hashes[row['name']]=hashlib.sha256(raw).hexdigest()
    config=AutoConfig.from_pretrained(model_folder,trust_remote_code=True,local_files_only=True)
    # Deliberately tiny random architecture, retaining tokenizer and image geometry.
    for sub in (config.text_config,config.vit_config,config.adapter_config):
        sub.hidden_size=64
        sub.head_dim=16
        sub.num_attention_heads=4
        sub.num_key_value_heads=2 if sub is config.text_config else 4
        sub.intermediate_size=128
        sub._attn_implementation='sdpa'
    config.text_config.num_hidden_layers=2
    config.vit_config.num_hidden_layers=2
    config.adapter_config.text_hidden_size=64
    config.adapter_config.vit_layers=[-1]
    config.patch_embed_dim=64
    config._attn_implementation='sdpa'
    model=AutoModelForImageTextToText.from_config(config,trust_remote_code=True).eval()
    processor=AutoProcessor.from_pretrained(model_folder,trust_remote_code=True,
        local_files_only=True,padding_side='left',use_fast=False)
    rows=[]
    for request in requests_for(Path(preparation)/'inputs'):
        with Image.open(Path(preparation)/request['image']) as image:
            inputs,metadata,logits=prepare_prompt_inputs(model,processor,image,request['prompt'])
        row={'case_id':request['case_id'],'prompt_tokens':inputs['input_ids'].shape[-1],
             'pooling_shape':list(metadata['token_pooling'].shape),
             'native_logits_processor':type(logits[0]).__name__,
             'serialized_metadata_sha256':hashlib.sha256(json.dumps(metadata_value(metadata),sort_keys=True).encode()).hexdigest()}
        if not rows:
            with torch.inference_mode():
                ids=model.generate(**inputs,logits_processor=logits,max_new_tokens=4,
                                   do_sample=False,num_beams=1)
            row['tiny_random_new_tokens']=ids.shape[-1]-inputs['input_ids'].shape[-1]
            assert 1 <= row['tiny_random_new_tokens'] <= 4
        rows.append(row)
    # Exercise the real AutoModel checkpoint-loading path and explicit dtype,
    # using ONLY freshly saved tiny random parameters, never the 8B shards.
    with tempfile.TemporaryDirectory(prefix='molmopoint-tiny-load-') as tiny:
        model.save_pretrained(tiny,safe_serialization=True)
        loaded=AutoModelForImageTextToText.from_pretrained(tiny,trust_remote_code=True,
            local_files_only=True,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True,
            attn_implementation='sdpa').eval()
        assert all(p.device.type=='cpu' and p.dtype==torch.bfloat16 for p in loaded.parameters())
        loaded_parameters=sum(p.numel() for p in loaded.parameters())
    assert not torch.cuda.is_initialized() and not attempts
    result=dict(model=MODEL,revision=REVISION,execution_device='cpu',network_attempts=0,
        torch=torch.__version__,transformers=transformers.__version__,accelerate=accelerate.__version__,
        pretrained_weights_loaded=False,pretrained_generations=0,tiny_random_generations=1,
        tiny_parameters=sum(p.numel() for p in model.parameters()),cases=rows,
        tiny_checkpoint_load_parameters=loaded_parameters,tiny_checkpoint_BF16_load_verified=True,
        code_and_metadata_sha256=hashes,isolated_full_GPU_installation_verified=False,
        qualification='Shared CPU dependency environment plus separate Transformers/Accelerate; tiny random model only.')
    with Path(output).open('x') as stream:
        json.dump(result,stream,sort_keys=True,indent=2)
    print(json.dumps({k:result[k] for k in ('pretrained_generations','tiny_random_generations','tiny_parameters','cases')}))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('model','preparation','output'):
        cli.add_argument('--'+name,required=True)
    args=cli.parse_args()
    check(args.model,args.preparation,args.output)
