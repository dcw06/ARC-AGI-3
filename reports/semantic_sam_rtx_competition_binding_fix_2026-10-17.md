# Semantic-SAM notebook: restore the RTX competition association

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
remain preserved. A GPU-disabled save-only update of the same notebook is the
next configuration step. It clears the consumed authority in the new saved
version while retaining historical version 1. No new GPU launch is authorized
by this repair; no training or segmentation generation is used as a probe.

After the save, independently verify its private/offline settings, exact source,
competition and input attachments. Then require the owner to reopen the notebook
and inspect the Accelerator menu with None selected. **Visible RTX availability
remains unverified until that observation is supplied.** Even then, any future
launch needs fresh lock-bound approval and a new single-use claim, and must
retain the actual-device guard. A requested machine-shape label is insufficient.
