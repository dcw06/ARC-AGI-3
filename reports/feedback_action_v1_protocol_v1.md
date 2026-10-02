# Feedback-action v1: experiment protocol v1 (draft r0, for review)

**Status: draft for review. Not frozen, not authorized.** No reservation, notebook, package or model call exists.
Nothing here approves compute. The budget in §11 is a proposal. This file supersedes
`reports/feedback_action_v1_protocol_draft.md` (r1), which stays as history. Design and CPU rehearsal evidence:
`reports/feedback_action_v1_design.md`. Evidence format: `transition_evidence_v2`, frozen at `eeb11ba`, used without
masks.

## 1. Research question

**Does structured hypothesis testing improve action selection?**

Both arms receive the same accurate action-effect evidence. The candidate also follows a bounded procedure and sees
its own previous statement:
- a hypothesis;
- supporting and conflicting references;
- an action;
- an observable prediction;
- what a different result would imply.

"Improve action selection" is measured by the behaviour metrics in §8: repetition after no observed change, choice
of untested actions, revision after a falsified prediction, invalid outputs and unsupported citations. A solving
improvement is claimed only from completed levels (§9).

This is a bounded exploratory development comparison:
- on exposed development games;
- not a generalization claim;
- not certification;
- not compute-matched.

## 2. Arms (two; no other arms in this experiment)

| | Baseline | Candidate |
|---|---|---|
| Observation and legal controls | the existing pipeline | identical bytes |
| Evidence | `action_effect_history`: full-frame `transition_evidence_v2` view, current segment, at most 8 entries | identical bytes |
| Procedure | none | `PROCEDURE` system paragraph, plus a required `hypothesis_test` response block |
| Carried state | none (stateless) | `previous_model_statement` beside the observation, by the carry rules in design §2 |
| Completion cap | 128 tokens | 640 tokens |
| Action schema and validator | `arc_action_v12` | identical |
| Dispatch rule | only if the action is valid | identical |
| Model and decoding | same model, temperature 0, seed 0, prefix caching off | identical |

**The carry rules.** The candidate carries the previous decision's valid hypothesis, status, prediction and
if_different, labelled as a model statement and not as evidence. Nothing is carried, with a stated reason, in three
cases:
- at the start of an episode;
- after an output without a valid block. An older statement is never substituted;
- after a reset, level change or terminal state, together with the evidence window.

**A bundled intervention.** The procedure, the response block, the carried statement and the larger completion cap
are applied together. This experiment cannot say which component matters.
- **If the candidate helps,** a later ablation can find which component contributed: procedure only, carried state
  only, or cap only.
- **If it fails,** first inspect whether the model used either component, before adding arms:
  - did it cite shown evidence;
  - did predictions follow from cited entries;
  - did revisions reference the carried statement.

No arms are added now. Isolation is tested: removing all four additions from a candidate request gives exactly the
baseline request, at every decision, rebuilt from the request bytes actually sent.

**Extra token cost per candidate call.** All of these are estimates until the tokenizer-exact pre-freeze measurement
(§12).

| Component | Size | Estimated tokens |
|---|---|---|
| System-prompt addition | 1,306 characters | about 300–450 |
| Response schema addition | 1,636 characters | about 400–550, *only if* the serving stack places the schema in the prompt. With guided decoding it usually constrains decoding instead. |
| Carried statement, when unavailable | 93–142 characters | about 30–50 |
| Carried statement, typical (rehearsals) | 408–430 characters | about 110–150 |
| Carried statement, at the text caps | up to about 800 characters | up to about 250 |
| Completion cap | 640 tokens against 128 | up to 512 more |

For comparison, the measured baseline prompt in action-effect history v1 (AEH v1) was about **23,600–24,700 tokens
per call**: 64×64 text grids, `reports/action_effect_history_v1_live_evaluation.json`. The candidate's prompt
additions are therefore about 2–5% of the prompt. Its completions are the dominant extra cost. The arms are **not
compute-matched**, and every call's prompt and completion tokens are reported.

## 3. Cases

**Partition, verified.** All three games are in the `development` list of `config/holdout_ledger.yaml`:

| Field | Value |
|---|---|
| `manifest_sha256` | `e3f5c27e…daa7d` |
| `partition_seed` | `arc-agi-3-plan8-public-partition-v1` |
| `consumption_events` | empty |
| s5i5, ls20, sk48 | none is in `h1` or `h2` |

