# Stage B attempt R1: packaged-source failure and R3 review

The private Kaggle notebook version 1 at
`https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r1`
returned `KernelWorkerStatus.ERROR`. Attempt
`gab1-3c3f2e141f1747a391434b6fcd8842a3` was consumed before upload;
there is no retry authority.

The provider log and retained `control/notebook-cost.json` agree on the
failure: `FileNotFoundError` for
`reports/phase4_torch_wheel_inspection.json` under the temporary packaged
source. The split-install module loads that frozen report at import. The R2
notebook omitted it from its embedded source inventory. The first-cell receipt
reports 0.224 seconds in the launch function, `study_status=null`, and
`dependency_trees_removed=true`. No install, model startup, worker, monitor,
game action, or scorecard evidence exists. This is a packaging failure, not
evidence about the model or grounded-action study.

The four downloaded provider files were independently checked against
`reports/perception_stage_b_live_download.json`: **four checked, zero hash or
size mismatches**. Their manifest retains paths, byte counts, and SHA-256
digests. The account-wide GPU `time_used` rose from 10,687.795 seconds at
prelaunch to 10,697.547 seconds at the first status check, a 9.752-second
difference. This is not exact per-attempt billing. No independent GPU cleanup
record was produced because the monitor never started; the notebook's own
receipt only confirms dependency-tree removal.

The corrected R3 source inventory includes the missing frozen report. A
clean, isolated Python process imported `prepare` and the torch contract
from the **unpacked notebook payload**, with no checkout fallback. The R3
GPU-disabled review notebook verified 1,043 source bindings and rejected
unapproved execution. Its review lock SHA-256 is
`b1b74caa5747d92e9721ea4a533305247343e456eb48242c0052429474e70e52`.
The R1 and R2 review notebooks remain historical; the R2 launch reservation
and authority records remain consumed and cannot authorize R3.

R3 has not been uploaded or run. It was superseded by R4 after separating
the successor's authority paths from the consumed R2 attempt. The active R4
review is recorded separately. Exact billing reconciliation and Phase 4
production certification remain open.
