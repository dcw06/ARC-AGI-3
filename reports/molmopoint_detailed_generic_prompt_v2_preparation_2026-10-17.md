# MolmoPoint: detailed generic discovery instruction, prepared

The owner's eight-rule generic instruction is retained verbatim in
[`prompts.py`](../research/object_discovery_boundaries_v1/prompts.py), with only
Markdown line-break escapes represented as ordinary line breaks. All six
initial development boards receive this same instruction. No game-specific
object descriptions or expected object count are supplied.

This is a new prompt condition, not a rerun of the assisted six-target test.
The earlier cued and uncued packages, raw outputs and consumed attempts remain
preserved. No new GPU attempt, upload, reservation or model generation has run.

| Setting | Prepared value |
|---|---|
| Profile | `detailed_whole_v2`; legacy default remains `legacy_whole_v1` |
| Model | Same pinned `allenai/MolmoPoint-8B` revision `188130f961c8e0888a34e11121a1423c461a01ba` |
| Images | Same six plain RGB 448 x 448 initial boards; original 64 x 64 colors in 7 x 7 blocks |
| Instruction | Same 3,290-character owner instruction on each board |
| Generation cap | 4,096 **new tokens** each, 24,576 maximum total; this is a token cap, not a character cap |
| Prior caps | Assisted test: 1,024 tokens; earlier uncued test: already 4,096 tokens |
| Native decoding | Existing complete-sequence checks and 96-point safety ceiling; no partial-output salvage |
| Runtime | Same isolated dependencies, checkpoint, BF16 CUDA loading and native logits constraints |
| Requested compute | One RTX PRO 6000, requested session timeout 3,600 s, worker 3,300 s, work cutoff 3,000 s and cleanup reserve 300 s |
| Calls/actions | Six greedy generations, no automatic retries, zero game actions or scorecards |
| Access | Private account-only notebook/raw outputs; sanitized summaries only |
| Time policy | Accepted provider overhead qualification retained; session/worker limits do not bound pre-cell mounting/allocation or GPU release |

## Validation and exact review packet

Preparation, installation staging, the GPU worker and independent replay all use
the explicitly bound prompt profile. Selecting a different profile or changing
the instruction makes request verification refuse. The builder includes the
prompt module in the locked executable source and binds the profile in the
runtime protocol. Legacy requests retain their original text and request fields.

- 192 distinct Linux regression checks are covered without unresolved skips:
  190 passed in the offline CPU processor interpreter; its two missing-SDK skips
  passed separately in the installed operator interpreter. Original logs and
  receipts are preserved; no test is counted twice.
- The pinned processor accepts the actual new instruction and all six images
  offline. Each input has 1,358 processor tokens, including template/image
  tokens. No model weights were loaded, CUDA initialized or network attempted.
- Read-only Kaggle checks verified the account, available quota, new target
  absence and the same dataset versions/inventories. This is preparation-time
  evidence; a fresh preflight is still required before any submission.
- Two complete builds have identical review hashes. The exact review notebook
  refuses before extraction or GPU use while authority is absent.
- The executable payload contains only seven agent input files and reviewed
  runtime source. Reference masks and evaluation code remain outside it.
- The existing required ARC competition attachment and canonical title/slug are
  bound in the new package. Actual RTX allocation must still pass runtime checks.

Final private review-lock SHA256:
`29d7b398683fd10fd02dd0fc972d3339bc43526873fba3781f86972858f775ef`

Runtime-lock SHA256:
`d157a28cd5a3ebac52f8e0455d478e36ee0f22722364f039cf3c9f2c7901e8d2`

Instruction UTF-8 SHA256:
`b79720a4f2638aa410aaafaed96df63666cd47844436a86b3b43e2d20e92e226`

Reference file SHA256 (unchanged):
`5304e35b1f0ee17e0ffd77293ac4fba260bbfa08755c2d48e914ed72ac9cec63`

The private packet is `gpu-live-review-r1` under the git-ignored
`molmopoint-generic-instructions-v2-2026-10-17` workspace. Authority is empty;
source/compute approval and a fresh reservation are not recorded. The existing
launch guard requires source/use/compute authority bound to this new hash;
previous attempts' claims cannot authorize it.

## Interpretation planned before inference

Measure valid termination, discovered points landing in the unchanged reviewed
whole-object inventory, duplicate/missed detections and completion-token use.
Retain failures and partial raw tokens without awarding partial-response credit.
The unchanged same-color component baseline is diagnostic; it does not certify
semantic object boundaries. Any later SAM mask extraction should use the newly
retained seeds as a separate, labelled stage.

Compare the new instruction with the earlier uncued run only as a descriptive
development comparison on exposed frames. This is not a randomized effect
estimate, independent replication or held-out generalization test. The detailed
whole/part wording may still disagree with the frozen single-owner inventory;
scores measure agreement with that inventory. Do not revise labels after seeing
the responses. No model-performance result follows from these CPU checks.
