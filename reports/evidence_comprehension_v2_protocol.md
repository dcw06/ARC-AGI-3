# Evidence comprehension v2: failure decomposition and two isolated comparisons (protocol r2, for review)

**Status:** revision 2, for review. The question set, keys, conditions, scorer and decision rules are frozen
and tested offline. No model has been called. The runner adaptation, the GPU-disabled notebook, the source
lock and the budget proposal come next. No compute is authorized: the unused v1 authorization is not
reusable. Revision 1 (`8e3eb5b`) is preserved at `reports/evidence_comprehension_v2_protocol_r1.md`.

## Changes in r2 (review of r1 at 8e3eb5b)

1. **The baseline freeze binds what v1 actually launched.** r1 hashed protocol revision 4
   (`evidence_comprehension_v1_protocol_r4.md`). The r3 package that launched bound revision 5,
   `reports/evidence_comprehension_v1_protocol.md`. The freeze record now:
   - binds revision 5;
   - binds the full r3 review source lock, SHA-256 `fa425fd07469defdccae26ffdbdc29233380d0086bbdd480b31e24515715c051`,
     and the launch package lock that names it;
   - requires every frozen file that the r3 lock binds (the protocol, question set, prompt and record code,
     scorer, review, summary and token audit) to match the hash that lock recorded. The build fails otherwise.

   Revision 4 is kept as historical context only. The questions themselves are unaffected.
2. **The budget accounts for the whole first cell.** r1 started from 416 s of model startup and added
   question time only. The estimate now separates four kinds of work that are not questions, each measured
   in v1 and given a planning allowance:
   - installation;
   - model startup;
   - other pre-question work;
   - post-question finalization.

   The 300 s cleanup reserve stays separate and is never spent by an estimate. r1's 1,509 s and 2.3×
   headroom were partial figures and are superseded (§11).
3. **`frame_since_step` states its limit.** The question now says that "stayed_same" compares final returned
   frames only, and that an intermediate returned frame may still have differed.

   Because the question set's version string seeds argument selection, the set was rebuilt as revision 2.
   It has the same rules and seeds, and every coverage minimum still holds. Counts below are for r2.
4. **Wording.**
   - An entry that counts toward `tried_unchanged` left no net final change. It is not described as having
     "no effect": a transient change can matter.
   - "No regression detected" under the 0.05 tolerance is not a proof of non-inferiority.

**Informed by the v1 result.** Everything here was designed after the v1 attempt `ecv1-4458251e` was
inspected. The v1 questions and answers are now development material, not an untouched validation set.

## Question

Can the model correctly identify what it can do now, and what it has already tried on the current frame
without a net final change? And which isolated representation change, if any, improves that?

This is a prerequisite for evidence-guided action selection. It is not a game-solving experiment: no action
is chosen and no game is played.

**Scope: observed frames only.** An identical visible frame does not imply identical hidden game state.
Every question and conclusion is about the frames and outcomes shown to the model.

## 1. The v1 baseline is frozen

`reports/evidence_comprehension_v1_baseline_freeze.json` (revision 2) binds the v1 attempt as launched. It
binds:
- the r3 review source lock (`fa425fd0…c051`) and the launch package lock that names it;
- protocol revision 5 (`reports/evidence_comprehension_v1_protocol.md`, the revision the lock bound);
- the prompts, questions and keys, record code, scorer, review, results, evaluation, archive, source approval,
  compute authorization and provider record.

That is 19 files in all. Every one the r3 lock binds must match the hash the lock recorded, and a test fails
if any file changes.

Protocol revision 4 is listed separately, as historical context only. v1's append-only dispositions record
is deliberately not hashed.

The findings this work targets are:

| Finding (v1; now development material) | Where v2 targets it |
|---|---|
| All 19 `coordinate_actions` errors answered `[6]` when ACTION6 was not legal | Control track |
| `tried_unchanged` was the weakest family (15/44) | History track: decomposed into six components |
| Changed-then-returned entries were read as no change | History track: `any_change`, `final_equals_pre`, `outcome_class` |

## 2. Failure decomposition: question families

Target families are the composites the decision rests on. Component families locate where reading breaks;
they are reported and checked for regressions, never gated on their own.