| Game | Initial controls (`reports/action_effect_history_v1_control_inventory.json`) | Win levels | Frames per response at reset |
|---|---|---:|---:|
| `s5i5-18d95033` | ACTION6 only (coordinates) | 8 | 1 |
| `ls20-9607627b` | ACTION1–4 (no coordinates) | 7 | 1 |
| `sk48-d8078629` | ACTION1–4, ACTION6, ACTION7 (mixed) | 8 | 1 |

**Why each tests a different action-selection difficulty:**
- **s5i5: where to act.** Only coordinate actions, in a 64×64 space.
  - Every action changes 1–2 cells of a step bar (row 63, x 49–63; `reports/transition_evidence_v2_design.md`,
    48 of 48 transitions). Under full-frame evidence every frame is new and no action ever shows "no observed
    change".
  - It tests whether the procedure helps when the evidence always says "changed". The consequences are in §8.
- **ls20: when to stop repeating and switch direction.** Directional actions only.
  - In closed-loop v1 both arms pressed ACTION1 20 times. The piece moved for 6 steps, then every later response
    returned the same final frame, with transient intermediate changes
    (`reports/phase4_closed_loop_v1_offline_findings.md`).
  - It tests repetition after no observed change, revision after a falsified prediction, and
    `changed_then_returned` versus no change.
- **sk48: switching action modes.** Mixed controls.
  - In closed-loop v1 both arms clicked background or panel cells 20 times and never issued a directional action
    (same report).
  - It tests whether the candidate tries untested action *types*, not only untested coordinates.

**Prior exposure.** No game is unexposed. All three are development cases, not independent validation.

| Game | Earlier runs that used it |
|---|---|
| s5i5 | closed-loop v1 live (20-action episodes, `reports/phase4_closed_loop_v1_evaluation.json`); diagnostic v4 (initial observation, `reports/phase4_diagnostic_v4_results.md`); **AEH v1 live** (2 episodes per arm, 12 actions, `reports/action_effect_history_v1_results.md`); evidence comprehension v1–v3 (archived AEH s5i5 observations; `reports/evidence_comprehension_v1_protocol_r4.md` and the v2/v3 token audits); transition-evidence v2 design (48 archived transitions, declared region); local scripted lifecycle runs v2/v3 |
| ls20 | closed-loop v1 live (20-action episodes); diagnostic v4 (initial observation); grounding diagnostic v1 (`reports/grounding_diagnostic_v1_protocol.md`); phase 0 local scripted runs (3 × 12 actions, `reports/phase0_status.md`); lifecycle preparation v1 offline dispatch (`reports/phase4_status.md`) |
| sk48 | closed-loop v1 live (20-action episodes); diagnostic v4 (initial observation); local scripted lifecycle runs |

**Dispatch reliability seen so far:**
- **s5i5.**
  - Lifecycle v2 quarantined s5i5 clients, among five games. Cause: one more action after an acknowledged
    `GAME_OVER` returned no frames.
  - Lifecycle v3's terminal-aware loop fixed this. The reproduction passed, and the v3 local workload had 0
    quarantines (`reports/phase4_status.md`, `reports/phase4_v3_terminal_reproduction.json`).
  - In AEH v1: the environment check acknowledged 12 of 12 scripted dispatches, and the live run had 0 dispatch
    failures.
- **ls20.** Phase 0 local runs acknowledged all 12 actions three times. The lifecycle-preparation offline dispatch
  passed. No quarantines were reported.
- **sk48.** No dispatch problems are reported in the closed-loop v1 or v3 local workloads.

None of these runs measured these games under this experiment's 24-action loop. A CPU environment and dispatch
check with 24 scripted legal actions per game is required before freezing (§12).

**Selection.** The three games came from the control-coverage rule in draft r1, written before any outcome of this
design was inspected:
- one game per control group: coordinate-only, no coordinate action, mixed;
- ar25, cd82 and ft09 excluded;
- lowest `sha256("feedback-action-v1:" + game_id)` within each group.

The user then confirmed them provisionally. **Games were not selected for producing favourable candidate results.
No candidate results exist:** the candidate has never been run with a model, and no game has been played under
either arm of this design.

