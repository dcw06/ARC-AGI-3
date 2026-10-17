# Empty automatic proposals: preserve undefined stability

The base UnSAMv2 automatic sc25 smoke completed inference but failed during
strict JSON evidence writing. With stability filtering disabled, upstream can
return an empty raw mask with a NaN stability score (zero divided by zero).
The raw NPZ and failed attempt remain preserved; the incomplete attempt is not
counted as a passing smoke.

Automatic adapters now retain original stability scores in a numeric NPZ array.
For a NaN belonging to an empty raw mask, JSON records `stability_score: null`
and `stability_score_state: undefined_empty_mask`. The proposal is retained in
the denominator. Nonempty masks with undefined stability, infinite stability,
and nonfinite predicted mask quality are refused. No model score is replaced
with zero and no mask is repaired.

The evaluator also has an explicit `--smoke-case` mode for replaying only the
declared one-image output. Its default six-board mode continues to refuse smoke
outputs, and a mismatched case is refused. This adds output verification without
reclassifying a smoke run as the full experiment.

All 28 focused adapter/runtime tests pass on Linux CPU with no skips. These
checks use synthetic outputs; actual checkpoint smoke progress is recorded
separately. No GPU job or Kaggle call was made.
