# SAM 2.1 Hiera-Large: retained MolmoPoint seed comparison

**October 17 audit:** [board binding, independent raw replay and frozen-reference rescoring](granularity_evaluation_integrity_fixes_2026-10-17.md)
pass for the retained evidence. The 12/37 and 6/37 SAM totals are unchanged under
the integrated owner scoring policy. The reference freeze is retrospective;
historical packages and evaluations remain preserved.

October 16, 2026. **SAM 2.1 improved mask extraction with the same retained
MolmoPoint seeds:** 12/37 reviewed whole objects match at IoU ≥ 0.5, versus
7/37 for same-color components. Exact masks improved from 3/37 to 6/37.
This is a completed local CPU segmentation test, not a new Kaggle GPU run.

| Measure | Same-color components | SAM 2.1 Hiera-Large |
|---|---:|---:|
| Fixed valid MolmoPoint seeds | 22 | 22 |
| Whole-object mask matches, IoU ≥ 0.5 | 7/37 | 12/37 |
| Mask recall over all reviewed whole objects | 18.9% | 32.4% |
| Precision over all 22 seed proposals | 31.8% | 54.5% |
| Exact masks | 3/37 (8.1%) | 6/37 (16.2%) |
| Matched IoU sum / all 37 reference objects | 0.170 | 0.282 |
| Boundary F1 sum / all 37 reference objects | 0.160 | 0.285 |

| Initial board | Reviewed whole objects | Fixed valid seeds | Component matches | SAM matches | Component exact | SAM exact |
|---|---:|---:|---:|---:|---:|---:|
| ls20 | 3 | 0 | 0 | 0 | 0 | 0 |
| s5i5 | 7 | 6 | 2 | 4 | 0 | 2 |
| cd82 | 5 | 5 | 2 | 3 | 1 | 1 |
| ft09 | 6 | 2 | 0 | 0 | 0 | 0 |
| ka59 | 10 | 6 | 2 | 3 | 1 | 1 |
| sc25 | 6 | 3 | 1 | 2 | 1 | 2 |
| **Total** | **37** | **22** | **7** | **12** | **3** | **6** |

ls20's original MolmoPoint output was invalid and length-limited. Its partial
points were not reused; it receives zero masks from both methods and remains
in the all-board denominators. All 22 valid seeds produced nonempty SAM masks.
The 57 reviewed parts are not combined with the whole-object score.

## Fixed comparison

Only mask extraction changed. The five valid boards, original floating-point
MolmoPoint pixel coordinates, image bytes, reference masks, whole/part
granularity, one-to-one IoU 0.5 matching and invalid-response handling were
unchanged. No new MolmoPoint generations were made. The model checkpoint is
[`facebook/sam2.1-hiera-large`](https://huggingface.co/facebook/sam2.1-hiera-large),
pinned at revision `665f8e2ad61cf5f53d65644ff27c8ee525124610`.
The [model card's image workflow](https://huggingface.co/facebook/sam2.1-hiera-large/blob/665f8e2ad61cf5f53d65644ff27c8ee525124610/README.md)
documents positive point prompts and multiple candidate masks.

Before SAM inference, the following policy was saved and hashed:

- One original positive pixel seed per independently prompted object. Other
  seeds are not treated as negatives. No boxes, corrective clicks or mask input.
- Preserve the external plain 448×448 image; SAM's pinned processor resizes
  internally to 1024×1024 and scales the original x/y coordinates accordingly.
- Ask for three candidate masks; choose the highest SAM-predicted quality,
  with the earliest candidate index resolving ties. Never choose by ground-truth IoU.
- Upsample logits to the original 448×448 size, threshold strictly above zero,
  then include a board cell when at least 25 of its 49 image pixels are foreground.
- No hole filling, small-component removal, cross-mask exclusion, reference-based
  repair, seed snapping or duplicate suppression. Retain failed/empty proposals
  explicitly; none were empty in this run.

The same-color baseline results were retained, not recomputed with revised
rules. Human masks were unavailable to the inference runner. The independent
evaluator subsequently compared both methods against the exact unchanged owner
reference, SHA256 `5304e35b1f0ee17e0ffd77293ac4fba260bbfa08755c2d48e914ed72ac9cec63`.
The comparison was designed after inspecting the baseline failure, so it is
development evidence rather than a held-out confirmation or model-superiority claim.

## Runtime and verification

| Item | Recorded result |
|---|---|
| Checkpoint | Safetensors, 897,897,416 bytes; SHA256 matched upstream LFS metadata |
| Weight SHA256 | `dc407dce21301fd94abb395c5099b4f2c455fdc8a8f261ac3d0ea6d4cd197230` |
| Config/processor files | Pinned Git-blob hashes and retained SHA256 verified |
| Loading | Explicit `Sam2Model` / `Sam2Processor`, local files only, no remote code; no reported missing, mismatched, unexpected keys or loading errors |
| Config qualification | Upstream config identifies `sam2_video`; the documented image classes were used, and the type warning is retained |
| CPU runtime | Transformers 4.57.1, Torch 2.10.0+cpu, FP32, four threads; 216,924,865 image-model parameters |
| Inference | Five image forwards with batched independent objects; 22 seed segmentations |
| Successful CPU lifecycle | 104.247 seconds through the post-receipt witness; 1,200-second bound |
| Raw evidence | All three low-resolution mask logits and quality scores retained for every seed before mask selection/projection |
| Independent replay | Rebuilt original-size logits, quality argmax and board-cell masks from saved arrays; exact agreement with every reported mask |
| Network during inference/replay | Disabled; zero attempted connections recorded |
| New GPU jobs / MolmoPoint calls / game actions | Zero / zero / zero |
| Local failed attempt | First wrapper stopped before segmentation due to calling `.eval()` on the loading-info tuple; preserved unchanged, then corrected |

This CPU result does not validate CUDA performance, Kaggle packaging or a new
GPU runtime. The original MolmoPoint attempt and its provider notebook-identity
warning remain unchanged. No existing approval or deployment lock was rewritten.

## Interpretation

SAM is a better tested extractor for these fixed seeds, but recovery is still
incomplete: 12/37 matches and 6/37 exact masks are not reliable full-object
segmentation. ft09 remains at zero matches. The reference hierarchy is one
owner's adopted inventory; a mask that differs from it may reflect granularity
ambiguity as well as a segmentation error.

SAM cannot supply objects that MolmoPoint never seeded. This experiment does
not improve object discovery, label semantic roles, prove collision boundaries,
execute controls or solve a level. Keep the component baseline and treat SAM
as a separate tested extractor condition. Later prompts, extra negatives,
grouping rules or reference changes need separate revisions.

The private independent comparison SHA256 is `3d9af9be30c1c3e44a4539749f2fdae4da694dbd2c6124c2009ebcd7e5d7eb8d`.
Raw masks, seed coordinates and the interactive reference/component/SAM viewer
remain git-ignored. Source: [adapter](../research/object_discovery_boundaries_v1/sam21.py),
[CPU runner](../scripts/run_sam21_retained_seeds.py),
[pinned file hashes](../research/object_discovery_boundaries_v1/sam21_model_pin.json).

## Subsequent scoring integration correction

The shared scorer originally rejected empty SAM proposals despite the adapter
marking them as failures. The [integration fix](sam21_empty_mask_scoring_fix_2026-10-16.md)
now retains explicitly marked empties in the proposal denominator without
crediting a match. All 22 masks in this reported run were nonempty. Re-scoring
the retained masks in the original Linux/Python 3.12 environment yields
identical SAM and baseline score dictionaries for every frame; the results
above and their original receipts remain unchanged.