## 4. Exclusions

- **H1, H2 and every withheld partition.** Never opened, listed in a request, or used to tune anything.
- **ar25, cd82, ft09:** subjects of earlier design work and dedicated diagnostics.
- **Other development games:** not selected by the rule above. wa30 is not used; it was AEH v1's no-coordinate case.
- **Masked evidence.** No masked arm and no masked evidence anywhere in this experiment. The declared-mask comparison
  (`reports/transition_evidence_v2_design.md` §4) is a separate experiment. Mixing it in would confound changing the
  evidence with changing the decision procedure. s5i5 runs with full-frame evidence (§8 states the consequence).
- **No replacement of a game for an outcome-based reason.** A technical incompatibility found by the CPU check
  replaces a game with the next one in its group's tie-break order:
  - coordinate-only: su15, then vc33;
  - no coordinate action: wa30, then tr87, then g50t;
  - mixed: lf52, then sc25, then sp80, then ka59.

  Any replacement is documented before the run.

## 5. Seeds, block order and repetition

**Seeds.**
- Environment: seed 0 for every game, as in AEH v1 (`seed_by_game = {game: 0}`).
- Model: temperature 0, seed 0, prefix caching **off**.
- Every episode starts from a fresh environment instance and a fresh local scorecard.

**Two blocks, each a separate session, with identical configuration.**

| Block (session) | s5i5 | ls20 | sk48 |
|---|---|---|---|
| 1 | baseline, then candidate | candidate, then baseline | baseline, then candidate |
| 2 | candidate, then baseline | baseline, then candidate | candidate, then baseline |

Games run in the order shown. Arm order alternates by game and reverses between blocks.

**Total:** 3 games × 2 arms × 2 blocks = **12 episodes**, at most 288 dispatched actions.

**Run-to-run variance.** Block 2 replicates block 1; it is not an independent sample. Variance is measured within
each arm and game, between blocks:
1. **First-request reproducibility.** Each episode's first request is byte-identical across blocks by construction.
   The responses are compared.
2. **Action-sequence agreement.** The length of the identical action prefix and the first divergent step.
3. **Metric differences.** The block-1 against block-2 difference for every §8 metric.

Each block is a separate session, so this variance includes the effect of a server restart. That is the
conservative choice. AEH v1 observed different responses to byte-identical requests at temperature 0.

## 6. Horizons and call caps

**Actions.** **24 dispatched actions per episode** for this initial pilot. An episode also ends at a terminal state:
WIN, or GAME_OVER with no further action, following the v3 terminal-aware loop.

**Decision-call cap.** **32 model calls per episode**: 24 plus an allowance of 8 for invalid outputs.
- An invalid output consumes a call but never an action.
- At temperature 0, a repeated identical request can repeat the same invalid output.
- When the cap is reached:
  - the episode stops with stop reason `decision_cap`;
  - no further calls are made;
  - every call and output is retained;
  - the episode is reported with its actions so far.

  A capped episode counts toward the reliability rule in §10, F2.

**Completion-token cap per call.** 128 tokens (baseline) and 640 tokens (candidate). A truncated response is invalid
in both arms. There is no per-episode token budget: 32 calls × 640 tokens bounds the candidate at 20,480 completion
tokens per episode.

**What 24 actions can test:**
- several prediction → feedback → revision cycles. One cycle needs at least three decisions;
- repetition after no observed change, as in ls20's blocked movement;
- whether untested action types are tried, as in sk48.

**What 24 actions cannot establish.** Every earlier development run completed 0 levels: closed-loop v1 at 20 actions,
AEH v1 at 12. Completing a level may need more than 24 actions. A null solving result here is **not** evidence that
the procedure cannot help solving, and 24 actions may be too short to establish solving capability at all.

## 7. Model-facing content per call

Both arms receive:
- the existing observation payload;
- the evidence view, current segment, at most 8 entries.

The candidate additionally receives the carried statement. Every request's exact bytes are retained. Every valid
`hypothesis_test` block whose action was dispatched is retained as a `transition_evidence_v2` `model_statement`
record, cited by `about_record_id`, never inside a transition record. Every transition is retained as a v2 record and
verified with `verify_history` against its raws.

## 8. Metrics and denominators

