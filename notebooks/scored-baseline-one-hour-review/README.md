# One-hour scored E1S-R review notebook

This public review artifact uses placeholder account and private model bindings. The owner-bound private draft
stays local. GPU, TPU and internet are disabled, source approval is false, and no authority or credentials are
embedded. This notebook has not been uploaded or submitted to Kaggle.

`submission.ipynb` and `kernel-metadata.json` are bound by `review-lock.json`. They show the proposed E1S-R scoring
runtime; they do not authorize execution, certify production readiness or establish a new score.

The required one-hour cap covers the entire GPU job, including mounting and provider setup. A platform-side cap
for the scored rerun has not been verified. Do not submit this notebook to test timeout inheritance. Full runtime,
gateway and exact-package validation and proper approval records remain required.

The placeholder specification is in `private-bindings.example.json`. To generate a new review artifact in a fresh
directory, run:

```sh
python scripts/build_scored_submission_v1.py --output <new-review-directory> --private-bindings notebooks/scored-baseline-one-hour-review/private-bindings.example.json
```

Each build creates a new draft attempt identifier; it is not a reservation or a consumed attempt. Retain previous
snapshots rather than overwriting them. See `reports/scored_baseline_v1_preparation.md` for the preparation status.
