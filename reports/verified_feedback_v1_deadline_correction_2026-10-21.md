# Verified-feedback review corrections

The review reproduced. The completed attempt and its original package remain
unchanged. The results report now separates the repeated-action and other-action
forecasts and compares the repeated action with persistence. Its net gain does
not demonstrate prediction beyond that baseline. See the
[corrected results report](verified_feedback_v1_attempt1_results_2026-10-21.md).

| Second-decision measure | Summary only | Verified feedback |
| --- | --- | --- |
| Repeated-action forecast equals its preceding observed effect | 5/8 | 8/8 |
| Repeated-action forecast correct | 3/8 | 5/8 |
| Other-action forecast correct | 3/8 | 3/8 |
| Persistence forecast correct for the repeated action | 5/8 | 5/8 |

These values were recomputed from the unchanged independent evaluation
`440b7078d88e13c2bab1c1dc15623382d61f996b7937ccd692419ad9d7bb6de5`
and evaluated run inventory
`41acebe93924ccf1e4e34d3fc1b072bd2505a539fb66d27428741a1e6e2f5634`.
This is a post-run interpretation correction, not a replacement analysis or new
preregistered endpoint. The original run remains technically valid.

## Deadline behavior corrected for future reuse

Previously, a check after the last action or during engine closure could relabel
a completed condition as a deadline failure. Unlimited-time replay then refused
the resulting evidence. A genuine partial prefix also conflicted with the
worker's full-schedule aggregate assumptions.

| Case | Corrected behavior |
| --- | --- |
| Both decisions/actions finish before the next admission check | Preserve the natural action-cap or terminal reason |
| Admission closes before another request or action | Record the precise failed check boundary and retain the complete observed prefix |
| A request or dispatch intent was journaled but not admitted | Retain the intent; do not count it as an actual HTTP request or engine action |
| Too little headroom remains to start another condition | Retain each remaining scheduled slot as `not_admitted`, without creating an engine |
| Partial schedule has a valid lifecycle | Return its scored report with `study_schedule_complete=False` and `technically_complete=False` |
| Transport, journal, engine-close or hard-lifecycle failure | Remain a failure; no generic timeout is converted into a graceful stop |

Independent replay reproduces the recorded admission-check boundary and compares
every preceding event, request, answer, forecast commitment and fresh engine
observation. Missing or malformed stop receipts, forged boundaries and work
resuming after schedule admission stops are refused. All 32 scheduled answer
slots remain in the denominator. Actual resets, restored actions, continuation
actions, HTTP requests and closes are derived from retained admitted work.

The action/HTTP admission cutoff stays at 3,000 seconds. Engine closure can use
the separate cleanup reserve; it cannot reopen bootstrap or dispatch afterward.
The supervisor keeps its independent 3,300-second hard watchdog through worker
closure, group/GPU cleanup, source/environment removal and finalization. A late
finalization witness or failed cleanup still cannot certify a run. The frozen
scientific protocol, candidates, prompts, model and numerical resource ceilings
are unchanged.

## Validation

| Check | Result |
| --- | --- |
| Old-code reproductions | Both retained completion/close-cutoff regressions fail on `149c9e2` |
| Final exact-source Linux suite | **156 passed, 0 failures/errors/skips** |
| New regression coverage | Nine tests, including partial prefixes, unissued intents, unstarted conditions, false stop records, transport failures, cleanup admission and incomplete-status certification |
| Derivation check | All 15 derived files reproduce from their pinned parents |
| Real CPU engine cutoff check | Expired action refused; bootstrap and close only, no dispatch; scorecard closed and process reaped inside the cleanup reserve |
| Scripted real-game rehearsal | 33 loopback HTTP requests; all 32 scheduled phases reached and valid; maximum prompt count 5,282/8,192 |
| Independent rehearsal replay | 80 engine boots/closes and 308 dispatches, including reference branches |
| Rehearsal reuse binding | Final snapshot has exactly the same execution-source inventory and decompressed payload-member hashes as the rehearsed snapshot; final evaluator/status changes were tested separately on final source |
| Exact review notebook | Refuses under Python `-S` before optional imports, with no created files |
| Missing launch authority | Refused before any reservation/claim or launch directory is created |
| SDK serialization | Checked offline; no send |
| Historical preservation | Original package, completed attempt and older evidence retained and hash-checked |
| New GPU jobs / neural generations / Kaggle calls | **0 / 0 / 0** |

The isolated CPU rehearsals and final tests verified their owned-process cleanup
and temporary-environment removal. An initial local final-test harness lacked a
multiprocessing main guard. That check was interrupted, its failed watchdog
record was retained, and its output was not accepted as passing evidence. The
corrected harness used a fresh evidence directory and passed with its hard
watchdog running and cleanup verified.

## Review snapshot, not launch authority

| Final review artifact | SHA256 |
| --- | --- |
| GPU-refusing correction review lock | `67883a145cfb8917f2bb252f1f1c630c5d5b94678a403111966a21376d97b28a` |
| Review notebook | `999197300402e095705866a1cf2abc3380e9b6f596372bde71cbad08a9f517a5` |
| Exact final CPU source archive | `e1ec0027d7481a8663e8d15632ee1e99281762ff1c3f89f61f1a720fa40cf860` |

Two final review builds matched byte for byte. The original attempt's review
lock `3a1aa3e4…` remains preserved with its source archive and receipts. It does
not authorize this changed code. The correction snapshot retains the already
used notebook binding for comparison, so it cannot pass an unused-target launch
preflight. Its authority slot is empty; no new reservation or claim exists.

The final snapshot was built on Linux; the earlier correction snapshot was built
on Windows. Their compressed payload containers differ, while every decompressed
payload member has the same hash. Rehearsal reuse is based on verified member
contents, not an assertion that the two compressed ZIP files are identical.

Private correction receipts are under the git-ignored
`.cache/github-review/verified-feedback-corrections-2026-10-21/`. Final tests are
in `final-tests-r2/`; the final review is in `stage-r2/review-only/`. The earlier
correction snapshot is retained as superseded, not launch-approved. This work
does not authorize or imply another GPU attempt.
