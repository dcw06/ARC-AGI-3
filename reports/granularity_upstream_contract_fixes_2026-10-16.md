# Granularity segmentation: upstream contract corrections

October 16, 2026. The three review findings on `cdfd69e` reproduced and are
corrected. The previous 87-test validation did not exercise real checkout
symlinks, the granularity decoder's return method, or the cold-cache builder.
It did not establish real checkpoint loading or model accuracy.

| Finding | Baseline reproduction | Correction |
|---|---|---|
| Pinned UnSAMv2 checkout refused | Four real links from the pinned archive trigger `symlink in upstream runtime` | Pin exact link names, link text and target state; permit only those tracked links or their explicit ZIP representation |
| Seeded decoder cardinality | The pinned `MaskDecoderGra.forward` method, with synthetic tensors, returns one mask/score; the old adapter raises `UnSAMv2 multimask response differs` | Require exactly one granularity mask, one score and one low-resolution logit map per seed; replay enforces the same cardinality |
| Undeclared Swin download | The pinned Semantic-SAM convenience builder reaches backbone preloading before the segmentation checkpoint is loaded | Construct from the same pinned config with `LOAD_PRETRAINED=False` and an empty preload path; load the verified segmentation checkpoint locally |

## Exact source representation

The four UnSAMv2 legacy links are under `sam2/sam2/`:

| Link | Exact target |
|---|---|
| `sam2_hiera_b+.yaml` | `configs/sam2/sam2_hiera_b+.yaml` |
| `sam2_hiera_l.yaml` | `configs/sam2/sam2_hiera_l.yaml` |
| `sam2_hiera_s.yaml` | `configs/sam2/sam2_hiera_s.yaml` |
| `sam2_hiera_t.yaml` | `configs/sam2/sam2_hiera_t.yaml` |

Their targets are absent in the exact pinned upstream tree. This unused legacy
state is preserved and checked; no replacement configuration is guessed.
The active `configs/unsamv2_small.yaml` remains a regular hash-verified file.
The source manifest now distinguishes 52 regular UnSAMv2 runtime/config files
and these four links, alongside the unchanged 83 Semantic-SAM files.

Linux checkout links are validated with `readlink`, an in-tree target path and
the expected absent target state. A GitHub ZIP snapshot is also explicitly
defined: only these four paths may be regular files containing the exact
UTF-8 link text, pinned by SHA256. Other links, changed text, missing entries,
newly populated legacy targets, changed active configs and symlinked runtime
directories are refused. Neither representation follows a legacy target.

## Decoder and checkpoint loading

UnSAMv2 still receives `multimask_output=True` and the requested `gra` value.
The [pinned granularity decoder](https://github.com/yujunwei04/UnSAMv2/blob/f4ec1136ce5ce2c38061dfbe3dc8233ea90dd53a/sam2/sam2/modeling/sam/gra_mask_decoder.py)
returns its single granularity mask and one score; the internal SAM candidates
are not exposed as three returned masks. Saved seeded arrays therefore have
shapes `(seeds,1,448,448)` and `(seeds,1)`. Replay takes channel zero and refuses
the obsolete three-mask shape. Separate granularity conditions, native seed
coordinates, majority projection and automatic proposal budgeting are retained.
The comparison policy now binds the decoder cardinality and disabled backbone
preloading, so old plans cannot silently cover this revision.

For Semantic-SAM, the adapter bypasses the
[upstream convenience builder](https://github.com/UX-Decoder/Semantic-SAM/blob/e11f8b518539faea731e2744cc3e44c24572e30d/semantic_sam/build_semantic_sam.py)
and overrides the two backbone-preload fields in a private in-memory copy of
the pinned config. Upstream source/config bytes remain unchanged. The locally
verified segmentation checkpoint is loaded on CPU with `weights_only=True`.
Both a direct ordered state dictionary and the upstream outer `model` wrapper
are supported, using its `model.` parameter prefix convention.

Every constructed model tensor must exist in that segmentation checkpoint at
the expected shape, followed by strict state loading. Missing or mismatched
backbone tensors cannot be filled with random weights or a cached URL model.
The wrapper is moved to CUDA only after the complete state check. Real released
checkpoint compatibility still requires the one-image qualification below.

## Verification

The retained reproduction executed the hash-verified upstream decoder's actual
return method with synthetic `predict_masks` tensors and the upstream builder
with a download-boundary stub. These are contract checks, not learned-model
inference. All three defects reproduce on `cdfd69e`; the repaired source
verification also passes with four real Linux symlinks and with the explicit
ZIP snapshot.

**97 Linux CPU tests passed, with no failures or skips.**
The [new validation receipt](granularity_review_fix_validation_2026-10-16.json)
records the final test count, baseline failures and current source hashes.
Regressions cover link/path tampering, single-mask acceptance and obsolete
three-mask refusal, raw replay, cold-cache preload suppression, complete and
incomplete serialized model states, and one-image routing. Historical
validation and consumed attempts are preserved.

## One-image qualification before the full comparison

`--smoke-case board-06` now selects exactly one retained image. A smoke record
is explicitly labelled `one_image_runtime_smoke`; the six-board evaluator
refuses it. A seeded smoke with no valid seeds is refused rather than reporting
success without inference. Each model/mode gets a fresh output directory.

Planning, without imports or inference:

```bash
python scripts/run_granularity_segmentation.py \
  --model unsamv2_plus --mode seeded --granularity 0.1 \
  --inputs /private/retained-seed-inputs --output /private/new-unsam-smoke-plan \
  --smoke-case board-06 --plan

python scripts/run_granularity_segmentation.py \
  --model semantic_sam_l --mode seeded --granularity 1 \
  --inputs /private/retained-seed-inputs --output /private/new-semantic-smoke-plan \
  --smoke-case board-06 --plan
```

Six such private plans were prepared: seeded and automatic modes for UnSAMv2,
UnSAMv2+ and Semantic-SAM. No model was imported by planning. After checkpoint
and runtime qualification, the existing explicit execution arguments can run
these as one-image checks before any six-board condition.

| Actual runtime prerequisite/check | State in this environment |
|---|---|
| Checkpoint acquisition and trusted byte receipts | Not yet present for either project |
| Backend packages | `sam2`, `semantic_sam`, Detectron2 and Hydra absent from the inspected CPU environment |
| Available test interpreter | Torch `2.10.0+cpu`; no CUDA build |
| Real one-image checkpoint load and inference | **Not run** for either backend |
| Full comparison | **Not run; requires the real one-image checks first** |
| Kaggle uploads, reservations or GPU launches | None |

The code fixes are not a substitute for those real runtime checks. Semantic-SAM's
pinned helper path remains CUDA-only; no unreviewed CPU port or new GPU job was
introduced to manufacture a smoke result. The existing models, reference masks,
inference outputs and original SAM comparison have not been changed.
