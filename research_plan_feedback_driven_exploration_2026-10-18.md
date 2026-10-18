# Next study: feedback-driven exploration

Draft recommendation based on the owner's one-month study guide and the
[completed initial-geometry study](reports/initial_geometry_r5_attempt3_results_2026-10-18.md).
This is a plan, not an implemented policy or authorization for model requests,
game actions, uploads or GPU compute. All previous attempts remain preserved.

**Update after the CPU audit:** [feedback availability results](reports/feedback_availability_audit_2026-10-18.md)
show that 154 repeated-action decisions already had a previous unchanged-grid
outcome visible; 123 also matched the current pre-observation. Only 23 decisions
had an older same-action unchanged example with none in the recent window.
The first comparison below is therefore narrowed to summaries of the same
recent evidence. Longer memory becomes a separate follow-up.

**Next research question:** Does an explicit, factual record of attempted
controls and observed outcomes help the same agent change ineffective actions
and complete a first level, compared with its current recent-history interface?

The CPU-only retained-log audit is complete. Next is a frozen, small comparison
of decision interfaces. Larger planning
systems should follow evidence that the agent can use feedback in this simpler
setting.

## Where the guide points

| Guide passage | Application to our next step |
|---|---|
| Page 3, Days 2, 6 and 7: retain state/action history, detect repetition and classify failures | Establish whether the agent had usable evidence of an ineffective action, and whether it changed its choice |
| Page 4, Days 8–12: competing explanations, exploration and discriminating probes | Choose actions that test alternatives; record which outcome would support each explanation |
| Page 4, Day 13: separate dynamics and objectives | A response to a control is not automatically progress or a known goal |
| Page 4, Day 14: matched-budget comparison | Change one decision-interface component while fixing geometry, model and action budget |
| Page 6: replay, new predictions and improved decisions are different tests | Our successful replay certifies the recorded trajectory, not understanding or planning ability |
| Page 9: observation → memory → hypotheses → probes → execution feedback | Test the missing feedback-use connection before adding the entire architecture |

Source: `ARC-AGI-3_One-Month_Study_Guide (1).pdf`, supplied by the owner,
SHA256 `b8c66993f67c878126166b526bc6efa5125e37e4f2cc324c14706b839da3ecec`.
Page numbers refer to its ten numbered pages. The recommendations below are
our application of the guide, not claims that the guide prescribes these
specific experimental arms.

## Why this question comes next

| Retained finding | Implication and limit |
|---|---|
| Geometry study: 0/6 first levels in both arms | Better initial geometry alone did not improve completion within 24 actions |
| Reviewed first-click object contact 5/5; automatic 4/5, conditional on clicking | Contact with a supplied object can work; this does not establish independent perception or useful control selection |
| Nine of ten click-based episodes repeated one exact coordinate for all 24 actions | Feedback-driven action selection is a concrete weakness to investigate; repetition alone does not prove a decision was irrational |
| Both ft09 and sc25 arms produced no final-grid change on any action | These retained cases support testing response to observable ineffectiveness; unchanged images do not prove unchanged hidden state |
| All 288 predictions were “unknown” | There is no measured prospective prediction accuracy; forcing non-abstention would hide rather than solve uncertainty |
| Earlier Track 1 hypothesis study and Track 3 reflection study showed no solving advantage | Do not simply add more hypothesis prose or generic reflection and presume benefit |
| Track 2 preserved access to old facts, without an advantage over state-keyed retrieval | Start with a simple evidence-linked history table; synthetic access results do not establish gameplay improvement |

## Step 1 — Audit the retained evidence on CPU

Use the already validated run, without new inference or gameplay. For each
decision, reconstruct exactly what the model could see: current observation,
initial geometry and the last two transitions. Compare this with earlier
retained outcomes, using only events preceding that decision.

| Audit output | Definition |
|---|---|
| Full action identity | Action ID plus coordinates/data; distinguish changing targets from repeating one click |
| Consecutive repeats and short action cycles | Descriptive patterns, with the underlying observations retained |
| Observed outcome | Exact changed cells, level/state transitions and the recorded action; no inferred roles or causal laws |
| Feedback availability | Was the relevant previous attempt visible in the current prompt, omitted by the history window, or ambiguous? |
| Repetition context | Did the entire observation repeat, only part of it, or did it change? Was there evidence that repetition might be necessary? |

