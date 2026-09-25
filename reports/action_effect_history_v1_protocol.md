# Action-effect history v1: protocol draft for review

**Status: draft for review.** It is not frozen and not authorized. There is no
reservation, runner, notebook or model call yet. Decisions marked **[review]**
need sign-off before freezing.

## Question

Does a short history of exact actions and objectively measured effects help
the agent choose informative actions and avoid ineffective repetition,
compared with its existing action-ID-only history?

The intervention is **tool-assisted feedback**. A deterministic
frame-comparison tool computes the effects, not the model. A positive result
would therefore not show that the model learned to compare frames. It is a
bounded exploratory comparison, not a solving or generalization claim, and not
Phase 4 certification.

## Departures from earlier runs (documented)

1. **New common baseline.** This is not unchanged E1S-R and not a continuation
   of R8. Both arms use one corrected system prompt (below). Compared with
   R8's control request, only the system prompt differs; the observation
   payload, response schema and decoding settings are byte-identical, and a
   test checks this.
2. **No prediction or feedback calls in either arm.** R8's sealed model
   prediction and feedback calls are removed from both arms. There is one
   policy call per action, and effects are computed deterministically.
3. **Horizon of 12 actions** per episode (R8 used 2).
4. **Three development cases** instead of ar25 alone.

## Cases

Only the development partition of `config/holdout_ledger.yaml` is eligible;
the 10 H1 and H2 holdouts are excluded.

**Prior-exposure audit.** All 15 development games were already run with the
model: all 15 in closed-loop v1 (20 actions each) and in the v13 pilot. None is
genuinely unexposed, so the two additional games are **additional development
cases, not independent validation**. ar25 informed this intervention and is the
design-informed development case.

**Selection rule, written before any outcome was inspected.** It uses only
each game's initial `available_actions` from
`reports/action_effect_history_v1_control_inventory.json` (zero actions
dispatched):

1. Development partition; exclude ar25 (the design case) and cd82 and ft09
   (subjects of dedicated single-game diagnostics that shaped this design).
2. Select one game whose initial controls are **coordinate-only** (ACTION6
   present, no ACTION1–4). Select one whose controls have **no coordinate
   action** (ACTION6 absent).
3. Within each group, break ties by the lowest
   `sha256("action-effect-history-v1:" + game_id)`.

| Case | Role | Initial legal actions | Win levels | Seed |
|---|---|---|---:|---:|
| `ar25-0c556536` | design-informed development case | 1, 2, 3, 4, 5, 6, 7 | 8 | 0 |
| `s5i5-18d95033` | additional development case (coordinate-only) | 6 | 8 | 0 |
| `wa30-ee6fef47` | additional development case (no coordinate action) | 1, 2, 3, 4, 5 | 9 | 0 |

The other candidates were su15 and vc33 for the coordinate-only group, and
ls20, tr87 and g50t for the no-coordinate group. In s5i5 the history can help
only by changing coordinates, never the action type. In wa30 clicking is
impossible, so neither arm can get stuck on ACTION6.

## Arms

Both arms use the same model and engine as all previous runs: Qwen3-VL-30B-A3B
FP8, vLLM 0.19.0, temperature 0, `max_tokens` 128, thinking disabled, and the
same `arc_action_v12` legal-action schema. The implementation is
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
definitions: ACTION1–5 and 7 are `SimpleAction`, and ACTION6 is
`ComplexAction` with x and y in 0..63. The prompt never states what any action
does and never mentions any game.

**Observation payload (both arms).** The unchanged `build_raw_bundle(...,
recent_limit=1).policy_payload()`, containing:
- `current_grid`, `previous_grid` and one `recent_final_grids` entry;
- `recent_actions` (action IDs only);
- `legal_actions`, `levels_completed`, `win_levels` and `state`;
- `history_compaction`.

**History arm only: one extra observation field, `action_effect_history`:**

```json
{"computed_by": "deterministic frame-comparison tool, not the model",
 "scope": "up to the 4 most recent dispatched actions since the last level change or reset, oldest first",
 "fields": "changed_cells_by_frame counts cells that differ from the frame before that action; null means the dispatch failed or its outcome is unknown, not that nothing changed",
 "omitted_entries": 0,
 "entries": [{"step": 0, "action_id": 6, "action_data": {"x": 16, "y": 16}, "status": "acknowledged",
              "returned_frame_count": 1, "changed_cells_by_frame": [0], "final_frame_changed": false,
              "level_delta": 0, "reset": false}]}
```

Each entry is `policy_view()` of an `action_effect_record_v1`, built only from
three things: the pre-action observation, the dispatched action and what the
engine returned. Entries contain no hashes, grids, object labels,
recommendations or offline probe data. A new segment starts after a level
change or reset. The first decision after one therefore sees an empty list.

## Schedule (two paired blocks, ABBA)

| Order | Block 1 | Block 2 |
|---|---|---|
| 1 | ar25 baseline | wa30 history |
| 2 | ar25 history | wa30 baseline |
| 3 | s5i5 baseline | s5i5 history |
| 4 | s5i5 history | s5i5 baseline |
| 5 | wa30 baseline | ar25 history |
| 6 | wa30 history | ar25 baseline |

