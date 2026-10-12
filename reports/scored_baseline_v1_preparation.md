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
| CPU checks | Four finalization tests passed in Linux with GPUs hidden and external networking disabled |
| Public review artifact | `notebooks/scored-baseline-one-hour-review/submission.ipynb`, with private bindings replaced by placeholders |
| Artifact integrity | Canonical byte writer and a native Windows regression verify that saved artifacts match their review-lock hashes |
| CPU scope | Late evidence write, missing source-removal certification, interruption after success write, final deadline checks |
| Full production validation | Not performed for this draft; new lifecycle, gateway and 110-distinct-client checks remain required |
| Authority/operator | No scored-scope approval records, reservation, claim or uploader created |

The draft has no publication or redistribution clearance. It has not been tested in the pinned Kaggle image and
must not be represented as a certified production runtime. In particular, the approval flag is a draft refusal
mechanism, not a substitute for real hash-bound source/use/compute/launch decisions. Runtime ownership, bounded
cleanup and failure paths still need full review before that mechanism is replaced with an authorized launcher.

Next: establish a supported platform-side one-hour cap for the scored rerun, then finish the CPU and pinned-image
validation, review the exact private source and scored use/output scope, and bind a single fresh attempt. Preserve
all existing research attempts. No further authorization is inferred from this draft.
