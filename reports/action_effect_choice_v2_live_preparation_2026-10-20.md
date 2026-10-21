# Phase-explicit format pilot: bounded live-package preparation

The prelaunch integration gaps from the review of `eabb499` are implemented in a
separate v2 path. A new private, GPU-disabled review notebook has been sealed.
No source/use/compute approval, reservation, launch claim, upload or GPU
submission has been recorded for it. Earlier consumed attempts are unchanged.

## Changes

| Previous gap | Implementation |
| --- | --- |
| V1 worker still selected | `action_effect_choice_live_v2.live_worker` executes the v2 phase-explicit flow and schemas. A separate notebook payload invokes that worker. V1 execution and evidence remain unchanged. |
| Larger limits | Frozen live protocol, worker ledger, engine admissions, runtime authority scope and independent totals all use the four-condition pilot: at most 9 generations/HTTP requests, 4 resets, 16 dispatches and 4 local scorecards. Resets plus dispatches total at most 20 offline actions. |
| Missing pilot input contract | Preparation verifies the original eight-case CPU manifest, selects only original ordinals 0 and 1, and reconstructs all four first requests. Separate frozen hashes pin the selected checkpoint file and inventory. Reordering/substitution, rehashed request changes, extra reference files and the wrong schema are refused. |
| Missing independent evaluation | Exact event replay rebuilds both phase-specific requests from full fresh game observations, carries the original first answer unchanged, and binds HTTP replies, request bodies, native counts, action admissions, final states and totals. Scheduled, reached and valid phase counts are separate. |
| Missing coverage rule | All eight study phases must be reached and valid to call format coverage complete. Invalid replies or a game ending after the first action preserve missing phases. Technical completion cannot promote missing coverage. Scientific outcome/arm-advantage claims remain disabled, even after a technically complete live run. |
| Missing exact notebook | The private lock binds 50 execution sources, 82 review sources, six inference files plus their manifest, immutable runtime/model/dependency contracts and historical scope evidence explicitly labelled as historical. New scoped-use approval remains pending. |

The runtime retains the reviewed deadline and cleanup machinery: requested
Kaggle session timeout 3,600 seconds, worker limit 3,300 seconds, admission cutoff
3,000 seconds and 300-second cleanup reserve. Provider allocation, mounting,
setup and release may extend the total beyond one hour. The actual allocation
must be exactly one RTX PRO 6000. Internet and TPU remain off; notebook, package
contents and raw outputs remain private and account-only. Sanitized summaries
only; zero online game calls or leaderboard submissions; no automatic retries.

## Validation

| Check | Result |
| --- | --- |
| Final exact-source Linux suite | **124 passed**, zero failures, errors or skips; includes the inventory guard and phase/stop/budget regressions |
| Actual worker, scripted HTTP | **9 requests**, all 8 study phases reached and valid; 4 real game conditions |
| Independent replay | 4 fresh real trajectory replays plus 16 reference branches; all 20 engines closed |
| Native prompt count | Maximum **3037 / 8,192** for the pilot's actual scripted requests |
| Lifecycle | Owned groups absent, descendants reaped, temporary environments removed within the 1,500-second CPU watchdog |
| Exact package | Two builds identical; GPU-refusing notebook runs without optional dependencies, rejects missing authority, and creates no launch claim |
| SDK boundary | Offline serialization matches source, RTX shape, image, privacy, attachments and requested timeout; nothing sent |
| Read-only provider readiness | Account, quota, absent target, dataset versions/privacy, 174-wheel/20-model-file inventories and 31 competition wheels matched; no provider writes |
| Preservation | All 434 inventoried completed-attempt files unchanged |

An additional read-only check exposed the scope inventory in the wrong local
subdirectory. The final package puts the factual model inventory at the expected
root, while keeping approval documents historical. A new build-time guard
rejects missing, duplicate, incomplete or invalid-size inventories. The final
124-test suite and connected rehearsal cover this corrected package.

The request-ledger regression reproduces the old gap: the old worker accepts a
10-request plan, while the pilot refuses it before admission. The pilot also
rejects older/expanded authority scopes. Rehashed phase/schema/forecast edits,
incorrect counters and stale lifecycle/provider evidence are refused.

One local package revision was superseded after adding the terminal-coverage
regression: the source-lock gate rejected the changed test hash. The corrected
private package was rebuilt twice with identical bytes. A subsequent CPU test
archive omitted the historical v1 protocol fixture; that failed check and its
cleanup receipt are preserved. A separate CPU-only archive adds the pinned
fixture without changing the private notebook or its lock.

These are local preparation checks, not GPU attempts. All scripted replies and
reference/replay data stay outside the private inference payload. Tests and
rehearsals establish software behavior, not neural format-compliance rates or
improved gameplay.

## Exact private package

| Binding | SHA256 |
| --- | --- |
| Private review lock | `81bd5bf4b1c831a1ff5b5eb9e372966ea6e2b04fc48ddadf30d70dc64a63e035` |
| GPU-refusing review notebook | `83c6736f093cebb8d0377277b3fd0dd28621eb141edc83a58069b9cac335167f` |
| Live inference manifest | `138bfcb8863a1129caf7ea95e9b9491a23332c814f8d4a8c2da973ac2cb11f52` |
| Corrected CPU-only verification archive | `b3a0cbbea99809bf29fc9ad374401735aa7908ca63afd3f770f34c29ddd26192` |

The private package and review packet are under
`.cache/github-review/action-effect-choice-live-v2-2026-10-20/stage-r3/`.
The review notebook remains `AUTHORITY = None`; running it refuses before setup.
The pending-use document is explicitly unapproved. Earlier use records were
retained in a historical subdirectory, without fabricating a new owner statement.

`scripts/derive_action_effect_choice_live_v2.py --check` verifies 18 derived
files against pinned v1 parents. The separate pilot contract and its seven
regressions are reviewed directly. The builder, worker, evaluator and operator
are part of the exact source lock. The previous CPU phase/schema derivation also
continues to match its three pinned parents.

## Owner/provider steps at preparation time

Subsequent update: the single approved pilot was submitted and independently
certified technically complete, with 8/8 valid study phases. See the
[results](action_effect_choice_v2_attempt1_results_2026-10-20.md).
The following preparation-time requirements remain recorded as history; they
do not describe an outstanding authorization for this consumed attempt.

Fresh approval must name the exact lock and scoped use, with one fresh RTX PRO
6000 attempt under the limits above. The authorization gate rejects older or
expanded scopes. Only after that can an operator perform a fresh read-only
provider preflight, create one reservation and claim, submit once and verify the
saved source/settings and actual accelerator. A read-only readiness snapshot passed at 2026-10-20T20:26:06.752728+00:00.
Quota, target and source availability must still be freshly rechecked before launch. No approval or
available GPU is inferred from the completed CPU checks.

A successful pilot would establish only end-to-end format acceptance and phase
coverage. It would not authorize the larger eight-checkpoint comparison.

Receipt hashes: final handoff `b43c7ba5141b68092bca566aeb26b646388cb04bde9c301c34b49716ff2620f4`; exact package audit `9abccb196eeec4a8dddc02083bca76ffb65d830e0678f02538bf9e56fc39e914`; successful CPU lifecycle `3730807252971565271507dd1837c9ff0e909cdfce23682f4c7fa43ba1072dbd`.