| Track | Role | Family | Question | Answer |
|---|---|---|---|---|
| control | component | `legal_actions` | Which action_ids are legal? | set of ids |
| control | component | `action6_legal` | Is 6 in legal_actions? | yes / no |
| control | component | `coordinate_rule` | Which ids take x, y under the rules, legal or not? | set of ids (always `[6]`: reported, not diagnostic) |
| control | **target** | `legal_coordinate_actions` | Which legal ids take x, y? (v1 wording) | set of ids |
| history | component | `step_action_match` | Was step *s* exactly this action, coordinates included? | yes / no / not_shown |
| history | component | `dispatch_status` | Was step *s* acknowledged, failed or unknown? | 3 statuses / not_shown |
| history | component | `any_change` | Did any returned frame of step *s* differ from the frame before? | yes / no / not_observed / not_shown |
| history | component | `final_equals_pre` | Was step *s*'s final frame the same as the frame before? | yes / no / not_observed / not_shown |
| history | component | `frame_since_step` | Has the frame stayed the same since step *s* started, comparing final returned frames only? | stayed_same / changed_at_least_once / cannot_tell / not_shown |
| history | component | `qualifying_steps` | Which shown entries left the still-current frame with no net final change? | set of steps |
| history | **target** | `tried_unchanged` | The deduplicated exact actions that qualify (v1 wording) | set of actions |
| history | **target** | `outcome_class` | The five-way outcome of step *s* (v1 wording) | 5 labels / not_shown |
| history | **target** | `observed_effect` | The latest outcome of exactly this action (v1 wording) | 5 labels / not_observed |

Target questions reuse the v1 wording and answer schemas verbatim, so any difference between the conditions
is attributable to the condition, not to the question.

**What qualifying means.** Following v1's explicit rule, an entry qualifies for `qualifying_steps` and
`tried_unchanged` if it was acknowledged, its final returned frame equals the frame before it, and no later
entry changed the final frame or had an unknown outcome. A changed-then-returned (transient) entry therefore
qualifies. Such entries are described as leaving **no net final change**, never as having "no effect": a
transient change is evidence and may matter.

**What `stayed_same` means.** In `frame_since_step`, "stayed_same" is a statement about final-frame
comparisons only. It does not mean that no intermediate returned frame differed, and the question says so.

## 3. Conditions: one registered intervention each

| Condition | Asked | Differs from the baseline by |
|---|---|---|
| `baseline` | every family | nothing: the frozen v1 questionnaire prompt and the live history field |
| `control_candidate` | control families | one sentence inserted into the system prompt, after the argument rules |
| `history_candidate` | history families | the history field replaced by normalized, information-equivalent records |

**Control instruction** (the only change to the prompt):

> To find which available actions take coordinates, intersect the two rules above: an action takes x and y
> only if it is ACTION6, and it is available only if its action_id is in legal_actions. When 6 is not in
> legal_actions, no available action takes coordinates, even if ACTION6 appears in the history.

**Normalized history records** (`research/evidence_comprehension_v2/representation.py`). Each entry carries
the same evidence and the same uncertainty as the baseline entry:
- the action becomes one object, `action`;
- `dispatch` states the status in words;
- `returned_frames` gives a phrase per returned frame: "same as the frame before the action", or "differs
  from the frame before the action (12 cells)";
- `final_frame` gives the final comparison;
- a failed or unknown dispatch reads "none observed" / "not observed" instead of null;
- the field description is rewritten to match. It no longer says every null is a failed dispatch.

Normalization and denormalization are exact inverses, which is tested on every shown entry and on dimension
changes. Every field is derived from its own entry only. No field aggregates across entries, so the model is
not handed the qualifying set. A tool that computes that answer would be a separate, separately
labelled arm; it is not part of this protocol.

The interventions contain no game-specific content, no action recommendation and no offline probe discovery.
This is tested.

## 4. Cases

**Fresh continuous synthetic trajectories** (`research/evidence_comprehension_v2/trajectories.py`) are
generated with frozen rules and seeds. They start from the same ar25 development frame as v1, and every
record is built by the real record code and shown through the live history field. Continuity is asserted
while building and re-checked independently.

There are ten templates, each targeting a v1 finding or a boundary case:
- **mixed:** a random mix of outcomes.
- **near-miss clicks:** clicks at neighbouring coordinates.
- **transient:** changed-then-returned outcomes.
- **failed and unknown:** failed and unknown dispatches.
- **same-frame repeats:** repeated actions on the same frame.
- **stale unchanged:** unchanged entries followed by a change or unknown, then more unchanged entries.
- **level boundary:** a level change partway through.
- **reset boundary:** a reset partway through.
- **long with omitted entries:** more entries than the history window shows.
- **empty history:** no entries.

