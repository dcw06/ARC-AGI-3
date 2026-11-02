# CPU leaderboard submission: E0 baseline with an exact ls20 specialization

Prepared November 2, 2026, following the owner's explicit request for an
**official leaderboard submission**, rather than a private ls20 demonstration.
Both original official submissions ended with Kaggle's generic system error
and returned no score. Corrected version 2 passed its expanded validation and
was submitted as **57922501**; see the
[comprehensive preflight report](cpu_leaderboard_preflight_r2_2026-11-02.md).

The competition evaluates unseen games. The memorized public ls20 route does
not establish a nonzero hidden-game score. This package uses the existing E0
deterministic action selector for other games. It uses the fitted policy only
when the complete game ID and initial observation match the tested ls20 trace.
There is no VLM, model attachment or GPU allocation.

| Setting | Package |
| --- | --- |
| Account and notebook | `daichongwei06/arc3-cpu-ls20-e0-submission-v1` |
| Visibility | Private, account-only |
| Hardware / network | CPU; GPU, TPU and internet disabled |
| Attachments | Competition only; no external wheel or model dataset |
| Installation | 31 competition-provided CPU wheels, individually hash checked; offline hash-pinned installation |
| Image | Original immutable image `37c64f7d…` |
| Phase A | Save & Run All: synthetic contracts only; official validation placeholder, no game calls |
| Phase B | One competition submission: hidden-game rerun; only the gateway creates scored `submission.parquet` |
| Game budget | Up to 110 games, 80 E0 actions each; exact ls20 specialization uses up to 151 actions |
| Maximum directional/interactive actions | 8,871 if ls20 plus 109 other games are present; 8,800 for 110 general games |
| Lifecycle | Requested session timeout 3,600 seconds; software lifecycle 3,300 seconds including installation and cleanup; game admission closes earlier |
| Scorecards / environment creation | One scorecard; at most one initial creation per game |
| Retries | No automatic action, validation-job or scored-submission retries |

The existing E0 action selector is reused, but the stopping rules and bounded
submission wrapper are new. General games stop at WIN, GAME_OVER or their action
cap; no recovery reset is sent. A fitted-trace mismatch stops that game without
switching to E0. This is not an unchanged rerun of the earlier 0.08 baseline,
and no score improvement is claimed before evaluation.

The old GPU scored draft is unchanged. Its unresolved GPU full-job cap is not
being relaxed or tested: this new candidate allocates no GPU. A requested
notebook timeout is not a guarantee about provider setup or scoring-rerun
inheritance. The worker's own deadline bounds its code after execution starts.

## Checks before upload

- 48 Linux tests passed with no failures or skips: 25 competition contracts,
  six packaging/deadline checks and 17 fitted-policy regressions.
- The final audit corrected a stale test fixture so the late-worker check
  actually advances its simulated clock. All 48 tests passed again; the
  deployed runtime was unchanged.
- Fresh offline installation of the 31 CPU dependencies passed, followed by
  all 48 tests. Local rehearsals caught a pip-less helper interpreter and a
  working-directory import collision before any provider write; both are
  preserved as local diagnostics, with zero real game calls.
- Child imports explicitly prioritize the frozen source tree. The scored
  worker receives an earlier admission cutoff and a later cleanup deadline.
- The hard watchdog remains active through artifact finalization and removal
  of the extracted source and temporary environment.
- Notebook and metadata hashes, all 33 embedded source hashes, the immutable
  image, attachment and CPU/offline flags are reviewed before the save.
- Read-only account checks confirmed competition entry, today's unused daily
  submission slot, the November 2 23:59 UTC deadline and the 31 mounted wheel
  names/sizes. Actual mounted bytes are checked inside the notebook.

Kaggle validation must complete before a separate scored submission. The
validation placeholder is explicitly labelled and is removed before the scored
rerun. It is never presented as a competition score. A missing gateway-generated
submission file or failed scorecard finalization makes the scored run fail.

## Package

These links are pinned to the source used by both original submissions:

