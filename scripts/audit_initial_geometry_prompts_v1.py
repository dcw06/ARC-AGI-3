"""Offline native Qwen processor audit; no weights, server or inference."""
import argparse
import base64
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import zipfile

os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.initial_geometry_assistance_v1.geometry import canonical
from research.initial_geometry_assistance_v1.policy import request_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    def no_network(*a, **kw):
        raise PermissionError('native CPU prompt audit: network forbidden')
    socket.socket.connect = socket.create_connection = no_network
    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoTokenizer
    torch.set_num_threads(2)
    if importlib.metadata.version('transformers') != '4.57.6':
        raise ValueError('pinned transformers differs')
    archive = ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != 'af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
        raise ValueError('pinned processor archive differs')
    manifest_raw = (args.inputs/'manifest.json').read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != args.manifest_sha256:
        raise ValueError('input manifest differs')
    manifest = json.loads(manifest_raw)
    raw = (args.inputs/'cases.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['files']['cases.json']:
        raise ValueError('cases differ')
    cases = json.loads(raw)['cases']
    protocol_raw = (ROOT/'research/initial_geometry_assistance_v1/protocol.json').read_bytes()
    if hashlib.sha256(protocol_raw).hexdigest() != manifest['protocol_sha256']:
        raise ValueError('protocol changed since preparation')
    protocol = json.loads(protocol_raw)
    tok_manifest = json.loads((ROOT/'certification/phase4_multimodal_preflight_v3/tokenizer_manifest.json').read_bytes())
    pins = {name: info['sha256'] for name, info in tok_manifest['files'].items()}
    pins.update({'preprocessor_config.json': '6a970fd06f30e6943b3e2c14d5d3b42d49b06cf99b99103d56689bef462d90f8',
                 'video_preprocessor_config.json': 'e203bc065dfcd75226838b8e937d624bec8f0eb6ef6630a397e9a675f2873ea6'})
    records = []
    with tempfile.TemporaryDirectory(prefix='initial-geometry-processor-') as folder, zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(pins) or len(bundle.namelist()) != len(pins):
            raise ValueError('processor inventory differs')
        for name, pin in pins.items():
            raw = bundle.read(name)
            if hashlib.sha256(raw).hexdigest() != pin or Path(name).name != name:
                raise ValueError('processor file differs')
            (Path(folder)/name).write_bytes(raw)
        tokenizer = AutoTokenizer.from_pretrained(folder, local_files_only=True, trust_remote_code=False)
        processor = AutoProcessor.from_pretrained(folder, local_files_only=True, trust_remote_code=False)
        if type(processor).__name__ != 'Qwen3VLProcessor':
            raise ValueError('unexpected processor class')
        for case in cases:
            obs = {'grid': case['grid'], 'state': 'NOT_FINISHED', 'levels_completed': 0, 'legal_actions': [1, 6]}
            for step in (0, 23):
                history = [{'step': i, 'before': obs, 'after': obs,
                            'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}} for i in range(step)]
                for arm in case['order']:
                    request = request_for(obs, case['geometry'][arm], obs, history, step, protocol['policy']['model'])
                    kwargs = request['chat_template_kwargs']
                    ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True, truncation=False, **kwargs)
                    text = tokenizer.apply_chat_template(request['messages'], tokenize=False, add_generation_prompt=True, **kwargs)
                    images = []
                    for part in request['messages'][1]['content']:
                        if part['type'] == 'image_url':
                            image = Image.open(io.BytesIO(base64.b64decode(part['image_url']['url'].split(',')[1])))
                            image.load()
                            if image.size != (448, 448):
                                raise ValueError('image geometry differs')
                            images.append(image.convert('RGB'))
                    full = processor(text=[text], images=images, return_tensors='pt')
                    grids = [[int(v) for v in row] for row in full['image_grid_thw']]
                    placeholders = ids.count(tokenizer.convert_tokens_to_ids('<|image_pad|>'))
                    merge = int(processor.image_processor.merge_size)
                    manual = len(ids)-placeholders+sum(t*h*w//(merge*merge) for t, h, w in grids)
                    actual = len(full['input_ids'][0])
                    if placeholders != len(images) or len(grids) != len(images) or manual != actual or actual+256 > 32768:
                        raise ValueError('native multimodal token accounting differs')
                    if any(v.device.type != 'cpu' for v in full.values() if hasattr(v, 'device')):
                        raise ValueError('unexpected accelerator tensor')
                    records.append({'case_id': case['case_id'], 'arm': arm, 'step': step, 'images': len(images),
                                    'image_grid_thw': grids, 'template_tokens': len(ids), 'manual_tokens': manual,
                                    'native_processor_tokens': actual, 'request_sha256': hashlib.sha256(canonical(request)).hexdigest()})
    receipt = {'schema': 'initial_geometry_native_CPU_prompt_audit_v1', 'passed': True,
               'input_manifest_sha256': args.manifest_sha256, 'model_revision': tok_manifest['revision'],
               'versions': {n: importlib.metadata.version(n) for n in ('torch', 'torchvision', 'transformers', 'pillow')},
               'CPU_processor_calls': len(records), 'maximum_native_prompt_tokens': max(r['native_processor_tokens'] for r in records),
               'required_server_limit_mm_per_prompt_images': 6, 'records': records,
               'model_generations': 0, 'GPU_jobs': 0,
               'qualification': 'Synthetic repeated-image histories test multi-image API and token counts; actual future trajectories are not yet generated. Each live request still needs native/server count validation.'}
    with args.output.open('xb') as stream:
        stream.write(canonical(receipt))
    print(json.dumps({k: v for k, v in receipt.items() if k != 'records'}))


if __name__ == '__main__':
    main()
