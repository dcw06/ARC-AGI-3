"""Pinned, offline CPU token replay of the exact reviewed live-worker requests."""
import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha,write_new
from research.initial_geometry_assistance_v1.model_io import TokenAudit
from research.feedback_summary_probe_live_v1.live_operator import verify_review
from research.feedback_summary_probe_live_v1.live_evaluation import lines


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('review','transport','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--review-pin',required=True)
    args=parser.parse_args()
    _,pin=verify_review(args.review,ROOT)
    if pin!=args.review_pin: raise ValueError('external review pin differs')
    os.environ.update(CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    def offline(*a,**kw): raise PermissionError('native audit network disabled')
    socket.socket.connect=socket.create_connection=offline
    if metadata.version('transformers')!='4.57.6': raise ValueError('pinned Transformers differs')
    import torch
    torch.set_num_threads(2)
    archive=ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if sha(archive)!='af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
        raise ValueError('processor fixture differs')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='summary-live-native-') as folder:
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).name!=name: raise ValueError('unsafe processor fixture member')
                (Path(folder)/name).write_bytes(bundle.read(name))
        native=TokenAudit(folder)
        for event in lines(args.transport):
            if event['kind']!='HTTP_request': continue
            count=native(event['body'])
            if type(event['native_prompt_tokens']) is not int or not 0<count<=8192 or count!=event['native_prompt_tokens']:
                raise ValueError('native prompt count differs or exceeds cap')
            rows.append({'id':event['id'],'request_sha256':digest(event['body']),'prompt_tokens':count})
    if not rows: raise ValueError('no HTTP request records')
    receipt={'passed':True,'review_lock_sha256':pin,'transport_sha256':sha(args.transport),'CPU_processor_calls':len(rows),
        'rows':rows,'maximum_prompt_tokens':max(r['prompt_tokens'] for r in rows),
        'versions':{n:metadata.version(n) for n in ('transformers','torch','pillow')},'GPU_jobs':0,'neural_generations':0}
    write_new(args.output,receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='rows'}))


if __name__=='__main__': main()
