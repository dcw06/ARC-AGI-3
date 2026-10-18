# Semantic-SAM notebook: restore the RTX competition association

**Verified outcome:** corrected r3 version 3 completed on an actual RTX PRO 6000
Blackwell. Lifecycle and replay checks pass; both segmentation modes score 0/6
whole-object matches on the single sc25 board. See the [results and limitations](semantic_sam_gpu_smoke_attempt2_results_2026-10-17.md).
The menu/submission observations below describe the preceding preparation.

**Subsequent owner confirmation:** the owner reports RTX PRO 6000 now appears
in this notebook's menu. After fresh r3 authorization, [one new attempt was
submitted as version 3](semantic_sam_gpu_smoke_attempt2_status_2026-10-17.md).
At submission its retained status was RUNNING. The menu observation was
owner-reported; actual allocation was subsequently verified by runtime evidence.

The failed Semantic-SAM notebook omitted the ARC-AGI-3 competition attachment.
Earlier retained RTX-configured smoke and object-identification notebooks attach
that competition while using the same immutable image. The owner's editor photo
of the unbound Semantic-SAM notebook shows None, T4 x2 and TPU options, with no
RTX entry. Runtime evidence independently confirms that its only attempted run
received two T4s and correctly refused before model loading.

The [official ARC Prize starter](https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter#choosing-an-accelerator)
describes RTX 6000 as reserved for ARC-AGI-3 notebooks. Together with the retained
earlier competition-binding repair in this project, this identifies a concrete
configuration defect. It does not prove that competition attachment alone will
make RTX visible for this account or guarantee future allocation.

## Changes

| Layer | Corrected behavior |
|---|---|
| Protocol | Requires exactly `arc-prize-2026-arc-agi-3` in `competition_sources` |
| Live notebook metadata | Attaches that competition with the existing private transport dataset |
| Actual GPU save specification | Binds the same competition; omission/substitution is refused |
| Runtime authority check | Refuses a protocol missing the exact competition binding |
| Disabled review notebook | Empty authority, GPU/TPU/internet off, notebook accelerator metadata `none` |
| Review-save guard | Allows QUICK_SAVE only; refuses run-all, GPU/TPU/internet enablement, altered source or missing attachments |

Competition attachment associates this legitimate ARC-AGI-3 runtime experiment
with the competition's notebook configuration. The worker does not read competition
files, install from them, play games, request scorecards or submit to a leaderboard.
The same checkpoint, retained seeds, plain image, fixed granularity, isolated
runtime and one-image seeded/automatic scientific scope remain in place.

## Validation

- Two retained regression tests fail on the original builder: it accepted missing,
  empty and substituted protocol associations, and emitted an empty competition
  list despite the supplied correct association. The repaired tests pass.
- **123 connected Linux CPU tests pass**, with zero failures, errors or skips.
  This includes review-save refusal tests and the process/lifecycle regressions.
- The final private r3 snapshot and its independent rebuild are byte-identical.
  Missing authority refuses before staging or GPU queries. The actual installed
  SDK's QUICK_SAVE serialization passes the offline request guard.

All prior private packages, failure evidence and the consumed GPU reservation
remain preserved. One GPU-disabled QUICK_SAVE of the same notebook completed
successfully as **version 2**. It clears the consumed authority in the new saved
version while retaining historical failed version 1. No new GPU launch is
authorized by this repair; no training or segmentation generation was used as
a probe.

Read-only pullback verifies the exact r3 review source, empty authority, private
access, GPU/TPU/internet off, unchanged image/input attachment and the added
competition association. The final provider status is COMPLETE. Its six log
entries contain nbconvert HTML conversion and dependency syntax warnings, no
cell/model output; there are no output files. The save requested no cell
execution. A separate offline audit matches the actual request/claim hash and
saved source, confirms that the scientific scope is unchanged and that all
staging/cleanup functions are identical to the prior snapshot. The final private
review lock, provider evidence and consumed save claim remain git-ignored.

The owner must now reopen the updated notebook and inspect the Accelerator
menu with None selected. **Visible RTX availability
remains unverified until that observation is supplied.** Even then, any future
launch needs fresh lock-bound approval and a new single-use claim, and must
retain the actual-device guard. A requested machine-shape label is insufficient.