**Unit of analysis: the episode.** Steps within an episode are never treated as independent samples. Each metric is
computed per episode. The comparison pairs the arms within each (game, block), giving 6 pairs.

**How results are reported.**
- Per game and arm: block 1, block 2, and their mean.
- Pooling across games is descriptive only.
- There are no step-level significance tests.

All metrics are computed by the independent evaluator from raw transitions and the retained request and response
bytes.

| Metric | Numerator | Denominator (per episode) | Arms |
|---|---|---|---|
| Exact repeat after no observed change, same state | dispatched decisions whose chosen exact action (id plus coordinates) had, as its latest same-state observation in the shown window, `no_observed_change` | **repeat opportunities**: decisions with a valid action at which the shown window contains at least one same-state `no_observed_change` exact action. **Requires an evaluator addition before freezing.** | both |
| Of which followed by a visible change or level | the repeats above whose transition showed a change or level completion | the repeats above | both. Reported beside the repeat rate so that repetition is not equated with waste. |
| Untested exact action chosen | decisions choosing an `untested` exact action | decisions with a valid action | both, with a breakdown by action type (simple vs ACTION6) |
| Untested action **type** chosen | decisions choosing an action id with no record in the window | decisions with a valid action | both. Primary for sk48. |
| Prediction accuracy | `correct` predictions | **scoreable** predictions: valid block, action dispatched and acknowledged, visual effect not indeterminate | candidate. Unscoreable predictions are reported with their own denominator, decisions with a valid block. |
| Revision after a falsified prediction | `recognized` | **revision opportunities**: a falsified prediction, followed by a decision whose request contained that statement | candidate. `previous_statement_absent` is reported separately and never counted. |
| Invalid action outputs | invalid outputs, by reason | model calls | both |
| Invalid procedure blocks | invalid blocks, by reason | candidate model calls | candidate |
| Unsupported citations | citations that are not `supported`, by category | all citations | candidate |
| Completed levels | `levels_completed` increases, or WIN | per episode (count) | both |
| Dispatch failures and unknown outcomes | `failed` plus `outcome_unknown` dispatches | dispatched actions | both |
| Cost | prompt tokens, completion tokens (provider usage), latency, wall time | per call and per episode | both |

**s5i5 under full-frame evidence (consequence, stated in advance).**
- **No repeat opportunities.** The step bar makes every returned frame unique, so `no_observed_change` and
  same-state observations never occur. Repeat opportunities will be 0 in both arms, so the repetition metric is
  undefined for s5i5. It is reported as "0 opportunities", never as 0 repeats.
- **Raw repeats are reported instead,** descriptively: identical exact actions in consecutive decisions, with the
  number of distinct coordinates.
- **Prediction accuracy is inflated.** `final_frame_differs` is always true there, so visual-effect accuracy is
  inflated. s5i5's prediction accuracy is reported separately from ls20 and sk48, along with its region-field
  accuracy.
- **s5i5 is not dropped.** It still tests coordinate choice, citation validity and revision.

## 9. Outcome rules (proposal)

1. **Technical validity first.** Unless all §10 checks pass, the result is `technically_incomplete` or `aborted`.
   No behaviour or solving claim is made then.
2. **Solving.** A solving improvement is claimed only if the candidate completes more levels than the baseline:
   - in at least 2 of 3 games;
   - in both blocks;
   - with no game where it completes fewer.

   Otherwise: "no demonstrated solving improvement", whatever the behaviour metrics show.
3. **Action selection (exploratory).** An improvement in a behaviour metric is reported only if it has the same
   direction in both blocks, in at least two games where the metric is defined. Any per-game arm difference smaller
   than that arm's block-1/block-2 difference is `within_run_to_run_variance`. Anything else is `inconclusive`.
4. **Prediction accuracy and revision are candidate-only and descriptive.** They are never a between-arm criterion.
5. **Advancement to an ablation or a larger study** needs rule 2, or rule 3 together with:
   - candidate invalid-action rate ≤ the baseline's + 0.05;
   - unsupported-citation rate ≤ 0.20.

## 10. Failure rules

