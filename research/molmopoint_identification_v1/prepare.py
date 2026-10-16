"""Prepare private plain-board pointing tasks; never install, load or launch."""
import hashlib
import json
from pathlib import Path

from certification.phase4_multimodal_preflight_v3.images import grid_from_png
from research.object_identification_v1.probe import verify
from scripts.serve_manual_strategy_worksheet import canonical, digest, private_directory
from .adapter import MODEL, REVISION, PROMPTS


def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('preserve earlier preparation')
    verify(source)
    references = json.loads((source/'references/answers.json').read_bytes())
    if len(references) != 6:
        raise ValueError('six retained boards required')
    files, requests = {}, []
    for index, ref in enumerate(references,1):
        case = f'board-{index:02d}'
        if ref['case_id'] != case:
            raise ValueError('unexpected board order')
        name = 'inputs/'+case+'.png'
        image = (source/name).read_bytes()
        grid = grid_from_png(image,cell=8)
        if len(grid) != 64 or len(grid[0]) != 64 or digest(grid) != ref['grid_sha256']:
            raise ValueError('original board differs')
        files[name] = image
        for task, prompt in PROMPTS.items():
            requests.append({'request_id':case+'.'+task,'case_id':case,'task':task,'model':MODEL,
                'revision':REVISION,'image':name,'image_sha256':hashlib.sha256(image).hexdigest(),
                'original_image_size_wh':[512,512],'prompt':prompt,'max_new_tokens':1024,
                'do_sample':False,'num_beams':1,'return_pointing_metadata':True,
                'native_logit_processor_required':True,'game_actions':0})
    files['inputs/requests.jsonl'] = b''.join(canonical(r) for r in requests)
    files['references/answers.json'] = canonical(references)
    files['model_pin.json'] = Path(__file__).with_name('model_pin.json').read_bytes()
    sources = [Path(__file__),Path(__file__).with_name('adapter.py'),Path(__file__).with_name('scoring.py')]
    files['preparation.json'] = canonical({'status':'draft_inputs_and_adapter_only_no_live_package',
        'source_bundle_sha256':hashlib.sha256((source/'review-lock.json').read_bytes()).hexdigest(),
        'model':MODEL,'revision':REVISION,'cases':6,'proposed_generation_requests':12,
        'proposed_max_new_tokens_each':1024,'input_policy':'original plain 512px boards; no pending grid aid',
        'references_never_mounted_with_model':True,'weights_downloaded':False,'model_calls':0,
        'game_actions':0,'provider_calls':0,'live_runs_enabled':False,'authority':None,
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}})
    private_directory(output)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    manifest = {name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(files.items())}
    with (output/'preparation-manifest.json').open('xb') as stream:
        stream.write(canonical(manifest))
    return {'prepared':str(output),'cases':6,'proposed_requests':12,'actual_model_calls':0,
            'GPU_launches':0,'live_package_ready':False}
