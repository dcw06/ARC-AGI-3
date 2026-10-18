# MolmoPoint detailed prompt: failed input guard, corrected before another run

The first detailed-instruction attempt is ERROR and remains consumed. It ran on
the requested RTX PRO 6000, installed successfully and loaded the model, then
failed before its first pretrained generation. This is a local integration
defect, not an object-localization result or evidence that the instruction is
too difficult for MolmoPoint.

The failure is:

```text
adapter.py, prepare_prompt_inputs
ValueError: bounded pointing prompt required
```

The adapter retained a **1,000-character input limit**. The owner's instruction
contains **3,290 characters**, so it was rejected. The 4,096-token generation cap
controls output and does not change that separate input guard. The initial
processor check called the upstream processor directly and bypassed the guard;
the earlier tests checked the new prompt profile without exercising this actual
adapter call. That validation gap allowed the defective package to be submitted.

## Preserved failure evidence

| Check | Result |
|---|---|
| Provider / notebook | ERROR, saved version 1; exact authorized source and identity verified |
| Actual hardware | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Mounted integrity | All 220 mounted files hash-checked: 177 publisher files, 34 model files, nine input-dataset files |
| Installation | Isolated installation and dependency checks passed |
| Model loading | Completed before the first durable case admission |
| Generation | One admission retained; first call refused in input preparation; no pretrained generation started or completed |
| Worker duration | 399.596 seconds through the failure receipt, well below the worker limit |
| Process cleanup | Eight registered process groups absent, no cleanup error or interruption |
| GPU / temporary environment | GPU cleanup verified; temporary environment removed |
| Finalization | Failure result retained; no successful completion witness exists |
| Collection | Read-only, hashes verified; no cancellation, retry or new submission |

The run-level generation counter is unavailable because the worker never wrote
its summary. Zero generation starts are derived from the first-call traceback
and absence of raw/finalized cases, rather than from an invented summary count.
No score is reported. Private raw logs, notebook, admission, failure receipt and
independent audit remain git-ignored.

Failed review-lock SHA256:
`29d7b398683fd10fd02dd0fc972d3339bc43526873fba3781f86972858f775ef`

## Correction and validation

- The adapter accepts an explicitly selected **4,096-character input limit** for
  the detailed profile. The original 1,000-character default stays in place for
  legacy calls. Only these two bounded integer limits are accepted.
- Every detailed-profile request binds `max_prompt_characters: 4096`, and the
  real inference path forwards it into the actual adapter. Missing or mutated
  request fields are refused. The **4,096-new-token output limit is unchanged**.
- A CPU reproduction loads the retained failed adapter: the exact instruction
  is rejected with the same error. The corrected adapter accepts it unchanged.
- Regressions exercise the real adapter through the runtime call, over-limit
  refusal, immutable request bounds, and legacy compatibility.
- A stronger offline rehearsal invokes the actual adapter and pinned native
  logits processor on all six boards with a tiny random CPU model. It also
  exercises one four-token random generation and BF16 tiny checkpoint loading.
  This is API qualification, not pretrained model inference or localization.
- A separately named candidate uses a canonical matching notebook title/slug;
  an explicit mismatched successor title is rejected. The failed notebook is
  not overwritten or rerun.

The exact owner instruction, six images, model checkpoint, dependencies,
reference masks and compute ceilings remain unchanged. The corrected request
metadata and source require a new review lock. The failed attempt's approval,
reservation and claim cannot authorize the corrected package. No second GPU
attempt has been launched automatically.

## Corrected candidate, awaiting fresh approval

195 distinct Linux checks are covered without unresolved skips: 193 passed in
the offline CPU interpreter, and its two missing-SDK skips passed separately in
the installed operator interpreter. Original receipts and logs are kept, with
no double counting. The actual native-adapter rehearsal passes on all six
images with 1,358 input tokens each. The old 1,000-character refusal also
reproduces from the retained failed source, before the same prompt passes the
corrected guard.

Two corrected private builds have the identical review-lock SHA256:
`c7c3d890d0c00383bba1aa0ae5d9a42b261fa6b0d408bd79a5e1455c8bb4b7ed`

Runtime-lock SHA256:
`890a5d0de61b49a17117ac36bb0b12636c1b8931a0d2dd25c6279c7519041511`

The corrected review notebook refuses before extraction or GPU use while
authority is empty. Read-only provider checks still find the same dataset
versions/inventories and a distinct unused target for the corrected candidate.
There is no new approval, reservation or launch claim. The existing launch
guard requires fresh authority bound to this changed hash before another
submission; the earlier consumed authorization cannot be reused.
