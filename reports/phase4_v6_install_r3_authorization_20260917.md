# Separate r3 GPU installation-check authorization

The user requested "Now acn you launch a new GPU run?" after reviewing the
verified Torch wheel versions and corrected r3 probe. This authorizes one new
private, offline RTX PRO 6000 installation-only attempt, with 1800 GPU-seconds
reserved and a 900-second internal limit. No automatic retries, model loading,
model pilot, holdout runs or scored submissions are authorized by this attempt.

The existing r3 notebook/source snapshot is unchanged. Its hashes were checked,
along with the older r1/r2 snapshots. A separate launch review additionally
binds the launcher, credential helper and local Torch resolver evidence.
The previous 18 focused test results and verified Torch wheel inspection apply
to the unchanged r3 source. Kaggle preflight passed with no reserved GPU time;
the previous attempt is terminal ERROR. This is a fresh reservation and claim;
no prior reservation is reused or released.

Provider timeout will be requested at 1800 seconds. Independent provider cutoff
enforcement is not verified. Retain the full reservation until exact usage can
be reconciled; account quota deltas alone are not per-attempt billing.
