"""Prepare private plain-board pointing tasks; never install, load or launch."""
import hashlib
import json
from pathlib import Path

from certification.phase4_multimodal_preflight_v3.images import grid_from_png, png
from research.object_identification_v1.probe import verify
from scripts.serve_manual_strategy_worksheet import canonical, digest, private_directory
from .adapter import MODEL, REVISION


def prepare(source, output, targets):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('preserve earlier preparation')
    verify(source)
    references = json.loads((source/'references/answers.json').read_bytes())
    if len(references) != 6:
        raise ValueError('six retained boards required')
    target_raw = Path(targets).read_bytes()
    plan = json.loads(target_raw)
    if (plan.get('schema') != 'molmopoint_target_plan_v1' or len(plan.get('targets',[])) != 6
            or {r['case_id'] for r in plan['targets']} != {r['case_id'] for r in references}):
        raise ValueError('one explicit target query per retained board required')
    target_by_case = {r['case_id']:r for r in plan['targets']}
    files, requests, selected = {}, [], []
    for index, ref in enumerate(references,1):
        case = f'board-{index:02d}'
        if ref['case_id'] != case:
            raise ValueError('unexpected board order')
        name = 'inputs/'+case+'.png'
        original = (source/name).read_bytes()
        grid = grid_from_png(original,cell=8)
        if len(grid) != 64 or len(grid[0]) != 64 or digest(grid) != ref['grid_sha256']:
            raise ValueError('original board differs')
        image = png(grid,cell=7)
        if grid_from_png(image,cell=7) != grid:
            raise ValueError('nearest-neighbor cell preservation failed')
        target = target_by_case[case]
        regions = [r for r in ref['regions'] if r['id'] == target['target_region_id']]
        prompt = target['prompt']
        if len(regions) != 1 or type(prompt) is not str or not 1 <= len(prompt) <= 1000:
            raise ValueError('target reference/prompt missing or ambiguous')
        if set(target) != {'case_id','target_region_id','prompt'}:
            raise ValueError('unexpected target-plan fields')
        files[name] = image
        files['source-grids/'+case+'.json'] = canonical(grid)
        requests.append({'request_id':case+'.targeted_point','case_id':case,'task':'targeted_point','model':MODEL,
            'revision':REVISION,'image':name,'image_sha256':hashlib.sha256(image).hexdigest(),
            'original_image_size_wh':[448,448],'board_shape':[64,64],'cell_pixels':7,
            'prompt':prompt,'max_new_tokens':1024,'do_sample':False,'num_beams':1,
            'return_pointing_metadata':True,'native_logit_processor_required':True,'game_actions':0})
        selected.append({'case_id':case,'request_id':requests[-1]['request_id'],
            'target_region_id':target['target_region_id'],'prompt':prompt,
            'source_grid_sha256':ref['grid_sha256'],
            'reference_region_sha256':hashlib.sha256(canonical(regions[0])).hexdigest()})
    files['inputs/requests.jsonl'] = b''.join(canonical(r) for r in requests)
    files['references/answers.json'] = canonical(references)
    files['references/target-plan.json'] = target_raw
    files['references/selected-targets.json'] = canonical(selected)
    files['model_pin.json'] = Path(__file__).with_name('model_pin.json').read_bytes()
    sources = [Path(__file__),Path(__file__).with_name('adapter.py'),Path(__file__).with_name('scoring.py')]
    files['preparation.json'] = canonical({'status':'draft_inputs_and_adapter_only_no_live_package',
        'source_bundle_sha256':hashlib.sha256((source/'review-lock.json').read_bytes()).hexdigest(),
        'model':MODEL,'revision':REVISION,'cases':6,'proposed_generation_requests':6,
        'proposed_max_new_tokens_each':1024,'input_policy':'plain 448px full board; nearest-neighbor 7px cells; no overlay, margin or external crop',
        'task':'cued_single_object_localization_not_free_inventory',
        'target_plan_sha256':hashlib.sha256(target_raw).hexdigest(),
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
    return {'prepared':str(output),'cases':6,'proposed_requests':6,'actual_model_calls':0,
            'GPU_launches':0,'live_package_ready':False}
