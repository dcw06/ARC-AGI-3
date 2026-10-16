"""Audit existing click/region labels without promoting them to segmentation truth.

Color components are pixel fragments, never automatically semantic objects.
This module has no model, network, engine or provider dependency.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_grid(grid):
    if (type(grid) is not list or len(grid)!=64 or any(type(row) is not list or len(row)!=64 for row in grid)
            or any(type(v) is not int or not 0<=v<16 for row in grid for v in row)):
        raise ValueError('64x64 integer ARC palette grid required')


def connected_sets(cells):
    remaining=set(cells); groups=[]
    while remaining:
        start=min(remaining,key=lambda p:(p[1],p[0])); remaining.remove(start)
        group={start}; todo=[start]
        while todo:
            x,y=todo.pop()
            for other in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if other in remaining:
                    remaining.remove(other);group.add(other);todo.append(other)
        groups.append(group)
    return groups


def color_components(grid):
    validate_grid(grid)
    colors={v for row in grid for v in row}
    return [group for color in sorted(colors)
            for group in connected_sets((x,y) for y,row in enumerate(grid) for x,v in enumerate(row) if v==color)]


def audit_case(reference,grid):
    validate_grid(grid)
    grid_pin=digest(canonical(grid))
    if reference['grid_sha256']!=grid_pin:
        raise ValueError('reference grid binding differs')
    regions=reference['regions']; ids=[r['id'] for r in regions]
    if len(ids)!=len(set(ids)):
        raise ValueError('duplicate reference IDs')
    by_id={r['id']:r for r in regions}
    component_by_cell={cell:group for group in color_components(grid) for cell in group}
    rows=[]; masks={}
    for r in regions:
        points=r['target_points']
        if (type(points) is not list or not points or any(type(p) is not list or len(p)!=2
                or any(type(v) is not int or not 0<=v<64 for v in p) for p in points)):
            raise ValueError('strict nonempty occupied-cell coordinates required')
        cells={tuple(p) for p in points}; masks[r['id']]=cells
        if len(cells)!=len(points): raise ValueError('duplicate occupied cells')
        bbox=[min(x for x,y in cells),min(y for x,y in cells),max(x for x,y in cells),max(y for x,y in cells)]
        if r['grid_sha256']!=grid_pin or r['bbox_xyxy']!=bbox:
            raise ValueError('region grid/bounding envelope differs')
        if r['geometry'] not in ('rectangle','mask','group'):
            raise ValueError('unknown reference geometry')
        parent=r['parent_id']
        if parent is not None and (parent not in by_id or parent==r['id']):
            raise ValueError('invalid reference parent')
        seen={r['id']}; ancestor=parent
        while ancestor is not None:
            if ancestor in seen: raise ValueError('cyclic reference hierarchy')
            seen.add(ancestor)
            if ancestor not in by_id: raise ValueError('missing ancestor')
            ancestor=by_id[ancestor]['parent_id']
        colors=Counter(grid[y][x] for x,y in cells)
        rectangle_area=(bbox[2]-bbox[0]+1)*(bbox[3]-bbox[1]+1)
        border={p for p in cells if any(q not in cells for q in (
            (p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)))}
        rows.append(dict(id=r['id'],parent_id=parent,geometry=r['geometry'],cells=len(cells),
            fills_bounding_rectangle=len(cells)==rectangle_area,colors=len(colors),
            four_connected_parts=len(connected_sets(cells)),boundary_cells=len(border),
            same_color_component_exact=any(component_by_cell[p]==cells for p in cells),
            boundary_truth_status=({'rectangle':'region_envelope_requires_mask_review',
                'mask':'explicit_cells_require_semantic_review',
                'group':'group_cells_require_membership_and_boundary_review'}[r['geometry']])))
    identical_siblings=[]
    for i,r in enumerate(regions):
        for other in regions[i+1:]:
            if r['parent_id']==other['parent_id'] and masks[r['id']]==masks[other['id']]:
                identical_siblings.append([r['id'],other['id']])
    return dict(case_id=reference['case_id'],grid_sha256=grid_pin,regions=rows,
        whole_regions=sum(r['parent_id'] is None for r in regions),
        parts=sum(r['parent_id'] is not None for r in regions),
        identical_sibling_masks_for_review=identical_siblings,
        reference_exhaustiveness_verified=False,independent_mask_review_verified=False,
        eligible_for_discovery_precision=False,eligible_for_boundary_pass_verdict=False)


def audit(preparation):
    preparation=Path(preparation).resolve()
    manifest=json.loads((preparation/'preparation-manifest.json').read_bytes())
    for name,pin in manifest.items():
        p=preparation/name
        if p.is_symlink() or not p.resolve().is_relative_to(preparation) or digest(p.read_bytes())!=pin:
            raise ValueError('prepared artifact changed: '+name)
    refs=json.loads((preparation/'references/answers.json').read_bytes())
    if len({r['case_id'] for r in refs})!=len(refs): raise ValueError('duplicate case IDs')
    for name in ['references/answers.json']+['source-grids/'+r['case_id']+'.json' for r in refs]:
        if name not in manifest: raise ValueError('unbound reference/grid: '+name)
    cases=[audit_case(r,json.loads((preparation/'source-grids'/(r['case_id']+'.json')).read_bytes())) for r in refs]
    rows=[r for c in cases for r in c['regions']]
    return dict(schema='object_boundary_reference_audit_v1',
        preparation_manifest_sha256=digest((preparation/'preparation-manifest.json').read_bytes()),cases=cases,
        summary=dict(frames=len(cases),regions=len(rows),whole_regions=sum(c['whole_regions'] for c in cases),
            parts=sum(c['parts'] for c in cases),
            rectangle_labels=sum(r['geometry']=='rectangle' for r in rows),
            explicit_cell_masks=sum(r['geometry']=='mask' for r in rows),
            grouped_regions=sum(r['geometry']=='group' for r in rows),
            multicolor_regions=sum(r['colors']>1 for r in rows),
            exact_single_color_components=sum(r['same_color_component_exact'] for r in rows),
            identical_sibling_mask_pairs=sum(len(c['identical_sibling_masks_for_review']) for c in cases),
            references_verified_exhaustive=False,boundary_truth_review_complete=False),
        model_calls=0,game_actions=0,provider_calls=0,
        qualification='Click-region coordinates and connected color fragments do not by themselves establish semantic object boundaries or exhaustive inventories.')
