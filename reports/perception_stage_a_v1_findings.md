# Stage A: offline inspection of paired perception R2

This is a descriptive analysis of the completed, unscored R2 development run at
`3283cbf`. The [generator](../scripts/inspect_phase4_perception_stage_a_v1.py)
reads the hash-verified completed archive, reruns the frozen evaluator, checks
each response hash and stored score, and draws the model's boxes over the same
grid used to generate the reference. It sends no model requests and executes no
environment actions. Green boxes are references; magenta boxes are predictions.
The [machine-readable analysis](perception_stage_a_v1/analysis.json) retains the
request/response hashes, original coordinates and every diagnostic comparison.

## What the overlays show

| Board and source | Text: boxes, mean nearest IoU | Image: boxes, mean nearest IoU | Concrete observation |
| --- | ---: | ---: | --- |
| [P1, retained ar25](perception_stage_a_v1/P1_text.png) / [image](perception_stage_a_v1/P1_image.png) | 6; 0.188 | 6; 0.078 | Text boxes loosely cover the two upper objects; its whole-board box is the closest one to the lower object. Image splits upper and lower areas into small boxes, with weak overlap only for the lower object. |
| [P2, synthetic rotation](perception_stage_a_v1/P2_text.png) / [image](perception_stage_a_v1/P2_image.png) | 6; 0.239 | 2; 0.026 | Text's first box overlaps reference A at IoU 0.477, just below the frozen 0.5 threshold; it misses B. Image's boxes are displaced from both references. |
| [P3, synthetic reflection](perception_stage_a_v1/P3_text.png) / [image](perception_stage_a_v1/P3_image.png) | 6; 0.239 | 2; 0.026 | Text again partly covers A but misses B; image repeats the displaced two-box pattern. |
| [P4, synthetic marking/stripe](perception_stage_a_v1/P4_text.png) / [image](perception_stage_a_v1/P4_image.png) | 6; 0.222 | 2; 0.217 | Text partly covers A; image B reaches IoU 0.368 but remains unmatched. The stripe is an explicit non-object reference region. |
| [P5, synthetic distinct shapes](perception_stage_a_v1/P5_text.png) / [image](perception_stage_a_v1/P5_image.png) | 6; 0.239 | 2; 0.026 | Text partly covers A and misses B; image repeats the displaced two-box pattern. |

The frozen one-to-one scorer still detects **0/11 objects in each arm** at IoU
≥ 0.5. The table's exploratory “nearest” rule lets *each* reference independently
choose the predicted box with greatest inclusive-box IoU, then nearest center,
then input order. One prediction may therefore be nearest to several references;
these numbers are **not rescored accuracy**. Across eleven reference objects,
mean nearest IoU is 0.222 for text and 0.075 for images. P2–P5 reuse the same
two synthetic object positions, so their similar answer patterns are correlated
and cannot establish a general failure rate.

P2 illustrates why the threshold alone is insufficient for diagnosis. Reference
A is `[8,10,16,18]`; text predicts `[11,11,17,17]`, centered two cells to the
right, with IoU 0.477. The image predicts `[15,15,23,23]`, centered seven cells
right and five down, with IoU 0.052. Reference B is `[38,30,46,38]`; the image
predicts `[41,41,49,49]`, centered three right and eleven down, with no overlap.
Those offsets do not support a single board-wide translation. The predicted
box widths are on the order of 7–9 cells, so a simple pixel-versus-cell factor
of 16 is also unsupported. A predeclared x/y axis-swap diagnostic leaves text's
mean nearest IoU at 0.222 and lowers images' from 0.075 to 0.020; it does not
explain the misses. An inclusive-boundary difference of one cell cannot explain
the larger displacements or absent second objects. These are exploratory checks
and never change frozen scores.

Both interface probes gave a correctly formed click on `(7,23)` with action 6,
the requested action 1 with no coordinates, and the expected directional
list/null. Both also declared *all seven* action IDs coordinate-taking, for
1/7 correct argument classifications each. The correct emitted actions show
that syntax construction can succeed alongside an inconsistent explanation;
they do not establish intentional targeting or known game effects.

## First prospective question

**Prioritized hypothesis:** requiring one explicit, observation-grounded target
and a coordinate commitment may produce more accurate target-to-action binding
than asking for an exhaustive inventory. The repeated extra boxes, partial
first-object overlaps and displaced image boxes motivate this test. They do
not distinguish prompt burden from visual grounding by themselves.

The next study should use one eligible development case with a fixed initial
state and a short action budget. Compare the unchanged action policy with one
compact target-commitment candidate under matched model, observations, seeds,
actions and total compute. Score common outcomes on actual transitions and
progress. The candidate's declared target is a process measure; collect
prediction and post-action interpretation through equal sealed audit calls in
both arms, without feeding those answers back into action choice. Require
an explicit target cell or box and action coordinates so a replay can distinguish
target recognition, coordinate mapping and effect prediction. No evaluator box
or game-source interpretation enters either model prompt. This is an exploratory
case study, not a claim of transfer or solving improvement.

The [Stage B protocol draft](perception_stage_b_v0_protocol.md) records the
remaining design decisions before local runner work. R2's reservation is
consumed and authorizes no new compute.

Verify all ten overlays read-only in a clean checkout with the Linux CPU
development environment:

```sh
python scripts/inspect_phase4_perception_stage_a_v1.py --check
```

This regenerates to temporary space and compares every byte with
`inspection-lock.json`. The command without `--check` is only for initial
creation when the versioned output directory does not yet exist.
