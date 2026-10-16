# MolmoPoint-8B grounding integration draft

October 16, 2026. Added a separate experimental native-pointing adapter and input
preparation command for `allenai/MolmoPoint-8B`. The gameplay policy and completed
InternVL study are unchanged. The owner's coordinate-grid choice remains pending;
this draft uses the original plain board images. No model weights were downloaded,
no model answers generated, and no Kaggle upload or job was started.

## Why this model

MolmoPoint selects visual patches/subpatches through special pointing tokens.
The publisher's decoder uses processor metadata to recover original image-pixel
coordinates. This lets our code map pixels into board cells, without asking the
model to write 0-63 coordinates as ordinary text. This is a promising candidate
for the observed grounding failure, not evidence that it works on ARC games.
[Official model card](https://huggingface.co/allenai/MolmoPoint-8B),
[technical report](https://arxiv.org/abs/2603.28069).

## Implemented

| Component | Current behavior |
|---|---|
| Immutable identity | Official revision `188130f961c8e0888a34e11121a1423c461a01ba`; upstream file sizes/blob or LFS hashes retained for all 33 files |
| Local acquisition | 25 non-weight files, 28,805,306 bytes, checked against the pinned tree; eight weight shards are absent |
| Snapshot verifier | Requires the complete expected local files, sizes/hashes and Python source set before custom code loading; does not download or load anything |
| Processor interface | One local image, native chat template, `return_pointing_metadata=True`; require original image dimensions and a nonempty native pointing logit processor |
| Native decoding | Retain generated IDs and special tokens; use `extract_image_points`, verify decoded point count against complete point triples; truncated/oversized completions invalid |
| Coordinate conversion | Publisher rows are `[object_id, image_index, pixel_x, pixel_y]`; validate then compute `floor(pixel_x / original_width * 64)` and the analogous y coordinate |
| Refusal | Reject nonfinite, negative, outside-image or wrong-image points; never clamp, round to a nearby object or repair an answer |
| Point-hit scoring | Maximum-cardinality one-to-one matching against exact owner-labelled occupied cells, with whole regions and parts separate |
| Input draft | Six anonymous original first-level boards; generic object and barrier-candidate requests, 12 proposed calls total, each at most 1,024 new tokens, zero actions |
| Reference isolation | Partial owner references retained separately from model inputs; no target names, locations, masks or annotations in prompts |
| Production integration | No active-policy change, action dispatch, model loading entry point or live notebook; native point helpers are for a separately reviewed future worker |

The image processor's crop and resize transforms are handled by the publisher's
decoder before our cell conversion. The adapter must receive the **original**
image dimensions, not internal crop dimensions. The current draft uses unchanged
512-by-512 full-board images, so each original cell occupies eight pixels. It
does not impose InternVL's 448-by-448 preprocessing on MolmoPoint.

## Validation and limits

Twelve local behavioral tests cover every board cell, x/y orientation,
rectangular image dimensions, boundaries, invalid values and caps, native metadata
and special-token handling, decoder omissions, wrong architecture, output
truncation, occupied-cell holes, duplicate coverage and partial references.
The pinned real processor also passed preprocessing on all six boards and a
synthetic native-decoder check locally on CPU, with 772 prompt tokens and
725-by-4 pooling metadata per object prompt. It used PyTorch 2.10.0+cpu and
Transformers 4.57.6, no weights, no generations, no network and no CUDA. This
validates processor/decoder interfaces only, not visual recognition or generation.
A follow-up used the project adapter with that real processor and an asymmetric
synthetic decoded point, verifying x/y order through the full helper interface;
the model and its logit processor were stand-ins, not loaded weights.
The [aggregate CPU record](molmopoint_identification_v1_cpu_validation_2026-10-16.json)
pins the private receipt and current source hashes. Unit fixtures are not model results.

The publisher recommends Transformers 4.57.1, whereas the retained InternVL
environment uses 4.57.6. That difference must be resolved and tested in a separate
dependency lock; existing installation receipts cannot certify the new runtime.
The metadata lists float32 checkpoint weights totalling **34,711,510,508 bytes**.
Runtime dtype, memory headroom and actual RTX compatibility still require validation.
[Pinned configuration](https://huggingface.co/allenai/MolmoPoint-8B/blob/188130f961c8e0888a34e11121a1423c461a01ba/config.json).

The model card identifies Apache-2.0 and also describes third-party training-data
use qualifications. These facts are retained for scoped-use review; this draft
does not supply a permission outcome or redistribution approval.
[Licence/use statement](https://huggingface.co/allenai/MolmoPoint-8B#license-and-use).

## What a result would establish

| Question | Measure and limitation |
|---|---|
| Does a point land on a labelled object? | Exact occupied-cell hits; large background/UI regions must be distinguished from controls and targets |
| Does it enumerate distinct regions? | One point cannot cover multiple regions within a stratum; partial references cannot establish exhaustive precision |
| Does it find barrier candidates? | Spatial coverage of the one owner-labelled obstacle candidate; other boards are not verified negative examples |
| Does it know an obstacle blocks movement? | Not tested by image pointing; requires action-effect evidence |
| Does it identify full objects or safe click regions? | A point hit does not establish extent, masks, semantics, controls or click success |
| Is it better than InternVL? | Requires a declared comparable metric; point hits cannot be directly compared with bounding-box IoU. Any model comparison changes the entire model/processing pipeline |

Next: validate the exact processor/runtime dependency set, acquire and byte-check
the checkpoint, establish the private model source and scoped-use evidence, and
build the guarded runtime/notebook with independent replay and a new exact review
lock. A fresh source/compute approval and single-use reservation precede any GPU
test. No previous attempt or approval is reset or reused.

Local preparation command (no downloads, inference or launches):

```text
python scripts/prepare_molmopoint_identification.py --source-bundle <retained-private-bundle> --output <new-private-directory>
```
