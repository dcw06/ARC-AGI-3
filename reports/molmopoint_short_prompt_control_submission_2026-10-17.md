# MolmoPoint: exact original short-prompt control submitted once

**Terminal update:** [completed and independently replayed](molmopoint_short_prompt_control_results_2026-10-17.md): 22 native points, 12/37 SAM matches and 6/37 exact masks. Actual RTX PRO 6000 and cleanup verified; ls20 remains invalid at the token cap. This submission record remains preserved.

October 17, 2026. The owner approved proceeding after the recommendation to
restore the original short prompt as a control. **One six-board control was
submitted once.** No additional prompt variant or retry is covered or launched.

The exact original instruction is restored:

> Point to each distinct visible whole object in this game image. Treat a composite object as one object, without also listing its internal parts. Include separate visible interface objects. Do not count background as an object.

| Item | Verified preparation / submission |
|---|---|
| Prompt | Exact original 226-character instruction; SHA256 `c7d4c53e4d224b7efb0c468b9b14769dc44865ab425c2705df8eb27666f82f64` |
| Six requests and six images | All seven executable input files byte-identical to the original discovery run |
| Effective scientific protocol | Unchanged; new notebook binding and explicit naming of the original implicit legacy profile |
| Model / runtime | Same pinned MolmoPoint checkpoint, immutable image, dependencies, BF16, native preprocessing/decoder and greedy generation |
| Generation budget | Six generations, at most 4,096 new tokens each / 24,576 total |
| Package checks | Two deterministic builds agree; current sources still match the retained 195-test coverage receipt; empty-authority notebook refuses |
| Read-only preflight | Account, available quota, unused target, dataset identities/inventories and private access pass |
| SDK / saved package | Exact serialized request and saved source/authority/available settings verified |
| Provider write | One accepted SaveKernel, saved version 1, no rejected sources, no automatic retries |
| Accelerator | RTX PRO 6000 requested; runtime must establish actual allocation before model loading |
| Latest read-only status | RUNNING; useful outputs and actual allocation remain unverified until collection |
| Prior attempts | Every consumed claim, failure and completed result remains preserved |

Review-lock SHA256:
`6f5f2611163b10ee91f583d9a68edb244f5d2fc04dec646a8b470a48ebacc3c2`

Runtime-lock SHA256:
`845581a44e1366814c841e0f6cb107bfa6f234a83d5189ed5fb290cd6146dd33`

Submission: 2026-10-18 03:27 UTC / October 17 23:27 America/New_York.

Scope remains one RTX PRO 6000, requested Kaggle session timeout 3,600 seconds,
worker limit 3,300 seconds, internet and TPU off, private account-only notebook
and raw outputs, zero game actions and scorecards, no automatic retries. The
accepted provider-overhead qualification remains: allocation, setup, mounting
and GPU release can extend total time beyond one hour. The API does not
independently echo timeout or dataset-version labels; validated request pins,
mounted-byte checks and the runtime device guard remain necessary.

This control tests whether native pointing returns when the original prompt
is restored under the current verified wrapper. Both completed detailed-prompt
runs returned the same zero-point outputs. A local CPU diagnostic of the pinned
upstream grammar processor confirmed that it permits ordinary text and EOS
before a point starts; it constrains point-token order rather than requiring
a pointing response. The diagnostic loaded no model weights, made no model
forward/generation calls and used no GPU. It does not identify which wording
caused the pretrained model to choose a text or empty response.

The original SAM 2.1 checkpoint was rehashed again before this submission.
Its separate offline CPU postprocessing plan is frozen: only new independently
replayed native seeds, positive point prompts, three candidate masks selected
by predicted quality, original-resolution logits strictly above zero and a
25-of-49 pixel board-cell projection. No label-based selection, borrowed seeds,
repair, snapping or duplicate suppression. Invalid responses and empty seed
sets are skipped without partial-output salvage. References remain outside
the executable notebook payload and are hash-bound before scoring.

Collection, independent replay and the SAM stage remain pending. Reports will
distinguish parser validity, nonempty native pointing and non-point text while
preserving the frozen scoring rules. No performance improvement is claimed
at submission time. A later concise prompt variant needs its own package and
fresh compute authority; it is not an automatic continuation of this attempt.

Related: [original SAM result](sam21_retained_seed_boundaries_v1_results_2026-10-16.md),
[completed detailed-prompt repeat](molmopoint_sam21_detailed_repeat_results_2026-10-17.md).
Private launch records and raw evidence remain git-ignored.
