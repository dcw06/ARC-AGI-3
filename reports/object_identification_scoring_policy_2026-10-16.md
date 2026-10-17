# Object identification: scoring policy for invalid responses and ignore regions

October 16, 2026. The owner evaluates the object-identification test cases by hand; the code evaluators are a
reference. These two rules were decided by the owner. The reference evaluators now follow them, so their output
agrees with the manual judgments.

| Situation | Rule |
|---|---|
| A frame whose model response is invalid (for example ls20's length-limited MolmoPoint output) | Counts as **zero objects found**. Its reference objects stay in every denominator as misses, and the frame is also listed as a format failure. An invalid response may not carry salvaged objects. |
| A prediction that matches a region marked **ignore** | **Neutral**: neither a hit nor a false positive. It is removed from the prediction count. |

How "matches an ignore region" is decided:

- Included references are matched first. A prediction that matches a real object counts as a hit even if it also
  overlaps an ignore region.
- Each remaining prediction may then match one ignore region, using the same IoU ≥ 0.5 rule and one-to-one
  matching as for real objects. A duplicate on the same ignore region therefore still counts as a false positive.
- Ignore regions apply only at their own hierarchy level: an ignored part does not absorb a whole-object prediction.
- Ambiguous regions keep their existing rule: any ambiguous region in a frame switches off false-positive counting
  for that frame.

**In the code** (branch `object-eval-policy-v1`):
- **`scoring.py`:** `score_frame` reports `prediction_count` (after removing ignore-region matches) beside
  `raw_prediction_count`, with `ignored_region_matches` listing each neutral prediction. Precision, false positives
  and unadjudicated predictions use the reduced count.
- **`evaluation.py`:** it scores an invalid frame as zero objects instead of refusing it, marks it
  `format_failure`, lists it in `format_failure_frames`, and requires `model_response_valid` to be an explicit
  boolean.
- **Unchanged evaluators:** the live and segmentation evaluators already scored invalid frames as zero objects.
  They pick up the ignore rule through `score_frame`.

**Tests.** There are new regressions in `tests/test_object_discovery_boundaries.py` and
`tests/test_object_boundary_preparation.py`. Across the ten object-boundary test modules, 104 tests pass on Linux /
Python 3.12. Fourteen are skipped because they need optional PyTorch or segmentation libraries.

**Caveat.** Changing `scoring.py` and `evaluation.py` again changes the source hashes that earlier preparation and
review packages pin. The committed evaluators already refused the retained uncued run after the empty-mask fix
(review finding, October 16), and that remains true. The reference evaluators can be run on new preparations
built from this code. No model, GPU or provider call was made.
