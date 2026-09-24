# Stage B second GPU attempt: import failure after installation

The private Kaggle notebook [version 1](https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r2)
returned `KernelWorkerStatus.ERROR`. Attempt
`gab1-f75fd59d52e9456ea08217df838ef883` and its 3,600-second reservation
were consumed. The launch receipt allows no automatic retry.

The split installation passed in 133.658 seconds. The first-cell receipt then
recorded `ModuleNotFoundError: No module named 'arcengine'` and stopped at
136.601 seconds. The provider log shows this arose when the launch function
imported `research.grounded_action_v1.target_supervisor`. An isolated-import
reproduction traced one path through `monitor`, `measurement`,
`phase4_v1.lifecycle`, and `agent.action` to `arcengine`. The supervisor also
imports `replay` at module load; it reaches `arcengine` through `agent.state`.
The notebook process intentionally has neither game's
distribution nor access to the isolated game interpreter's site-packages.
The prior packaged-source omission was fixed: installation reached its
successful receipt before this new import-boundary failure.

All **seven** downloaded files were independently checked for byte count and
SHA-256 against `reports/perception_stage_b_r2_download.json`. The download
has no worker trajectory, model or monitor evidence. No study calls, game
actions, or level outcomes can be inferred or independently replayed. The
first-cell receipt confirms dependency-tree removal, but no independent GPU
cleanup check was reached. This is a pre-study failure, not evidence about
the grounded-action comparison or Phase 4 certification.

Account-wide GPU `time_used` rose from 10,697.547 seconds at prelaunch to
10,843.402 seconds after the error, a 145.855-second difference. That is
not exact billing for this attempt; exact per-attempt billing remains open.

The next local repair should keep `arcengine` imports inside the game
interpreter. Deferring only the replay import does not solve startup because
the monitor path also imports it. A successor should run the supervisor and
independent replay in the game interpreter, or review a complete split of
those import chains. Add a regression that imports the actual first-cell
boundary with `arcengine` absent and exercises live replay on CPU.
Freeze a successor notebook and obtain new approvals before considering
another GPU attempt. Do not reuse this consumed reservation.
