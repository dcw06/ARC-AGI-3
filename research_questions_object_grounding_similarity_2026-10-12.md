# Object grounding, control discovery and similarity: research proposal

October 12, 2026. **Draft questions only.** No protocol frozen, implementation, model query, game action or GPU
attempt is authorized by this document. The four completed/qualified research tracks keep their recorded results.

## Motivation and evidence boundary

The owner's replay inspection suggests clicks near objects rather than on them, and insufficient exploration of
how objects move. This is a useful hypothesis, not yet an annotated targeting result: the replay does not contain
a human-defined intended target or an interaction-region reference for each click.

The retained Track 3 session-2 continuation episodes provide these counts:

| Public game | Controls reported available throughout its 40 steps | Recorded actions |
| --- | --- | --- |
| ar25 | ACTION1–7 | 40 ACTION6 clicks |
| wa30 | ACTION1–5 | ACTION1: 11; ACTION2: 21; ACTION3: 8 |
| ls20 | ACTION1–4 | ACTION1: 1; ACTION2: 21; ACTION3: 18 |
| s5i5 | ACTION6 only | 40 ACTION6 clicks |

ACTION4 was available but unused in three episodes. ACTION1–3 were used in two. These counts do not establish
which object an action controls, or whether an unused action would help. Absence of directional actions in s5i5
is not a control-selection failure because those actions were unavailable.

## Primary research question

**Can the agent localize a specified object and use legal controls and observed action effects to select an
interaction that affects that object, instead of repeatedly acting on nearby background?**

## Object-similarity research question

**Can the agent find objects that share a specified visual structure despite changes in position, color or
orientation, while rejecting distractors and keeping visual similarity separate from shared function?**

| Question | Minimal diagnostic | What to measure |
| --- | --- | --- |
| Is the intended object correctly localized? | Specify a visible target and ask for its mask and one point inside it; score against a reference fixed before querying the model. | Object-mask overlap, point-in-mask rate, and distance of misses from the target mask. A bounding box alone does not prove object contact. |
| Can it match similar objects? | Give a reference object and find all matching objects, with same-color/different-shape and same-shape/different-color distractors and no-match cases. | Precision/recall of the selected set, localization of each match, and correct abstention when no match exists. |
| Can it discover which controls affect the target? | Supply only currently legal controls and a short retained action-effect record; ask for the observed target displacement and a useful next probe, allowing “unknown”. | Correct effect reading, legal/nonredundant probe selection, and later verified target motion. Count unused controls only when available; trying every direction is not itself success. |
| Can it use a match to guide interaction? | After visual matching passes, test whether action-effect evidence from one object supports a prediction about another, including similar-looking objects with different roles. | Correct transfer predictions and uncertainty; actual effects under a later bounded public-game test. Appearance alone supplies no functional label. |

## Define “similar” before testing

| Matching condition | Intended interpretation |
| --- | --- |
| Same shape, relocated | Compare the object pattern independently of absolute screen position. |
| Same shape, changed color | Test shape matching with color explicitly declared irrelevant. |
| Rotated or reflected shape | Separate conditions with the allowed transformations stated in advance. Do not silently treat every orientation as equivalent. |
| Similar color, different shape | A distractor when the rule is shape matching. |
| Same visual structure, different observed behavior | A visual match whose functional equivalence is not established. |
| Occluded, merged or otherwise ambiguous objects | Report separately; permit uncertainty rather than forcing a match. |

## Proposed order

1. **Reference annotation and no-action diagnostic.** Use retained public-game boards. Fix target masks, matching
   rules, admissible answers and ambiguous cases before model queries. Keep initial localization and within-board
   matching separate from tracking the same object across frames.
   Balance target positions and distractors; use fresh instances for testing and report results by scene/game.
   Repeated frames or actions from one episode are not independent evidence of generalization.
2. **Separate perception from action choice.** Compare the same tasks with raw observations versus correct object
   annotations. In a distinct comparison, add the same observed action-effect evidence. Change one input at a time;
   tool-supplied locations demonstrate assistance, not unaided perception.
3. **Public-game interaction pilot only if warranted.** Track the specified object's observed position/effect,
   separately from camera movement, HUD changes and level completion. A point on a visual object does not prove
   that clicking it is supported; valid interaction regions/mechanics need their own evidence.

A localization failure would motivate better perception. Correct localization with poor probe choice would
motivate control discovery. Successful visual matching without valid effect transfer would motivate a separate
test of role/mechanic understanding. None of these diagnostic outcomes alone establishes better game solving.

Existing grounding, perception and structured-target studies already found weaknesses. This proposal adds a
reference-based diagnosis of the apparent near misses, an explicit visual-matching task, and an intervention
that separates supplied object locations from control/effect reasoning. Case counts, thresholds and runtime
budgets remain open for protocol design. No launch follows from this draft; the full-job GPU cap remains in force.
