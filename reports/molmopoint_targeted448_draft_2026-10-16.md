# First MolmoPoint test: plain 448-by-448 targeted pointing

October 16, 2026. The owner selected **448-by-448 nearest-neighbor board images,
with no visible grid overlay**. This supersedes the initial 512px generic-inventory
draft for the first test. All earlier drafts, results and consumed attempts remain
preserved. No model answers, uploads or GPU jobs were produced by this revision.

| Setting | Selected input draft |
|---|---|
| Model | `allenai/MolmoPoint-8B`, revision `188130f961c8e0888a34e11121a1423c461a01ba` |
| Source boards | The six retained first-level initial frames; original 64-by-64 colour arrays preserved and hash-checked |
| Supplied image | 448 by 448, exact nearest-neighbor enlargement: each original cell is a uniform 7-by-7 pixel block |
| Overlays | No grid lines, labels, margins or external crops |
| Task | One predeclared visual target per frame; a short "Point to the center of ..." prompt |
| Prompt specificity | Frame-specific appearance descriptions; small-blue-square wording is used only where it identifies the intended target. Disambiguating relative descriptions are retained privately |
| Proposed calls | Six separate generations, at most 1,024 new tokens each; zero game actions, no automatic retries |
| Native pointing | Require `return_pointing_metadata=True`, original image dimensions, native logit processor and `extract_image_points(...)` |
| Cell conversion | Validate the decoded original-image point first, then `x = floor(px / 7)` and `y = floor(py / 7)` |
| Primary measure | Whether the single decoded point lands in the predeclared target's labelled occupied-cell set |
| Invalid answers | Out-of-bounds/nonfinite pixel points, unfinished outputs and multi-point answers to single-target prompts remain invalid; no clamping, repair or target substitution |
| No detection | Retain an empty point output as no detection, a target miss |
| References | Expected target IDs, occupied cells and annotations stay outside `inputs/`; source arrays stay separately retained |

The target plan is fixed before inference. Choosing any other labelled object
cannot earn credit for the requested object. This is a **cued localization test**;
it does not measure free object inventory, obstacle mechanics, safe click execution
or game solving. Target-mask containment is the primary metric; exact geometric
centre accuracy is not implied by a hit.

## Local validation

- Six inputs reconstruct their original 64-by-64 arrays exactly, including every
  pixel in each 7-by-7 cell. There is no interpolation blur in the supplied PNGs.
- Six fixed prompts and target-reference hashes are retained privately, with an
  offline review page showing the exact model inputs and separately hidden scoring
  references. No reference identifier or mask is sent to the processor.
- **16 behavioral tests pass**, including all 4,096 cells at the new scale, x/y
  orientation, the 7-pixel boundaries, image-edge rejection, exact occupied-cell
  target hits, distractors, multi-point refusal, preparation isolation and refusal
  to overwrite earlier drafts.
- The pinned real MolmoPoint processor accepts all six 448px inputs and their
  target prompts. Local CPU checks produce 771-781 prompt tokens per request,
  retain 448-by-448 original-image metadata and decode asymmetric synthetic points
  through the project adapter. No weights or model generations were involved.
  [Aggregate CPU validation](molmopoint_targeted448_cpu_validation_2026-10-16.json).
- This CPU check uses PyTorch 2.10.0+cpu and Transformers 4.57.6. It does not
  certify the publisher-recommended 4.57.1 dependency set, a complete checkpoint
  load, native generation constraints on a real model, GPU memory or Kaggle.

## Comparison limits and later experiments

Keeping the supplied canvas at 448px controls its dimensions, but does not make
this a model-only change from the completed InternVL inventory run. That run used
bicubic preprocessing and a generic bounding-box inventory prompt. This draft
uses nearest-neighbor source pixels, cued pointing and a target-hit metric.
MolmoPoint's own internal crop/resize processing also differs from InternVL's;
its native decoder returns coordinates in the supplied original image.

A direct comparison would need the same supplied pixels, target prompts and
point-hit scoring for both models. The earlier 0/6 inventory-contract result is
retained and is not relabelled as that comparison. A later crop experiment should
be specified separately after inspecting retained errors; this draft does not
automatically crop, recenter or retry failed targets. Proximity alone does not
prove that the model selected the correct object.

Full model bytes, the exact runtime environment, a guarded live package, scoped-use
evidence and new lock-bound compute authorization remain necessary before any GPU
test. This input revision supplies no launch authority.

Local input-preparation command:

```text
python scripts/prepare_molmopoint_identification.py --source-bundle <retained-private-bundle> --targets <private-target-plan.json> --output <new-private-directory>
```
