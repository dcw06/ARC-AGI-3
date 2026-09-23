"""Actual pinned processor CPU regression; no weights, inference, server or network.

Requires torch 2.10.0, torchvision 0.25.0, transformers 4.57.6 and pillow
12.2.0. CPU builds of torch/vision are intentional; this is not a CUDA test.
"""
import argparse, hashlib, importlib.metadata, json, os, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def run(tokenizer_folder,processor_folder):
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='')
    versions={n:importlib.metadata.version(n) for n in ('torch','torchvision','transformers','pillow')}
    for n,v in {'torch':'2.10.0','torchvision':'0.25.0','transformers':'4.57.6','pillow':'12.2.0'}.items():
        assert versions[n].split('+')[0]==v,(n,versions[n])
    from certification.phase4_multimodal_preflight_v3.tokenizer_binding import verify
    from certification.phase4_multimodal_preflight_v3.service import PINNED_PROCESSOR,expected_prompt,audited_probe
    from certification.phase4_multimodal_preflight_v3.response_evidence import ResponseValidationError
    from certification.phase4_multimodal_preflight_v3.cases import load_cases
    from transformers import AutoProcessor,AutoTokenizer
    verify(tokenizer_folder)
    manifest=json.loads((ROOT/'certification/phase4_multimodal_preflight_v3/tokenizer_manifest.json').read_bytes())
    files={};records=[]
    with tempfile.TemporaryDirectory() as tmp:
        mount=Path(tmp)
        for name,row in manifest['files'].items():
            raw=(tokenizer_folder/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
            (mount/name).write_bytes(raw);files[name]=row['sha256']
        for name,digest in PINNED_PROCESSOR.items():
            raw=(processor_folder/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
            (mount/name).write_bytes(raw);files[name]=digest
        tokenizer=AutoTokenizer.from_pretrained(mount,local_files_only=True,trust_remote_code=False)
        processor=AutoProcessor.from_pretrained(mount,local_files_only=True,trust_remote_code=False)
        assert type(processor).__name__=='Qwen3VLProcessor'
        assert type(processor.image_processor).__name__=='Qwen2VLImageProcessorFast'
        calls=[]
        class RecordingProcessor:
            image_processor=processor.image_processor
            def __call__(self,**kwargs):
                assert kwargs['return_tensors']=='pt'
                value=processor(**kwargs)
                assert all(v.device.type=='cpu' for v in value.values() if hasattr(v,'device'))
                calls.append(kwargs['return_tensors']);return value
        class HistoricalNumpy:
            image_processor=processor.image_processor
            def __call__(self,**kwargs):
                kwargs['return_tensors']='np';return processor(**kwargs)
        transport=[]
        for row in load_cases():
            result=expected_prompt(tokenizer,RecordingProcessor(),row['request'])
            if 'image' in row:
                a=row['image']['provisional_arithmetic']
                assert result['input_width']==row['image']['input_width'] and result['input_height']==row['image']['input_height']
                assert result['image_grid_thw']==a['grid_thw']
                assert result['processed_width']==a['processed_width'] and result['processed_height']==a['processed_height']
                assert result['patch_size']==16 and result['merge_size']==2
                assert result['processor_full_prompt_tokens']==result['manual_prompt_tokens']==result['expected_prompt_tokens']
                try:audited_probe(tokenizer,HistoricalNumpy(),row['request'],transport.append)
                except ResponseValidationError as exc:
                    audit=exc.response_evidence['audit']
                    assert audit['failure_kind']=='processor_execution_failure'
                    assert audit['failure_stage']=='processor_execution' and audit['exception_type']=='ValueError'
                    assert audit['transport_attempted'] is False and 'server_prompt_tokens' not in audit
                    assert 'Only returning PyTorch tensors' in str(exc)
                else:raise AssertionError('historical NumPy path unexpectedly succeeded')
            records.append({'probe_id':row['probe_id'],'request_sha256':row['request_sha256'],**result})
        assert calls==['pt']*3 and transport==[]
    return {'passed':True,'versions':versions,'python':sys.version.split()[0],'platform':sys.platform,
        'processor_class':'Qwen3VLProcessor','image_processor_class':'Qwen2VLImageProcessorFast',
        'revision':manifest['revision'],'file_hashes':files,'cases':records,
        'historical_numpy_failure_reproduced_all_images':True,'processor_calls_on_cpu':True,
        'image_server_dispatches':0,'model_calls':0,'gpu_runs':0,
        'limitation':'Pinned processor API and image accounting on CPU; not target Python/CUDA or vLLM compatibility.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path);p.add_argument('--processor',type=Path)
    p.add_argument('--archive',type=Path,default=ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip')
    args=p.parse_args()
    if args.tokenizer or args.processor:
        if not (args.tokenizer and args.processor):p.error('both local folders are required')
        result=run(args.tokenizer,args.processor)
    else:
        from certification.phase4_multimodal_preflight_v3.service import PINNED_PROCESSOR
        manifest=json.loads((ROOT/'certification/phase4_multimodal_preflight_v3/tokenizer_manifest.json').read_bytes())
        names=set(manifest['files'])|set(PINNED_PROCESSOR)
        with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(args.archive) as z:
            assert set(z.namelist())==names and len(z.namelist())==len(names)
            for name in sorted(names):(Path(tmp)/name).write_bytes(z.read(name))
            result=run(Path(tmp),Path(tmp))
        result['portable_inputs_sha256']=hashlib.sha256(args.archive.read_bytes()).hexdigest()
    (ROOT/'reports/phase4_multimodal_preflight_v3_processor_audit.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result,indent=2))
