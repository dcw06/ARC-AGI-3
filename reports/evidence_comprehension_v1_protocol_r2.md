# Evidence comprehension v1: protocol revision 2 (for review; no compute authorized)

**Status:** revision 2 of the draft. Revision 1 (`064bb9a`) is preserved as
`reports/evidence_comprehension_v1_protocol_r1.md`, `research/evidence_comprehension_v1/probes_r1.json`
and `reports/evidence_comprehension_v1_probe_summary_r1.json`.

The frozen probe set, keys, scorer, token audit and tests are built and pass offline. No model has
been called. The live runner and GPU-disabled review package come next. No GPU reservation,
upload or launch.

## Changes in r2 (review of r1)

1. **Prompt.** r1 kept the live instruction "choose exactly one action_id from legal_actions",
   which conflicts with questions asking for several ids, outcome labels or past actions.
   - The r2 system prompt says the task is a retrospective questionnaire, not a policy decision.
     It keeps the live factual control rules verbatim: the action-argument rules, and the note
     that a legal action's effect is unknown until observed.
   - It restates the one fact the imperative carried: `legal_actions` lists the ids that may be
     chosen next, and reset is never among them.
   - This is a documented departure from the live prompt. A test checks that the imperative is
     absent and that the factual spans match the live prompt.
2. **Schema validation.** r1's scorer accepted `{"answer":[6,6,6,6,6,6,6,6,6]}` (nine items, above
   `maxItems: 8`) and ignored numeric bounds.
   - r2 validates every response against the family's complete schema with an independent
     validator (`jsonschema`, Draft 2020-12) before any semantic scoring.
   - Integers must be real JSON integers. The validator itself accepts `6.0` and would otherwise
     let it through; booleans are rejected too.
   - Duplicates are recorded only within the permitted schema.
   - Regressions cover the reviewer's case, list length, numeric bounds, malformed action objects,
     envelope errors and non-finite numbers.
3. **Continuity.** r1 combined independent fixture pre- and post-frames, which left 27 adjacent
   acknowledged transitions discontinuous. That count is reproduced on r1's code.
   - r2 generates continuous trajectories from the ar25 development frame, using the real record
     code for every record:
     - every acknowledged result's final frame is the next action's starting frame;
     - a failed dispatch leaves the frame unchanged;
     - after an unknown outcome, the next frame may or may not differ.
   - Continuity is asserted by the builder, and re-checked independently by the key module, which
     decodes the frames itself.
   - Regressions break continuity after each outcome kind and require both checks to reject it.
4. **Labels and dependence.** r2 uses operational labels only: `criterion_met`,
   `below_accuracy_floor`, `inconclusive` and `not_diagnostic`. Each describes this diagnostic's
   criterion, never general comprehension. Questions share contexts, so:
   - question-level intervals are descriptive. The interval reported is a context-resampling
     bootstrap (2,000 resamples of whole contexts).
   - context-level results are reported: contexts, and contexts answered entirely correctly.
   - the gate uses no confidence bound. It uses point accuracy, plus accuracy on the questions
     where the family's most accurate shortcut is wrong.
5. **Grid comparison.** r1 compared different contexts and attributed any difference to the grids.
   - r2 asks identical questions about six preselected archived live observations twice: verbatim
     with grids, and with only `current_grid`, `previous_grid` and `recent_final_grids` removed.
   - The comparison is paired: both correct, only with grids, only without, neither.
   - It is still descriptive. A difference means presenting these grids changed the answers to
     these questions. It does not identify why.
6. **Contradictory description.** The live history description says `null` means a failed or
   unknown dispatch, but a dimension change also records `null` in an acknowledged entry.
   - Dimension changes are excluded from the gated set.
   - Three designed dimension-change trajectories are asked twice: with the live description
     (`legacy_description`) and with a corrected one (`corrected_description`). Only the
     description text differs.
   - The group is reported separately as a legacy-interface ambiguity and never enters the gate.

Also changed:
- **Per-family `max_tokens`**, set from the longest schema-valid answer, measured with the pinned
  tokenizer even when pretty-printed. r1's flat 192 could truncate a valid eight-action answer,
  which takes 297 tokens pretty-printed.
- **Exact token audit.**
- **Cache-disabled runtime scenarios**, built from bounds measured in the archive (see Budget).

## Question

Roadmap step 1: can the model answer factual questions about its own controls and
action-effect evidence? It never chooses an action, and no game is played.

Meeting the criterion means meeting this diagnostic's criterion on these questions. It does not
establish general comprehension. Failing it would not by itself show that the evidence
presentation is at fault: the diagnostic prompt and the model's underlying capability remain
alternative explanations.

## Question families

| Family | Research question | Answer |
|---|---|---|
| `available_actions` | Available vs unavailable actions (history may contain ids that are not currently legal) | set of ids |
| `coordinate_actions` | Which choosable actions need x and y | set of ids |
| `recall_action` | The exact action and coordinates at step *s* (shown, omitted or absent) | action, or `not_shown` |
| `outcome_class` | Acknowledged no-change vs failed vs unknown; transient vs final change | 5 outcome labels, or `not_shown` |
| `observed_effect` | An action's effect is unknown until observed (near-miss clicks are different actions) | outcome label, or `not_observed` |
| `tried_unchanged` | Which exact actions already left the still-current frame unchanged | set of actions |

## Conditions

