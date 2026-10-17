# UnSAMv2 / UnSAMv2+ and Semantic-SAM integration

October 16, 2026. **Development adapters and a local comparison runner are implemented.**
No checkpoint from either project has been loaded or run. No Kaggle save,
upload, reservation or GPU job was made. Existing attempts, references and
SAM 2.1 results are preserved. This is not an approved live package.

| Backend | Pinned upstream source | Retained-point mode | Whole-image mode |
|---|---|---|---|
| UnSAMv2 / UnSAMv2+ | `f4ec1136ce5ce2c38061dfbe3dc8233ea90dd53a` | Original floating-point pixel coordinates; `predict(..., gra=...)`; highest predicted quality of three masks, earliest tie | `generate(image, gra=...)`, independent of MolmoPoint seeds |
| Semantic-SAM Swin-L | `e11f8b518539faea731e2744cc3e44c24572e30d` | Normalized original pixel coordinates; raw `predict()` masks; fixed decoder channel for each requested granularity | `SemanticSamAutomaticMaskGenerator(..., level=[...])`, independent of MolmoPoint seeds |

The inspected [UnSAMv2 notebooks](https://github.com/yujunwei04/UnSAMv2/tree/f4ec1136ce5ce2c38061dfbe3dc8233ea90dd53a/sam2/notebooks)
document both inference modes. Semantic-SAM's [raw interactive predictor](https://github.com/UX-Decoder/Semantic-SAM/blob/e11f8b518539faea731e2744cc3e44c24572e30d/tasks/interactive_predictor.py)
and [automatic generator](https://github.com/UX-Decoder/Semantic-SAM/blob/e11f8b518539faea731e2744cc3e44c24572e30d/tasks/automatic_mask_generator.py)
define the two interfaces used here. Its `predict_masks()` returns visualizations;
the adapter deliberately uses raw `predict()` instead.

## Comparison design

| Setting | Declared behavior |
|---|---|
| Inputs | The same six plain 448 x 448 initial boards; no visible overlay |
| UnSAM granularities | 0.1, 0.3, 0.5, 0.7, 0.9, each a separate condition |
| Semantic-SAM granularities | 1 through 6, each a separate condition; raw channels are 3, 2, 0, 4, 1, 5 respectively |
| Seeded comparison | Same valid retained MolmoPoint points; no snapping or partial ls20 salvage |
| Automatic discovery | All six boards, including ls20; 16 x 16 regular prompt grid, batch 16, no external point cues |
| Automatic filtering | Predicted IoU and stability thresholds 0; within-image box NMS 0.7; no crops or small-region repair |
| Proposal budget | At most 96 scored masks per board and condition; descending predicted quality, original-index ties; raw count and discarded count retained |
| Hierarchy | Each mask pool is compared with the existing whole-object references; no asserted semantic parent/child labels |
| Mask conversion | Original-frame 448px mask; at least 25 foreground pixels per 7 x 7 original cell |
| Semantic-SAM preprocessing | Documented bicubic enlargement to 640px; raw logits return by bilinear interpolation before zero threshold; already binary automatic masks return by nearest interpolation |
| Refinement | No M2M, CascadePSP, hole filling, component merging, reference-based selection or mask repair |
| Evidence | All returned masks and qualities saved before budget selection; selected masks, source indices, empty flags, source pins and environment versions retained |
| Evaluation | Separate process accepts references and replays raw masks; no best-level selection or pooled whole/part score |

This is a development grid, not a confirmatory model-ranking experiment. More
granularities create more opportunities to inspect the same exposed boards.
Report each condition; a reference-chosen best mask or level would be an oracle
diagnostic, not autonomous performance. Raw automatic proposals have already
passed upstream generator NMS; the retained pool is not every decoder output.
The 96-mask budget can reduce recall, and is explicitly reported.

The failure cases motivate whole-structure coverage for the sc25 nine-tile
panel and ft09 clusters, and automatic discovery of the ls20 cross, destination
and reference square. Yellow-bar change requires before/after observations;
this static-image implementation does not test temporal change or gameplay.

## Code and commands

| File | Purpose |
|---|---|
| `research/object_discovery_boundaries_v1/granularity.py` | Separate conditions, strict geometry, quality-only proposal budget |
| `granularity_backends.py` in that directory | Both real upstream API adapters and original-frame conversion |
| `granularity_sources.json` in that directory | SHA256 pins for 56 UnSAMv2 and 83 Semantic-SAM runtime/config files |
| `granularity_runtime.py` in that directory | Reject missing/changed sources, wrong checkpoint bytes, version drift or imported fork collisions |
| `granularity_worker.py` in that directory | Reference-free six-frame worker and durable raw outputs |
| `scripts/run_granularity_segmentation.py` | Planning or explicit, bounded Linux development execution |
| `scripts/evaluate_granularity_segmentation.py` | Raw replay, image/reference binding and existing one-to-one whole-mask scoring |
| `tests/test_object_boundary_granularity.py` | Synthetic adapter, geometry, routing and replay tests; no real model inference |

Planning requires only Python and the existing private retained-seed inputs:

```bash
python scripts/run_granularity_segmentation.py \
  --model unsamv2_plus --mode automatic --granularity 0.1 \
  --inputs /private/retained-seed-inputs --output /private/new-plan --plan

python scripts/run_granularity_segmentation.py \
  --model semantic_sam_l --mode automatic --granularity 1 \
  --inputs /private/retained-seed-inputs --output /private/another-new-plan --plan
```

Each input directory contains only the six PNGs, `seeds.json` and their
`manifest.json`; answer files are refused. Plans never import Torch or models.

After separately qualifying an isolated backend environment, the execution
interface adds `--execute`, `--source <pinned-checkout>`, `--checkpoint <file>`,
`--checkpoint-receipt <json>`, `--runtime-lock <json>`, `--python <backend-python>`,
`--device cpu|cuda` and `--seconds <1..3300>`. Omit `--plan`. Use a fresh output
directory for every condition/attempt; previous outputs are never overwritten.
The checkpoint receipt requires `model`, `source`, `bytes` and `sha256`.
The version lock maps installed distribution names to exact versions and must
include Torch, torchvision, NumPy and Pillow. It is a version check, not a
wheel-provenance or GPU-compatibility certification.

The Linux parent reuses the existing `InstallationProcesses` owner to cover
startup, timeout/interruption, process groups and descendant cleanup. The
budget includes source/checkpoint checks, model loading, inference and output
writing. The worker checks its parent's absolute deadline; the parent can
terminate it. A successful development return is not Kaggle authorization or
an independent GPU-lifecycle certificate. No provider allocation/setup cap is
claimed. Python socket connection guards and offline environment settings are
used; they are not a network namespace or provider internet setting.

Evaluation runs separately, after the worker exits:

```bash
python scripts/evaluate_granularity_segmentation.py \
  --frames /private/attempt/frames --inputs /private/retained-seed-inputs \
  --references /private/confirmed-review.json --output /private/new-evaluation.json
```

## Verification and remaining runtime work

Both public source archives were fetched and their exact entry points inspected.
The 139 pinned runtime/config files verify against those source snapshots.
Plans for both automatic backends were generated from the real retained inputs
without loading a model. Synthetic CPU tests exercise raw API arguments, the
Semantic-SAM channel mapping, 640-to-448 conversion, empty/duplicate masks,
proposal caps, six-frame routing and rejection of altered masks even after
output hashes are updated. **87 Linux CPU tests passed, with no failures or
skips** (14 new integration tests plus the existing 73 boundary regressions).
The [machine-readable validation](granularity_segmentation_validation_2026-10-16.json)
records source hashes and the upstream API checks.
An additional real Linux CLI check with deliberately missing upstream sources
refused before model loading, wrote no worker-success receipt, and verified
that its owned subprocess groups were absent.

| Requirement before actual model testing | State |
|---|---|
| Adapters, worker, raw replay and existing scorer integration | Implemented and tested with synthetic outputs |
| UnSAMv2 / UnSAMv2+ checkpoint acquisition and hash receipt | Pending; model zoo links retained below |
| Semantic-SAM Swin-L checkpoint acquisition and hash receipt | Pending |
| Fully resolved dependencies, wheel/source provenance and clean installation | Pending for separate environments |
| Real checkpoint load and output-shape qualification | Pending for both backends |
| Exact GPU-image compatibility | Pending; not inferred from upstream instructions |
| Private Kaggle package and any new compute approval | Not prepared or launched by this change |

[UnSAMv2 installation](https://github.com/yujunwei04/UnSAMv2/blob/f4ec1136ce5ce2c38061dfbe3dc8233ea90dd53a/INSTALL.md)
documents Python 3.10 / Torch 2.5.1 and its own SAM fork; Detectron2 is not
needed for its inference path. [Semantic-SAM installation](https://github.com/UX-Decoder/Semantic-SAM/blob/e11f8b518539faea731e2744cc3e44c24572e30d/README.md)
documents Torch 1.13.1 and a Detectron2 fork. These are upstream recipes,
not validated locks for the project's current GPU image. Its helpers require
CUDA, and no silent CPU port or substitution has been made. CUDA extension and
Blackwell support must be established independently before an RTX launch.

Checkpoint sources: [UnSAMv2 model zoo](https://github.com/yujunwei04/UnSAMv2/tree/f4ec1136ce5ce2c38061dfbe3dc8233ea90dd53a#model-zoo),
[Semantic-SAM Swin-L release](https://github.com/UX-Decoder/Semantic-SAM/releases/download/checkpoint/swinl_only_sam_many2many.pth).
Source revision pins do not pin or certify checkpoint bytes. No accuracy result
for either model on these boards is claimed.
