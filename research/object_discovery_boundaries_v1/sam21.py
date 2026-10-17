"""SAM 2.1 retained-seed adapter. No weights, references or inference on import."""
import math
from .masks import MAX_OBJECTS,boundary,envelope,ordered,cells

MODEL='facebook/sam2.1-hiera-large'
REVISION='665f8e2ad61cf5f53d65644ff27c8ee525124610'
POLICY=dict(model=MODEL,revision=REVISION,condition='retained_molmopoint_seeds_sam21',
    image_size_wh=[448,448],board_size_wh=[64,64],cell_pixels=7,
    prompts='one original decoded pixel seed, positive label, per independent object',
    multimask_output=True,candidate_selection='highest SAM predicted IoU; earliest index on tie',
    original_resolution_logit_threshold=0.0,foreground_rule='strictly greater than threshold',
    board_projection='at least 25 of 49 pixels in each 7x7 block are foreground',
    hole_fill=False,sprinkle_removal=False,non_overlapping_constraints=False,
    negative_points=False,boxes=False,reference_input=False,duplicate_suppression=False,
    seed_snapping=False,mask_repair=False,invalid_molmopoint_response='skip with zero masks; never salvage partial points',
    advancement_verdict=None)


def point_prompts(points):
    """Preserve native MolmoPoint x/y floats; each seed is a separate object."""
    if type(points) is not list or len(points)>MAX_OBJECTS:raise ValueError('bounded seed list required')
    pixel=[]
    for p in points:
        xy=p.get('pixel_xy') if type(p) is dict else None
        if (type(xy) is not list or len(xy)!=2 or any(type(v) not in (int,float) or
                not math.isfinite(v) or not 0<=v<448 for v in xy)):
            raise ValueError('finite original-image pixel x/y required')
        if p.get('cell_xy')!=[math.floor(v/7) for v in xy]:raise ValueError('seed pixel/cell coordinates differ')
        pixel.append([[float(xy[0]),float(xy[1])]])
    return dict(input_points=[pixel],input_labels=[[[1] for _ in pixel]])


def select_candidate(scores):
    if (type(scores) is not list or len(scores)!=3 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in scores)):
        raise ValueError('three finite predicted-quality scores required')
    return max(range(3),key=lambda i:scores[i])


def mask_from_logits(logits):
    """Projection at original 448px resolution; no reference-based decisions."""
    if type(logits) is not list or len(logits)!=448 or any(type(r) is not list or len(r)!=448 for r in logits):
        raise ValueError('original 448x448 mask logits required')
    counts=[[0]*64 for _ in range(64)]
    for y,row in enumerate(logits):
        for x,v in enumerate(row):
            if type(v) not in (int,float) or not math.isfinite(v):raise ValueError('finite mask logits required')
            if v>0:counts[y//7][x//7]+=1
    return [[x,y] for y in range(64) for x in range(64) if counts[y][x]>=25]


def proposal(index,point,mask,quality_scores,selected):
    """Keep empty masks as explicit failed proposals; do not repair or hide them."""
    mask_set=cells(mask,empty=True)
    if type(index) is not int or not 1<=index<=MAX_OBJECTS:raise ValueError('proposal index required')
    point_prompts([point])
    if selected!=select_candidate(quality_scores):raise ValueError('mask candidate is not predicted-quality selection')
    return dict(id=f'candidate-{index:03d}',level='whole',parent_id=None,
        seed_cell=list(point['cell_xy']),seed_pixel_xy=list(point['pixel_xy']),cells=ordered(mask_set),
        bbox_xyxy=envelope(mask_set),boundary_cells=ordered(boundary(mask_set)),
        method='sam21_hiera_large_positive_seed',sam_predicted_quality=quality_scores,
        selected_candidate_index=selected,empty_mask=not mask_set,semantic_object_boundary_certified=False)
