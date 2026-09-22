# Integrated ar25 v1 scoring rubric

Score predictions before viewing their resulting frames; assess feedback only
against the recorded observations. No game-source labels, hidden state or human
solution sequence serve as ground truth. Record mechanically checked measures
separately from human adjudications. Keep incorrect valid answers as outcomes.
Technical acceptance is independent of diagnostic accuracy.

## Coordinates, segmentation and geometry

Zero-based x right, y down, grid[y][x], inclusive bounds. Pixel cells are squares;
silhouettes are occupied-cell masks. The fixed observation-only reference has
three candidate regions A/B/C in `geometry_reference.json`: these are annotation
units, not asserted game objects. Each silhouette has 45 cells. A includes its
five color-0 internal marking cells in the silhouette; report these separately
from the surrounding color-5 cells. B and C have no differently colored internal
cells under this segmentation. The reference also records stripe/border regions
without assigning them control or goal roles.

For localization report exact bbox and mask match, plus pixel intersection over
union (IoU). Match predicted masks one-to-one to A/B/C by maximum total IoU;
ties use prediction order then A/B/C lexical order. A localized object requires
IoU >= 0.8; an exact silhouette requires equality. Count unmatched predictions
and missing reference regions explicitly. Valid stripe/border descriptions are
context regions, not false objects, when labeled as such. Do not give an object
count bonus for splitting markings into five separate entities.

Prose alone is not exact geometry evidence. Human raters may map unambiguous
prose to a unique ROI, but it receives only `qualitative_localization`; do not
convert it into invented exact cells. Alternative segmentation explicitly noted
as ambiguous is retained as `ambiguous_segmentation`; the fixed-mask score and
the interpretation note are both reported. A merged or split object claim does
not secretly receive the best post-hoc reference. Do not penalize uncertainty
as confident falsehood, or treat abstention as a correct localization.

For each claimed pair, normalize occupied cells by minimum x/y (translation
removed), compare all eight square-grid D4 transforms, and accept ANY matching
transform from the enumerated set. In y-down coordinates clockwise quarter turn
is (x,y)->(-y,x); reflect_x means (x,y)->(-x,y), then rotate, then normalize.
Translation-only requires normalized-mask equality and one fixed displacement
mapping every cell. Report actual displacement when claimed. Rotation/reflection
ambiguity is expected for symmetric shapes: a claim of a UNIQUE transformation
is unsupported if another transform also matches. Color/position cannot stand
in for silhouette equality. Report pair-claim precision, pair coverage, exact
contour boundary-cell matches, and marking-cell/color matches separately.

Visible geometry does not establish game rules: “these masks match after a
reflection” can be verified; “the objective is to match them” stays a hypothesis.
Goal certainty unsupported by supplied evidence receives an unsupported-rule
flag, not a geometry error. Markings cannot be declared irrelevant without an
experiment; their role remains unknown even if silhouette matching ignores color.

## Control and intention

At every step verify action availability and argument schema against the actual
pre-observation. IDs 1..5 and 7 require empty data; ACTION6 requires integer x/y
in [0,63]. RESET is excluded. Do not supply presumed effects for any ID.
Report declared inventory correctness, legal output rate and exact equality of
model action, serialized command, dispatch and acknowledgement independently.

Structured ACTION6 target hit means the dispatched cell lies in its PREDECLARED
intended cell set, not just its bounding box. For an object declared by reference,
use the model's own earlier mask, then separately check that mask against the
visible reference. A confidently wrong mask can produce a self-consistent click
without correct grounding. Explicitly distinguish these two results. A location
target is assessed as a location, not retroactively labeled an object click.
Nonspatial actions have spatial-hit score not applicable. A wire-level hit does
not prove the game selected or affected that object. Without observable evidence,
game-side targeting is unresolved. Baseline intent and effect knowledge are
unobserved, even if the executed cell overlaps a reference object.

## Informative predictions and experiments

Rate each pre-action experiment with separate binary items: (1) two nonidentical
hypotheses, (2) evaluable primary prediction, (3) distinct evaluable alternative,
(4) at least one possible observable result differentiates their predictions,
(5) this distinction has not already been resolved in the supplied history.
Require explicit region/frame/predicate arguments for mechanical evaluation.
Do not infer a missing alternative or repair a vacuous prediction after dispatch.
Two hypotheses yielding the same observable result on the chosen action are
non-discriminating, even if both sound plausible. A repeated action can pass item
5 if it tests a declared conditional/reliability claim still unresolved by history;
mere repetition or novelty earns no credit. Record all five items, not just sum.

Support means the precommitted predicate held; contradiction means it did not
and required evidence exists; unresolved covers nonobservable effects, missing
relevant evidence or alternatives simultaneously satisfied. Never infer a hidden
mechanic from a single supported prediction. Label ambiguous free-text predicates
`not_mechanically_evaluable`; retain human notes separately.

## Feedback and revision

For each returned frame compare every cell with the pre-action final frame and
with the preceding returned frame. Record changed-cell count, inclusive bbox,
and exact before/after colors; unchanged => zero and null bbox. A shape change is
`dimension_change`, not fabricated cell correspondence. A transient is any
intermediate/final difference; retain indices, including change followed by return.
Report model changed-cell precision/recall if exact cells supplied, exact bbox
agreement if only bbox supplied, and incorrect claims separately. Bbox accuracy
does not imply correct cell identification or mechanics understanding.

Score the feedback verdict against the frozen predicate. Score the update as
consistent, inconsistent, or unresolved relative to that verdict and the model's
declared hypotheses. At the following decision record whether it cites the
feedback and whether its selected test addresses the remaining uncertainty.
If contradicted, keeping a hypothesis without acknowledging contrary evidence is
inconsistent; revising a confidence label alone is not evidence of behavioral use.
Repeating the action with a specific unresolved test may be consistent. A different
action without a connection to feedback does not demonstrate updating. The last
feedback has no subsequent behavioral-use opportunity and is not applicable.

## Progress and interpretation

Report actions used, unique/repeated commands, pixel changes, environment level
counter delta and WIN separately. Repetition and changes are descriptive only.
A subgoal is assessed for specificity and consistency with its declared hypothesis;
its “completion” is not a solved-level claim. Progress requires an increased
levels_completed counter; full completion requires environment WIN. Counter
decrease or unexplained state discontinuity is a technical evidence defect.

Use outcomes `demonstrated_on_this_case`, `observed_failure`, `unresolved`,
`unobserved`, and `not_applicable` per stage/opportunity. The first consequential
break requires an explicit evidence link to the attempted action or subgoal, not
just any wrong incidental description. Multiple plausible breaks may remain tied;
do not force a single diagnosis. Lack of progress at eight actions is censored
early-development evidence, not a general inability result.

Human adjudication: two reviewers independently score ambiguous descriptions,
experiment discrimination and update consistency with raw evidence IDs, without
source access or aggregate arm success. Report agreement and both initial labels;
resolve by written consensus, otherwise retain unresolved. If only one reviewer
is available, label judgments provisional; mechanical results remain reportable.
Never change masks or scoring rules after seeing responses without a new version
and a clearly separate exploratory analysis. No confidence/verbosity bonuses.

The arm comparison reports a stage profile, first-break evidence, environment
progress and total requests/tokens/latency/startup-inclusive runtime per arm.
No causal or statistical significance claim follows from this single board pair.
