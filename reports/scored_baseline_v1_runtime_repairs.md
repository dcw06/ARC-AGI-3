# Scored baseline runtime repair verification

The four findings reviewed at `ab202f3d5dd1f164ca302167bc2d438592b3725e` are addressed in the scored draft.
No Kaggle call, upload, reservation, GPU job or scored submission was made. No attempt was consumed.

| Finding | Repair | Reproduction on `ab202f3` | Repaired result |
| --- | --- | --- | --- |
| Bootstrap imports game SDK before installation | Lazy agent exports; refuse unapproved source before optional imports | Exact generated notebook fails with missing `arcengine` in `python -I -S` | Approval refusal; extraction tree removed |
| Process census stalls before SIGKILL | Scored owner sends SIGTERM before probing; bounded `/proc` worker probes; SIGKILL on uncertain absence; installation uses the same owner | 6.06 s despite 0.2 s deadline; neither termination signal sent; false absence receipt | Returns within 0.8 s; real child killed/reaped; stalled verification fails closed |
| Completion response has only an inactivity timeout | One-shot bounded caller wait covers headers, streamed body, JSON and response close; late results ignored; overdue client cannot be reused | Dripped response returns without the required timeout | Absolute deadline enforced; one call; real loopback HTTP drip also times out |
| Policy can return after admission closes and still act | Recheck after policy/fallback; gateway command admission after payload/cookie preparation, before journal dispatch | One acknowledged action after cancellation | Zero actions; refusal recorded before transport; scorecard close remains available |

The scoped installer adapter restores its factory even on interruption. Existing frozen research installer and
server files were not edited. Model/game startup keeps the retained interruption-safe ownership registration.
Shutdown does not signal a group again after verified absence; uncertain ownership never certifies absence.
Handled cleanup interruption still reaches termination and produces a failed receipt. The canary uses the same
bounded completion transport as the policy. An overdue reader may finish in an abandoned daemon thread, but its
result is ignored, the client refuses further calls, and the worker process group is terminated during cleanup.

## CPU verification

Linux development interpreter, GPUs hidden, network namespace with external networking disabled (loopback only):

| Check | Result |
| --- | --- |
| New runtime regressions | 10 pass, no failures or skips |
| Existing scored finalization and artifact tests | 5 pass |
| Broader affected controller, transport-equivalence, Phase 2 execution and diagnostic suite | 76 tests total: 75 pass, 1 pre-existing error, no skips |
| Native Windows finalization/artifact checks | 5 pass (same tests, not additional distinct coverage) |
| Four reproductions on archived `ab202f3` | All four fail at their behavioral assertions |
| Public and private saved notebook cells in clean pre-install interpreters | Both refuse at approval; no dependency import failure; extraction trees removed |
| Both snapshots | All artifact hashes, 163 payload hashes and Python compilation verified; GPU/TPU/internet disabled; unapproved |

The broader suite's one error is `ConfigurationTests.test_all_registries_are_json_compatible_and_versioned`:
it assumes every historical JSON ledger/claim has `schema_version`. This same `KeyError` occurs unchanged on
`ab202f3`; it was not silenced or repaired by changing retained research records. The suite therefore does **not**
have a clean overall pass. These checks use development fixtures and process/HTTP fault injections, not Kaggle
scoring or the actual pinned-image installation.

Regressions are retained in `tests/test_scored_runtime_gaps.py`. For the before/after comparison, archive `ab202f3`
into a separate clean directory, copy this test file into its `tests/`, and run these four methods from
`tests.test_scored_runtime_gaps.RuntimeGaps`:

- `test_clean_preinstall_notebook_refuses_at_approval`
- `test_stalled_census_cannot_delay_sigkill`
- `test_dripping_response_has_absolute_deadline`
- `test_policy_return_after_cutoff_dispatches_zero_actions`

Retained local evidence: `ab202f3_regressions.log`, `runtime_fixes_cpu.log`, and
`rebuilt_drafts_verification_r4.json` in the git-ignored scored-submission preparation directory. Earlier private
drafts and snapshot exports remain preserved. The current public review lock SHA-256 is
`51e06461f8400953162091476dbb6661e6a96dd27a14ca9eef3a406d78efcd0f`.

## Remaining launch gates

The submission remains blocked. Provider-side enforcement of the owner's one-hour cap over the **entire GPU job**,
including mounting/setup, has not been established. Still needed: independent review of these repairs and the
exact private package, pinned-image and production gateway validation, scored-use/output permission, hash-bound
source/compute approval, and a single-use reservation/claim. The draft approval boolean supplies none of these.
