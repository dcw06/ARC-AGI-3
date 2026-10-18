# Initial geometry gameplay: launch preflight, October 18

**Updated: bounded live code and private review r4 are prepared; 70 tests and
read-only provider checks pass. No GPU submission was made.** The implementation,
package hash and current gates are recorded in the [live-runtime report](initial_geometry_live_runtime_2026-10-18.md).
Fresh approval records, a single-use reservation/claim and a new pre-send
preflight are still required. Earlier consumed attempts remain unchanged.

## Historical check before the live implementation

At this earlier check, the study lacked an executable live package.
The owner's new launch request triggered this check. It did not cause an old
zero-action MolmoPoint notebook to be reused for gameplay or a CPU rehearsal to
be presented as model inference.

Claude's three review repairs were on `initial-geometry-fixes-v1` (`591a281`,
documented in `3090718`). The automatic-arm provenance repair was on
`track-resumption-v1` (`2e263f0`). They have now been combined, preserving both
histories and unrelated local files.

| Gate | Result |
|---|---|
| Combined CPU regressions | 54 pass, no skips |
| Automatic-arm provenance | Committed replay producer; protocol r2 pins artifact and provenance; previous full replay reproduces `baaf83…` |
| Combined real-engine rehearsal | Fresh offline 31-wheel install; 12 two-action episodes with r2 inputs; all 12 independent engine replays pass |
| Game environment receipt | Independently pinned to `01b85c78457386896777692a3790c998ed9fd917b7bd90ac89f60af2dfa5292e` |
| Input manifest | `9698045c8a65c94e31935c4139ec36dd47e397d9cc7d0bc04467e81c0d63f491` |
| Native Qwen preparation | Historical processor receipt retained; request construction is unchanged; no new model forward pass claimed |
| Bounded live runner | **Absent**; `episodes.py` explicitly requires an external supervisor for injected engine/completion calls |
| Live Kaggle notebook/package | **Absent** for this study; the CPU preparation snapshot is marked `live_launch_package: false` |
| Protocol execution switch | `live_runs_enabled: false`; no launch was attempted |
| Actual accelerator availability/allocation | Not checked; local package gate fails first |

The current CLI entrypoints prepare input data, replay retained perception
evidence, audit Qwen prompts on CPU, and run a scripted CPU rehearsal. They do
not install/start the live Qwen service or supervise its connection to the
isolated game engine. `episode()` uses injected callbacks and explicitly cannot
interrupt a stalled callback; its content audit never supplies a lifecycle
certificate. Those limitations are unchanged by the four review fixes.

An executable private package still needs the model/game runtime wiring,
six-image vLLM configuration, absolute transport and engine deadlines, complete
child ownership and termination, GPU/temp cleanup and fail-closed finalization.
Its exact notebook/image/attachments, scoped-use evidence and launch authority
must then be bound and checked. Those are implementation and package-review
tasks, not issues that changing an approval flag would resolve. No existing
zero-action notebook is a substitute for this gameplay package.

The proposed study remains 12 episodes with at most 24 policy actions each,
one RTX PRO 6000, requested session timeout 3,600 s, worker limit 3,300 s,
up to 289 generations including a canary, and no automatic retries. The later
final protocol should explicitly list the supplied-mask and supplied-anchor
click diagnostics added by Claude. No claim that this proposed live runtime is
implemented, reviewed or allocated follows from the CPU checks above.

The local combined rehearsal used 24 scripted dispatches plus 12 bootstrap
resets, then independently replayed the same 36 offline actions. It opened and
closed 24 **local** scorecards in total. It made zero online game calls, online
scorecards, leaderboard submissions, model requests or GPU jobs. Private raw
traces remain git-ignored. Every earlier consumed attempt is unchanged.
