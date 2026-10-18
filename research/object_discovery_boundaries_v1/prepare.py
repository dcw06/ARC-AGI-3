"""Prepare uncued discovery inputs and separate, unapproved reference review."""
import json
from pathlib import Path
from certification.phase4_multimodal_preflight_v3.images import grid_from_png
from research.molmopoint_identification_v1.adapter import MODEL,REVISION
from .reference_audit import audit,canonical,digest
from .prompts import LEGACY_PROFILE, select_prompt

PROMPT=('Point to each distinct visible whole object in this game image. '
        'Treat a composite object as one object, without also listing its internal parts. '
        'Include separate visible interface objects. Do not count background as an object.')
MAX_NEW_TOKENS=4096


def request_for(case,image,*,prompt_profile=LEGACY_PROFILE):
    grid=grid_from_png(image,cell=7)
    if len(grid)!=64 or any(len(row)!=64 for row in grid):raise ValueError('plain 448px board required')
    return dict(case_id=case,request_id=case+'.uncued_whole_inventory',task='uncued_whole_inventory',
        image='inputs/'+case+'.png',image_sha256=digest(image),grid_sha256=digest(canonical(grid)),
        model=MODEL,revision=REVISION,prompt=select_prompt(prompt_profile,PROMPT),max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,num_beams=1,original_image_size_wh=[448,448],board_shape=[64,64],cell_pixels=7,
        max_points=96,return_pointing_metadata=True,native_logit_processor_required=True,
        boundary_method='seed_color_component_4',game_actions=0)


def requests_for(inputs,*,prompt_profile=LEGACY_PROFILE):
    inputs=Path(inputs).resolve()
    expected_names={'requests.jsonl'}|{f'board-{i:02d}.png' for i in range(1,7)}
    if (any(p.is_symlink() for p in inputs.rglob('*'))
            or {p.relative_to(inputs).as_posix() for p in inputs.rglob('*') if p.is_file()}!=expected_names):
        raise ValueError('input inventory must contain only six boards and generic requests')
    expected=[request_for(f'board-{i:02d}',(inputs/f'board-{i:02d}.png').read_bytes(),prompt_profile=prompt_profile) for i in range(1,7)]
    actual=[json.loads(line) for line in (inputs/'requests.jsonl').read_bytes().splitlines()]
    if canonical(actual)!=canonical(expected):raise ValueError('uncued request contract differs')
    return expected


def prepare(source,output,*,prompt_profile=LEGACY_PROFILE):
    source,output=Path(source),Path(output)
    if output.exists():raise FileExistsError('preserve previous preparation/reviews')
    inspected=audit(source)
    refs=json.loads((source/'references/answers.json').read_bytes())
    if [r['case_id'] for r in refs]!=[f'board-{i:02d}' for i in range(1,7)]:
        raise ValueError('six frozen ordered boards required')
    files={};requests=[];frames=[]
    for ref in refs:
        case=ref['case_id'];grid=json.loads((source/'source-grids'/(case+'.json')).read_bytes())
        image=(source/'inputs'/(case+'.png')).read_bytes()
        if grid_from_png(image,cell=7)!=grid:raise ValueError('image/grid differ')
        files['inputs/'+case+'.png']=image
        requests.append(request_for(case,image,prompt_profile=prompt_profile))
        frames.append(dict(case_id=case,grid_sha256=ref['grid_sha256'],grid=grid,
            inventory_policy='Visible whole objects and separately labelled parts; backgrounds and ambiguous grouping require explicit review.',
            reference_exhaustive_confirmed=False,reviewer='',regions=[dict(id=r['id'],label=r['label'],
                parent_id=r['parent_id'],cells=r['target_points'],source_geometry=r['geometry'],
                source_region_sha256=digest(canonical(r)),mask_reviewed=False,disposition='include') for r in ref['regions']]))
    files['inputs/requests.jsonl']=b''.join(canonical(r) for r in requests)
    files['references/review-draft.json']=canonical(dict(schema='object_boundary_reference_review_v1',frames=frames,
        source_preparation_manifest_sha256=inspected['preparation_manifest_sha256'],
        qualification='Pending new boundary and exhaustive-inventory review; prior click-label review is not imported as approval.'))
    files['references/source-audit.json']=canonical(inspected)
    root=Path(__file__).resolve().parents[2]
    names=['research/object_discovery_boundaries_v1/'+name+'.py' for name in (
        '__init__','reference_audit','prepare','prompts','masks','decoding','scoring','evaluation','experiment')]+[
        'research/molmopoint_identification_v1/adapter.py','certification/phase4_multimodal_preflight_v3/images.py']
    files['protocol.json']=canonical(dict(schema='object_discovery_boundaries_preparation_v1',
        live_runs_enabled=False,approved=False,model=MODEL,revision=REVISION,condition='uncued_whole_inventory',
        proposed_generations=6,proposed_max_new_tokens_each=MAX_NEW_TOKENS,max_points_each=96,
        game_actions=0,scorecards=0,automatic_retries=0,provider_calls=0,reference_review_complete=False,
        passing_thresholds_frozen=False,GPU_package_ready=False,
        boundary_baseline='same-color 4-connected component from each predicted seed; keep duplicates/background',
        hierarchy='whole objects primary; parts/group assembly not implemented as a model condition',
        prompt=select_prompt(prompt_profile,PROMPT),prompt_profile=prompt_profile,
        source_sha256={name:digest((root/name).read_bytes()) for name in names}))
    output.mkdir(parents=True)
    for name,raw in files.items():
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    (output/'preparation-manifest.json').write_bytes(canonical({n:digest(v) for n,v in sorted(files.items())}))
    return dict(output=str(output),frames=6,reference_regions=inspected['summary']['regions'],
                model_calls=0,provider_calls=0,live_runs_enabled=False)
