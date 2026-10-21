# Verified-feedback study: corrected interpretation and deadline fixes

The review led to two corrections:

1. **The forecast gain does not show improvement beyond a simple rule:** predict that an action will have the same effect as last time.
2. **The code now handles the time limit correctly:** it preserves completed work and reports unfinished work without calling the study complete.

The completed GPU run remains technically valid. Its original data and software
package are unchanged. The deadline bug did not affect that run; the code fix is
for future use.

## What the forecast results mean

The study compared two settings: the existing summary alone, and the same
summary plus verified feedback about the previous action. Each setting was
tested at eight checkpoints.

At each checkpoint, the model chose between two actions and predicted the effect
of each. It then made a second decision with the same two options. In every
case, it chose its first action again. The feedback block told it what that
action had just done.

Overall, second-decision forecasts were correct **6/16 times with the summary
alone** and **8/16 times with feedback**. Splitting those forecasts by action
shows where the difference came from:

| Second-decision measure | Summary alone | With verified feedback |
| --- | --- | --- |
| Predicted the same effect as last time for the repeated action | 5/8 | 8/8 |
| Correctly predicted the repeated action's next effect | 3/8 | 5/8 |
| Correctly predicted the other action's effect | 3/8 | 3/8 |
| Simple baseline: predict the repeated action's effect will stay the same | 5/8 | 5/8 |

**The feedback setting's 5/8 score on the repeated action exactly matches that
simple baseline.** There was no net accuracy gain on the other action, and no
change in the selected actions. The results are consistent with copying the
previous effect into the next forecast. They do not establish better prediction
beyond that rule, better action selection, or an internal reasoning mechanism.

This breakdown was added after the run to explain the existing results. It does
not change any answers or scores, replace the original analysis, or count as a
new test planned before the experiment. See the
[corrected results report](verified_feedback_v1_attempt1_results_2026-10-21.md).

## Agent answer log from the completed run

Below are all **32 study answers** from the original completed GPU run: two
decisions under each setting at all eight checkpoints. These are the agent's
actual structured answers, not examples or outputs from the corrected runner.
No new inference was performed to create this log.

Each row preserves every answer field. The candidate actions and actual changed-
cell counts are added from the verified event log to make the answers easier to
follow. Counts include interface pixels and do not measure progress toward
solving the game. Action IDs are shown as recorded, without assuming what each
control means in a particular game.

Forecast categories mean: `none` = 0 changed cells, `1_to_4` = 1–4,
`5_to_64` = 5–64, and `65_plus` = 65 or more. `not_applicable` is required
on decision 1 because there is no preceding study action to check. On decision
2, the two previous-action fields refer to decision 1. The final column instead
shows what happened **after the action in that row**.

The feedback setting is given the preceding action's effect and forecast check
before decision 2. Repeating those supplied values is a consistency check, not
evidence of independent understanding. Both settings repeat the same selected
action at decision 2 in every checkpoint.

Open a game below to read its four answers. For the original answer text, see
the [downloadable JSON log](verified_feedback_v1_attempt1_agent_answers_2026-10-21.json).
That file includes all 32 model replies verbatim, plus the same action facts.
Private provider logs, dataset details, credentials and image payloads are
excluded from this public excerpt.

<details>
<summary>ls20 — board-01-step02</summary>

**Candidate A:** ID 2. **Candidate B:** ID 1.

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `5_to_64` | `5_to_64` | A (ID 2) | `not_applicable` | `not_applicable` | 2 |
| Summary alone | 2 | `5_to_64` | `none` | A (ID 2) | `unknown` | `unknown` | 2 |
| With feedback | 1 | `5_to_64` | `5_to_64` | A (ID 2) | `not_applicable` | `not_applicable` | 2 |
| With feedback | 2 | `1_to_4` | `65_plus` | A (ID 2) | `yes` | `mismatched` | 2 |

</details>

<details>
<summary>s5i5 — board-02-step02</summary>

**Candidate A:** ID 6 at (31, 63). **Candidate B:** ID 6 at (52, 9).

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `1_to_4` | `1_to_4` | A (ID 6 at (31, 63)) | `not_applicable` | `not_applicable` | 1 |
| Summary alone | 2 | `1_to_4` | `1_to_4` | A (ID 6 at (31, 63)) | `unknown` | `unknown` | 1 |
| With feedback | 1 | `1_to_4` | `1_to_4` | A (ID 6 at (31, 63)) | `not_applicable` | `not_applicable` | 1 |
| With feedback | 2 | `1_to_4` | `1_to_4` | A (ID 6 at (31, 63)) | `yes` | `matched` | 1 |

</details>

<details>
<summary>cd82 — board-03-step02</summary>

