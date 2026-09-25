# Action-effect history v1: protocol draft, revision 2 for review

**Status: revised draft.** It is not frozen and not authorized. There is no
reservation, notebook or model call. Revision 2 applies the review of
`5dc1cd6`:
- seeds decided;
- denominator and outcome rules fixed;
- admission, token-ceiling and environment-check corrections A–C.

## Question

Does a short history of exact actions and objectively measured effects help
the agent choose informative actions and avoid ineffective repetition,
compared with its existing action-ID-only history?

The intervention is **tool-assisted feedback**. A deterministic
frame-comparison tool computes the effects, not the model. The comparison
asks whether factual action-effect history changes behaviour. It does not ask
whether the agent has learned perception, planning or game solving. It is a
bounded exploratory development comparison, not a generalization claim, and
not Phase 4 certification.

## Departures from earlier runs (documented)

1. **New common baseline.** This is not unchanged E1S-R and not a continuation
   of R8. Both arms use one corrected system prompt. Compared with R8's
   control request, only the system prompt differs; the observation payload,
   response schema and decoding settings are byte-identical, and a test checks
   this.
2. **No model prediction or feedback calls in either arm.** There is one policy
   call per action, and effects are computed deterministically.
3. **Horizon of 12 actions** per episode (R8 used 2).
4. **Three development cases** instead of ar25 alone.

## Cases

Only the development partition of `config/holdout_ledger.yaml` is eligible;
H1 and H2 are excluded.

**Prior exposure.** All 15 development games were already run with the model
(closed-loop v1 and the v13 pilot). None is unexposed, so all three cases are
**development cases, not independent validation**. ar25 informed this
intervention.

**Selection rule, written before any outcome was inspected.** It uses only
initial `available_actions`
(`reports/action_effect_history_v1_control_inventory.json`, zero actions
dispatched):

1. Development partition; exclude ar25 (the design case) and cd82 and ft09
   (subjects of dedicated single-game diagnostics).
2. Select one game whose initial controls are **coordinate-only** (ACTION6
   present, no ACTION1–4). Select one whose controls have **no coordinate
   action** (ACTION6 absent).
3. Within each group, break ties by the lowest
   `sha256("action-effect-history-v1:" + game_id)`.

| Case | Role | Initial legal actions | Win levels | Seed |
|---|---|---|---:|---:|
| `ar25-0c556536` | design-informed development case | 1–7 | 8 | 0 |
| `s5i5-18d95033` | development case, coordinate-only | 6 | 8 | 0 |
| `wa30-ee6fef47` | development case, no coordinate action | 1–5 | 9 | 0 |

**Predeclared replacement rule (technical incompatibility only).** A
selected game is replaced only if the CPU environment and dispatch check below
shows a technical incompatibility that prevents execution. The replacement is
the next game in the same group's tie-break order:
- coordinate-only group: s5i5, then su15, then vc33;
- no-coordinate group: wa30, then ls20, then tr87, then g50t.

The failure is documented. A game is never replaced for any outcome-based
reason.

**Environment check (correction C).** s5i5 was one of five games with
`outcome_unknown` quarantines in the historical v2 lifecycle run: an extra
action after `GAME_OVER` returned no frames. v3's terminal-aware loop fixed
that, and its reproduction passed on s5i5.

`reports/action_effect_history_v1_environment_check.json` drives the runner's
own offline dispatch path with 12 fixed scripted legal actions per case, and
records technical fields only (no effect statistics). **All three cases are
compatible:** 12 of 12 dispatches acknowledged with 64×64 frames, no
empty-frame response, no exception, client and scorecard closed. No
replacement applies. The runner still stops at `GAME_OVER` and records any
frameless acknowledgement as `outcome_unknown`.

## Arms

Both arms use Qwen3-VL-30B-A3B FP8 on vLLM 0.19.0, temperature 0, request
seed 0, `max_tokens` 128, thinking disabled, and the `arc_action_v12`
legal-action schema. The implementation is
`research/action_effect_history_v1/contract.py`.

**Common system prompt (identical in both arms):**

```
You control one ARC-AGI-3 game from the supplied observation. Return only one compact JSON object
matching the supplied action schema, with no rationale or Markdown, under 64 tokens.
Actions: choose exactly one action_id from legal_actions. Never choose reset or action 0. ACTION6 is
the only action that takes arguments: action_data must be {"x": X, "y": Y} with integers 0 to 63,
where x is the column counted left to right and y is the row counted top to bottom, so the selected
cell is current_grid[y][x]. Every other action (1, 2, 3, 4, 5, 7) takes empty action_data {}.
An action being legal does not mean its effect is known. This prompt does not describe what any
action does in this game; effects can only be learned from observations. history_compaction reports
any older transitions omitted from this prompt.
```

