# MolmoPoint six-board runtime preparation

October 16, 2026. Local runtime preparation is complete. **No pretrained
MolmoPoint inference, Kaggle upload, reservation or GPU launch occurred.**
The private candidate remains review-only; it is not an approved live package.

| Component | Evidence and status |
|---|---|
| Checkpoint | `allenai/MolmoPoint-8B`, revision `188130f961c8e0888a34e11121a1423c461a01ba`; all 33 files verified, including eight weight shards totaling 34,711,510,508 bytes |
| Dependencies | Separate Linux/Python 3.12 lock: 48 exact versions and wheel SHA256 hashes; Transformers 4.57.1, Accelerate 1.12.0, Torch 2.10.0, expected CUDA build 12.8 |
| Dependency acquisition | 46 existing publisher artifacts plus two newly acquired, hash-verified universal wheels; all transitive constraints and Python-version checks reproduce offline from 48 retained official metadata records |
| Images and prompts | Six existing fixed requests, unchanged plain 448-by-448 RGB boards, nearest-neighbor 7-by-7 cells; no grid, labels, margins or external crop |
| Inference | Offline AutoProcessor and AutoModelForImageTextToText; explicit BF16 weights, native pointing metadata and logits constraints, one greedy generation per board |
| Retained evidence | Durable per-case admission, exact prompt and continuation IDs, raw special-token text, nested pointing metadata, native points, decode validity and timing |
| Scoring | Separate CPU replay rebuilds prompts and metadata, re-decodes the native sequence and tests exact occupied-cell containment for each predeclared target; reference masks stay outside inference inputs |
| Lifecycle | Owned installation/inference/census process groups, timeout/interruption cleanup, GPU cleanup verification, temporary-environment removal and final evidence writes all remain inside the bounded lifecycle |
| Completion | Provisional receipt, post-write witness, saved-cell marker, provider COMPLETE and independent replay are all needed; a saved receipt alone cannot certify completion |
| Review candidate | GPU/TPU/internet disabled, empty authority slot, live execution disabled and attachment bindings unconfirmed; notebook and supervisor refuse before any external process |

Requirements lock SHA256:
`5e844b7caff3cd6740f70f97d11fb91bf956ce59d15f86ce2b6c5c916da93ce7`.

Private review-candidate r1 lock SHA256:
`4359d7ad5b559f676e61c7f78a22ea04381aa3a21f13cf729318f2109c55297d`.

## Verification and limits

**87 Linux tests pass, with no failures, errors or skips.** The group includes
38 MolmoPoint tests and the reused inference, deployment and installation
process-group regressions. New checks cover six-call admission, no retries,
native-generation wiring, raw-output preservation, nested metadata serialization,
source drift, interrupted finalization and provider/witness/output binding.

An additional CPU replay rehearsal passes all six explicitly synthetic EOS-only
fixtures and refuses five mutations: requests, metadata, counter types, decoded
points and generation limits. These fixtures are not model answers or results.

With Transformers 4.57.1 and Accelerate 1.12.0, the pinned upstream processor
prepares all six images with native MolmoPoint logits constraints. Prompt counts
are 771, 777, 775, 776, 774 and 781; all pooling arrays have shape 725 by 4.
A **19,748,169-parameter tiny random model**, deliberately distinct from the 8B
checkpoint, generated four tokens on CPU. Its saved checkpoint also loads through
the real AutoModel factory with explicit BF16 conversion. No pretrained weights
were loaded for this rehearsal. It shares existing CPU-only dependencies and
does **not** prove an isolated 48-package CUDA installation or GPU compatibility.

Checkpoint bytes were verified during acquisition and again by the first review
build. A packaging-only independent rebuild reused that verified receipt, avoided
a third full weight read, and reproduced every review artifact byte for byte.

## Proposed single GPU pilot

| Limit | Proposed value; not authorized |
|---|---|
| Accelerator | Exactly one RTX PRO 6000; no fallback |
| Time | Requested Kaggle session timeout 3,600 s; worker 3,300 s; work cutoff 3,000 s; cleanup reserve 300 s |
| Stage ceilings | Installation 900 s; model loading 900 s; each generation 180 s |
| Generations | Six, one per board, at most 1,024 new tokens each; greedy, one beam |
| Actions / scorecards / automatic retries | Zero / zero / zero |
| Access | Private, account holder only; internet and TPU disabled |

Provider allocation, setup, mounting and release are outside the worker limit;
this is not an enforced one-hour full-job guarantee. A changed live package still
needs its own exact approval and single-use reservation/claim.

Private model/input datasets must first be staged and attached, the MolmoPoint
scoped-use evidence completed, and the exact final private package reviewed.
The current candidate hash cannot authorize a subsequently changed live package.

The pilot will establish whether the full model runs and whether its points land
inside these six requested objects. It will not establish object discovery,
object extent, obstacle mechanics, successful clicking, gameplay, or a causal
model-only improvement over InternVL. All previous attempts remain preserved.

Implementation: [worker](../research/molmopoint_identification_v1/inference.py),
[supervisor](../research/molmopoint_identification_v1/supervisor.py),
[CPU replay and scoring](../research/molmopoint_identification_v1/evaluate.py),
[review builder](../scripts/build_molmopoint_review.py).