**Candidate A:** ID 1. **Candidate B:** ID 6 at (31, 28).

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `none` | `none` | A (ID 1) | `not_applicable` | `not_applicable` | 1 |
| Summary alone | 2 | `none` | `1_to_4` | A (ID 1) | `unknown` | `unknown` | 1 |
| With feedback | 1 | `none` | `none` | A (ID 1) | `not_applicable` | `not_applicable` | 1 |
| With feedback | 2 | `1_to_4` | `none` | A (ID 1) | `yes` | `mismatched` | 1 |

</details>

<details>
<summary>cd82 — board-03-step03</summary>

**Candidate A:** ID 1. **Candidate B:** ID 6 at (31, 28).

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `none` | `1_to_4` | B (ID 6 at (31, 28)) | `not_applicable` | `not_applicable` | 1 |
| Summary alone | 2 | `1_to_4` | `1_to_4` | B (ID 6 at (31, 28)) | `unknown` | `unknown` | 0 |
| With feedback | 1 | `none` | `1_to_4` | B (ID 6 at (31, 28)) | `not_applicable` | `not_applicable` | 1 |
| With feedback | 2 | `1_to_4` | `1_to_4` | B (ID 6 at (31, 28)) | `yes` | `matched` | 0 |

</details>

<details>
<summary>ft09 — board-04-step02</summary>

**Candidate A:** ID 6 at (31, 63). **Candidate B:** ID 6 at (14, 12).

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `none` | `none` | A (ID 6 at (31, 63)) | `not_applicable` | `not_applicable` | 0 |
| Summary alone | 2 | `none` | `none` | A (ID 6 at (31, 63)) | `no` | `matched` | 0 |
| With feedback | 1 | `none` | `none` | A (ID 6 at (31, 63)) | `not_applicable` | `not_applicable` | 0 |
| With feedback | 2 | `none` | `none` | A (ID 6 at (31, 63)) | `no` | `matched` | 0 |

</details>

<details>
<summary>ka59 — board-05-step02</summary>

**Candidate A:** ID 6 at (31, 31). **Candidate B:** ID 1.

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `1_to_4` | `none` | A (ID 6 at (31, 31)) | `not_applicable` | `not_applicable` | 1 |
| Summary alone | 2 | `1_to_4` | `none` | A (ID 6 at (31, 31)) | `unknown` | `unknown` | 1 |
| With feedback | 1 | `1_to_4` | `none` | A (ID 6 at (31, 31)) | `not_applicable` | `not_applicable` | 1 |
| With feedback | 2 | `1_to_4` | `none` | A (ID 6 at (31, 31)) | `yes` | `matched` | 1 |

</details>

<details>
<summary>ka59 — board-05-step03</summary>

**Candidate A:** ID 1. **Candidate B:** ID 6 at (31, 31).

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `none` | `1_to_4` | B (ID 6 at (31, 31)) | `not_applicable` | `not_applicable` | 1 |
| Summary alone | 2 | `1_to_4` | `1_to_4` | B (ID 6 at (31, 31)) | `unknown` | `unknown` | 0 |
| With feedback | 1 | `none` | `1_to_4` | B (ID 6 at (31, 31)) | `not_applicable` | `not_applicable` | 1 |
| With feedback | 2 | `1_to_4` | `1_to_4` | B (ID 6 at (31, 31)) | `yes` | `matched` | 0 |

</details>

<details>
<summary>sc25 — board-06-step02</summary>

**Candidate A:** ID 1. **Candidate B:** ID 6 at (15, 54).

| Setting | Decision | Forecast A | Forecast B | Chosen action | Reports previous change | Checks previous forecast | Actual changed cells after action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Summary alone | 1 | `none` | `none` | A (ID 1) | `not_applicable` | `not_applicable` | 8 |
| Summary alone | 2 | `none` | `1_to_4` | A (ID 1) | `unknown` | `unknown` | 4 |
| With feedback | 1 | `none` | `none` | A (ID 1) | `not_applicable` | `not_applicable` | 8 |
| With feedback | 2 | `5_to_64` | `none` | A (ID 1) | `yes` | `mismatched` | 4 |

</details>

## What was wrong with the deadline handling

The runner has two time limits:

- **At 3,000 seconds:** stop allowing new model requests and game actions.
- **By 3,300 seconds:** finish shutting down processes, cleaning up the GPU,
  removing temporary files and saving the final evidence.

The old code could check the first limit after the last action had already
finished, or while closing the game engine. It could then incorrectly label a
finished trial as a deadline failure. Here, a *trial* means one checkpoint run
under one of the two settings.

The independent evaluator also assumed a complete history. It could reject the
whole evaluation when a trial stopped partway through, instead of reporting the
work that had finished and clearly marking what was missing.

## How the corrected code behaves

| Situation | Corrected behavior |
| --- | --- |
| A trial finishes its two actions or reaches a game stopping condition | Keep the actual stopping reason; do not relabel it because the new-work cutoff passes during cleanup |
| The cutoff arrives before another request or action | Stop new work and save the exact point where it stopped, along with everything already observed |
| The log records a planned request or action that was never sent | Keep the log entry, but do not count it as work performed |
| Too little time remains to start another trial | Mark each remaining trial as `not_admitted`; do not start its game engine |
| Only part of the study finishes, but shutdown and cleanup succeed | Score the available evidence and mark the study incomplete: `study_schedule_complete=False` and `technically_complete=False` |
| A request, evidence write, engine shutdown or final deadline check fails | Keep the failure; do not treat it as an ordinary stop at the new-work cutoff |