The argument rules were checked against the pinned `arcengine` `GameAction`
definitions.

**Observation payload (both arms).** The unchanged `build_raw_bundle(...,
recent_limit=1).policy_payload()`: current, previous and one recent final
grid; action-ID-only `recent_actions`; legal actions; levels; state;
`history_compaction`.

**History arm only: one extra field, `action_effect_history`.** It holds the
last 4 `action_effect_record_v1` policy views since the latest level change
or reset, oldest first. It is labelled as computed by a frame-comparison
tool, not the model. `null` counts mean the dispatch failed or its outcome is
unknown, not "no change". It holds no hashes, grids, object labels,
recommendations or offline probe data. Each record is built only from that
arm's own pre-action observation, dispatched action and returned frames.
**Histories are isolated per episode and per arm.**

## Schedule

| Order | Block 1 | Block 2 |
|---|---|---|
| 1 | ar25 baseline | wa30 history |
| 2 | ar25 history | wa30 baseline |
| 3 | s5i5 baseline | s5i5 history |
| 4 | s5i5 history | s5i5 baseline |
| 5 | wa30 baseline | ar25 history |
| 6 | wa30 history | ar25 baseline |

Every episode gets a fresh offline environment and its own scorecard, a
fresh policy context, at most **12 dispatched actions**, and **one policy
call per action**. That makes at most **144 policy calls**, plus one startup
canary.

**Seeds (decided).** Environment seed 0 and request seed 0 in both blocks.
Block 2 is an **order-reversed replication, not an independent sample**.
Broader seed coverage belongs in a later experiment.

## Stop rules

**Per episode.** An episode stops at the first of:
- **12 actions**;
- **`WIN`**;
- **`GAME_OVER`** (no reset, no restart);
- an **invalid policy output**: unparseable, schema-invalid, illegal, or
  `finish_reason` other than `stop`. It is retained and stops the episode as
  `invalid_output`, with no retry and no fallback;
- a **failed or unknown dispatch**, including a frameless acknowledgement. It
  is retained as such, never as a no-op, and stops the episode as
  `dispatch_failure`.

A level completion does not stop the episode; a new history segment begins.

**Per run (correction A).**
- **Admission.** A pair (both arms of one game in one block) is admitted only
  if the remaining workload time covers the frozen conservative pair
  allowance: 2 bootstraps and scorecards, 24 policy calls at 10 s each, 24
  dispatches, evidence writing and finalization for both episodes. That is
  **300 s per pair**.
- **Deadline.** The run deadline is enforced **even if a pair is
  interrupted**. An allowance is a planning figure, not a hard bound on
  inference, dispatch or failures.
- **Incomplete pairs.** An interrupted or incomplete pair is **retained and
  reported**.
- **What each analysis uses.** Behaviour comparisons use complete pairs.
  **Reliability reporting covers every attempted episode**, including
  interrupted, invalid-output and dispatch-failure episodes. An arm-specific
  failure can never disappear through pair exclusion.
- **Technical failures.** A technical failure (model service, monitor,
  cleanup, or a token-count mismatch) stops the run. All evidence written so
  far is retained.
- **Evidence layout.** The run directory holds a small index (`run.json`) and
  one file per episode. Only the index and the current episode are rewritten
  and fsynced at each event. Intent is durable before every call and
  dispatch, and received bytes are durable before validation.

## Metrics

All metrics are reported per game and per block, and pooled. Every rate shows
its **numerator and denominator**. **A rate with a zero denominator is `null`,
never 0.**

A **comparable observed state** is one with an identical pre-action final
frame hash and level count.

1. **Level completion:** total `level_delta` per episode, and episodes reaching
   `WIN`. This is the only solving metric.
2. **Exact repetition after no change** (primary behaviour metric).
   - An opportunity is an action whose predecessor was acknowledged with
     `final_frame_changed = false` and `level_delta = 0`, from a comparable
     observed state.
   - A repeat is the identical `action_id` and `action_data`.
   - Report repeats, opportunities and the rate, both immediate and against
     any earlier no-change action from the same state within the segment.
3. **Opportunity creation,** reported alongside metric 2:
   - the number of no-change results each arm produced;
   - valid actions taken;
   - actions producing observable change;
   - level progress.

   An arm can have fewer repetition opportunities because it chose effective
   actions sooner, or because it stopped early. Fewer opportunities are
   interpreted with these counts, never as a repetition improvement by
   themselves.
4. **Action-type repetition after no change:** the same `action_id` with
   different `action_data`, reported separately from exact repeats.
