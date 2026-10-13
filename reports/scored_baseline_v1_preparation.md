# One-hour scored E1S-R submission: blocked draft

October 12, 2026. This is a new scored-submission workstream, separate from the four research tracks.

**Not a launch-ready or approved package.** The owner requires one RTX PRO 6000, no automatic retries, and an
enforced one-hour limit on the entire GPU job, including mounting and provider setup. No upload, GPU launch,
scored submission, reservation or launch claim has been made for this draft.

The installed Kaggle SDK offers `session_timeout_seconds` through `kernels_push(timeout=...)`, but
`competition_submit_code` uses a separate `CreateCodeSubmission` request and has no timeout argument. This
inspection does not establish that the saved version's timeout is inherited by competition evaluation. No
platform-side one-hour enforcement has been verified. The agent's own deadline cannot limit mounting before the
first cell starts. Do not use a scored submission as an experiment to discover whether the cap is inherited.

Read-only signed-in competition metadata confirmed the competition is open, with a November 2, 2026 final
deadline, and **one daily scored submission**, rather than the older constraints registry's two. Quota is sufficient
for one hour; this does not establish current accelerator allocation or a submission slot remaining today.

## Draft work

| Item | Status |
| --- | --- |
| Policy | Existing E1S-R provisional primary; no research intervention promoted |
| Runtime sources | Draft split-interpreter installer/model/game wrapper using retained publisher and model inventories |
| Proposed agent deadlines | 3,600 s authorized; 3,300 s internal; study admission closes at 3,000 s |
| Proposed work ceilings | At most 110 games, 80 actions each; 8,800 policy generations and one canary; one scorecard, one scored submission |
| Draft packaging | Private notebook, GPU/TPU/internet disabled; source approval false; version-pinned inputs and immutable image |
| CPU checks | 15 scored-runtime/artifact tests pass on Linux; broader affected suite: 75 pass, one pre-existing registry-schema error, no skips |
| Public review artifact | `notebooks/scored-baseline-one-hour-review/submission.ipynb`, with private bindings replaced by placeholders |
| Artifact integrity | Canonical byte writer and a native Windows regression verify that saved artifacts match their review-lock hashes |
| CPU scope | Bootstrap, bounded termination despite stalled census/handled interruption, absolute response deadline, late action refusal, finalization; four regressions fail on `ab202f3` |
| Full production validation | Not performed for this draft; affected 110-client fixture passes, but actual scored package/gateway and pinned-image validation remain required |
| Authority/operator | No scored-scope approval records, reservation, claim or uploader created |

The draft has no publication or redistribution clearance. It has not been tested in the pinned Kaggle image and
must not be represented as a certified production runtime. In particular, the approval flag is a draft refusal
mechanism, not a substitute for real hash-bound source/use/compute/launch decisions. Runtime ownership, bounded
cleanup and failure paths still need independent review before that mechanism is replaced with an authorized launcher.

The four runtime findings from `ab202f3` are addressed and both disabled snapshots have been rebuilt. The public
review lock is `51e06461f8400953162091476dbb6661e6a96dd27a14ca9eef3a406d78efcd0f`; all 163 embedded source
hashes and saved artifact hashes verify. The exact saved cell refuses at the approval gate in a clean pre-install
interpreter and removes its extraction tree. See [repair verification](scored_baseline_v1_runtime_repairs.md) for
the before/after evidence and the existing broad-suite failure. No GPU or scored submission attempt was consumed.

Next: establish a supported platform-side one-hour cap for the scored rerun, then finish the CPU and pinned-image
validation, review the exact private source and scored use/output scope, and bind a single fresh attempt. Preserve
all existing research attempts. No further authorization is inferred from this draft.

The owner has reconfirmed the full-job cap and chosen the Kaggle-support path. The
[support request](scored_baseline_v1_platform_cap_support_request.md) is prepared but **not sent**. Read-only
inspection of the installed SDK also found a kernel-session cancellation request, but did not establish control
of a scoring rerun or guaranteed termination; a local watcher is not accepted as the cap. No scored launch is
authorized to test timeout inheritance. The current source and review snapshots are unchanged.

For the owner's immediate goal of seeing actions, a [private replay of retained real Qwen runs](retained_public_game_replay.md)
has been built and opened locally: four public games, 160 acknowledged actions, with before/after boards and playback.
This uses no fresh compute and does not create an official score or resolve the scored-job cap. Only the replay
builder/template and aggregate description are published; raw observations and the generated viewer stay local.