The schedule has 12 episodes. Each one gets:
- a fresh offline environment (seed 0) and its own offline scorecard;
- a fresh, isolated policy context (no state carried between episodes);
- at most **12 dispatched actions**, with **one policy call per action**.

That makes at most **144 policy calls**, plus one startup canary.

**[review]** Both blocks use environment seed 0 and request seed 0, with
temperature 0. Differences between blocks therefore measure order effects
and server nondeterminism, not independent samples. The alternative is
request seed 1 in block 2.

## Stop rules

**Per episode.** An episode stops at the first of:
- **12 actions** (`action_cap`);
- **`WIN`**;
- **`GAME_OVER`** (no reset, no restart);
- an **invalid policy output**: unparseable, schema-invalid, illegal, or
  `finish_reason` other than `stop`. It is retained and stops the episode as
  `invalid_output`, with no retry and no fallback action;
- a **failed or unknown dispatch**: retained as such (never as a no-op), and
  the episode stops as `dispatch_failure`.

A **level completion does not stop the episode.** A new history segment
begins and play continues within the 12-action cap.

**Per run.**
- A technical failure (model service, monitor, deadline or cleanup) stops the
  run.
- A pair (both arms of one game in one block) is analyzed only if both
  episodes completed without a technical or dispatch failure. Incomplete
  pairs are reported, not analyzed.
- **Balanced admission.** A pair starts only if the remaining workload time
  covers both of its episodes at the conservative rate below. Otherwise the
  run stops before that pair; it is never cut off mid-pair.

## Metrics (reported separately; no composite)

A **comparable observed state** is one whose pre-action final frame hash and
level count are identical.

1. **Level completion:** total `level_delta` per episode, and episodes reaching
   `WIN`. This is the only solving metric.
2. **Exact repetition after no change** (primary behaviour metric).
   - An opportunity is any action whose predecessor was acknowledged with
     `final_frame_changed = false` and `level_delta = 0`, from a comparable
     observed state.
   - A repeat is the identical `action_id` and `action_data`.
   - It is also reported for any earlier no-change action taken from the same
     observed state within the segment.
3. **Action-type repetition after no change,** at the same opportunities: the
   same `action_id` with different `action_data`. It is reported separately
   from coordinate-exact repeats.
4. **Observable-change frequency:** the share of acknowledged actions with any
   changed frame.
5. **State coverage:** distinct observed states, and revisits of an earlier
   state. These flag back-and-forth movement.
6. **Cost and validity:** invalid outputs, failed or unknown dispatches,
   per-call latency, and prompt and completion tokens.

Action diversity and observable change are **never counted as success on their
own**. More changes together with more state revisits is reported as possible
oscillation.

## Interpretation rules [review: thresholds]

- **Behaviour changed as hypothesized** requires all of the following:
  - the history arm's pooled exact-repeat rate is **at most half** the
    baseline's;
  - the baseline had **at least 4** opportunities;
  - the reduction is in the same direction in **at least 2 of 3 games in each
    block**.
- **Solving signal** means the history arm completes more levels than the
  baseline, in both blocks, for at least 2 of 3 games. Otherwise the result
  is reported as **no demonstrated solving improvement**, even if behaviour
  changed.
- Anything else is **inconclusive**. With one seed per game, no result
  generalizes beyond these three development cases.

## Budget proposal (separate; zero authority)

See `action_effect_history_v1_budget.json`. The proposal is one attempt of
**3,600 provider seconds**, with a 3,300-second internal limit and no
automatic retry.

| Component | Basis | Conservative allowance |
|---|---|---:|
| Install and setup | measured 134 s (Stage B R2) and 157 s (preflight worker start) | 160 s |
| Model startup | measured 423–630 s; cap | 900 s |
| 144 policy calls | worst prompt 26,292 tokens (audited); R8's 25.8k-token decisions took 1.4–1.7 s; allow 4 s per call, about 2.5× | 576 s |
| 12 bootstraps, transitions, evidence writing | engine steps take milliseconds | 60 s |
| Cleanup reserve | unchanged | 300 s |
| **Total** | | **1,996 s** |

That leaves about 1,300 s of margin within the 3,300-second limit. At 8 s per
call (1,152 s), the total is 2,572 s, which still fits. The workload therefore
does not need to shrink. The balanced-admission rule above uses 10 s per call
to decide whether a pair may start.

Token ceilings:
- Prompts: at most 144 × 26,292 = 3.79 M tokens, plus the canary.
- Completions: at most 144 × 128 = 18,432 tokens.
- Per request: a hard ceiling of 60,000 prompt tokens, checked by exact
  tokenization before inference, with no truncation.

## Not yet done (before any reservation)

Runner implementation still has to:
- reuse the Stage B supervisor, monitor, bridge and cleanup stack;
- take effect records from the dispatch receipts;
- implement balanced admission.

It also still needs:
- local CPU rehearsal with scripted responses, including invalid output,
  dispatch failure and unknown outcome;
- a check that records carry only previously observed information;
- confirmation that historical R8 replay is unchanged;
- a frozen review notebook and lock, source approval and a separate compute
  authorization.

Geometry and localization work remains queued. Phase 4 remains open.
