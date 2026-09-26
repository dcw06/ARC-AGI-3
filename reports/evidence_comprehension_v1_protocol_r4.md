# Evidence comprehension v1: protocol revision 4 (for review; no compute authorized)

**Status:** revision 4, accompanying the local runner and GPU-disabled review package. Earlier
revisions are preserved:
- r3 (`fbb70cd`): `reports/evidence_comprehension_v1_protocol_r3.md`;
- r2 (`1a6bf29`): `reports/evidence_comprehension_v1_protocol_r2.md`;
- r1 (`064bb9a`): `reports/evidence_comprehension_v1_protocol_r1.md`,
  `research/evidence_comprehension_v1/probes_r1.json` and
  `reports/evidence_comprehension_v1_probe_summary_r1.json`.

The probe set changed in r4: 14 duplicate questions were removed (see below).

The frozen probe set, keys, scorer, token audit and tests are built and pass offline. No model has
been called. The live runner and GPU-disabled review package come next. No GPU reservation,
upload or launch.

## Changes in r4 (review of r3, and runner development)

1. **Admission timing validation.** `admit` now rejects booleans, non-finite values, negative
   elapsed times, non-positive timeouts, and any cutoff that is not positive or that would eat into
   the cleanup reserve. `Admission` validates its settings when constructed. Regressions cover every
   value the review reproduced, including the negative timeout that admitted a call after the cutoff.
2. **Duplicate questions removed.** While building the host's allow-list of frozen requests, 14 of
   the 668 probes turned out to repeat another probe's exact request in the same context: two
   randomly chosen outcome questions could land on the same step. They would have counted one
   question twice.
   - Question arguments are now deduplicated per context.
   - A test requires every request to be unique.
   - The set is now 654 probes, of which 454 are gated. The coverage minimums still hold.
3. **Per-call bound.** Admission now budgets 80 s per call:
   - the 60 s timeout;
   - a 15 s window in which the host must observe the server idle after a cancellation;
   - a 5 s bridge margin.
4. **How caching and cancellation are verified on the running server.**
   - **Caching off:** the frozen launch spec passes `--enable-prefix-caching`. The live host derives
     its argv with exactly that flag replaced by `--no-enable-prefix-caching`, refuses any other
     difference, and retains the derived argv. After the canary, the server's own metrics must show
     `vllm:prompt_tokens_total` > 0 with `vllm:prefix_cache_queries_total` = 0. With caching off,
     vLLM 0.19.0's KV-cache manager returns before recording any prefix-cache query. The check is
     repeated after every answer.
   - **Cancellation:** the host transport enforces a total 60 s deadline (a per-socket-read timeout
     would not). On expiry it shuts the connection down. vLLM 0.19.0's `/v1/chat/completions` route
     carries `with_cancellation`, so the server aborts the request. This is not assumed: the host must
     observe `vllm:num_requests_running` and `vllm:num_requests_waiting` at zero within 15 s. If they
     are, the call is recorded `timed_out` with a retained cancellation receipt. If they are not, the
     service refuses every later call and the run stops.

## Changes in r3 (review of r2)

1. **Missing evidence can never pass.** In r2, "both correct" was computed with `all(...)` over the
   supplied passes, so zero passes passed everything, one perfect pass met the criterion, and two
   empty passes showed 100% agreement.
   - Passes are now supplied as identified `pass_1` and `pass_2`. The final gate requires both.
   - An answer exists only if the call returned a response. A missing answer or a missing pass makes
     the family `incomplete`, and the overall gate status is `incomplete` unless every gated probe
     is answered in both passes.
   - Single-pass results are reported separately, as diagnostics.
   - Agreement is computed over valid answer pairs only. Missing and invalid pairs are counted
     separately.
   - Regressions: zero passes, one perfect pass (either one), two empty passes, an interrupted
     first pass, an interrupted second pass, a single missing answer, invalid pairs, and
     unidentified passes.
2. **Throughput figures are historical planning estimates, not bounds.**
   - The largest observed completion rate is one favourable call, not a floor.
   - "First call after a game change" does not prove a cold cache: the shared service had already
     seen the block-2 games, and common prefixes may have stayed cached.
   - Actual cache-disabled performance is unmeasured. The exact token counts do not establish
     runtime.
3. **Gate-first ordering prioritizes the gate; it does not guarantee it.** An incomplete gate is
   explicitly permitted and reported.
   - Per-call timeouts and admission control protect the cleanup reserve, whatever the timing
     estimates (see Schedule).
   - A local simulation interrupts the deadline during gate pass 1, during gate pass 2, and after a
     slow startup; every run ends `incomplete` and leaves the reserve untouched.
   - The runner's review package must rehearse the same interruptions on the connected path.

The best-shortcut rule compares against the single most accurate predeclared shortcut. It is an
engineering diagnostic and does not exclude every possible shortcut.

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
- **Cache-disabled runtime scenarios** from archived timings. r2 called these measured bounds; r3 corrects that: they are historical planning estimates (see Budget).

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
| `evidence_only` | 36 generated + 8 designed continuous trajectories, no grids | 454 | **the main gate** |
| `legacy_description` / `corrected_description` | 3 designed dimension-change trajectories | 34 + 34 | matched; legacy-interface ambiguity, reported separately |
| `archived_with_grids` / `archived_without_grids` | 6 exact archived live observations (b1 history episodes of ar25, s5i5 and wa30, at decisions 5 and 11, preselected) | 66 + 66 | matched; descriptive |

