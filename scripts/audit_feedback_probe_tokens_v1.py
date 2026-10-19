"""Pinned CPU processor audit of sealed diagnostic inputs or scripted transport."""
import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.model_io import TokenAudit
from research.feedback_probe_v1.preparation import verify_prepared
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True); parser.add_argument('--draft-pin', required=True)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--transport', type=Path)
    args = parser.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    def offline(*a, **k): raise PermissionError('CPU audit networking forbidden')
    socket.socket.connect = socket.create_connection = offline
    prepared = verify_prepared(args.inputs, args.draft_pin, ROOT)
    if metadata.version('transformers') != '4.57.6': raise ValueError('pinned Transformers differs')
    import torch
    torch.set_num_threads(2)
    rows = [{'id': r['checkpoint_id']+'/'+r['kind'], 'body': json.loads((args.inputs/r['path']).read_bytes())}
            for r in prepared['model_input_rows']]
    if args.transport:
        rows = [e for e in (json.loads(x) for x in args.transport.read_text().splitlines()) if e['kind'] == 'request']
    archive = ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if sha(archive) != 'af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1': raise ValueError('processor bytes differ')
    counted = []
    with tempfile.TemporaryDirectory(prefix='feedback-probe-native-') as folder:
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).name != name: raise ValueError('unsafe processor file')
                (Path(folder)/name).write_bytes(bundle.read(name))
        native = TokenAudit(folder)
        for row in rows:
            count = native(row['body'])
            if not 0 < count <= 8192 or ('native_prompt_tokens' in row and count != row['native_prompt_tokens']):
                raise ValueError('native token mismatch or budget exceeded')
            counted.append({'id': row['id'], 'prompt_tokens': count, 'request_sha256': digest(row['body'])})
    write_new(args.output, {'passed': True, 'draft_lock_sha256': args.draft_pin, 'CPU_processor_calls': len(counted),
        'rows': counted, 'maximum_prompt_tokens': max(r['prompt_tokens'] for r in counted),
        'transport_sha256': sha(args.transport) if args.transport else None,
        'versions': {n: metadata.version(n) for n in ('transformers', 'torch', 'pillow')},
        'GPU_jobs': 0, 'neural_model_generations': 0,
        'qualification': 'Prepared/scripted contexts only; future real requests require prospective token admission checks.'})
    print(json.dumps({'passed': True, 'CPU_processor_calls': len(counted), 'max_prompt_tokens': max(r['prompt_tokens'] for r in counted)}))
