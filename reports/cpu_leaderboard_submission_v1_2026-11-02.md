# CPU leaderboard submission: E0 baseline with an exact ls20 specialization

Prepared November 2, 2026, following the owner's explicit request for an
**official leaderboard submission**, rather than a private ls20 demonstration.
Provider submission status will be recorded below after the actual calls.

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

- [Private notebook source](../notebooks/cpu-leaderboard-ls20-e0-v1/submission.ipynb)
- [Metadata](../notebooks/cpu-leaderboard-ls20-e0-v1/kernel-metadata.json)
- [Review lock](../notebooks/cpu-leaderboard-ls20-e0-v1/review-lock.json)
- [Competition runtime](../research/cpu_competition_v1/runtime.py)
- [Offline installer and supervisor](../research/cpu_competition_v1/supervisor.py)
- [Builder](../scripts/build_cpu_competition_v1.py)

Final package review-lock SHA256:
`66c632afcfc2b12dcc2db7e68c011b012b5e536b23e10ac8ab263a6bc2f706e2`.
Notebook SHA256:
`88ebe3ebedfaf79c23fe861c0c67c7b3c57b30846fb0897d55eda57bb6423b92`.

Account tokens, raw provider responses, operation intents and collected private
outputs stay outside Git in the local operational workspace. Prior research
attempts and the earlier scored submission are preserved.

## Provider status

Not uploaded or submitted at the time of this preparation record.
