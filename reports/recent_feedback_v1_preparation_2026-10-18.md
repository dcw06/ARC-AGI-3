# Recent-feedback comparison: CPU preparation

The optional feedback-summary interface is implemented separately from the
completed r5 study. It compares **the same recent visual evidence presented
with or without deterministic summary text**. The r5 protocol, runtime source,
review snapshot, raw evidence and consumed attempts are unchanged. This is
CPU preparation, not a live launch package or model-performance result.

## Research question and intervention

Does making recent action outcomes explicit help the same agent adapt its
choices and complete level 1? The
[retained audit](feedback_availability_audit_2026-10-18.md) found 154 decisions
with an earlier same-action unchanged result already visible, including 123
with a matching pre-observation. This motivates testing feedback presentation
before extending memory.

| Held fixed | Both variants |
|---|---|
| Geometry | Same owner-reviewed initial objects, explicitly historical |
| Observation | Same 448px images, no overlay; initial/current images and at most two recent before/after transitions |
| Model and decoding | Existing Qwen model/revision; temperature 0, seed 0 |
| Controls and response | Same legal controls and action JSON; prediction abstention allowed |
| Proposed prospective budget | Same 24-action episode cap and 256 new-token cap; no extra reflection call |

| Variant | Difference |
|---|---|
| `recent_raw` | Exact existing request; no instruction or text changes |
| `recent_summary` | Same request with one additional final text block describing only the displayed recent transitions |

The summary is computed from the **prompt's embedded PNGs and historical
metadata**, rather than from privileged engine state or the unbounded trace.
It records the previous full action, source step, changed-cell count, inclusive
bounding box of all changed cells, before/after grid equality with the current
image, before/after state labels and the displayed after-level count.

Historical legal-action lists and before-level counts are excluded because
they were not in the old historical display. The bounding box describes pixel
changes, not an object, cause or progress region. No UI area is discarded, no
control function is inferred, no action is recommended, and no repeated action
is automatically forbidden. At step 0 the summary has no transition entries.

The draft summary limit is 4,096 UTF-8 bytes, with refusal instead of silent
truncation. This is distinct from the unchanged 256 **new-token** response cap.
Actual added token cost is measured separately. The comparison estimates the
entire summary interface's effect, not unaided visual reasoning or an isolated
wording effect.

## Implementation and independent checking

| Component | Behavior |
|---|---|
| `research/recent_feedback_v1/interface.py` | Deterministic, optional request enrichment; raw requests stay byte-equivalent under canonical serialization |
| `episodes.py` | Adapter around the unchanged r5 episode path; both variants use reviewed geometry; emitted and sent requests receive the identical transformation |
| `audit.py` | Independently recomputes summary counts/bounds from displayed pixels; then checks the original episode/request/action/terminal contract and optional engine replay |
| `protocol.json` | Draft comparison, explicit exclusions, outcomes and candidate counterbalanced order; no launch authority |
| Preparation CLI | Produces matched fixtures from independently certified retained evidence; checks the original source lock and evaluation/evidence pins |
| Token audit CLI | Offline native CPU processor audit using pinned Transformers 4.57.6 |
| Rehearsal CLI | Fresh isolated game environment, scripted loopback HTTP, recorded requests and real-engine replay; no neural inference |

The summary checker does not accept a producer's count or box as evidence. It
recalculates differences independently using row/column counts, removes the
verified summary and passes the remaining request through the original frozen
request reconstruction. Rehashing a false summary or changed system prompt
cannot make it pass. This is content verification, not a live lifecycle certificate.

## Prepared private fixtures

| Item | Result |
|---|---|
| Contexts | 144 retained reviewed-arm decisions: 24 per game across six games |
| Matched requests | 288: raw and summarized versions at each identical context |
| Maximum summary size on these contexts | 902 UTF-8 bytes |
| Prepared manifest SHA256 | `6258daebf784f351becd922e46b16ee838290564b1557ecce63079b70ada94c4` |
| CPU draft-lock SHA256 | `ec66c2805038bfe79a053087b76f783ed97f6bc5b8843755caba9c5e37b86f09` |

These are **fixed historical contexts**, not future agent trajectories. They
do not contain new neural responses and cannot measure how the intervention
changes later gameplay. The private fixtures and receipts are under the main
workspace's `.cache/github-review/recent-feedback-comparison-2026-10-18/`.
`teacher-forced-inputs-r3/` binds the final CPU preparation sources; earlier
draft revisions are preserved. No review notebook, reservation or claim exists
for this successor.

## Completed CPU validation

| Check | Result |
|---|---|
| Linux combined suite | **104 tests passed**, zero failures, errors or skips |
| Focused new checks | 14 interface/episode checks plus nine retained-feedback audit checks |
| Exact baseline preservation | Raw requests recover the old body; removing and independently checking the summary recovers that same body |
| Native token audit | All 288 prepared requests pass the real pinned Transformers 4.57.6 processor |
| Maximum prompt tokens | Raw 4,607; summary 4,816 |
| Added summary tokens | 56–229, depending on the retained context |
| Connected rehearsal | Fresh offline 31-wheel game install; 12 four-action episodes, 48 scripted HTTP replies; all 12 independent engine replays pass |
| Request accounting | Journaled requests equal the actual scripted-server requests, in order; one response per call, no extra reflection calls |
| Cleanup | Owned process groups absent; temporary interpreter, processor fixture and replay trees removed |

The local game rehearsal used **120 offline actions including replay resets**:
48 play dispatches + 12 resets + 48 replay dispatches + 12 replay resets. It
opened 24 local scorecards in total. There were zero neural model requests,
online game calls, provider writes or GPU jobs. Its CPU processor is Transformers
4.57.1; the separate token audit above uses the exact pinned 4.57.6 version.
The rehearsal exercises four decisions per episode, including truncation to the
last two transitions; it does not certify a full 24-action future trajectory.

The first network-namespace check refused before installation or gameplay
because `/sys/class/net` still reflected the host's mounted sysfs. The corrected
check uses the process-local `/proc/net/dev`; the original refusal log is kept.
The deliberately killed watchdog regression emits Python's semaphore-recovery
warning, as in previous checks; its child-absence assertion passes.

| Private validation receipt | SHA256 |
|---|---|
| `linux-tests-r2.json` | `ff15580b4ee0dfcca1034365a25ac56d52299eb83775a9f711a2adc87a8894f7` |
| `native-token-audit-r3.json` | `f505e9c77305da132dbda15b0021ccfba424ac90f6281e1e807240ea8008d69a` |
| `connected-CPU-r2/receipt.json` | `ac85542b1cc92be20eb4d9f7b98e5bbeca5c41639d4d38c099d02acd48daf001` |
| `connected-CPU-r2/lifecycle.json` | `cbb13351df673a50474a4d1df890afc50eefd303b42721df2c524ee00fa0ec84` |

## Remaining before prospective inference

Finalize operational secondary metrics and prospective token/resource limits,
then build and review the exact bounded live package and independent evaluator.
Retained-context token measurements do not bound all future trajectories.
The first-level completion outcome stays primary; action diversity or escaping
one unchanged frame is diagnostic only. Include all six exposed game pairs
and all failures without treating individual actions as independent samples.

Fresh scoped-use/source approval, compute authorization and a new single-use
reservation are required for that eventual package. No old attempt or approval
is reused. No dataset upload, Kaggle write or GPU job occurred in this work.