| Rule | Trigger | Action |
|---|---|---|
| F1 technical incompleteness | any of the 12 episodes missing; lifecycle or cleanup failure; the independent replay does not reproduce the evaluation | result `technically_incomplete`; no claims; no rerun without new approval |
| F2 invalid outputs | either arm's invalid-action rate exceeds 0.25 over its first 24 calls of a session; **or** 2 or more episodes of one arm end at `decision_cap` | F2a (rate): stop the session (technical abort); retain everything; result `aborted_invalid_outputs`. F2b (caps): finish the schedule, but report the arm comparison as `inconclusive_reliability` |
| F3 holdout identifier | any H1, H2 or non-development game id appears in a request, an environment open or a scorecard tag | stop immediately; quarantine the outputs; report the incident; record a consumption event in `config/holdout_ledger.yaml` per its rules |
| F4 integrity | canary fails; source lock mismatch; a transition record fails v2 `verify_history`; a request fails the isolation check; prefix-cache hits > 0 | stop the session; result `technically_invalid`; retain everything |
| F5 dispatch reliability | failed plus unknown dispatches exceed 0.10 of dispatched actions in a session | stop the session (technical abort); retain |
| F6 deadline | a session's internal deadline (3,300 s) is reached | stop scheduling; finalize and clean up; F1 applies |

Session 2 does not start if session 1 ends under F2a, F3, F4, F5 or F6. That outcome is reported first.

## 11. Runtime estimate and proposed budget (estimates; a proposal only)

**Measured rates.**

| Source | Measurement |
|---|---|
| AEH v1 (`reports/action_effect_history_v1_results.md`, `…_live_evaluation.json`) | model startup 403 s; per-call latency, mean of each baseline episode 1.21–1.38 s, single maximum 1.44 s; about 24k prompt and 20–33 completion tokens per call; supervisor 735 s for 144 calls, including startup |
| Diagnostic v4 | startup 462 s |
| ECv3 (`reports/evidence_comprehension_v3_results.md`) | installation 141 s; startup **819 s** |

**Not measured:** the decode rate for long completions. The AEH v1 differences suggest roughly 6 ms per token, but
that is weak evidence. **Estimate used: 10–20 ms per completion token.**

**Estimate per session** (one block: 6 episodes, 144 actions, 72 calls per arm nominally, 96 at the call cap):

| Item | Typical (estimate) | Worst case at caps (estimate) |
|---|---|---|
| Installation | 141 s | 141 s |
| Model startup | 403–900 s | 900 s |
| Baseline calls | 72 × 1.4 s ≈ 100 s | 96 × 1.44 s ≈ 140 s |
| Candidate calls | 72 × (1.6 s prefill + 200–350 tokens × 10–20 ms) ≈ 260–620 s | 96 × (1.6 + 640 × 0.020) s ≈ 1,380 s |
| Environment and supervisor overhead | about 1.0 s × 144 ≈ 145 s | about 1.0 s × 192 ≈ 190 s |
| **Session total** | **about 1,050–1,900 s** | **about 2,750 s** |

The overhead figure is derived from AEH v1: 735 − 403 − about 200 s of calls, over 144 actions.

**Both sessions:** typical about 2,100–3,800 s; worst case about 5,500 s.

**Proposed budget (a proposal; nothing reserved or approved).**
- Two sessions on one GPU, one per block.
- Each with a 3,600 s provider timeout and a 3,300 s internal deadline.
- **Proposed ceiling: 7,200 s of account GPU time in total.** That is about 30% headroom over the worst case and
  about 2× the typical estimate.
- No outcome-based reruns. A technical abort produces a report, not a silent rerun; a rerun needs a new approval.
- Exact billed seconds are not reported by the provider. The account counter is recorded before and after.

## 12. Before freezing (required)

1. **Evaluator additions:**
   - repeat opportunities, and untested-action-type choice (§8);
   - raw consecutive repeats and distinct coordinates for s5i5.

   Tested on the existing fixtures.
2. **Live adapter integration** with the real observation pipeline (`agent.representation`, as in AEH v1). The
   producer must retain request bytes, v2 records and `model_statement` records.
3. **Tokenizer-exact token counts** for both arms on recorded development observations (offline), replacing the
   estimates in §2 and §11.
4. **CPU environment and dispatch check:** 24 scripted legal actions per game on s5i5, ls20 and sk48, through the
   runner's own dispatch path.
5. **Package review, source lock, compute authorization and approval.** None exist.
