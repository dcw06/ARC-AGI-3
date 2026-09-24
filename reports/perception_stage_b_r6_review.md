# Stage B R6 source review after the second attempt

The consumed second Kaggle attempt failed after the split install passed,
when the notebook interpreter imported game-only `arcengine` through the
supervisor's monitoring dependencies. The verified failure archive and
accounting limits are recorded in `reports/perception_stage_b_r2_failure.md`
and `reports/perception_stage_b_r2_archive.json`. No study call or game
action was observed in that attempt.

R6 keeps the split model/game installation and moves the entire live
supervisor into the pinned game interpreter. The notebook process imports
only its game-free first-cell launcher. The parent owns the supervisor
process group, retains bounded output, enforces the startup-inclusive
deadline, checks the supervisor's report, and terminates recorded descendant
groups even if their leader has exited. A malformed ownership record still
triggers cleanup of the known supervisor group and an explicit failure.
The existing supervisor retains its worker/monitor lifecycle, independent
trajectory replay, and independent GPU cleanup checks inside the game
interpreter. A missing report or cleanup evidence cannot pass.

The repaired first-cell import passed with `arcengine` and `arc_agi`
excluded. The packaged-source test imported both the first-cell launcher
and the game supervisor from the unpacked notebook payload without a
checkout fallback. The connected CPU lifecycle tests covered success,
startup failure, cancellation, deadline, evidence exhaustion, cleanup
failure, and the new parent process-group cases. **24 relevant tests passed**.
The notebook reviewer verified all **1,043** unpacked source bindings and
rejected unapproved execution. R4 and the intermediate R5 snapshots remain
unchanged.

The active R6 review lock SHA-256 is
`3afce33e6d3e7bbe763b3850cccb9e8cf901c11a8aec390c4e09ef78a8266da3`.
`notebooks/phase4-grounded-action-v1-launch-r6` is private, Internet-off,
and **GPU-disabled**. The proposed successor authority namespace is
`phase4-grounded-action-stage-b-live-r3`; it has no source approval,
compute authorization, execution lock, reservation, or launch package.
The historical R2 reservation remains consumed and cannot authorize R6.

This is a CPU and source-review result, not target-runtime validation.
Before any further Kaggle use, obtain explicit R6 source approval and
separate authorization for one newly budgeted attempt, then reserve,
package, verify, and submit once. The study remains unscored development
work; exact billing and Phase 4 production certification remain open.