5. **Observable-change frequency:** acknowledged actions with any changed
   frame, as a share of acknowledged actions.
6. **State coverage:** distinct observed states and revisits. These flag
   back-and-forth movement.
7. **Reliability and cost:** per attempted episode:
   - the stop reason;
   - invalid outputs;
   - failed or unknown dispatches;
   - interruptions;
   - per-call latency;
   - prompt and completion tokens.

Action diversity and observable change are never counted as success on their
own.

## Outcome classes and interpretation (frozen before results)

**Behaviour.** A game–block comparison is **eligible** only if:
- both episodes are complete;
- neither stopped on invalid output or a dispatch failure before 12 actions,
  unless it stopped on `WIN` or `GAME_OVER`;
- the baseline repeat rate is **positive**, with at least 1 repeat.

An arm that stops early on invalid output is **ineligible** for the repetition
comparison and is counted as an arm failure. It can never earn a favourable
repetition result by taking fewer actions.

Each eligible comparison is classified as follows:

- **reduced**: both arms had repetition opportunities, and the history arm's
  rate is at most half the baseline's rate.
- **opportunities eliminated**: the history arm had zero opportunities, so its
  rate is `null`. This is reported **separately**, together with valid action
  counts, observable changes and progress. It is **never counted as reduced**.
- **not reduced**: both arms had opportunities and the history arm's rate is
  above half the baseline's rate;
- **worse**: the history arm's rate is at least 1.5× the baseline's, with at
  least 2 more repeats.

**Overall behaviour result.** This requires **all six planned pairs**
complete. Otherwise it is **inconclusive: incomplete schedule**. With all six:
- **Behaviour changed as hypothesized:** at least 2 of 3 games are *reduced*
  in **each** block, and no game is *worse* in either block.
- **Candidate worse:** at least 2 of 3 games are *worse* in either block, or
  the history arm has more invalid-output or dispatch-failure episodes than
  the baseline across the six pairs.
- **No improvement observed:** every comparison is eligible and none is
  *reduced* or *opportunities eliminated*.
- **Inconclusive:** anything else, including too few eligible comparisons.
  *Opportunities eliminated* comparisons are listed with their action,
  change and progress counts, whichever overall class applies.

**Precedence.** The classes are checked in a fixed order, and the first that
applies is reported:
1. incomplete schedule;
2. candidate worse;
3. behaviour changed as hypothesized;
4. no improvement observed;
5. inconclusive.

Checking candidate worse first means an arm that stops more often on errors
can never also be reported as having reduced repetition.

**Solving (strong exploratory signal only).** The history arm completes more
levels than the baseline in both blocks for at least 2 of 3 games, with all
six pairs complete. Otherwise the result is **no demonstrated solving
improvement**, even if behaviour changed. Neither class is a statistical or
generalization claim. A behaviour change without level progress is evidence
of changed behaviour, not of solving.

## Budget proposal (separate; zero authority; correction B)

The proposal is one attempt of **3,600 provider seconds**, with a
3,300-second internal limit and no automatic retry. It is plausible but
**conditional on runtime admission and clean stopping**. The audited request
sizes are estimates, not a worst-case proof.

| Component | Basis | Planning allowance |
|---|---|---:|
| Install and setup | measured 134 s and 157 s | 160 s |
| Model startup | measured 423–630 s; cap | 900 s |
| 144 policy calls | largest audited request 26,292 tokens; R8's 25.8k-token decisions took 1.4–1.7 s; allow 4 s per call | 576 s |
| Bootstraps, transitions, evidence, finalization | | 60 s |
| Cleanup reserve | unchanged | 300 s |
| **Planning total** | | **1,996 s** |

The live pair-admission allowance is stricter, at 300 s per pair, or 1,800 s
for six pairs.

- **Largest audited request:** 26,292 prompt tokens, from the exact first and
  steady-state requests for each case plus a maximal history. It is not a
  proven maximum: later frames and history contents can tokenize differently.
- **Live ceiling:** 60,000 prompt tokens per request, enforced by exact
  tokenization before inference, with no truncation. At the live ceiling, 144
  calls allow up to **8.64 M prompt tokens**, excluding the canary. The
  audited estimate is about 3.79 M.
- **Completions:** at most 144 × 128 = 18,432 tokens.

## Before freezing

The protocol is frozen only with:
- the runner, meeting the next milestone list;
- CPU rehearsals of deadline overrun, invalid output, failed dispatch and
  unknown outcome;
- an evaluator that implements the null-denominator and eligibility rules;
- unchanged historical R8 replay.

After that come a review notebook and source lock, source approval, and a
separate compute authorization. Geometry and localization work remains
queued. Phase 4 remains open.
