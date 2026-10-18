# Initial geometry assistance: paired short-gameplay preparation

**Status: CPU preparation verified; live launcher and final GPU package pending. No LLM gameplay results.**

**Provenance correction:** the r1 admission used a hash-pinned private comparison
without a committed producer. [Preparation r2](initial_geometry_automatic_provenance_fix_2026-10-18.md)
now reproduces native pointing/deployment evidence and raw SAM masks through
committed code before admitting either arm. The original masks and the r1
receipts below are preserved; r2 has its own protocol, input manifest and review
snapshot. Recorded success flags alone no longer admit the automatic arm.

The owner chose short gameplay with geometry supplied only for the initial
frame. This is a new development experiment, separate from Track 1's consumed
attempts. No earlier attempt, approval or scientific result is replaced.

| Research question | Proposed comparison | Interpretation limit |
|---|---|---|
| Does better starting object geometry improve first-level completion? | Retained automatic MolmoPoint + SAM 2.1 geometry versus owner-reviewed whole-object geometry, using one shared action policy | Tests the complete starting representation, including inventory omissions and boundaries; not boundary accuracy alone |
| Does assistance improve initial click localization? | First policy action, when it is ACTION6: does its point occupy a reviewed whole-object cell? | Object containment does not establish a correct interaction region, mechanic or intended target; later clicks cannot use stale initial labels |
| Can the shared policy predict visible consequences? | Record yes/no/unknown before dispatch and compare with the next final image | Includes counters and interface changes; not evidence that a game rule or causal mechanism was learned |

## Paired design

| Setting | Draft r1 |
|---|---|
| Games | `ls20`, `s5i5`, `cd82`, `ft09`, `ka59`, `sc25`, reviewed level-1 starts, seed 0 |
| Episodes | One per arm per game: 12 total; AB/BA counterbalanced across games |
| Per-episode cap | 24 policy calls/actions; stop on first level completion, game over or cap; an invalid answer ends the episode without repair |
| Shared policy | New Qwen3-VL-30B-A3B-Instruct-FP8 visual measurement policy at revision `d9748a51…`; not an unchanged E1S-R baseline |
| Geometry interface | Lossless occupied-cell row runs, inclusive bounding boxes and a centroid-nearest **occupied** anchor; neutral IDs only |
| Context | Historical step-0 image and geometry, current image, latest two before/after transitions; older omissions explicitly counted |
| Images | Plain 448 × 448, exact 7 × 7 enlargement of each original cell, no overlays |
| Rules and controls | No game-specific meanings, roles, strategies or human action logs; common legal-action/coordinate API only |
| Output | One strict JSON action and a pre-action visible-change prediction; no fallback, rounding, clamping or automatic retry |
| Primary analysis | Six paired first-level-completion results, reported per game; no independent-sample claim for individual steps |

The same historical-geometry warning appears in both arms at every step. Initial
masks are never updated, tracked or certified as current positions. Fresh images
follow every dispatch. Duplicate and empty geometry proposals remain proposals;
no reviewed geometry repairs the automatic arm. Both arms use the same anchor
construction, not method-specific pointing hints. Input-token costs can differ
because the supplied inventories differ and must be reported by arm.

| Game | Automatic proposals | Reviewed whole objects |
|---|---:|---:|
| ls20 | 0 | 3 |
| s5i5 | 6 | 7 |
| cd82 | 5 | 5 |
| ft09 | 2 | 6 |
| ka59 | 6 | 10 |
| sc25 | 3 | 6 |
| Total | 22 | 37 |

The invalid automatic ls20 response is retained as an empty inventory. The
reviewed arm excludes the 57 separately labelled parts and strips object names,
roles, parent names, functions, reviewer text, source methods and old results.
Every mask is tied to the exact initial board. Preparation verifies independently
fixed hashes before reading reference or automatic-mask content.

## Completed CPU checks

| Check | Result |
|---|---|
| New state-machine/geometry/replay regressions | 30 pass on Windows and Linux, no skips |
| Offline game installation | All 31 retained wheels verified and installed with `--no-index --require-hashes`; `MPLBACKEND=Agg` |
| Real engine versions | arc-agi 0.9.8, arcengine 0.9.3, numpy 2.4.4, Python 3.12/Linux |
| Starting-board binding | All 12 episode starts reproduce the reviewed board exactly |
| Scripted rehearsal | 12 two-action episodes; 24 scripted decisions, **zero model calls** |
| Fresh independent engine replay | All 12 traces reproduce every observation and transition |
| CPU action accounting, including replay | 48 policy dispatches + 24 bootstrap resets = 72 offline actions; 24 local scorecards; zero online calls or leaderboard submissions |
| Native Qwen multimodal preparation | 24 real CPU processor calls, step 0 and synthetic step 23 for both arms on all six boards |
| Token agreement | Native processor count equals independently expanded image-token count in every case; maximum 4,609 input tokens |
| Required server image allowance | Six images per request, to accommodate initial/current and two historical before/after pairs |

