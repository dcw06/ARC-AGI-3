"""Lazy upstream API adapters; importing this module never loads a checkpoint."""
from .granularity import condition, normalized_semantic_point, SEMANTIC_CHANNEL
from .sam21 import point_prompts


def automatic_options():
    return dict(points_per_side=16, points_per_batch=16, pred_iou_thresh=0.0,
                stability_score_thresh=0.0, stability_score_offset=1.0,
                box_nms_thresh=0.7, crop_n_layers=0, crop_nms_thresh=0.7,
                min_mask_region_area=0, output_mode='binary_mask')


def binary_original(masks, *, logits):
    """Raw logits: bilinear/zero threshold; already binary: nearest resize.

    Semantic-SAM's documented preprocessor enlarges the 448px source to 640px.
    Never interpret its 640px output directly as 448px coordinates.
    """
    import numpy as np
    import torch
    import torch.nn.functional as F
    masks = np.asarray(masks)
    if masks.ndim != 3 or masks.shape[-2:] not in ((448, 448), (640, 640)):
        raise ValueError('N original448 or Semantic640 masks required')
    if not np.isfinite(masks).all():
        raise ValueError('nonfinite masks')
    if not logits and masks.dtype != np.bool_:
        raise ValueError('automatic generator must return binary masks')
    if len(masks) == 0:
        return np.zeros((0, 448, 448), dtype=bool)
    values = torch.as_tensor(masks.copy(), dtype=torch.float32)[:, None]
    if masks.shape[-2:] != (448, 448):
        values = F.interpolate(values, size=(448, 448), mode='bilinear' if logits else 'nearest',
                               **({'align_corners': False} if logits else {}))
    return (values[:, 0] > (0.0 if logits else 0.5)).numpy()


def automatic_result(records, resolution):
    import numpy as np
    if not isinstance(records, list) or len(records) > 4096:
        raise ValueError('bounded upstream proposal inventory required')
    masks = np.stack([r['segmentation'] for r in records]) if records else np.zeros((0, resolution, resolution), dtype=bool)
    if masks.shape != (len(records), resolution, resolution):
        raise ValueError('automatic masks differ from declared image frame')
    qualities = [float(r['predicted_iou']) for r in records]
    return dict(masks=binary_original(masks, logits=False), qualities=qualities,
                raw_masks=masks, raw_qualities=np.asarray(qualities),
                metadata=[{k: r[k] for k in ('predicted_iou', 'stability_score', 'point_coords', 'crop_box', 'area')}
                          for r in records])


class UnSAMv2Backend:
    def __init__(self, model, predictor_factory, generator_factory, variant='unsamv2_plus'):
        self.model, self.variant = model, variant
        self.predictor_factory, self.generator_factory = predictor_factory, generator_factory

    def seeded(self, image, points, granularity):
        import numpy as np
        condition(self.variant, 'seeded', granularity)
        point_prompts(points)
        predictor = self.predictor_factory(self.model)
        predictor.set_image(image)
        raw_masks, raw_scores, raw_logits, selected = [], [], [], []
        for point in points:
            masks, scores, logits = predictor.predict(
                point_coords=np.asarray([point['pixel_xy']], dtype=np.float32),
                point_labels=np.asarray([1], dtype=np.int32), multimask_output=True,
                return_logits=True, gra=granularity)
            masks, scores, logits = np.asarray(masks), np.asarray(scores), np.asarray(logits)
            # MaskDecoderGra.forward returns the granularity mask alone, even
            # when multimask_output=True. Its SAM candidates stay internal.
            if (masks.shape != (1, 448, 448) or scores.shape != (1,) or
                    logits.shape != (1,256,256) or not np.isfinite(scores).all() or
                    not np.isfinite(logits).all()):
                raise ValueError('UnSAMv2 single granularity-mask response differs')
            raw_masks.append(masks); raw_scores.append(scores); raw_logits.append(logits)
            selected.append(0)
        if not points:
            return dict(masks=np.zeros((0,448,448), dtype=bool), qualities=[], metadata=[],
                        raw_masks=np.zeros((0,1,448,448)), raw_qualities=np.zeros((0,1)))
        chosen = np.stack([m[i] for m,i in zip(raw_masks, selected)])
        return dict(masks=binary_original(chosen, logits=True),
                    qualities=[float(s[i]) for s,i in zip(raw_scores,selected)],
                    raw_masks=np.stack(raw_masks), raw_qualities=np.stack(raw_scores),
                    raw_low_resolution_logits=np.stack(raw_logits), metadata=dict(selected_indices=selected))

    def automatic(self, image, granularity):
        condition(self.variant, 'automatic', granularity)
        generator = self.generator_factory(self.model, **automatic_options(), mask_threshold=0.0,
                                           use_m2m=False, multimask_output=True)
        return automatic_result(generator.generate(image, gra=granularity), 448)


class SemanticSAMBackend:
    def __init__(self, model, predictor_factory, generator_factory, image_tensor):
        self.model = model
        self.predictor_factory, self.generator_factory = predictor_factory, generator_factory
        self.image_tensor = image_tensor

    def seeded(self, image, points, granularity):
        import numpy as np
        condition('semantic_sam_l', 'seeded', granularity)
        point_prompts(points)
        original, tensor = self.image_tensor(image)
        predictor = self.predictor_factory(self.model)
        raw_masks, raw_scores = [], []
        for point in points:
            # predict(), NOT predict_masks(): the latter returns rendered PIL
            # visualizations after thresholding, deduplication and mask repair.
            masks, scores = predictor.predict(original, tensor, point=normalized_semantic_point(point))
            masks = masks.detach().float().cpu().numpy()
            scores = scores.detach().float().cpu().numpy()
            if masks.shape != (6,640,640) or scores.shape != (1,1,6) or not np.isfinite(scores).all():
                raise ValueError('Semantic-SAM six-channel raw response differs')
            raw_masks.append(masks); raw_scores.append(scores[0,0])
        channel = SEMANTIC_CHANNEL[granularity]
        if not points:
            return dict(masks=np.zeros((0,448,448), dtype=bool), qualities=[], metadata=[],
                        raw_masks=np.zeros((0,6,640,640)), raw_qualities=np.zeros((0,6)))
        return dict(masks=binary_original(np.stack([m[channel] for m in raw_masks]), logits=True),
                    qualities=[float(s[channel]) for s in raw_scores],
                    raw_masks=np.stack(raw_masks), raw_qualities=np.stack(raw_scores),
                    metadata=dict(raw_channel=channel, normalized_seed_points=[normalized_semantic_point(p) for p in points]))

    def automatic(self, image, granularity):
        condition('semantic_sam_l', 'automatic', granularity)
        _, tensor = self.image_tensor(image)
        generator = self.generator_factory(self.model, **automatic_options(), level=[granularity])
        return automatic_result(generator.generate(tensor), 640)
