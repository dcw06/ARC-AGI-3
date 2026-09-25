# Stage B R8: four-action diagnosis

This diagnosis is based on the exact archived requests and responses of R8,
together with two offline checks. It makes no new model calls and runs no GPU.
The visual replay is `reports/perception_stage_b_r8_replay/index.html`,
generated only from the hash-verified archive.

R8's feedback was **sealed**: it was recorded but never entered a later
request. R8 therefore did not test whether the agent can improve its next
action by learning from feedback.

## The four actions

| Arm | Action | Click | Declared target | Cell value at click | Cells changed | Prediction | Feedback |
|---|---|---|---|---:|---:|---|---|
| Control | 1 | (16,16) | not requested | 9 (background) | 0 | `no_change`, correct | `supported`, `frame_0_changed: true` (wrong) |
| Control | 2 | (16,16) | not requested | 9 | 0 | `no_change`, correct | same, wrong |
| Target | 1 | (17,16) | cell `[17,16,17,16]` | 9 | 0 | `no_change`, correct | same, wrong |
| Target | 2 | (16,16) | cell `[16,16,16,16]` | 9 | 0 | `no_change`, correct | same, wrong |

All 12 calls finished with `stop`, and the tokenizer and server prompt counts
match.

## New offline evidence: what a single action does in this state

`scripts/diagnose_stage_b_r8_click_mapping.py` restores the manifest-verified
development game. For each probe it starts a fresh seed-0 ar25 episode,
confirms R8's exact initial state hash (`2318e77b…`) and dispatches one action.
The output is in `reports/perception_stage_b_r8_click_mapping.json`. It is
**evaluation-only** evidence about the engine's visible response. It is not a
policy input and makes no claim about what the changes mean.

- **ACTION6 at 9 positions:** 0 cells changed at every one. The positions were
  R8's two cells, one cell inside each reviewer object A, B and C, A's left
  edge and a marking inside A, the stripe, and a far background cell. R8's own
  cells reproduce R8's recorded no-change, which validates the harness.
- **ACTION1 to ACTION4:** 109 cells changed each, with slightly different
  changed regions per action.
- **ACTION5:** 1 cell changed, at (63,0).
- **ACTION7:** 0 cells changed.

In this state, then, **no click tested changes anything, and each directional
action does**. Both R8 arms chose only ACTION6.

## Answers to the six questions

**1. Were the relevant objects present and legible in the input?**
*Present: confirmed.* Each decision request contains the full 64×64 grid as
JSON integer rows. Row 16 reads `9 9 9 9 5 0 5 5 0 5 5 0 5 9` from x=14, so
A's left edge is at x=18. *Legible to the model: unresolved, with evidence
against it.* In perception R2, the same text representation located 0 of 11
reference objects. R8 alone cannot show whether the model located A.

**2. Were coordinates, orientation and click mapping correct?**
- *The click mapping is confirmed correct as recorded:* `action_data` x is the
  column and y the row of the displayed frame. Both clicks land on background
  cells (value 9).
- *The axis convention was unevenly stated (confirmed prompt defect).* The
  target prompt states `grid[y][x]`; the control prompt states no axis
  convention at all.
- *Orientation errors do not explain the result.* An x/y swap cannot reach A:
  (16,16) is symmetric, and (16,17) is also background.
- *Why the clicks sit where they do is unresolved.* Both land 1–2 columns left
  of A, on A's own rows. That fits an aim at A with a small column
  under-count, but a fixed prior for (16,16) also fits: integrated v1 and v2
  control clicked the same cells, although neither R8 prompt contains `16` or
  any example coordinate. The retained evidence cannot separate the two.
- *It does not matter for R8's outcome.* A click inside A would also have
  changed nothing.

**3. Did the selected target correspond to an object or merely contain the
click?**
It merely contained the click (confirmed). Both targets are one-cell boxes
identical to the click. The protocol allowed `kind: "cell"`, so "target
contains click" was satisfied by construction and says nothing about object
selection. That makes it a measurement-design weakness, not evidence of
grounding.