The native check uses Torch 2.10.0+cpu, torchvision 0.25.0+cpu,
transformers 4.57.6 and Pillow 12.2.0. It loads hash-verified tokenizer/processor
files only, with networking disabled. It loads no weights and proves no GPU or
vLLM behavior. Synthetic histories test the API and image accounting; actual
future trajectories still need per-request native/server token checks.

Regression coverage includes hollow/disconnected masks, empty/duplicate
proposals, semantic-field rejection, fresh-image/historical-mask separation,
invalid outputs without repairs, interruption at evidence writing, inference
overruns, admission closing during a pre-dispatch write, and late final writes.
Independent replay reconstructs the entire prompt and request, validates the
dispatch chain, re-derives terminal labels and totals, and rejects rehashed
request mutations, changed observations and boolean counters.

The episode component deliberately emits **no lifecycle certificate**, even
after successful content replay. Its deadline admission checks cannot interrupt
a stalled injected call. A separately supervised live runtime remains necessary.

Setup observations are retained privately: the first host interpreter lacked
pip; a Windows-mounted installation subsequently exceeded its local setup
timeout. Its exact remaining installer child was stopped. A Linux temporary
installation succeeded. WSL cleared that temporary interpreter before a later
command, so the successful final preparation ran installation and rehearsal in
one WSL lifetime. These are CPU setup records, not consumed GPU attempts.

## Remaining live preparation and proposed authorization scope

No Kaggle write, reservation, GPU attempt or model generation was made for this
study. `live_runs_enabled` remains false. In particular, an episode-content audit
must never be substituted for cleanup/finalization evidence.

Before asking for launch approval, the live package must include the isolated
game and model interpreters; full wheel/model-byte verification; a six-image
vLLM configuration; absolute inference and engine-call deadlines; ownership of
every child process; GPU/process/temp cleanup; fail-closed finalization; exact
private notebook/image/attachment bindings; and the matching scoped-use records.
The final review must bind that executable package and its evidence. Earlier
zero-action pointing approvals do not authorize gameplay.

| Proposed ceiling, **not authorized** | Value |
|---|---:|
| Accelerator | Exactly one RTX PRO 6000 |
| Session timeout requested / worker limit | 3,600 s / 3,300 s |
| Action/request admission cutoff / cleanup reserve | 3,000 s / 300 s |
| Fresh attempts / automatic retries | 1 / 0 |
| Study generations | ≤288 |
| Startup canary | ≤1; total generations ≤289 |
| Counted model-server HTTP requests | ≤300, subject to the final request plan |
| New tokens per study answer | ≤256 |
| Offline engine actions | ≤288 policy dispatches + 12 bootstrap resets = 300 |
| Offline local scorecards / online scorecards | ≤12 / 0 |
| Online game calls / leaderboard submissions | 0 / 0 |

Allocation, setup, mounting and GPU release may extend provider time beyond the
requested session timeout, as in the owner's previously accepted timeout model.
A run with missing pairs or failed lifecycle checks cannot support a complete
paired-study verdict. All attempts and partial evidence must remain on record.

## Reproducibility bindings

| Retained item | SHA256 |
|---|---|
| Owner-confirmed reference | `5304e35b1f0ee17e0ffd77293ac4fba260bbfa08755c2d48e914ed72ac9cec63` |
| Verified automatic source evaluation | `32eae91f0e49ad7da71e87e2b82b24f16d1dba440fe115522b47d1d5d53600ff` |
| Verified SAM masks/evaluation | `baaf83f11b36343580a80e996c166e23bd2ece31a561173dbf02ace9d8290408` |
| Private geometry input manifest | `95fa2d57de3cf9d40732a731d49aeebf9c57bf896ec97f4b5e4e02f14502b8bd` |
| Draft protocol r1 | `ea17c055100d62100e5dcd95a0ee280d6fdd208dcaf09ef5c88309610df9969b` |
| Game requirements lock | `9cbd701f16f3e3441692d9328f57b1f3c15c168a7e227431223cf9a3ddb1eb7d` |

Private inputs, masks, traces and processor receipts remain git-ignored. Public
code provides preparation, a CPU-only scripted rehearsal, native prompt auditing
and an episode-content evaluator. **It does not yet provide a live launcher.**