Across all templates, legal sets alternate between including and excluding ACTION6. Clicks appear in
history whether or not ACTION6 is legal now, and the starting level varies.

Across the ten templates the question set covers every required boundary case:
- unavailable ACTION6 with clicks in history (34 withheld control contexts);
- neighbouring click coordinates;
- absent history;
- failed dispatch;
- unknown outcome;
- transient change;
- reset;
- level transition.

After a reset or level change, the live field shows only the new segment. Questions about earlier steps have
the key `not_shown`, which is tested.

**Partitions.** Near-duplicate questions from one trajectory always stay in the same partition.

| Partition | Contexts | Seed | Passes | Use |
|---|---|---|---|---|
| withheld | 120 (12 per template) | `evidence-comprehension-v2-withheld` | 2 | **the decision** |
| development | 30 (3 per template) | `evidence-comprehension-v2-development` | 1 | descriptive; for later development |
| transfer | the 6 archived live observations v1 asked without grids | from v1 | 1 | descriptive transfer check; previously exposed |

No observation appears twice, in any partition, so no request is repeated and no withheld question reappears
in development. The withheld partition and both candidates are frozen in the same commit, before any model
answers exist.

**Balance.** For each question the balancer picks the argument that minimises the use so far of its key label
and of its most-used correct shortcut. It uses keys and shortcuts only, never answers. The resulting target
key distributions in the withheld partition are:
- `legal_coordinate_actions`: 60 `[6]` / 60 `[]`;
- `tried_unchanged`: 62 non-empty / 58 empty;
- `outcome_class`: 23 no change, 52 changed then returned, 21 failed, 18 final changed, 19 unknown, 38 not
  shown;
- `observed_effect`: every label 20 or more times.

## 5. Keys

Every key is computed twice:
1. **Primary:** `probes.primary_key`, from the shown baseline entries.
2. **Independent:** `independent.py` imports nothing. It decodes frames, recounts changes, applies the
   segment boundary and the four-entry window itself, and answers with separate logic. Archived contexts are
   rebuilt from the hash-verified archived engine steps.

The build fails on any disagreement, any discontinuity, any non-equivalent candidate record, or any
condition that differs from the baseline by more than its intervention.

The frozen set (revision 2) is `research/evidence_comprehension_v2/probes.json`, SHA-256 `d713e414…7cec`,
with 4,532 questions. A fresh build is byte-identical to it.

## 6. Shortcuts (predeclared, withheld partition)

The shortcuts include the v1 error patterns: always `[6]`, a transient change read as no change, and a null
read as no change. The best shortcut per family:

| Family | Best shortcut | Accuracy | Questions where it is wrong |
|---|---|---|---|
| legal_coordinate_actions | always `[]` (always `[6]` ties) | 0.500 | 60 / 120 |
| tried_unchanged | transient entries excluded | 0.783 | 26 / 120 |
| outcome_class | changed-then-returned read as no change | 0.696 | 52 / 171 |
| observed_effect | changed-then-returned read as no change | 0.848 | 25 / 164 |
| legal_actions | all seven | 0.083 | 110 / 120 |
| action6_legal | always "no" | 0.500 | 60 / 120 |
| step_action_match | ignore coordinates | 0.657 | 69 / 201 |
| dispatch_status | the latest entry's status | 0.283 | 86 / 120 |
| any_change | the final frame only | 0.800 | 24 / 120 |
| final_equals_pre | null read as no change | 0.525 | 57 / 120 |
| frame_since_step | unknown read as unchanged | 0.742 | 31 / 120 |
| qualifying_steps | transient entries excluded | 0.758 | 29 / 120 |

These frozen minimums are enforced by the build, per target family and condition in the withheld
partition: at least 60 questions, at least 20 on which the best shortcut is wrong, and at least 30 contexts.
Every component family has at least 60 questions.

## 7. Inference settings (fixed)

- **Model:** `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`, with the pinned Qwen3-VL tokenizer (`.cache/phase4-tokenizer`).
- **Decoding:** temperature 0, seed 0, thinking disabled.
- **Response format:** strict JSON Schema per family.
- **`max_tokens`:** per family, at least the longest schema-valid answer pretty-printed (checked by the audit).
- **Prefix caching:** disabled and verified on the running server, as in v1.
- **Request:** the system prompt, then one user message holding `{observation, question}`.

