# V7 pilot launch proposal after source approval

The user approved the frozen v7 source/protocol/notebook snapshot by replying
"Yes please continue" to the explicit source-approval question. The approval
record is `reports/phase4_v7_source_approval.json`; the approved review-lock hash
remains `2ccab9336f3d27d174741f03b437138dd94c682ab449372ed9a0a38f9957e87b`.
All approved source and notebook hashes were reverified without modification.

The concrete launch proposal is
`notebooks/phase4-v7-pilot-launch-proposal-r1/`. It packages the same approved
code with separate execution-authority sidecars and private RTX PRO 6000
metadata. Its ledger currently authorizes zero seconds and contains no reserve
or launch event. A direct isolated execution test confirmed it refuses before
installation. The original approved review notebook remains GPU-disabled.

Requested next authorization:

- One private offline RTX PRO 6000 development model pilot.
- 28800 GPU-seconds (eight hours) reserved; provider timeout requested at that limit.
- 27540-second first-cell lifecycle limit (7 hours 39 minutes), including setup
  and finalization, with a 600-second finalization reserve.
- Frozen model loading and the approved 110-client development workload only.
- No automatic retry, holdout run or scored submission.
- Evaluate final notebook, model/token audit, monitoring and cleanup evidence;
  reconcile usage afterward. Exact billing is distinct from aggregate quota delta.

Preflight at 2026-09-17 13:25:20 UTC passed: r5 is COMPLETE and account GPU usage
is 26675.767 of 108000 seconds, with zero provider-reserved time. The remaining
81324.233 seconds exceeds the proposed reservation. Quota must be rechecked at
actual launch. Provider hard-stop enforcement remains unverified.

No GPU reservation or submission has been made. After separate authorization,
the single attempt needs its reserve/launch claim and authorized sidecars bound
into the final launch package. The packager is
`scripts/prepare_phase4_v7_launch.py`; it checks the approved hashes before every
build. Changes to these authority sidecars do not alter approved pilot source.
