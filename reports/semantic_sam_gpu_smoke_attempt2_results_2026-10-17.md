# Semantic-SAM r3: runtime complete, sc25 segmentation unsuccessful

The corrected r3 package completed its single authorized GPU attempt as private
Kaggle version 3. Actual runtime evidence confirms **one NVIDIA RTX PRO 6000
Blackwell Server Edition**. Both seeded and automatic Semantic-SAM L inference
ran, and the independent offline lifecycle audit and raw-mask replay pass.
Whole-object segmentation does not succeed on this smoke frame.

| Condition | Raw proposals | Scored proposals | Empty proposals | Whole-object matches (IoU >= 0.5) | Exact masks | Precision |
|---|---:|---:|---:|---:|---:|---:|
| Semantic-SAM L, seeded | 3 | 3 | 0 | 0/6 | 0/6 | 0% |
| Semantic-SAM L, automatic | 1 | 1 | 0 | 0/6 | 0/6 | 0% |

Both conditions use only the original sc25 / board-06, a plain 448 x 448 image,
the existing fixed 640 x 640 Semantic-SAM preprocessing, and predeclared
granularity **1**. Seeded mode uses the same three uncorrected MolmoPoint points.
Automatic mode uses the fixed 16 x 16 grid, batch size 16 and quality-based
96-proposal ceiling. Only one proposal survived the upstream automatic generator;
none was discarded by the downstream proposal budget. No granularity was chosen
using reference scores.

Visual inspection of every scored proposal on the hash-bound source board shows
large, mostly background masks: the three seeded masks contain 3,623, 3,835 and
3,905 original cells, and the automatic mask contains 3,444 of 4,096 cells. This
explains the failed whole-object matches, but does not establish the underlying
cause or performance at other granularities. It does not justify declaring the
model generally incapable of object segmentation.

## Technical verification

| Check | Retained result |
|---|---|
| Provider | COMPLETE, saved version 3, exact authorized source |
| Package | Review-lock SHA256 `956a28ee2a6c07c219656efa29009eff043a6cbfe522548d093d584901500625` |
| Runtime binding | Runtime-lock SHA256 `7e5798d3eac24c1b3942d76dac422dbc890816887b8f28ff3e060e90b68420f8` |
| Configuration | Private, internet/TPU off, immutable image and exact competition/transport attachments verified |
| Actual GPU | One RTX PRO 6000 Blackwell; initial and final identity agree |
| Mounted bytes | All 21 transport files checked; all 12 originals restored with matching hashes and both pinned manifests |
| Worker duration | 113.495658 seconds through the completion witness, below the 3,300-second worker limit |
| Finalization | Result hash, completion witness, unique provider-log return marker and provider COMPLETE verified together |
| Output integrity | All 22 output-manifest hashes match; both worker manifests and scope records match |
| Environment | Exact 99-package version receipt, pinned checkpoint and upstream source revision verified |
| Replay | Both raw NPZ outputs reproduce the retained proposals; independent vectorized majority projection agrees |
| Board/reference binding | Input image hash, seed binding, reference grid and externally frozen reference/source manifest verified before scoring |
| Cleanup | Six owned process groups absent, no GPU compute process, owned temporary runtime and sandbox removed |
| Scope | Zero new MolmoPoint generations, model HTTP requests, game actions and scorecards |

Worker timing excludes provider allocation, mounting before the first cell and
GPU release. Those remain outside the accepted session/worker time policy.
Provider attachment metadata does not expose an independent saved version label;
the version-1 request and actual mounted-byte identity establish the consumed
content. The reference manifest was frozen retrospectively for the earlier
retained comparisons, before this GPU attempt; it is an integrity anchor, not
an independent reference annotation or a preregistration claim.

## Interpretation and next step

This establishes that the pinned Semantic-SAM runtime can load and infer on the
actual RTX PRO 6000. It does **not** establish useful whole-object boundaries on
sc25 at granularity 1, six-board accuracy or gameplay ability. The earlier UnSAM
CPU smokes also scored 0/6 on this board at their separate granularity 0.1; this
is not a general ranking across models or granularities.

The next useful preparation is a review of this granularity's intended semantics
and a separately declared boundary diagnostic, rather than treating runtime
completion as clearance for a full six-board study. No further inference was
started or authorized while collecting and analyzing this attempt.

The first GPU allocation failure remains consumed and preserved. Version 2's
disabled review save is unchanged. This second GPU attempt is also consumed;
there were no automatic retries. Raw outputs, exact notebook, approvals, masks,
reference files and an interactive local mask viewer remain private and
git-ignored. Only this aggregate report is public.