A test enforces that requests contain nothing else: no keys, strata, shortcuts, trajectories, partition names,
future events or grids.

## 8. Order, repetition and stopping

- **Order:**
  1. withheld, pass 1: contexts in seeded order, with each question's baseline and candidate adjacent in
     seeded order;
  2. withheld, pass 2, in exactly reversed order;
  3. development, pass 1;
  4. transfer, pass 1.
- **Scheduled calls:** 8,004. The withheld passes take 3,472 calls each, development 874 and transfer 186.
- **Repetition:** the two withheld passes are repeated deterministic calls, not independent samples. A
  withheld question counts as correct only if it is correct in both passes. Disagreement between the passes
  is reported. Uncertainty is estimated at context level.
- **Stopping and admission:** v1's controls are reused unchanged:
  - the per-call bound;
  - idle verification after a cancellation;
  - admission control against the 3,000 s cutoff (the 3,300 s internal limit less the 300 s cleanup
    reserve);
  - a stop after two consecutive timeouts.

  A cut run is reported as cut.

**Complete or incomplete.** The withheld result is `complete` only if every withheld question has a returned
answer in both passes. Otherwise each affected track is `incomplete`, and nothing is promoted. A missing answer
is never scored. An invalid answer was returned, so it counts as wrong.

## 9. Metrics and decision rules (frozen in `research/evidence_comprehension_v2/score.py`)

**Per family and condition** (withheld partition, both-correct), the v1 rules apply unchanged:

| Label | Rule |
|---|---|
| `incomplete` | Any question lacks an answer in either pass. |
| `not_diagnostic` | The best shortcut reaches ≥ 0.90. |
| `below_accuracy_floor` | Accuracy < 0.70. |
| `criterion_met` | Accuracy ≥ 0.90, at least 10 questions where the best shortcut is wrong, and ≥ 0.90 on those. |
| `inconclusive` | Anything else. |

These are the continuing proposed comprehension criterion: 90% overall and 90% on shortcut-disagreement
questions. They are provisional engineering thresholds and are not revised after results are seen.

**Paired, per track and family**, on the same questions:
- improvements (baseline wrong, candidate right);
- regressions (the reverse);
- both right, and neither right;
- the accuracy difference, with a 95% interval from 2,000 whole-context resamples.

**Track verdict** (withheld partition only). The first rule that applies decides:

| Verdict | Rule |
|---|---|
| `incomplete` | Any withheld question of the track lacks an answer, under either condition, in either pass. |
| `baseline_meets_criterion` | The baseline meets the criterion on every target family. |
| `candidate_clear_improvement` | The candidate meets the criterion on every target; wherever the baseline does not, the difference's lower bound is > 0; and no family of the track regresses. |
| `mixed` | Some target's lower bound is > 0, and some family regresses. |
| `improved_below_criterion` | Some target's lower bound is > 0, and nothing regresses. |
| `no_clear_improvement` | Anything else. |

A family regresses when its difference's upper bound is < 0, or when the candidate's accuracy is more than
0.05 below the baseline's. This tolerance is a preregistered engineering choice. When no regression is
detected, that is reported as such; it is **not** a demonstration of non-inferiority.

Only `candidate_clear_improvement` promotes a candidate.

**Always reported, never pooled away:**
- the single-condition labels for both conditions;
- components by family;
- strata (legal status × clicks in history, templates, not_shown / not_observed, neighbouring clicks, entry
  outcomes);
- agreement between the passes;
- the development and transfer partitions, as descriptive results;
- token counts and latency, from the run's own records;
- provider accounting, separately from internal timing.

## 10. How the result is used (step 8)

| Result | Next step |
|---|---|
| Both tracks meet the criterion, through `candidate_clear_improvement` or `baseline_meets_criterion` | Consider a small prospective action-selection experiment. It needs its own protocol and authorization. |
| A track is `improved_below_criterion` or `no_clear_improvement` | Investigate that track's evidence representation or the model's capability before adding planning. The components show where reading breaks. |
| A track is `mixed` or `incomplete` | Report it as such. Do not promote the intervention. |