Do not call any changed pixel “progress.” Timers, animation and interface
counters can change without task progress; Track 3 already exposed that risk.
Likewise, do not remove a supposed timer region using knowledge from human
solutions. Initially preserve all changes and label task relevance unknown.
Identical observations may hide different states. This audit can describe
information availability and behavior; it cannot uniquely diagnose the model's
internal reason for repeating an action.

Deliverable: a per-game feedback/repetition table and a few private before/after
examples. Audit classification should distinguish “evidence missing” from
“evidence present but the action repeated.” No new GPU is needed for this step.

## Step 2 — Test explicit presentation of recent feedback

Keep **reviewed initial geometry in both arms** to hold this source of variation
fixed. Use the same model/revision, rendering, legal-action contract, decoding,
24-action cap and six development-game starts. Reviewed geometry stays marked
as step-0 information; it is not silently updated to current positions.

| Arm | Information available |
|---|---|
| A: recent history | Current shared policy interface with the last two transitions |
| B: explicit recent-outcome record | The same interface plus a deterministic table of the same last two full actions, source steps, changed cells/regions and observation-field changes; no older evidence |

The additional table is built from the already displayed past observations only.
Present all recent action outcomes before choosing, without access to the future
chosen action or its outcome. A later, separately frozen comparison can add
older attempts. The table cannot contain
human solutions, object functions, hidden engine state, a known winning action
or an unsupported claim that a control never works. Record current matches as
observational matches, not proof of identical underlying state. Freeze table
selection and token budgets before inference; record actual input
tokens because the table adds information and processing cost. The result
would estimate the feedback-summary interface's effect, not prove that a
particular wording or numerical field caused it.

Retain the action/output contract initially. Do not simultaneously add a
reflection call, new planner, compulsory prediction, hard action override or
larger action budget. If needed, a separate later experiment can test an
explicit probe instruction or a controller, after this interface comparison.

## Step 3 — Measure decisions and completion separately

| Measure | What it can establish |
|---|---|
| Primary: first-level completion within the cap | Whether the interface improves the actual short-gameplay objective |
| Repeated-action patterns, by observation context | Whether action selection changes; fewer repeats alone is not success |
| Legal action types and distinct targets tried | Describes exploration; more unique actions alone is not useful exploration |
| Recorded feedback used in subsequent decisions | Requires a frozen observable criterion; written explanations alone do not prove use |
| Prediction coverage and accuracy when asserted | Abstention remains allowed; do not report 0/0 as zero accuracy or success |
| Calls, input/output tokens, elapsed time and invalid outputs | Cost and reliability of the interface change |

Freeze operational definitions before a new run. Keep all six pairs, failures,
early stops and consumed attempts. Analyze at game level; individual steps are
not independent replicates. Identical deterministic reruns check reproducibility,
not independent scientific replication. These exposed games remain development
evidence; changed-mechanic toy tasks or genuinely unexposed starts are needed
for a later transfer claim.

For this pilot, improvement in contact or action diversity without completion
should be reported as diagnostic improvement only. Do not select a successful
game after observing outcomes or relax the success criterion afterward.

## Step 4 — Advance only after the diagnostic

| Outcome | Following experiment |
|---|---|
| Relevant evidence was absent; the new record helps decisions | Test economical state-keyed retrieval and its gameplay benefit |
| Evidence was already visible; the agent still repeats ineffective actions | Test explicit alternative probes or an execution controller as a separate intervention |
| Better exploration, still no completed level | Test control-effect prediction and goal hypotheses separately |
| Reliable prospective effects and improved decisions | Then test an executable transition model and bounded planning, as on guide page 6 |
| No interface benefit | Preserve the negative result; inspect grounding, control semantics and chosen task budget before scaling |

A controller must not ban every repeated action. Movement, toggles, charging,
delayed effects or hidden modes can require repetition. A future controller
needs evidence-linked triggers, exceptions and its own ablation; a changed
pixel or arbitrary repetition count is not a universal stagnation certificate.

**Recommended order:** retained-log audit → freeze the attempt/outcome record
and evaluator → CPU and scripted-engine checks → review the exact package →
seek one fresh, explicitly bounded compute authorization. No new live run is
authorized by this plan, and the completed r5 attempt cannot be reused.
