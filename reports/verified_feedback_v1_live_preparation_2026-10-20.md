# Verified executed feedback v1: bounded live-package preparation

Subsequent status: the owner authorized this exact package and one attempt was
submitted after fresh preflight. See the [launch record](verified_feedback_v1_attempt1_launch_2026-10-20.md).
The preparation account below preserves the state before that authorization.

The bounded runner, independent evaluator and exact private review package are
implemented and checked. **No upload, GPU launch, reservation, claim or new
authorization was created.** The review notebook remains GPU-disabled and
refuses before setup without fresh authority.

This follows the [CPU successor preparation](verified_feedback_v1_CPU_preparation_2026-10-20.md).
The question remains whether explicit, verified feedback about an executed
action changes subsequent forecasts or choices. Supplied retrospective labels
do not earn model-understanding credit. These checks used scripted replies and
establish software behavior, not neural improvement.

## Exact private review

| Binding | SHA256 |
| --- | --- |
| Final private review lock | `3a1aa3e4295c79c76dbf8728e0b29e493d0a01bc74fd6d6ad8e10b8605d66e0a` |
| GPU-refusing notebook | `a01c1849fb2ca57bb12565faa8736d15113f0babacdd8bf6fa483a4d2eb0bd41` |
| Live inference manifest | `af141118f37bbc41771d72de430d4bb520d8f4002c3b4910c8febceeb30883ad` |
| Exact CPU verification archive | `c321c88ba28cd748a3eb9c9384924a6b3ae0a386a91420e40944008cfe8e0aea` |
| Final handoff | `581219c0d7f00dff53c2c0ad334561323b58f0121910157fbc5fdf3059661847` |
| Private review packet | `634a5180b56793e9908ded245da4da4dfc43e8937befebad420ee2c89d8dfc57` |

The package and packet remain under the git-ignored
`.cache/github-review/verified-feedback-live-v1-2026-10-20/stage-r2/`.
`review_packet.md` identifies the exact notebook, immutable image, private model
source/mount, wheel source, use proposal and checks. Two private builds matched
byte for byte. The lock binds 87 review-source files and 55 execution-source
files. The inference payload contains no scripted server, test answers or
reference outcomes.

## Proposed execution scope, not authorization

| Resource | Ceiling/settings |
| --- | --- |
| Study | All eight original exposed checkpoints, 16 conditions, two decisions each |
| Model | Same pinned Qwen3-VL-30B-A3B-Instruct-FP8 dataset copy and revision |
| Accelerator | Exactly one RTX PRO 6000; actual allocation must be verified |
| Time | Requested session timeout 3,600 s; worker 3,300 s; admission cutoff 3,000 s; cleanup reserve 300 s |
| HTTP/generations | 33 total: one canary and 32 study replies |
| Tokens | Study cap 256 new tokens; canary 16; prompt cap 8,192 |
| Offline actions | 84 including 16 resets, 36 prefix actions and at most 32 new actions |
| Scorecards | 16 local; zero online game calls or leaderboard submissions |
| Access | Private account-only; internet/TPU off; sanitized summaries only |
| Attempts/retries | One attempt, zero automatic retries |

The requested session timeout is not a demonstrated full-job wall-clock cap:
provider allocation, mounting, setup and release may add time. All 174 wheels
are hash-checked before installation, with the retained hash-pinned requirements;
the model tree and 31 competition game wheels remain verified under the same
immutable runtime contract. Historical use and licence records are retained as
history, not relabelled as approval for this lock. The new use draft is explicitly
unapproved and has no owner statement.

## Implemented independent checks

The worker journals the original first answer and its forecast envelope before
dispatch. The independent evaluator rebuilds that envelope from the raw answer,
fixed candidate pair, event index and replayed before-state. It separately
derives changed cells, categories and forecast comparisons from actual
observations; it does not call the production receipt builder for this check.
Tests poison both production and replay with the same receipt/commitment bug
and require the independent checks to reject it.

Every request, observation, full action, transition and stop reason is rebuilt.
Native prompt counts, complete HTTP replies, ledgers and run-level action and
scorecard totals are checked. Reference branches are generated only during
independent evaluation, after inference. Supplied retrospective correctness
fields are moved into a diagnostic explicitly forbidding understanding credit;
future-action forecasts retain their independent reference scores. All scheduled
slots, including invalid or unreached ones, remain in the evidence.

The evaluator reports first-answer and second-state equality without filtering
divergent conditions. A second-state comparison requires both actual second
requests and observed second-phase records. Matching post-first-action states
alone do not establish that a second decision happened.

Startup ownership, installation descendants, absolute deadlines and cleanup
safeguards are inherited through 15 hash-pinned derivations. Final evidence
writes, GPU cleanup and source/environment removal remain within the lifecycle.
A provisional receipt alone cannot pass: the evaluator also requires the exact
return witness/marker, independently collected provider COMPLETE, matching saved
source/settings and exact evaluated evidence hashes.

## Exact-source validation

| Check | Result |
| --- | --- |
| Linux suite | **147 passed, 0 failures/errors/skips** |
| Fault coverage | Interrupted startup and registration, descendant cleanup, late writes/removal, source drift, false counters, shared receipt bugs and missing second phases |
| Actual worker path | **33 scripted loopback HTTP requests**, 32/32 phases reached and valid |
| Native prompt audit | Maximum **5,282/8,192** tokens |
| Independent CPU game/reference replay | 80 boots, 308 dispatches, 80 closes; separate from the proposed GPU action budget |
| CPU lifecycle | 539.71 s within the 1,500 s outer bound; owned groups absent, descendants reaped, temporary sources/environment removed |
| Review notebook | Refuses missing authority under Python `-S`, before optional imports; creates no files |
| Unauthorized launch packaging | Refuses without creating a reservation or claim |
| SDK boundary | Source/settings/shape/image/attachments/timeout serialization checked offline, no send |
| Historical attempts | All 456 inventoried files unchanged |
| Neural generations / GPU jobs / provider writes | **0 / 0 / 0** |

The initial local snapshot passed 146 tests but had a reporting edge case: it
could label a post-first-action state pair comparable when the second decisions
were absent. That snapshot remains preserved and unapproved. The final snapshot
adds the missing-phase regression and corrects the reporting; no model data or
scientific protocol changed between snapshots.

Read-only provider checks at `2026-10-21T02:53:00.617286+00:00` (October 20 in
the owner's timezone) passed account, quota, unused target, dataset versions,
private-model access, wheel/model inventories and competition-wheel inventory.
This was a zero-write snapshot, not current launch clearance or proof of actual
RTX allocation. The source-bound preflight must be refreshed before any send.

| Validation receipt | SHA256 |
| --- | --- |
| Exact-package audit | `7554c1760cc3357791afe9738bc950c3d575c63228729c24f3242d4a7b06f61d` |
| CPU lifecycle | `07607f967cce29529c8bf814948decb4b2413ab072977a683c7f26631a3038bb` |
| Scripted worker/replay | `df4a069b5905f326af71f44b12b39691352174446b41c5257a036a14d5565842` |

## Remaining launch gates

Fresh source/use and compute authorization must bind the final lock and the
33-generation scope. `live_runtime.check_authority` rejects missing or stale
proofs; the consumed nine-generation pilot approval cannot cover this package.
Only afterward can the operator refresh preflight, create a single-use
reservation/claim, submit once and verify the provider's saved configuration and
actual allocated accelerator. None of those steps has been performed here.

Even a technically complete run supports only a descriptive comparison on eight
correlated, exposed development checkpoints. It cannot establish generalization,
an internal reasoning mechanism or free object discovery/game-solving ability.
