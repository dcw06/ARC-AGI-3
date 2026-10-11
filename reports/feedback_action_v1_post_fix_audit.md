# Track 1 (feedback_action_v1): post-fix audit of the retained evidence

**Status: study closed (owner decision, October 11, 2026) with two qualifications.**
1. **Technical completeness depends on the evaluator.** Both sessions are technically complete under the original
   evaluator (`edc9566`, the package that ran). Under the post-fix evaluator (`d0c6518`) both are technically
   incomplete (F1), because the pre-fix runtime wrote no finalization receipt; every evidence-level check passes
   there, and the findings below are identical.
2. **Finalization is not certified.** The recorded deadline margins (2,479 s and 2,438 s) make a late-finalization
   overrun unlikely, but the missing finalization evidence prevents certification
   (`reports/feedback_action_v1_post_fix_audit.md`).

**What this is.** A read-only audit of the two completed sessions' retained evidence with the evaluator at `d0c6518`,
which includes the six prelaunch-gap repairs (`3aeeb65`, `d218567`, `3f140bb`, `641ea70`) and the fail-closed
finalization (`cfda982`). No provider call was made, and nothing was relaunched; every attempt is preserved. This is
the operator's own audit, not the independent validation, which remains pending.

## Why it was needed

Both runs used the fixed private package with lock `23cb7142…`, built from `edc9566`. The six repairs and the
fail-closed finalization were committed afterwards to the same branch by another session, at 03:35–04:55 UTC on
October 11, before the replacement launch (05:11 UTC). The operator did not check the branch history before building
and launching, so the runs used the pre-fix package. The owner's authorizations named that package's lock, so the
runs were authorized, but they lack those fixes. A separate public r7/r8 and private r8 package incorporating them
was prepared and was not used.

## Method

- A private audit checkout of `d0c6518` with the same three private bindings, and its own GPU-disabled private review
  snapshot (lock `901c727a09390c43f153d0661d8184bac587b5495fa4ded16c1963a198cc72ca`; only `runtime.json` differs from
  public r8; 12 review documents, including the replay contract).
- `scripts/evaluate_feedback_action_v1.evaluate_output` in live mode over each session's retained output, then
  `live_evaluation.evaluate_sessions`, which recomputes both evaluations before pooling.

## Results

| Check (evaluator at `d0c6518`) | Session 1 (`fa1-s1r-d1bc3d6b…`) | Session 2 (`fa1-s2-c1264812…`) |
|---|---|---|
| Evidence manifest and run evidence | verified; run complete | verified; run complete |
| Independent reconstruction of every frozen request from retained transitions (the replay contract) | passed | passed |
| Terminal labels, final states, pair completion and call/action/token totals derived from events | 0 problems | 0 problems |
| Canary token types and frozen bounds | no lifecycle error | no lifecycle error |
| F2a–F6 | none | none |
| Review lock of the evaluating checkout | verified (`901c727a…`) | verified (`901c727a…`) |
| **Lifecycle finalization and source removal certified** | **no**: the pre-fix runtime wrote no finalization receipt (`finalization_guard_version` absent) | **no**: same |
| Classification under the post-fix rules | technically incomplete (F1) | technically incomplete (F1) |

**Two-session evaluation, recomputed:** not technically valid in both sessions, because of F1 above. The solving
table, the pooled rates and the exploratory thresholds are **identical** to the original evaluation: no solving
claim (zero levels everywhere), action selection inconclusive, thresholds met.

**What the older runtime did record about finalization**, for both sessions:
- dependency trees removed and first-cell cleanup verified;
- independent GPU cleanup verified, with 0 remaining GPU processes;
- process groups exited, scratch removed, no first-cell cleanup errors, no pending-finalization marker;
- a first-cell lifecycle of 820.6 s and 862.2 s against the 3,300 s internal deadline, so the margins were 2,479 s
  and 2,438 s.

The late-finalization defect that `cfda982` repairs concerns evidence writes or source removal crossing the deadline.
These margins make such an overrun unlikely, but the missing finalization evidence prevents certification, and the
post-fix evaluator correctly refuses to infer it.

## What this means

- Every evidence-level check of the study passes under the fixed evaluator, and the scientific findings are
  unchanged.
- The runs cannot be certified technically complete under the post-fix rules, because they predate the
  finalization certification. That is a documented limitation of these runs, not a defect found in their evidence.
- **Owner decision (October 11, 2026): the study is closed with the two qualifications above.** No new GPU run:
  amendment A1 permits no further session-1 replacement, and any new study would need its own protocol decision.