The total is 654 probes per pass, every request unique. Every evidence-only outcome label appears
as the key at least 9 times. The keys are distributed as follows:

| Outcome label | Probes |
|---|---|
| no change | 40 |
| changed then returned | 12 |
| dispatch failed | 13 |
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
frozen set, SHA-256 `dc623450…130e`.

## Shortcuts

Shortcuts are fixed before any model answers exist. The best shortcut per gated family:

| Family | Best shortcut | Accuracy |
|---|---|---|
| available_actions | ids seen in history | 0.159 |
| coordinate_actions | always `[6]` | 0.523 |
| recall_action | the latest entry | 0.533 |
| outcome_class | the latest entry's outcome | 0.381 |
| observed_effect | ignore coordinates | 0.664 |
| tried_unchanged | every no-change entry | 0.659 |

## Pre-registered analysis

The thresholds are provisional engineering thresholds, not established scientific boundaries.

For each gated family, using answers correct in **both** identified passes:

| Label | Rule |
|---|---|
| `incomplete` | Either pass is missing, or any question in the family has no returned answer in either pass. Checked first. |
| `not_diagnostic` | The best shortcut reaches ≥ 0.90. None do in the gated set. |
| `below_accuracy_floor` | Accuracy < 0.70. |
| `criterion_met` | Accuracy ≥ 0.90, **and** at least 10 questions where the best shortcut is wrong, **and** ≥ 0.90 accuracy on those questions. |
| `inconclusive` | Anything else, including too few shortcut-wrong questions. |

A constant shortcut cannot meet the criterion: it would need 0.90 overall, which only a
non-diagnostic family allows. This compares against the single most accurate predeclared
shortcut; it does not exclude every possible shortcut.

An invalid answer was returned, so it counts as wrong. A missing answer means no response was
returned, for example after a timeout, cancellation or deadline; it is never scored, and it makes
the result `incomplete`. The overall gate status is `complete` only when every gated question is
answered in both passes.

Always reported, never pooled away:
- single-pass diagnostics, both-correct accuracy, and answer agreement over valid pairs, with
  missing and invalid pairs counted separately;
- context-level results and the descriptive context-bootstrap intervals;
- the strata: near-miss clicks, untried actions, absent steps, empty history, and history
  containing unavailable ids;
- the matched tables for grids and for descriptions.

**Two passes.** Prefix caching is disabled, and the runner must verify that from the running
server. Pass 2 runs in reverse order. Two passes measure observed disagreement, not a precise
variance estimate.

## Schedule, timeouts and cleanup protection

These live in `research/evidence_comprehension_v1/schedule.py`.

The order is:
1. gate pass 1;
2. gate pass 2, reversed;
3. descriptive groups, pass 1;
4. descriptive groups, pass 2, reversed.

This **prioritizes** gate completion but cannot guarantee it. Slower startup, inference or storage,
or a failure, can interrupt the gate, and an incomplete gate is reported as `incomplete`.

The cleanup reserve does not depend on any estimate:
- **Admission:** a call starts only if its full 80 s bound would end by the admission cutoff. The
  bound is the 60 s timeout, 15 s of idle verification and a 5 s margin; the cutoff is the 3,300 s
  internal limit minus the 300 s cleanup reserve. No admitted call can reach the reserve.
- **Timeout:** a call still running at 60 s is cancelled on the server and recorded as
  `timed_out`, with no score row, but only once the server is observed idle. Otherwise the run
  stops. Under the slow assumed rates, the slowest request takes about 19 s.
- **Consecutive timeouts:** two in a row stop admission as a technical failure.
- **Backstop:** the supervisor's process-group teardown at the internal limit.

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
| Calls | 1,308 (654 × 2 passes) |
| Prompt tokens per pass | 2,064,987 (4.13 M total) |
| Largest prompt | 26,294 tokens |
| Longest key answer | 52 tokens |

All requests are within the 60,000-token prompt ceiling and the 65,536-token context.

**Runtime is unmeasured.** Actual cache-disabled performance has not been measured, and the
exact token counts do not establish runtime. The scenarios below are for planning only:
- **Historical estimate**, from the archived run on a cached shared service. These are not bounds.
  - 110 completion tokens/s: the largest observed ratio, from one favourable call.
  - 8,929 prompt tokens/s: the slowest first call after a game change. That call was not
    necessarily uncached.
- **Assumed slow:** 2,500 prompt tokens/s and 40 completion tokens/s.

The schedule is:
1. evidence-only pass 1;
2. evidence-only pass 2, reversed;
3. the descriptive groups, pass 1;
4. the descriptive groups, pass 2, reversed.

With the 403 s startup, which is itself historical, not guaranteed:

| Scenario | Startup + gate | Everything |
|---|---|---|
| Historical estimate | 782 s | 1,320 s |
| Assumed slow | 1,258 s | 2,963 s |
| Assumed slow, every call at its token cap | 2,430 s | 4,630 s (would be cut at the cutoff) |

If reality is slower than these scenarios, admission control stops the run at the cutoff and the
result is reported incomplete. The gate itself can be cut.

The admission cutoff is 3,000 s: an internal limit of 3,300 s less a 300 s cleanup reserve. The
proposal remains one attempt of ≤ 3,600 s.

## Next

The local runner and GPU-disabled review package are built; see
`reports/evidence_comprehension_v1_review.md`. Your review comes next, then separate source approval
and compute authorization.
