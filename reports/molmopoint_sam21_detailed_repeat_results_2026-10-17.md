# MolmoPoint plus SAM 2.1: detailed-prompt repeat completed

October 17, 2026. **The fresh requested repeat completed, but again produced
zero native points across all six boards.** With no seeds, the frozen SAM 2.1
stage was skipped. End-to-end mask coverage is 0/37 and exact masks are 0/37;
this run does not measure SAM's boundary accuracy.

| Game | Reviewed whole objects | Native points | Output tokens | Termination |
|---|---:|---:|---:|---|
| ls20 | 3 | 0 | 31 | Normal stop |
| s5i5 | 7 | 0 | 1 | Normal stop |
| cd82 | 5 | 0 | 1 | Normal stop |
| ft09 | 6 | 0 | 1 | Normal stop |
| ka59 | 10 | 0 | 60 | Normal stop |
| sc25 | 6 | 0 | 1 | Normal stop |
| **Total** | **37** | **0** | **95** | **6 normal stops** |

All six generated-token sequences are **identical to the previous completed
detailed-prompt attempt**, including special tokens. Four boards end immediately;
ls20 returns pseudo-pointer text and ka59 a prose inventory. None reaches the
4,096-token cap. The output is retained verbatim privately; text is not converted
into invented points.

The frozen decoder marks all six empty decodings parser-valid. That label does
not establish compliance with the native-only pointing instruction or successful
discovery. Precision is undefined with zero proposals. The fixed rules were not
changed after observing the answers.

| Comparison | Original short generic instruction | Detailed instruction, previous run | Detailed instruction, this repeat |
|---|---:|---:|---:|
| Valid native seeds | 22 across five boards | 0 | 0 |
| SAM IoU ≥ 0.5 matches | 12/37 | No seeds; not run | No seeds; skipped |
| Exact SAM masks | 6/37 | No seeds; not run | No seeds; skipped |
| Output cap per board | 4,096 | 4,096 | 4,096 |

The original 6/37 result came from a Kaggle MolmoPoint run followed by **local
CPU SAM inference**, rather than a single notebook containing both models. This
repeat preserves that workflow. Compared with the original discovery requests,
only the exact eight-rule instruction and its bounded input-character allowance
changed; the model revision, six plain 448 × 448 images, dependency locks,
native decoder, generation settings and coordinate mapping remain unchanged.
The output cap was already 4,096 in the original run.

The original SAM policy and checkpoint were frozen and rehashed before this
submission. That policy requires points from this attempt alone. Because all
six inventories are empty, postprocessing records six skips and zero proposals,
without loading SAM, invoking a forward pass, borrowing the old 22 seeds or
repairing responses. The unchanged owner-reference hash is checked before
scoring. No new segmentation-performance claim follows from zero masks.

| Runtime / integrity check | Verified result |
|---|---|
| Provider | COMPLETE, one accepted submission, no automatic retries |
| Actual accelerator | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Worker lifecycle through post-write witness | 253.647 seconds, below 3,300; not total provider job time |
| Integrity | All 220 mounted files and seven embedded inputs hash-match |
| Saved package | Exact source/authority, available privacy/settings, image and attachments verified |
| Independent CPU replay | Checkpoint bytes, frozen requests, processor inputs/metadata, raw/generated IDs, native points and masks verified |
| Cleanup | Owned process groups absent, GPU cleanup verified, temporary environment removed |
| Scope | Six generations, 95 total output tokens; zero game actions or scorecards |
| Postprocessing | Zero SAM forwards, zero additional MolmoPoint generations, no new GPU job |
| Local viewer | Six boards, reference overlay, exact private raw outputs and original-cell hover coordinates; eight CPU browser checks pass |

Review-lock SHA256:
`cdaab9fe9c10fe7fb14699d2ef89fd831ebb2e88a225d0c2643f8a0c68b672aa`

Independent replay SHA256:
`867322b02df8bd9a7340177777945cd07db2577e2d0a707195ad4a83aaccd202`

Frozen empty-seed postprocessing result SHA256:
`82fb3193563e78d263869a0d5db6840496b200da3cd64d5bef609a87df8ace7a`

Kaggle's API does not independently echo the requested timeout or saved
dataset-version labels. The validated request and runtime mounted-byte checks
remain the supporting evidence. The accepted provider-overhead qualification
is preserved; the worker duration is not a certified full-job cap.

This repeat reproduces the detailed instruction's failure to elicit native
points on these six exposed development boards. It does not demonstrate that
the model sees no objects, that token budget was exhausted, or that SAM became
worse. The ka59 prose itself contains visual descriptions. No prompt, decoder,
reference or stopping rule was changed after seeing this run. Further prompt
experiments require a separately prepared condition and fresh compute authority.
All earlier attempts and consumed claims remain preserved; no retry follows.

Records: [submission](molmopoint_sam21_detailed_repeat_submission_2026-10-17.md),
[original SAM comparison](sam21_retained_seed_boundaries_v1_results_2026-10-16.md),
[previous detailed-prompt result](molmopoint_detailed_generic_v2_attempt2_results_2026-10-17.md).
Raw outputs, masks, launch records and the viewer remain private and git-ignored.
