# Stage B v0: minimal grounded-action draft

Status: **draft with a local scripted v1 prototype**, not a frozen live executable, source
approval, compute reservation or GPU launch. It follows the Stage A analysis
at `reports/perception_stage_a_v1_findings.md`. The completed R2 run and its
0/11 frozen scores remain unchanged.

The local prototype and its remaining live-integration limits are recorded in
`reports/perception_stage_b_v1_local_review.md`.

## Question and scope

For one already inspected, eligible development case at a fixed initial state,
does a compact target commitment help the agent choose an intentional legal
action and interpret its observed effect within a short matched budget? This is
one case study. It cannot establish a general completion rate or production
admission limit.

Use two conditions only: the unchanged action policy and one candidate whose
additional policy requirement is a bounded visible target commitment. Elicit a
descriptive prediction and distinguishable alternative through the **same
sealed audit call in both arms**, after each policy has committed its action and
before dispatch. The audit response cannot revise the committed action or enter
subsequent policy context in this study. Elicit a post-action interpretation in
the same way from both arms; it is a process measure, not evidence that either
policy used the update to choose a later action. Count these audit calls and
all generated tokens within each arm's matched total budget. Do not introduce
image/text representation changes, coordinate history or evaluator-provided
boxes at the same time.

## Proposed executable contracts

- Bind the episode to the exact game ID, development eligibility, initial
  observation hash, model revision, seed, permitted action IDs and budget.
  Construct isolated episodes from the same state. If equality cannot be
  established, censor the pair rather than interpreting a difference.
- The candidate commits one visible target as a bounded cell or box in
  `grid[y][x]` coordinates, its legal action and required arguments. It may mark target `null` when
  choosing an action for which a visible target does not apply. Free text may
  explain a target but cannot substitute for coordinates. If it chooses the
  coordinate click (action 6), a non-null target is required; score whether
  the click lies in that declared target and whether both lie on a visible
  reference object as separate questions. A null target on a click remains a
  retained invalid proposal, not an automatic fallback.
- Record the exact request/response bytes and hashes, token counts, finish
  reason, target commitment and sealed prediction durably **before** action dispatch.
  Strictly validate the action; retain invalid proposals. Never silently
  rewrite a model action into another action. If a separately labeled safety
  fallback is ever permitted, it is an intervention and must be predeclared.
- The independent evaluator checks whether the declared target refers to
  visible cells, whether action 6 coordinates land in that target when action
  6 is chosen, and whether the action receipt and returned frames bind to the
  commitment. A legal action is not automatically an intentional one; a
  target match is not proof of a correct game hypothesis.
- Retain every returned frame, including intermediate frames, exposed
  progress/terminal signals and a shared monotonic timeline. Distinguish
  unchanged final frame, transient change, timed-out dispatch and unknown
  outcome. Do not retry an action after an unknown acknowledgement.
- Independently replay initial-state equality, request/action/observation
  bindings, complete paired episodes, chronology, deadlines, resource limits
  and final cleanup. Missing or censored evidence is neither success nor a
  no-effect outcome.

## Measurement

The shared primary outcome must be selected before launch from observed
transition or level progress within the fixed action and total compute limits.
Report completed levels separately; a short diagnostic may have none. Shared
secondary measures are legal action rate, actual target contact where it can
be inferred without game-source labels, changed frames, progress signals,
repeated actions and total token/time cost. Candidate-only process measures
include declared-target localization and action-to-declared-target consistency.
Prediction and post-action interpretation can be measured in both arms, but
cannot establish feedback use in action selection because the sealed audit
answers do not feed the policy. Keep observation-only findings
separate from game-source-assisted interpretation. Human walkthroughs and
source-derived winning moves never enter model requests.

## Decisions still required before freezing

1. Choose the exact eligible case and action allowance. In particular, decide
   whether a coordinate click is a permissible informative action without
   forcing the unchanged baseline to make one.
2. Freeze the initial-state restoration method and prove paired equality.
3. Specify the short action, inference, token, time and evidence ceilings from
   local profiling; include startup and cleanup. No duration is assumed here.
4. Define the concrete prediction/update schema and scoring for ambiguous,
   delayed and transient effects. Identify what can be scored mechanically
   from observations and what must remain unresolved.
5. Test malformed outputs, wrong coordinates, missing target, incomplete pair,
   deadline, unknown dispatch, monitor failure and cleanup in a supervised
   local runner. Package a GPU-disabled notebook and review its unpacked code.

Only after those decisions, local tests and a new source lock should separate
source approval and compute authorization be considered. No new GPU session or
full pilot is part of this draft.