**4. What history was available when the agent repeated an ineffective
action?**
Confirmed from the second decision requests in both arms:

- `recent_actions: [6]` (action IDs only);
- one retained transition;
- a previous grid identical to the current grid.

The request did not include the earlier click coordinates or any feedback.
The agent could at most infer that the last action changed nothing, not where
it had clicked or what to try instead. The control arm repeated (16,16). The
target arm moved one cell, from (17,16) to (16,16). Neither tried another
action type.

**5. Were before and after frames presented clearly and in order?**
- *Order: correct.* `before` precedes the post-action frames in every feedback
  request, and all four before/after pairs are identical.
- *Clarity (confirmed presentation weaknesses):*
  - The post-action frames sit under the key `observation`, not `after`.
  - The system prompt calls them "returned frame(s)".
  - The feedback stage encodes grids as `hex_rows_v1` strings, while the
    decision and prediction stages use JSON integer arrays.

  These make comparison harder to follow. Whether they caused the errors is
  unresolved.

**6. Why could feedback say "prediction supported" and also report a changed
frame?**
The two fields are independent in the schema (`assessment` enum, then
`frame_0_changed` boolean), and nothing forces them to agree.

- `assessment: "supported"` was correct in all four cases.
- `frame_0_changed: true` was wrong in all four cases.
- *Model error (confirmed):* the combination is internally inconsistent.
- *Cause (unresolved hypotheses):*
  - a default-true bias on a boolean field;
  - no cell-by-cell comparison of two 64-row hex blocks;
  - confusion from the `observation` / "returned frame" naming.

  Four identical cases cannot separate these. A change-detection fixture set
  can.

## Classification

**Confirmed defects (design and measurement):**
- The control prompt states no axis convention.
- Decision history omits earlier click coordinates and any outcome summary.
  Feedback is sealed by design.
- The target measure is trivially satisfied by one-cell targets.
- The feedback stage uses a different grid encoding and an unlabeled "after"
  key.
- The R8 evaluator did not check the first-cell deadline. This is fixed and
  revalidated in `perception_stage_b_r8_deadline_revalidation.json`.

**Model errors (confirmed):**
- All four feedback frame judgments were false positives on identical frames,
  and inconsistent with the model's own `supported` assessment.
- Both arms repeated a visibly ineffective action type.

**Unresolved hypotheses:**
- Whether the clicks were aimed at A (column under-count) or reflect a fixed
  coordinate prior.
- Whether the model can locate ar25's objects in the text grid at all
  (perception R2 suggests not).
- The cause of the false change reports.
- Why the policy chooses ACTION6 exclusively. Candidates are the prompt's
  emphasis on ACTION6 or the model's belief that every action takes
  coordinates. Perception R2's interface probe marked all seven actions as
  coordinate-taking.

**Not supported by the evidence:**
- That R8's lack of progress came from clicking outside objects. The engine
  probe shows a click on each reviewer object also changes nothing in this
  state.

## Strongest next hypothesis

On ar25, **action-type selection is the first-order bottleneck**, ahead of
click grounding. The policy uses only ACTION6, which has no visible effect
anywhere tested in this state. It also receives no information that would
lead it to try another action type. Improving click accuracy alone cannot
produce a visible change here.

This is established for one game, one initial state and single actions. It
does not show that directional actions lead to progress, or that the same
holds for other games. Perception R2's localization failure and the false
change reports remain separate, real weaknesses.

A diagnostic that distinguishes this hypothesis from its alternative (click
grounding) would compare three things, from the same initial states and under
the same budget:

- the unchanged policy;
- a policy whose history reports, from the frames, *which action and
  coordinates were tried and whether anything changed*, with no hint about
  which action to use;
- the effect-rate of each chosen action.

The deterministic diff is supplied as a separately labeled tool, not as
autonomous perception. Candidate selection and the frozen protocol follow
after the local diagnostic fixtures (plan step 4). No new compute is
authorized.