- [Private notebook source](https://github.com/dcw06/ARC-AGI-3/blob/993397d/notebooks/cpu-leaderboard-ls20-e0-v1/submission.ipynb)
- [Metadata](https://github.com/dcw06/ARC-AGI-3/blob/993397d/notebooks/cpu-leaderboard-ls20-e0-v1/kernel-metadata.json)
- [Review lock](https://github.com/dcw06/ARC-AGI-3/blob/993397d/notebooks/cpu-leaderboard-ls20-e0-v1/review-lock.json)
- [Competition runtime](https://github.com/dcw06/ARC-AGI-3/blob/993397d/research/cpu_competition_v1/runtime.py)
- [Offline installer and supervisor](https://github.com/dcw06/ARC-AGI-3/blob/993397d/research/cpu_competition_v1/supervisor.py)
- [Builder](https://github.com/dcw06/ARC-AGI-3/blob/993397d/scripts/build_cpu_competition_v1.py)

Final package review-lock SHA256:
`5a2153e2b7f9f466d7eed0ce51bd32f3142c213aa7467ebc5e45ed98da6026e4`.
Notebook SHA256:
`f91197a4ac85b88f91058994514bdc14651d32fb364a8ff942d9fd932c73cef9`.

Account tokens, raw provider responses, operation intents and collected private
outputs stay outside Git in the local operational workspace. Prior research
attempts and the earlier scored submission are preserved.

## Provider status

| Event | Retained observation |
| --- | --- |
| Validation save | One Save & Run All at 19:39:14 UTC, November 2; private version 1; no rejected sources |
| Saved-package check | Source, immutable image, competition attachment, CPU/offline settings and version match the review lock |
| Validation outcome | COMPLETE, checked at 19:40:47 UTC |
| Official submission | **57919767**, accepted at 19:41:08 UTC; exact notebook version 1 |
| Initial scoring status | PENDING at 19:41:35 UTC |
| Terminal scoring status | **ERROR**, checked at 20:30:00 UTC; no score returned |
| Initial writes / retries | One validation save and one scored submission; zero automatic retries |

[Private notebook](https://www.kaggle.com/code/daichongwei06/arc3-cpu-ls20-e0-submission-v1)
is available to the owner; the submitted version is 1.
[Competition submissions](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/submissions)
shows both failed submissions when signed in. Both remain preserved.

Validation completion is not an official score. The hidden-game scoring rerun
is a separate provider job. The local single-use submission intent is consumed;
the operator will not repeat it automatically.

## System-error diagnosis

Kaggle returned: "A system error. Please try resubmitting to resolve the error
and contact Kaggle Support if it persists."

Read-only checks after the error established:

- The validation notebook remains COMPLETE. Its source, settings and version
  still match the reviewed package at 20:33:29 UTC.
- Its retained log confirms 48 tests passed, the validation placeholder was
  written, and the CPU lifecycle finished with cleanup in 17.4 seconds. These
  are validation results, not evidence that the scoring worker ran.
- The scoring API exposes no episodes for submission 57919767. Its submission
  record gives no scoring-session ID or detailed traceback. The cause is
  therefore unresolved; the generic message does not establish a code fault
  or prove that failure happened before execution.
- Kaggle's submission-limits endpoint reports `numAllowedNow = 1`. The earlier
  assumption that this failure consumed the daily allowance is corrected:
  Kaggle currently permits one submission, while the original local attempt
  remains consumed and preserved.

No source fix, provider write or fresh attempt was made during diagnosis. The
owner then explicitly authorized one fresh CPU submission, recorded below.
Raw API records and logs remain in the private operational workspace.

## Separately authorized fresh submission

The owner's instruction was: "Authorize one fresh CPU submission."

The fresh preflight confirmed the unchanged version-1 source and review lock,
private CPU/offline settings, immutable image and competition-only attachment.
It also confirmed the original attempt was ERROR, no other submission had been
made today, competition entry was valid, and one submission was still allowed.
An independent static review checked the new single-use request guard.

| Event | Retained observation |
| --- | --- |
| Submission | **57920889**, accepted at 20:36:23 UTC, November 2 |
| Source | Same validated notebook version 1; same review lock `5a2153e2…` |
| Initial status | PENDING at 20:36:53 UTC |
| Terminal status | **ERROR**, checked at 21:42:15 UTC; same generic system error, no score |
| New provider writes | Exactly one scored-submission request; no notebook save or validation rerun |
| Automatic retries | Zero; its separate send intent is consumed |

Both submission attempts and their independent operation records are retained.
No additional submission follows automatically if this attempt fails.