The independent evaluator replays the saved history using fresh CPU game
engines. It checks the requests, answers, original forecasts saved before each
action, and resulting observations. It also verifies exactly where new work
stopped. Missing or altered stop records, inconsistent stopping points, and work
that restarts after admission has stopped are rejected.

All **32 planned study-answer slots** remain in the results, including missing
ones. Counts of resets, replayed setup actions, new actions, model requests and
engine closures come from the work actually recorded as performed.

Cleanup may use the time between the two limits, but it cannot allow new game
actions to start. A separate watchdog process enforces the final 3,300-second
deadline. Failed cleanup or late final evidence still prevents certification.
The scientific protocol, candidate actions, prompts, model and resource limits
are unchanged.

## Checks performed

| Check | Result |
| --- | --- |
| Reproduce the old deadline bugs | Both saved regression tests fail on `149c9e2` |
| Test the final corrected source on Linux | **156 tests passed; no failures, errors or skips** |
| Cover the new behavior | Nine regression tests cover partly finished trials, logged but unsent work, unstarted trials, false stop records, request failures, cleanup limits and incomplete-study status |
| Rebuild generated source files | All 15 files match the versions generated from their fixed parent files |
| Test the cutoff with a real CPU game engine | The late action was refused; no game action was sent. The scorecard closed and the engine process exited during the cleanup reserve |
| Rehearse with real games and a local scripted answer server | 33 local API requests; all 32 study answers completed and had valid format; largest prompt was 5,282 of 8,192 tokens |
| Independently replay the rehearsal | 80 engine starts, 80 closures and 308 actions, including the alternative-action checks used for scoring |

The final snapshot has the same execution-source files and the same unpacked
payload contents as the snapshot used for that rehearsal. This was checked by
file hash. The final evaluator changes were tested on the final source.

Additional package and preservation checks passed:

| Check | Result |
| --- | --- |
| Run the exact review notebook without authorization | It refuses before loading optional dependencies, including under Python `-S`, and creates no files |
| Try to build a launch without authorization | It refuses before creating a reservation, launch claim or launch directory |
| Check the Kaggle SDK request format | Checked offline; nothing sent |
| Check earlier evidence | The original package, completed run and older evidence are preserved and still match their recorded hashes |
| New GPU jobs, model generations or Kaggle calls during this correction | **Zero** |

The CPU checks also verified that their child processes were stopped and their
temporary environments removed. One local test attempt could not start its
watchdog because the test harness was missing the Python startup guard needed
for child processes. That attempt was stopped and its failure record kept; it
was not counted as a pass. After the harness was fixed, the checks passed in a
fresh evidence directory with the watchdog running and cleanup verified.

## Current status

The corrected package is **for review only**. Its notebook refuses to run
without authorization. No new approval, reservation or launch claim was created,
and no GPU run was started.

The snapshot still refers to the notebook used by the completed attempt, for
comparison purposes. It therefore cannot pass the launch check that requires an
unused notebook target. The old attempt's approval does not cover the changed
code.

Two builds of the final review package were identical. The final snapshot was
built on Linux and the earlier correction snapshot on Windows. The ZIP payloads
embedded in their notebooks differ, but all files inside those payloads have
matching hashes. Those matching execution files justify reusing the rehearsal.
The evaluator changes were tested separately on the final source.

## Evidence and file identifiers

The result breakdown was checked against these unchanged records:

| Record | SHA256 |
| --- | --- |
| Independent evaluation | `440b7078d88e13c2bab1c1dc15623382d61f996b7937ccd692419ad9d7bb6de5` |
| Evaluated run's file inventory | `41acebe93924ccf1e4e34d3fc1b072bd2505a539fb66d27428741a1e6e2f5634` |

The final correction snapshot is identified by:

| Artifact | SHA256 |
| --- | --- |
| Review lock identifying the exact correction package | `67883a145cfb8917f2bb252f1f1c630c5d5b94678a403111966a21376d97b28a` |
| Review notebook | `999197300402e095705866a1cf2abc3380e9b6f596372bde71cbad08a9f517a5` |
| Final CPU source archive | `e1ec0027d7481a8663e8d15632ee1e99281762ff1c3f89f61f1a720fa40cf860` |

The original attempt's review lock, `3a1aa3e4...`, remains preserved with its
source archive and evidence records.

Private correction records are in the git-ignored directory
`.cache/github-review/verified-feedback-corrections-2026-10-21/`:

- `final-tests-r2/` contains the final test evidence.
- `stage-r2/review-only/` contains the final review package.
- The earlier correction snapshot is retained as superseded and was never
  approved for launch.