| Condition | Contexts | Probes | Role |
|---|---|---|---|
| `evidence_only` | 36 generated + 8 designed continuous trajectories, no grids | 468 | **the main gate** |
| `legacy_description` / `corrected_description` | 3 designed dimension-change trajectories | 34 + 34 | matched; legacy-interface ambiguity, reported separately |
| `archived_with_grids` / `archived_without_grids` | 6 exact archived live observations (b1 history episodes of ar25, s5i5 and wa30, at decisions 5 and 11, preselected) | 66 + 66 | matched; descriptive |

The total is 668 probes per pass. Every evidence-only outcome label appears as the key at least
9 times. The keys are distributed as follows:

| Outcome label | Probes |
|---|---|
| no change | 48 |
| changed then returned | 16 |
| dispatch failed | 14 |
| final frame changed | 9 |
| outcome unknown | 9 |
| not shown | 22 |

Every gated family has at least 15 questions on which its best shortcut is wrong.

## Keys

Every key is computed twice:
1. **Primary:** from the shown history entries.
2. **Independent:** `independent.py` imports nothing. It decodes frames, recounts changes,
   re-checks continuity and answers with separate logic. For archived contexts, it works from the
   archived engine steps.

The build fails on any disagreement or discontinuity. A fresh build is byte-identical to the
frozen set, SHA-256 `f6f666a5…6309`.

## Shortcuts

Shortcuts are fixed before any model answers exist. The best shortcut per gated family:

| Family | Best shortcut | Accuracy |
|---|---|---|
| available_actions | ids seen in history | 0.159 |
| coordinate_actions | always `[6]` | 0.523 |
| recall_action | the latest entry | 0.533 |
| outcome_class | always no-change | 0.407 |
| observed_effect | ignore coordinates | 0.658 |
| tried_unchanged | every no-change entry | 0.659 |

## Pre-registered analysis

The thresholds are provisional engineering thresholds, not established scientific boundaries.

For each gated family, using answers correct in **both** passes:

| Label | Rule |
|---|---|
| `not_diagnostic` | The best shortcut reaches ≥ 0.90. None do in the gated set. |
| `below_accuracy_floor` | Accuracy < 0.70. |
| `criterion_met` | Accuracy ≥ 0.90, **and** at least 10 questions where the best shortcut is wrong, **and** ≥ 0.90 accuracy on those questions. |
| `inconclusive` | Anything else, including too few shortcut-wrong questions. |

A constant shortcut cannot meet the criterion: it would need 0.90 overall, which only a
non-diagnostic family allows. Missing and invalid answers count as wrong.

Always reported, never pooled away:
- per-pass labels, answer agreement, and both-correct accuracy;
- context-level results and the descriptive context-bootstrap intervals;
- the strata: near-miss clicks, untried actions, absent steps, empty history, and history
  containing unavailable ids;
- the matched tables for grids and for descriptions.

**Two passes.** Prefix caching is disabled, and the runner must verify that from the running
server. Pass 2 runs in reverse order. Two passes measure observed disagreement, not a precise
variance estimate.

## How the result is used

- **Gate families meet the criterion:** the evidence can be read under this prompt, and roadmap
  step 3 (evidence-guided action selection) is the next intervention.
- **Below the floor, or inconclusive:** that family's reading is the first thing to investigate.
  Candidate causes are the presentation, the diagnostic prompt, and model capability; this
  diagnostic does not choose between them.
- **Grid and description tables:** descriptive inputs to later presentation choices.

## Guardrails

- The bottom-row pattern in s5i5 and wa30 stays a hypothesis. Nothing masks it or reinterprets
  the completed experiment.
- Probes never recommend an action, and no answer reaches a policy.
- Development cases only. Archived contexts come from previously exposed games.
- Step 2 (progress versus visible change) will be a separate question set, with independently
  justified labels.

## Budget

These are exact counts from the pinned tokenizer, in `reports/evidence_comprehension_v1_token_audit.json`:

| Measure | Value |
|---|---|
| Calls | 1,336 (668 × 2 passes) |
| Prompt tokens per pass | 2,073,634 (4.15 M total) |
| Largest prompt | 26,294 tokens |
| Longest key answer | 52 tokens |

All requests are within the 60,000-token prompt ceiling and the 65,536-token context.

**Runtime.** Earlier timings came from a cached service and are not a bound. The runtime uses
bounds measured in the archived run:
- decode ≥ 110 tokens/s: the maximum over all calls of completion tokens per second of total
  latency. Caching does not affect decoding.
- uncached prefill ≥ 8,929 tokens/s: the slowest first call on a newly started game, with its whole
  latency counted as prefill. Those prompts were about 8.8 k tokens.

The schedule is:
1. evidence-only pass 1;
2. evidence-only pass 2, reversed;
3. the descriptive groups, pass 1;
4. the descriptive groups, pass 2, reversed.

The runner stops admitting calls at the admission cutoff, so a shortfall can only cut descriptive
groups. Including the 403 s startup:

| Scenario | Startup + gate | Everything |
|---|---|---|
| Measured bounds | 793 s | 1,331 s |
| Stress: prefill 2,500/s, decode 40/s | 1,283 s | 2,987 s |
| Stress: every call at its token cap | 2,464 s | 4,664 s (descriptive groups cut) |

The admission cutoff is 3,000 s: an internal limit of 3,300 s less a 300 s cleanup reserve. The
proposal remains one attempt of ≤ 3,600 s.

## Next

1. Runner, reusing the reviewed action-effect-history host, supervisor and evidence stack:
   - prefix caching disabled and verified from the running server;
   - the ordered schedule, with admission control;
   - per-call evidence, and scoring by the independent scorer.
2. The GPU-disabled review package, with a CPU rehearsal.
3. Your review, then separate source approval and compute authorization.
