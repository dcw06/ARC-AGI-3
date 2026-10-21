# Action-effect choice v2: completed format pilot

The single authorized pilot is **technically complete**, with **8/8 scheduled
study phases reached and valid**. The revised phase-specific interface worked
on these exposed cases. This is a compatibility result, not evidence of an arm
advantage or improved gameplay.

| Runtime and integrity | Result |
| --- | --- |
| Provider status / submissions | COMPLETE / one submission, no retry |
| Actual GPU | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Bounded lifecycle | 1,543.29 seconds, below the 3,300-second worker limit |
| Generations | 9/9 ceiling: one canary and eight study replies |
| Offline actions including resets | 20/20 ceiling: four resets, eight prefix actions, eight new actions |
| Local scorecards / online game calls | 4 / 0 |
| Native prompt counts | All nine independently matched; maximum 3,040/8,192 |
| Completion tokens | Maximum 53/256; all nine replies ended with `stop` |
| Cleanup | Verified, zero GPU processes; temporary environments and extracted sources removed |
| Evidence | All 19 downloaded files and 17 runtime-inventory files verified |
| Preservation | All 434 inventoried earlier-attempt files unchanged; this attempt consumed and retained |

The exact review lock is
`81bd5bf4b1c831a1ff5b5eb9e372966ea6e2b04fc48ddadf30d70dc64a63e035`,
built from reviewed source commit `e54f0b4`. The attempt is
`aec2-6683d6bf30fa4259ba1452ff8ba8a20c`.
The [submission record](action_effect_choice_v2_attempt1_submission_2026-10-20.md)
retains the prospective scope and provider-setting qualifications.

## Descriptive content checks

Only the first two original checkpoints, from ls20 and s5i5, were scheduled.
Each ran both arms with two decisions. Reference outcomes were reconstructed
afterward on fresh offline game restorations and were not supplied to the model.

| Arm | Phase | Reached / scheduled | Valid | Correct candidate-effect forecasts |
| --- | --- | --- | --- | --- |
| Neutral choice | First | 2/2 | 2/2 | 3/4 |
| Neutral choice | Second | 2/2 | 2/2 | 2/4 |
| Compare and review | First | 2/2 | 2/2 | 3/4 |
| Compare and review | Second | 2/2 | 2/2 | 2/4 |
| Total | Both | 8/8 | 8/8 | 10/16 |

These are exact pilot counts, not an accuracy estimate for new games. Both arms
produced identical parsed decisions at each corresponding checkpoint and phase.
There were six incorrect candidate-effect forecasts and no unknown candidate
forecasts. Both arms exhausted their planned two-action cap; no level was
completed.

| Second-phase feedback field | Correct | Recorded behavior |
| --- | --- | --- |
| Whether the preceding action changed the visible board | 0/4 | All four replies said `unknown` |
| Whether the immutable preceding forecast matched the result | 0/4 | All four replies said `unknown` |

The second-phase abstentions are valid schema outputs. They do not earn a
correct feedback interpretation when the retained observations and known
previous forecast determine the answer. Nothing was repaired, reclassified or
replaced after inference. The pilot resolves the observed format-compatibility
issue on its scheduled cases; feedback interpretation remains an open problem.

## Independent completion audit

Collection used read-only provider calls and checked version 1's saved source,
authority and settings before and after downloading. The evaluator checked the
review lock, lifecycle witness, exact return marker and provider COMPLETE, then
independently rebuilt requests, full game observations, transition outcomes and
scope counters. Its result is `technically_complete: true`,
`format_coverage_complete: true`, and `outcome_claim_permitted: false`.

Native tokenization used pinned Transformers 4.57.6 on CPU with networking and
GPUs disabled. A slow source check over the Windows/WSL filesystem boundary was
explicitly stopped without a receipt. The same audit then passed against the
externally pinned prelaunch source archive extracted on Linux-local storage;
no source or verification requirement was relaxed. Both check histories are
retained privately.

Independent game replay used a fresh hash-pinned offline environment: 20 engine
boots, 72 dispatches and 20 closes, including the counterfactual reference
branches. These evaluation-only CPU effects are separate from the GPU attempt's
20-action ceiling. The CPU audit finished in 409.04 seconds within its own
900-second bound, with owned process groups absent and its temporary environment
removed. Collection and evaluation made zero provider writes, zero new GPU
launches and zero neural generations.

| Retained receipt | SHA256 |
| --- | --- |
| Independent evaluation | `17c31034505edb9d252df1eadaf0cb5f0db3bf8f111b4e7f0099e5479a056fc2` |
| Exact evaluated run inventory | `236c9db32578db58d4ed9664cb484fcf22efd6808dfd014e348a304fc5b65484` |
| Native token replay | `144223085af64905ea8c0fb3314674915645a0dea4030f434beb57fe7c719da8` |
| Independent CPU lifecycle | `63d5bc3e2cb7953566f0817e538e46f8cfe482a564e41723bcc4a96844b22e78` |
| Sanitized aggregates | `8441b7181620e60291f7e4eb0dbfe9e9dc6143f071b576ca2711bb8eae8b3c4c` |

Raw outputs, approvals and replay journals remain private under the git-ignored
`.cache/github-review/action-effect-choice-live-v2-2026-10-20/collection-attempt1-r1/`;
original downloaded files remain under `.cache/aec2result1/`.

The next useful analysis is a read-only diagnosis of why the second-phase
replies abstained despite available feedback. The larger eight-checkpoint
comparison has not run and is not authorized by this consumed pilot attempt.

That [read-only diagnosis](action_effect_choice_v2_feedback_diagnosis_2026-10-20.md)
is now complete: the exact counts and unchanged prior forecasts were supplied
and correctly bound in all four second-phase prompts. The model's internal
reason for abstaining remains unestablished. No experiment or completed score
was changed.
