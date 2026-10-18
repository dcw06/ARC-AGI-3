# MolmoPoint plus SAM 2.1: requested detailed-prompt repeat

October 17, 2026. The owner explicitly requested a fresh submission of the
pipeline behind the earlier **6/37 exact SAM masks**, with the revised prompt
and token limit. One private GPU notebook was submitted once, without retries.
This is a submission record, not a new model-performance result.

| Item | Frozen condition / verification |
|---|---|
| MolmoPoint | Same pinned checkpoint, dependencies, BF16, native preprocessing/decoder and greedy generation |
| Images | Same six plain 448 × 448 development boards; original 64 × 64 cells enlarged 7× |
| Prompt | Exact revised eight-rule instruction, 3,290 characters; SHA256 `b79720a4f2638aa410aaafaed96df63666cd47844436a86b3b43e2d20e92e226` |
| Input limit | 4,096 characters, explicitly forwarded to the adapter |
| Output limit | Six generations, at most 4,096 new tokens each / 24,576 total |
| Requests versus original discovery run | Only the instruction and its input-character allowance differ; the original output cap was already 4,096 |
| Requests versus latest completed detailed run | Identical; this is an owner-requested repeat, not a new prompt condition |
| SAM stage | Original separate local CPU method, using only this new run's independently replayed valid seeds |
| Reference | Same owner-confirmed 37 whole objects; no masks supplied to model inference |
| Package | Two deterministic builds agree; source-bound previous validation remains exact; unapproved notebook refuses before extraction |
| Read-only preflight | Account, quota, unused target, dataset versions/inventories and private access pass |
| SDK / saved source | Serialized request and saved notebook, authority and available settings match |
| Provider submission | One accepted SaveKernel, saved version 1, no rejected sources; 2026-10-18 02:46 UTC / October 17 22:46 America/New_York |
| Accelerator | RTX PRO 6000 requested; actual allocation must still pass the runtime guard |
| Latest read-only status | RUNNING; this alone does not establish actual hardware or useful model output |
| Attempts | Fresh single-use reservation consumed; every earlier attempt remains preserved |

Review-lock SHA256:
`cdaab9fe9c10fe7fb14699d2ef89fd831ebb2e88a225d0c2643f8a0c68b672aa`

Runtime-lock SHA256:
`9b6e0dd01db5d9f0bd65d8f9ebec59e5d4d32fcce5069fb2dec5e3b73fd257b9`

The request retains the existing bounds: exactly one RTX PRO 6000, requested
Kaggle session timeout 3,600 seconds, worker 3,300 seconds, private account-only
access, internet and TPU off, zero game actions or scorecards, and no automatic
retries. The accepted provider-overhead qualification remains: allocation,
setup, mounting and GPU release may extend total time beyond one hour. The API
does not independently echo timeout or dataset-version labels; request pins
and the runtime's mandatory mounted-byte verification remain necessary.

The [original SAM result](sam21_retained_seed_boundaries_v1_results_2026-10-16.md)
was a two-stage experiment: a Kaggle MolmoPoint run, followed by local CPU SAM
inference. It was not one GPU notebook containing both models. This repeat
keeps that separation. The original SAM checkpoint was rehashed locally before
submission. Its fixed policy remains positive seeds, three candidates, highest
predicted quality with earliest-index tie break, original-resolution logits
strictly above zero, and at least 25 of 49 foreground pixels per board cell.
There is no reference-based selection, seed snapping, repair or deduplication.
The postprocessing plan was frozen before this run's output was available.

The latest completed [detailed-prompt attempt](molmopoint_detailed_generic_v2_attempt2_results_2026-10-17.md)
returned zero native points. Reusing its outputs with SAM could not restore
unseeded objects. The present repeat has not demonstrated an improvement. If
the new run also has empty inventories, retain zero proposals rather than
inventing seeds or borrowing the earlier 22 points. Invalid responses receive
no partial-output salvage.

Collection and independent replay remain pending. They must establish actual
hardware, all mounted bytes, complete evidence, native decoding, cleanup and
finalization before any scientific comparison. Raw outputs and private launch
records remain git-ignored. This report authorizes no further attempt.
