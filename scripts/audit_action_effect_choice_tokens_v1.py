"""Offline pinned CPU token audit of all rehearsed/current-forecast input variants."""
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
from research.action_effect_choice_v1.preparation import verify

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','requests','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--input-pin',required=True);args=parser.parse_args()
    verify(args.inputs,args.input_pin)
    os.environ.update(CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    def offline(*a,**kw):raise PermissionError('CPU token audit is offline')
    socket.create_connection=socket.socket.connect=offline
    if metadata.version('transformers')!='4.57.6':raise ValueError('pinned Transformers differs')
    import torch
    torch.set_num_threads(2)
    archive=ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if sha(archive)!='af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':raise ValueError('processor fixture changed')
    requests=json.loads(args.requests.read_bytes());rows=[]
    with tempfile.TemporaryDirectory(prefix='action-effect-native-')as folder:
        with zipfile.ZipFile(archive)as bundle:
            for name in bundle.namelist():
                if Path(name).name!=name:raise ValueError('unsafe processor member')
                (Path(folder)/name).write_bytes(bundle.read(name))
        native=TokenAudit(folder)
        for row in requests:
            if digest(row['body'])!=row['request_sha256']:raise ValueError('audited input changed')
            count=native(row['body'])
            if type(count)is not int or not 0<count<=8192:raise ValueError('prompt ceiling exceeded')
            rows.append({'id':row['id'],'request_sha256':row['request_sha256'],'prompt_tokens':count})
    result={'passed':True,'input_manifest_sha256':args.input_pin,'request_file_sha256':sha(args.requests),
        'CPU_processor_calls':len(rows),'maximum_prompt_tokens':max(row['prompt_tokens']for row in rows),
        'rows':rows,'versions':{key:metadata.version(key)for key in ('transformers','torch','pillow')},
        'GPU_jobs':0,'neural_generations':0}
    write_new(args.output,result)
    print(json.dumps({key:value for key,value in result.items()if key!='rows'}))
