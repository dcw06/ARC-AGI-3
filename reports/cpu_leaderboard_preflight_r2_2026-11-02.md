# CPU leaderboard successor: comprehensive preflight

The first two submissions, **57919767** and **57920889**, returned Kaggle's
generic system error and no score. Both attempts and their original notebook
version are preserved. Their cause is still unresolved: the API exposes no
scoring traceback, and there are no exposed scoring episodes for the first
attempt. The saved notebook's log belongs to validation, not hidden scoring.

This successor fixes a reproduced startup gap, improves failure diagnostics,
and expands the checks that run before an official submission. It keeps the
same policies, action budgets, CPU hardware and private access scope.

## Findings and corrections

| Finding | Correction | Verification |
| --- | --- | --- |
| The worker aborted on the first unavailable gateway request. | Poll only the read-only inventory GET for up to 600 seconds, within the earlier work deadline. In-flight HTTP requests share that deadline. | The new regression fails on `5dd7664` and passes after the fix. Delayed HTTP 503 readiness is also tested over loopback. |
| Validation tested fake adapters but did not exercise the real HTTP transport and scored CLI together. | Add five integration tests using the production session, adapter and CLI against a loopback-only synthetic gateway. | Test startup, cookies, click coordinates, directional actions, scorecard close, lost acknowledgements and no POST retries. |
| Removing the temporary environment also deleted its worker log on failure. | Preserve a log tail of at most 2 MiB and a worker/cleanup diagnostic record before removal, while the hard watchdog remains active. | Failure-retention and no-overwrite regressions pass. The diagnostic record explicitly does not certify final lifecycle success. |
| Mock-clock tests printed apparent run-completion receipts into the notebook log. | Capture those fixture prints inside the tests. | Test results remain visible; simulated 3,030-second timings no longer appear as real run telemetry. |

The official starter also waits for gateway readiness. This supports the
startup correction; it does not prove either failed submission hit that race.
[Official starter](https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter/blob/main/scripts/build_notebook.py)

## What the broader audit checked

| Area | Result |
| --- | --- |
| Dependency installation | Fresh offline installation of all 31 hash-pinned CPU wheels passed. |
| Expanded suite | **63 Linux tests passed, zero failures or skips**, including five real HTTP integration tests and eight readiness regressions. |
| Network isolation | The fresh-install rehearsal ran in a local network namespace with only loopback enabled; no external services were reachable. |
| Exact built-notebook rehearsal | Attempted in a private filesystem namespace, but the local system rejected the first bind mount before any notebook code ran. The failure is retained; this check is not counted as passed. |
| Actual SDK compatibility | A separate local check used the installed `arc-agi 0.9.8` / `arcengine 0.9.3` REST handlers in competition mode over six retained development games: 170 successful handler calls and 161 acknowledged actions, including all 151 fitted ls20 moves. Three ls20 levels completed and one scorecard closed. |
| Budgets | Up to 110 games; 80 baseline actions per general game, or 151 fitted ls20 actions; one scorecard; no recovery resets. |
| Deadlines | Requested session timeout 3,600 seconds; software lifecycle 3,300 seconds, including installation, bounded readiness, work and cleanup. Admission and worker termination leave cleanup time. |
| Failure handling | No scorecard, bootstrap, action or official-submission request is automatically retried. Only safe readiness GETs may repeat. |
| Evidence and output | Scoring must use gateway-generated `submission.parquet`. Validation's dummy file is removed before scoring and is never reported as a real score. |
| Sealing | Both artifact hashes and all **35 embedded source hashes** match the review lock. |
| Settings | Private CPU notebook; GPU, TPU and internet off; immutable image; competition-only attachment; no external dataset or model. |

The `sitecustomize` message about missing `wrapt` appeared before the original
validation tests. Execution continued: all 48 tests passed and validation
finished in 17.4 seconds. That message is not a retained scoring traceback and
does not establish the system-error cause. Provider startup hooks have not
been disabled to hide it.

The public ls20 route is an exact-match specialization. Unseen games use the
E0 baseline. Neither the local ls20 success nor these deployment checks
establish a positive hidden-game score.

## Final package

| Item | SHA256 |
| --- | --- |
| Review lock, stage r5 | `c5e94554140ad712db4da40e1d40c73c2deffbd9973b07dd092aa79b01f745e0` |
| Notebook | `56f7d29a128468f4f1c67f1138b7f6f042d498cb3d7ad8f74c71c6672c0275d1` |

- [Notebook](../notebooks/cpu-leaderboard-ls20-e0-v1/submission.ipynb)
- [Review lock](../notebooks/cpu-leaderboard-ls20-e0-v1/review-lock.json)
- [Runtime](../research/cpu_competition_v1/runtime.py)
- [Installer and supervisor](../research/cpu_competition_v1/supervisor.py)

An independent review found no additional blocking issue in these source
bindings, deadlines or diagnostic writes. The complete built notebook could
not be rehearsed locally because of the mount failure above; the real scored
CLI and HTTP path did pass their separate integration checks. Provider
validation is recorded below when completed. Neither local tests nor a
validation run can certify Kaggle's hidden scoring infrastructure or guarantee
that a new official job will succeed.

## Successor execution status

| Check or event | Retained result |
| --- | --- |
| Corrected source commit | `0d6b3f3`, pushed before validation |
| Private validation save | One Save & Run All, creating version 2; no rejected sources |
| Provider source review | Exact reviewed source, image, attachments and private CPU/offline settings verified after save and again before scoring |
| Kaggle validation | COMPLETE, checked at 21:59:57 UTC, November 2 |
| Validation log audit | All **63 tests passed**; final CPU lifecycle closed; worker log, worker/cleanup diagnostic and validation parquet retained |
| Startup diagnostic | The missing-`wrapt` sitecustomize message also appeared in this validation; execution continued and all checks above completed |
| Fresh scoring preflight | Correct account and competition entry; both prior attempts still ERROR; no unexpected submission; provider allowance available; before deadline |
| Official submission | **57922501**, accepted at 22:00:53 UTC, using exact notebook version 2 |
| Latest scoring status | **PENDING**, checked at 22:01:22 UTC; no score or error yet |
| Attempts | One successor validation and one successor scored submission; no automatic retries |

[Monitor official submissions](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/submissions)
or open the
[private notebook](https://www.kaggle.com/code/daichongwei06/arc3-cpu-ls20-e0-submission-v1).
Version 1 and both failed official submissions remain untouched. Private
operation intents, raw provider responses and validation logs stay outside Git.
