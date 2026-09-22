# Integrated case v1: second issue review

Conclusion: **not launch-ready**. All four first-review blockers remain open.
No runner, independent integrated evaluator or GPU-disabled integrated notebook
has appeared. No source/specification bytes were changed during this review.
Offline probes passed; that means the findings reproduced, not that a launch passed.

## Findings, ordered by consequence

| Finding | Evidence / status | Required resolution |
|---|---|---|
| Missing integrated executable and replay | Worker, evaluator and notebook paths remain absent. Existing transient execution is six episodes, 120 calls, 20 actions per episode. | Implement the two-arm state machine and independently verify the new schedule. Never upload an old notebook as this study. |
| Structured requests are rejected | Actual historical validator rejects 2048 tokens (`request settings`) and the new prompt at 128 tokens (`prompt`); service also enforces 128. | Freeze exact per-stage schemas, prompt builders, call ordering and guards; preserve baseline requests. |
| Adaptive payload size is unresolved | Constructed pre-frame plus six identical retained grids produces an 89,132-byte request; current 65,536-byte guard rejects it. This is a stress fixture, not an observed ar25 transition. | Predeclare frame/history admission and byte/context ceilings. Audit pinned tokenizer lengths and fail without silent frame removal. |
| Longer outputs may exceed response retention | Actual capture of 8,193 ASCII bytes retains 8,192, flags truncation and preserves the full hash. A 2048-token cap alone is not a byte bound. | Freeze coordinated response-byte/token/schema bounds, transport and replay limits; regression-test overflows before inference. No evidence-loss bypass. |
| Baseline implementation is not bound by the case lock | `spec-lock.json` binds the historical protocol but not its contract builder, action contract or `agent/representation.py`. | Execution source lock must bind the full dependency inventory. Differential tests must compare baseline requests on identical complete runtime states, including histories. This is an execution-readiness gap, not corruption of the specification. |
| Current-frame target identity unresolved | The initial reference masks are static; named targets can refer to prior masks after motion/rotation. | Bind declared intended masks and object references to the current pre-observation. Score self-consistent targeting separately from correct object grounding; ambiguous identity stays unresolved. |
| Prediction semantics incomplete | `any_returned`, `no_cell_change`, region masks and translated masks are named, but quantifiers, empty regions, clipping/occlusion and dimension-change behavior are not defined as executable predicates. | Define truth tables and schemas; keep supported predicate distinct from established mechanic. Define overlap of primary/alternative and unavailable-evidence cases. Test these before live calls. |
| Invalid diagnostic output disposition unclear | Specification says reject out-of-bounds references and retain invalid outputs, but does not fully define whether a valid action in the same response is dispatched or how later slots end. | Freeze one policy before execution. Recommended: no dispatch from an invalid structured decision, retain a model-output failure outcome and censored downstream stages; distinguish this from transport/cleanup failure. No repair or retry. |
| Stopping and final feedback need explicit ordering | Final feedback is required, while progress/WIN/GAME_OVER closes the episode. Bootstrap-terminal states are not fully specified. | Close action admission at a terminal/progress observation; permit only the already-budgeted final feedback if technical/time admission allows. Define bootstrap-terminal mismatch handling and omission reasons. |
| Human adjudication is not an automatic technical gate | First consequential break, discrimination and behavioral use require judgments beyond pixel checks. Two-reviewer procedure exists, but no completed adjudication is available. | Report mechanical results independently; label single-reviewer judgments provisional. Do not turn an unfinished adjudication into a technical pass/fail or a causal diagnosis. |
| Compute and resource proposal remains incomplete | Correct ceiling: 25 study calls + one canary, 16 actions, 19,584 generated tokens. No actual adaptive tokenizer audit or provider-time ceiling exists. | Freeze startup-inclusive wall time, admission/cleanup reserve, resources and total evidence before reservation. Preserve consumed historical attempts. |

## Corrections and limits of the first review

- **Bridge capacity is not a demonstrated blocker.** Historical transport accepts
  JSON messages up to 1 MiB and already carries bounded response evidence on
  failure. It does not hardcode a 128-token action schema. New schemas need bridge
  regression coverage, but there is no evidence that bridge redesign is required.
- **Local scorecards are not production submissions.** The existing OFFLINE
  adapter requires a local scorecard for bootstrap. The protocol permits local
  bookkeeping and forbids production scorecards; these are compatible. The new
  runner must record local opens/closes and enforce OFFLINE mode, rather than
  falsely reporting zero scorecards of any kind.
- **Canonical state equality already covers most relevant observation fields.**
  `Observation.canonical_hash` includes all frames, game ID, state, levels,
  win-level count and legal actions, but excludes GUID and `full_reset`. This is
  useful for paired equality. Still verify bootstrap/reset status and equality
  to the frozen historical initial state, not merely equality between arms.
- **The readiness helper is not a future launch gate.**
  `check_integrated_launch_readiness_v1.py` intentionally returns `launch_ready=False`
  and probes one historical contract. It cannot certify a later integrated runner.
  Do not change that field to true as a substitute for executable checks.
- Historical numerical limits are valid for their own experiments. They are
  incompatibilities with this proposed workload, not proof of defects in the
  completed coordinate or transient results.

## Reconfirmed sound parts

The frozen archive/member/geometry/specification hashes reproduce. The three
45-cell masks and five internal color-0 markings are verified from retained grids.
Reflection and rotation both match A to B/C, so the rubric correctly rejects a
unique-transformation assumption. Translation B to C is (+15,+30).

The protocol correctly separates visible geometry from game-rule hypotheses,
labels prior source exposure, prevents source-derived policy inputs, treats
baseline intent as unobserved, and distinguishes the scaffold bundle from a pure
prompt comparison. It does not confuse pixel changes with environment progress.
These design properties do not substitute for executable validation.

## Reproduction

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/recheck_integrated_issues_v1.py
```

Machine-readable results and inspected source hashes:
`reports/integrated_case_v1_second_review.json`.
No model calls, environment actions, GPU launches, reservations or new authority
receipts were created. Existing user launch intent remains recorded; this review
does not request redundant permission or authorize a different experiment.
