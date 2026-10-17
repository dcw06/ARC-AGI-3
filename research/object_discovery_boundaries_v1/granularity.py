"""Reference-free segmentation conditions and shared board-mask conversion.

These are development comparisons, not an approved Kaggle launch package.
Each granularity is a separate condition; never choose a level using labels.
"""
import math

from .masks import MAX_OBJECTS, boundary, cells, envelope, ordered
from .sam21 import mask_from_logits, point_prompts

UNSAM_LEVELS = (0.1, 0.3, 0.5, 0.7, 0.9)
SEMANTIC_LEVELS = (1, 2, 3, 4, 5, 6)
# Upstream tasks/automatic_mask_generator.py::prompt_switch, not numeric order
# of the raw interactive decoder's six outputs.
SEMANTIC_CHANNEL = {1: 3, 2: 2, 3: 0, 4: 4, 5: 1, 6: 5}
MODELS = ('unsamv2', 'unsamv2_plus', 'semantic_sam_l')


def condition(model, mode, granularity):
    if model not in MODELS or mode not in ('seeded', 'automatic'):
        raise ValueError('explicit model and segmentation mode required')
    levels = SEMANTIC_LEVELS if model == 'semantic_sam_l' else UNSAM_LEVELS
    kind = int if model == 'semantic_sam_l' else float
    if type(granularity) is not kind or granularity not in levels:
        raise ValueError('granularity must be one of the declared separate conditions')
    return dict(model=model, mode=mode, granularity=granularity,
                image_size_wh=[448, 448], board_size_wh=[64, 64],
                semantic_resize_wh=[640, 640] if model == 'semantic_sam_l' else None,
                seeded_decoder_masks=6 if model == 'semantic_sam_l' else 1,
                semantic_backbone_preload=False,
                projection='25 of 49 pixels per original cell',
                max_scored_proposals=MAX_OBJECTS,
                automatic_selection='predicted quality descending; original index on tie',
                automatic_grid_side=16, automatic_point_batch=16,
                automatic_pred_iou_threshold=0.0, automatic_stability_threshold=0.0,
                automatic_box_nms_threshold=0.7, crop_layers=0,
                mask_repair=False, references_available_to_inference=False,
                refinement=False, select_best_granularity=False,
                advancement_verdict=None)


def levels(model):
    if model not in MODELS:
        raise ValueError('unknown model')
    return SEMANTIC_LEVELS if model == 'semantic_sam_l' else UNSAM_LEVELS


def normalized_semantic_point(point):
    point_prompts([point])
    return [[v / 448.0 for v in point['pixel_xy']]]


def ranked_indices(qualities, limit=MAX_OBJECTS):
    if (type(qualities) is not list or len(qualities) > 4096 or
            type(limit) is not int or not 1 <= limit <= MAX_OBJECTS or
            any(type(q) not in (float, int) or not math.isfinite(q) for q in qualities)):
        raise ValueError('bounded finite model qualities required')
    return sorted(range(len(qualities)), key=lambda i: (-qualities[i], i))[:limit]


def proposal(index, mask, *, source_index, quality, policy, point=None):
    condition(policy['model'], policy['mode'], policy['granularity'])
    if type(index) is not int or not 1 <= index <= MAX_OBJECTS:
        raise ValueError('bounded proposal index required')
    ranked_indices([quality])
    occupied = cells(mask, empty=True)
    result = dict(id=f'candidate-{index:03d}', level='whole', parent_id=None,
                  cells=ordered(occupied), bbox_xyxy=envelope(occupied),
                  boundary_cells=ordered(boundary(occupied)), empty_mask=not occupied,
                  method=policy['model'] + '_' + policy['mode'],
                  granularity=policy['granularity'], source_index=source_index,
                  predicted_quality=quality, semantic_object_boundary_certified=False)
    if point is not None:
        point_prompts([point])
        result.update(seed_cell=list(point['cell_xy']), seed_pixel_xy=list(point['pixel_xy']))
    return result


def project(binary_mask):
    """No hole filling, color filtering, snapping or reference-based repair."""
    if (type(binary_mask) is not list or len(binary_mask) != 448 or
            any(type(row) is not list or len(row) != 448 for row in binary_mask) or
            any(type(v) is not bool for row in binary_mask for v in row)):
        raise ValueError('448x448 boolean original-image mask required')
    return mask_from_logits([[1.0 if v else -1.0 for v in row] for row in binary_mask])


def assemble(raw, policy, points=None):
    """Convert raw original-frame masks. Retain empties and duplicate proposals.

    The caller must persist ALL raw proposals before this bounded selection.
    Automatic masks exceeding the common 96-proposal budget are explicitly
    reported as discarded; this is not recall over an unlimited mask pool.
    """
    expected = condition(policy['model'], policy['mode'], policy['granularity'])
    if policy != expected:
        raise ValueError('comparison policy drift')
    qualities = raw['qualities']
    indices = ranked_indices(qualities)
    masks = raw['masks']
    if len(masks) != len(qualities):
        raise ValueError('mask/quality cardinality differs')
    if policy['mode'] == 'seeded':
        point_prompts(points)
        if len(points) != len(masks):
            raise ValueError('one selected mask per retained seed required')
        indices = list(range(len(points)))
    elif points is not None:
        raise ValueError('automatic discovery does not consume MolmoPoint seeds')
    objects = [proposal(j, project(masks[i].tolist()), source_index=i,
                        quality=qualities[i], policy=policy,
                        point=points[i] if points is not None else None)
               for j, i in enumerate(indices, 1)]
    return dict(objects=objects, raw_proposal_count=len(masks),
                scored_proposal_count=len(objects), discarded_by_proposal_budget=len(masks)-len(objects),
                selected_raw_indices=indices)