A later tool that computes the answer would be labelled tool-assisted. It would not be claimed as unaided
comprehension.

The action-selection experiment that might follow would ask whether understood evidence helps the agent
avoid unproductive repetition and complete more levels within the same budget. It must still permit
deliberate repetition when that is justified: no visible change is evidence, not an automatic penalty or a
permanent ban.

## 11. Budget

The prompt-token counts below are exact, from the pinned tokenizer, in
`reports/evidence_comprehension_v2_token_audit.json`.

| Measure | Value |
|---|---|
| Scheduled calls | 8,004 (4,532 distinct requests) |
| Prompt tokens scheduled | 4.97 M |
| Largest prompt | 916 tokens |
| Longest valid answer | Within every family's `max_tokens` |

**The whole first cell.** v1's first cell took 916.1 s, all of it measured and retained in the v1 archive.
The allowances are planning figures, not measurements:

| Work | v1 measured | Allowance |
|---|---|---|
| Installation | 131.2 s | 262 s (2×) |
| Model startup | 415.8 s | 624 s (1.5×) |
| Other pre-question work (monitor, canary) | 2.0 s | 30 s (minimum) |
| Questions | 363.0 s (a different workload) | from the fitted rates below |
| Post-question finalization | 4.1 s | 30 s (minimum) |
| Cleanup reserve | — | 300 s, separate; no estimate spends it |

**Question time** is fitted to v1's 1,308 measured call slots, taken with caching off on one RTX Pro 6000.
The fit is 0.0187 s per call, plus 5.5e-5 s per prompt token, plus 0.0066 s per completion token. It
describes a different workload, so the scenarios are not guarantees.

| Scenario | Questions start | Withheld done | Everything done | First cell ends |
|---|---|---|---|---|
| Measured overhead, v1 rates | 549 s | 1,647 s | 1,819 s | 1,823 s |
| Allowance overhead, v1 rates | 916 s | 2,014 s | 2,186 s | 2,216 s |
| Allowance overhead, 2× slower | 916 s | 3,112 s: withheld pass 2 cut, `incomplete` | cut | — |
| Allowance overhead, 3× slower, every call at its cap | 916 s | cut | cut | — |

The withheld decision fits the 3,000 s admission cutoff up to a slowdown of 2.23× the v1 rates with measured
overhead, or 1.9× with the allowances. Beyond that, admission control stops the run and the result is
`incomplete`. These figures replace r1's 1,509 s and 2.3×, which counted model startup but no other overhead.

The proposal remains one attempt of ≤ 3,600 s. A new, separately sized authorization is required.

## 12. Next (not done yet)

1. Review this protocol and the frozen question set.
2. Adapt the v1 supervised questionnaire stack. This means the frozen schedule, identified passes and
   partition-aware completeness, together with the required regressions: every response retained and
   independently rescored, and interrupted schedules reported incomplete. No new infrastructure is added
   without a concrete need.
3. Build the GPU-disabled notebook, source lock and budget proposal; then package review.
4. Obtain source approval and a new compute authorization; then reserve and launch one attempt.
5. Archive the run, reproduce the evaluation independently, and record provider accounting separately.

Subgoals, hazard reasoning, recovery and deliberate restarting remain the subsequent research program.

## Files

| File | Contents |
|---|---|
| `research/evidence_comprehension_v2/trajectories.py` | generation rules, templates, seeds |
| `research/evidence_comprehension_v2/probes.py` | families, questions, conditions, keys, shortcuts, balancing |
| `research/evidence_comprehension_v2/representation.py` | the normalized history candidate |
| `research/evidence_comprehension_v2/independent.py` | independent keys (imports nothing) |
| `research/evidence_comprehension_v2/score.py` | scoring, paired comparison, verdicts |
| `research/evidence_comprehension_v2/probes.json` | the frozen question set, trajectories, frames and schedule |
| `scripts/build_evidence_comprehension_v2.py` | build and `--check` |
| `scripts/audit_evidence_comprehension_v2_tokens.py` | token audit and runtime scenarios |
| `reports/evidence_comprehension_v2_probe_summary.json` | counts, strata, shortcuts |
| `reports/evidence_comprehension_v1_baseline_freeze.json` | v1 baseline hashes |
| `tests/test_evidence_comprehension_v2.py` | 35 regressions |
| `reports/evidence_comprehension_v2_protocol_r1.md` | protocol revision 1, preserved |
