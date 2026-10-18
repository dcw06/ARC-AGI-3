"""Pinned native CPU token audit of prepared fixtures; no model weights or inference."""
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
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.model_io import TokenAudit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--draft-lock-pin', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    def offline(*a, **kw):
        raise PermissionError('native CPU audit forbids networking')
    socket.socket.connect = socket.create_connection = offline
    if sha(args.inputs/'draft-lock.json') != args.draft_lock_pin:
        raise ValueError('draft lock differs')
    lock = json.loads((args.inputs/'draft-lock.json').read_bytes())
    if sha(args.inputs/'manifest.json') != lock['manifest_sha256']:
        raise ValueError('prepared manifest changed')
    for name, pin in lock['sources'].items():
        if sha(ROOT/name) != pin:
            raise ValueError('prepared source changed: '+name)
    import torch
    torch.set_num_threads(2)
    if metadata.version('transformers') != '4.57.6':
        raise ValueError('requires pinned Transformers 4.57.6')
    archive = ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if sha(archive) != 'af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
        raise ValueError('processor fixture differs')
    manifest = json.loads((args.inputs/'manifest.json').read_bytes())
    rows = []
    with tempfile.TemporaryDirectory(prefix='recent-feedback-CPU-tokens-') as folder:
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).name != name:
                    raise ValueError('unsafe processor member')
                (Path(folder)/name).write_bytes(bundle.read(name))
        native = TokenAudit(folder)
        for row in manifest['rows']:
            path = args.inputs/row['path']
            if sha(path) != row['sha256']:
                raise ValueError('prepared request changed')
            body = json.loads(path.read_bytes())
            count = native(body)
            rows.append({k: row[k] for k in ('case_id', 'step', 'variant', 'request_sha256')} |
                        {'native_prompt_tokens': count})
    pairs = {}
    for row in rows:
        pairs.setdefault((row['case_id'], row['step']), {})[row['variant']] = row['native_prompt_tokens']
    differences = [p['recent_summary']-p['recent_raw'] for p in pairs.values()]
    receipt = {'passed': True, 'draft_lock_sha256': args.draft_lock_pin, 'CPU_processor_calls': len(rows),
        'paired_contexts': len(pairs), 'rows': rows,
        'maximum_prompt_tokens_by_variant': {v: max(r['native_prompt_tokens'] for r in rows if r['variant'] == v)
                                            for v in ('recent_raw', 'recent_summary')},
        'summary_added_tokens_min': min(differences), 'summary_added_tokens_max': max(differences),
        'versions': {n: metadata.version(n) for n in ('transformers', 'torch', 'pillow')},
        'GPU_jobs': 0, 'model_generations': 0,
        'qualification': 'Retained contexts only, not a bound on future trajectories; live requests still need a frozen prospective token budget.'}
    write_new(args.output, receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
