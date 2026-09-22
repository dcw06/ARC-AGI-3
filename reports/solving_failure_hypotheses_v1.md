# Solving development: failure hypotheses and smallest distinguishing tests

Decision: adopt the attachment's revised sequence, not its earlier comprehensive
platform proposal. Freeze the boundary, consolidate existing traces, and use the
already-submitted grounding diagnostic before proposing another model experiment.
Do not build memory, planning, object extraction, or hazard modules together.
No new compute, examples, policy edits, or environment interactions are authorized
by this specification.

Objective: on an unfamiliar eligible development game, intentionally operate the
controls, identify relevant visual structure, learn action effects, and execute a
plan producing environment-verified level completion within a fixed budget.
Reliable execution of tested workloads is supporting evidence, not proof of this
capability chain. Failure attribution remains a hypothesis unless a distinguishing
test supports it.

## Boundary and unchanged comparison

`solving_development_boundary_v1.json` records the 15 games already used in the
closed-loop comparison. Historical inspection reports visual review of their
initial frames and programmatic inspection of their trajectories. Source-excerpt
provenance is separately flagged. All fifteen are conservatively treated as
inspected development data; none is an untouched transfer test. Human solution
walkthrough exposure is not established by this record, not assumed absent.

No exact reserved-evaluation roster has been established here. Unknown games are
not automatically eligible or untouched. Review their provenance before prospective
sampling, without opening reserved game content to establish eligibility. A human
walkthrough or source-derived solution that informs development retires that game
from untouched generalization claims. Observation-only diagnosis, supplied rules,
and source-assisted interpretation must remain separate conditions.

Preserve the existing runnable **transient v2 control arm** as the narrow
no-example comparison baseline: E1S-R-derived `arc_action_v12`, raw grids, the
frozen Qwen model/tokenizer, non-thinking temperature-zero decoding, 128 output
tokens, and no transient-field treatment. The boundary receipt binds its protocol,
prompt, and source lock. It is an unpromoted development control, not a replacement
for `agent/production_main.py` or unchanged historical E1S-R admission evidence.
The previous experiment used 20 actions, environment seed 0, request seeds 0/1/2.
Any future comparison must freeze new games/order, seeds, full runtime/token
budget and stopping rules before approval; old compute authority cannot be reused.

## Consolidated observations and hypotheses

| Observation-only evidence | Competing explanations, still unresolved | Smallest distinguishing test | Limits |
|---|---|---|---|
| A valid ACTION6 at `(32,32)` was dispatched repeatedly in ft09. | Model misreads coordinates; fails to choose a useful target; does not know the effect; chooses repetition despite seeing it. | Explicitly request a marked asymmetric grid coordinate; compare target, emitted action, serialized action, and mocked dispatch. Include unavailable controls and terminal cases. | Existing strict dispatch validation proves wire consistency, not that the model intended the right target. |
| The prior ft09 trace returned five frames with an 80-cell transient outline change, but the next original request contained unchanged final grids. | Missing information; inability to extract the changed region; inability to use correctly perceived feedback. | Use the already-frozen grounding change/localization cases and independently grade their outputs. | A source-assisted explanation of what the outline means is not observation-only truth and must not enter the live request. |
| Adding the selected transient frame yielded zero levels; all 57 exposed decisions matched paired control actions. | Grounding failure; action-selection failure; feedback insufficient or irrelevant to the chosen strategy. | First evaluate the submitted grounding diagnostic, separating reading, localization and change detection. | This closes the tested treatment as no demonstrated benefit. It does not prove information can never help; do not rerun unchanged. |
| Removing concrete action examples reduced repetition in the earlier 15-game comparison, with zero levels in both arms. | Example copying affected outputs; useful perception or strategy still missing. | No additional copying diagnostic; use existing evidence and current grounding results. | Reduced repetition/diversity is not completed-level benefit. |
| Prior requests omitted click coordinates from retained action history. | Repetition might reflect missing prior-coordinate information, but may also occur with fully understood feedback. | Only if still warranted after grounding/interface tests: isolate previous-click coordinates as one treatment. | A hypothesis notebook adds memory, interpretation, and planning simultaneously; not the default treatment. |

Evidence anchors: `phase4_closed_loop_v1_offline_findings.md`,
`phase4_ft09_information_v1/findings.md` (observation-only section), and
`phase4_transient_v2_disposition.md`. The source excerpts support retrospective
interpretation only; they do not establish that the policy saw those mechanics.
Unchanged final pixels do not prove unchanged hidden state; changed pixels do not
prove progress.

## Immediate diagnostic decision

The existing grounding v1 submission is already authorized and consumed:
`og1-b98f644f0122470699224f74b5961d49`, provider version 1, at most 1,800 seconds
and 12 diagnostic calls plus one canary. This specification neither resubmits nor
changes it. Its current terminal result is not asserted here. Retrieve and replay
that result under its existing protocol before choosing new model work.

Its cases distinguish basic reading/localization/change extraction, not deliberate
control selection, shape reflection, mechanics discovery, or planning. Four source
groups must not be treated as twelve independent generalization trials. Preserve
valid incorrect answers; technical failures make the capability conclusion
incomplete, not evidence of a perception deficit.

Predeclared routing:

- **Technical failure or incomplete coverage:** diagnose the specific evidence or
  runtime failure; no automatic retry and no capability verdict from missing data.
- **Incorrect reading/localization/change answers:** reproduce the exact error,
  including coordinate-axis confusion or ambiguity. Propose only the smallest
  relevant follow-up, potentially a same-information representation comparison.
- **Accurate direct-question perception:** perception is demonstrated only on
  these examples. The next unresolved distinction is intentional interface use
  versus useful strategy; a small explicitly instructed control test comes before
  attributing failure to planning.
- **Mixed results:** retain task- and game-level profiles and label attribution
  unresolved. Do not select the most favorable score after seeing outputs.

The next interface proposal, if needed, should cover requested legal movement,
marked click coordinates, grid/display versus browser coordinates, unavailable
actions, terminal refusal, and intended-versus-dispatched equality. Its exact
targets are interface facts, not hidden game rules. Local mock dispatch can test
serialization without new environment actions; model intent tests still require
separately frozen requests and approval. No broad geometry suite is mandated now.
If a trace specifically implicates shape confusion, use unambiguous color-independent
translation/reflection/rotation and one-cell near-match fixtures, with outer contour
and internal markings scored separately, before considering object modules.

## Decisions for a later isolated intervention

For each proposed treatment, freeze one falsifiable hypothesis, paired cases and
game/episode units, baseline rollback, inference costs, regression limits, and
promote/reject/inconclusive rules. Reproduce locally before a GPU-disabled review.
Diagnostic gains and gameplay gains are separate claims: a better fixture score
supports only the targeted diagnostic, not promotion. Diagnostics need not become
mandatory prerequisites for every justified bounded gameplay experiment.

A later gameplay comparison must measure explicit completed-level increase and
wins, actions, runtime, and failures. Repetition and visual change remain secondary.
Reject a treatment with no demonstrated primary benefit in the tested budget;
report incomplete or conflicting evidence as inconclusive. Prospective transfer
on separately eligible cases and budget compliance are required before promotion.
Human-supplied rules versus rules-withheld discovery require separate conditions.
Predictions must name observable effects and be checked against subsequent frames;
written explanations are not proof of internal reasoning.

## Separate completion obligations

This solving-development track does not close production one-scorecard/
110-distinct-game certification, workload-specific admission limits, or exact
accounting. Neither a diagnostic success nor another solving experiment supplies
those missing forms of evidence. The consumed reservations remain consumed.
