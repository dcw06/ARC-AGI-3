# Initial geometry gameplay: launch preflight, October 18

**Updated: [smaller r5](initial_geometry_small_package_r5_2026-10-18.md) was approved
and submitted once; Kaggle reports RUNNING.** Its 343,350-byte review notebook uses the existing
competition wheel mount. Eighty-one Linux tests and a fresh exact-payload CPU
installation/12-episode replay pass. All seven fresh preflight checks passed
at 17:05:01 UTC. One new reservation/claim was consumed; SaveKernel returned
HTTP 200/version 1. Saved source/settings match r5, including the RTX PRO 6000
request; actual allocation and runtime results remain pending.

Previously, r4 was approved; two separately authorized submissions each passed
fresh preflight and failed with SSL EOF. No notebook/run is confirmed. The
history is retained in the [live-runtime report](initial_geometry_live_runtime_2026-10-18.md).
Both uncertain attempts and reservations remain consumed, with no automatic retry.
Source/use approval for r4 remains historical. Fresh r5 source/use and compute
records, reservation and claim are retained privately. Earlier consumed attempts
remain unchanged. No additional attempt or automatic retry is authorized.

[Read-only diagnosis](initial_geometry_ssl_diagnosis_2026-10-18.md) now strongly
implicates oversized request rejection: the notebook's embedded wheels expand
its JSON submission to about 58 MB. Verified TLS and small metadata calls pass;
large read-only requests reproduce rejection/SSL failure. No exact SaveKernel
size limit was established. The approved r4 package was not changed or resent.

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
