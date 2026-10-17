# Granularity segmentation: checkpoint preparation and one-image checks

The UnSAMv2 and UnSAMv2+ seeded and automatic **CPU runtime smoke checks pass**.
Semantic-SAM's checkpoint is acquired; its isolated CUDA environment, both native
extension builds and offline imports now pass. Its real GPU inference is still
pending. The six-board comparison has not started.
No GPU job, Kaggle upload, game action or scorecard was created in this preparation.

## Checkpoints and environments

The public [checkpoint registry](../research/object_discovery_boundaries_v1/granularity_checkpoints.json)
records the exact source, byte size and SHA256 for all three checkpoints.
Each downloaded file was independently reread and matched its acquisition receipt.
UnSAMv2+ additionally matches the publisher's pinned Hugging Face LFS digest.
The other two sources supplied no publisher digest: their hashes establish local
byte identity, not independent publisher authentication.

| Backend | Checkpoint bytes | Acquisition qualification | Runtime status |
|---|---:|---|---|
| UnSAMv2 | 188,689,844 | Official model-zoo link; locally pinned SHA256 | Clean Python 3.12 / Torch 2.10 CPU environment; seeded and automatic inference complete |
| UnSAMv2+ | 188,689,844 | Pinned publisher Space revision and matching publisher SHA256 | Same isolated CPU environment; seeded and automatic inference complete |
| Semantic-SAM L | 895,495,739 | Official release asset; locally pinned SHA256 | Separate Python 3.10 / Torch 2.10 CUDA 12.8 environment; both native extensions compiled for sm_120 and offline imports pass; inference pending |

The UnSAM environment has no inherited site packages. Its 23 installation wheels
are hash-pinned in the [CPU requirements](../research/object_discovery_boundaries_v1/runtime_profiles/unsam_cpu_requirements.lock);
the [installed-version receipt](../research/object_discovery_boundaries_v1/runtime_profiles/unsam_cpu_versions.json)
also records pip. Publisher metadata verified the downloaded wheel/source digests;
the two source-built wheels retain their source and build-tool receipts privately.
`pip check` passes. This CPU profile does not certify a Kaggle GPU image.

## Real one-image results

All conditions use the same initial **sc25 / board-06**, plain 448 × 448 image,
the original uncorrected MolmoPoint seeds, and the predeclared **granularity 0.1**.
Automatic mode uses the fixed 16 × 16 point grid and selects at most 96 proposals
by model quality, before reference scoring. No other granularity was measured.

| Condition | Successful CPU lifecycle (s) | Raw proposals | Scored proposals | Empty scored proposals | Whole-object matches at IoU ≥ 0.5 | Exact matches |
|---|---:|---:|---:|---:|---:|---:|
| UnSAMv2+ seeded | 29.828 | 3 | 3 | 0 | 0/6 | 0/6 |
| UnSAMv2+ automatic | 68.050 | 255 | 96 | 1 | 0/6 | 0/6 |
| UnSAMv2 seeded | 34.082 | 3 | 3 | 2 | 0/6 | 0/6 |
| UnSAMv2 automatic | 76.534 | 256 | 96 | 9 | 0/6 | 0/6 |

The runtime checks succeeded; whole-object segmentation did not succeed on this
smoke frame at this granularity. Visual inspection shows mostly small fragments
and empty masks. These measurements do not establish performance on other boards
or granularities and do not supersede the earlier SAM 2.1 comparison.

## Replay, failures and preservation

- All four successful outputs pass raw-array replay and manifest verification.
  A separate vectorized implementation also reproduces every selected 7 × 7
  majority projection into original board cells.
- The board PNG hash is
  `d3ef3611d70bb1010833e93cb2400f779d7c49da48a558f9235e655e5bb2c126`.
  A private contact sheet and interactive proposal viewer were generated from
  that image; the contact sheet was inspected. References remained evaluator-only.
- Process cleanup verifies all owned groups absent in each successful lifecycle.
- Seven explicit CPU attempts are preserved: four successful checks, a
  distribution-name check refusal, a missing-OpenCV import failure, and a base
  automatic run whose inference completed but evidence writing rejected NaN
  stability for empty masks. Fresh attempts followed the corresponding fixes;
  there were no automatic retries or overwritten attempts.
- The [distribution-name fix](granularity_environment_name_fix_2026-10-16.md)
  and [empty-stability/replay fix](granularity_empty_stability_fix_2026-10-16.md)
  are pushed. The full Linux CPU group passes **101 tests, zero failures,
  zero errors and zero skips**.

Raw masks, images, acquired model files, installation/build logs, provenance
receipts and attempt folders remain in the private git-ignored workspace.

## Remaining gates

1. Finish portable-runtime packaging and relocation checks. Semantic-SAM's
   isolated dependencies, both native builds and offline imports pass; a
   [two-line native API compatibility fix](semantic_sam_native_build_compatibility_2026-10-16.md)
   was needed for the deformable-attention extension. Build and dependency pins
   are recorded; actual CUDA execution remains unverified.
2. Run its seeded and automatic one-image checks on suitable CUDA hardware;
   inspect masks on the bound board and replay the saved outputs independently.
3. Proceed to the six-board comparison only after both backends' runtime checks
   pass. Evaluate each granularity separately; do not select one using reference
   scores. Any remote GPU execution needs its own final reviewed package and
   applicable authorization.
