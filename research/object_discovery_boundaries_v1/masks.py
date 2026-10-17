"""Strict board-cell masks and a transparent seed/color-component baseline."""
from .reference_audit import color_components,validate_grid

MAX_OBJECTS=96


def cells(value,*,empty=False):
    if (type(value) is not list or (not value and not empty) or len(value)>4096
            or any(type(p) is not list or len(p)!=2 or any(type(v) is not int or not 0<=v<64 for v in p) for p in value)):
        raise ValueError('strict bounded board-cell mask required')
    result={tuple(p) for p in value}
    if len(result)!=len(value): raise ValueError('duplicate cells in mask')
    return result


def ordered(value): return [[x,y] for x,y in sorted(value,key=lambda p:(p[1],p[0]))]


def boundary(value):
    return {p for p in value if any(q not in value for q in (
        (p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)))}


def envelope(value):
    if not value: return None
    return [min(x for x,y in value),min(y for x,y in value),max(x for x,y in value),max(y for x,y in value)]


def seed_masks(grid,points,*,level='whole'):
    """Use only visible pixels and predicted cells. Never accept a reference mask.

    Keep duplicates and background components; there is no oracle filtering,
    hole filling, color dropping, component merging or nearest-object snapping.
    """
    validate_grid(grid)
    if level not in ('whole','parts'): raise ValueError('declared hierarchy level required')
    if type(points) is not list or len(points)>MAX_OBJECTS: raise ValueError('bounded point inventory required')
    groups={p:group for group in color_components(grid) for p in group}
    result=[]
    for index,point in enumerate(points,1):
        if type(point) is not dict or 'cell_xy' not in point: raise ValueError('decoded cell point required')
        seed=cells([point['cell_xy']]).pop();mask=groups[seed]
        result.append(dict(id=f'candidate-{index:03d}',level=level,parent_id=None,
            seed_cell=list(seed),palette_index=grid[seed[1]][seed[0]],cells=ordered(mask),
            bbox_xyxy=envelope(mask),boundary_cells=ordered(boundary(mask)),
            method='seed_color_component_4',semantic_object_boundary_certified=False))
    return result


def validate_predictions(predictions):
    if type(predictions) is not list or len(predictions)>MAX_OBJECTS: raise ValueError('bounded mask inventory required')
    ids=[];result=[]
    for p in predictions:
        if type(p) is not dict or type(p.get('id')) is not str or not p['id'] or p.get('level') not in ('whole','parts'):
            raise ValueError('mask identity/level required')
        if 'empty_mask' in p and type(p['empty_mask']) is not bool:
            raise ValueError('empty-mask flag must be boolean')
        explicitly_empty=p.get('empty_mask') is True
        ids.append(p['id']);mask=cells(p['cells'],empty=explicitly_empty)
        if 'empty_mask' in p and p['empty_mask'] != (not mask):
            raise ValueError('empty-mask flag differs from occupied cells')
        if 'bbox_xyxy' in p and p['bbox_xyxy']!=envelope(mask): raise ValueError('mask envelope differs')
        if 'boundary_cells' in p and cells(p['boundary_cells'],empty=explicitly_empty)!=boundary(mask): raise ValueError('mask boundary differs')
        result.append(mask)
    if len(ids)!=len(set(ids)): raise ValueError('duplicate prediction IDs')
    return result
