# Separate r5 GPU installation-check authorization

The user requested "Now can you start another GPU session" after the plotting-backend repair to the split model/game
environments. This authorizes one fresh private offline RTX PRO 6000
installation-only attempt, reserving 1800 GPU-seconds with one shared 900-second
internal deadline. No automatic retries, model loading, model pilot, holdout
runs or scored submissions are authorized by this attempt.

The unchanged r5 notebook and source hashes were checked, along with historical
r1/r2/r3/r4 snapshots. The separate launch review additionally binds the launcher,
credential helper, dependency audit, local game-isolation evidence and split
tests. Seven focused r5 tests passed before submission. Both dependency
sets passed their separate metadata audits, and the real local game install
passed. Model imports and CUDA execution are still pending target validation.

Kaggle preflight passed; the previous run is ERROR, and no GPU time is currently
reserved by the provider. This is a new reservation and launch claim. Prior
reservations are neither reused nor released.

Provider timeout is requested at 1800 seconds; independent enforcement is not
verified. Retain the full reservation until exact usage is reconciled. Aggregate
quota deltas alone do not establish per-attempt billing. This installation probe
does not implement the remaining tokenizer/service separation for a model pilot.
