# Feedback-action v1: experiment protocol v2 (draft r0, for review)

**Status: draft for review. Not frozen, not authorized.** No reservation, package lock, notebook or model call exists.
Nothing here approves compute.

This revision applies the review of protocol v1 (`75e69b9`). Protocol v1
(`reports/feedback_action_v1_protocol_v1.md`) stays as history. Where this document says "unchanged from v1", v1's
text and evidence apply as written. Evidence format: `transition_evidence_v2`, frozen at `eeb11ba`, without masks.

## 1. Research question (unchanged from v1)

**Does structured hypothesis testing improve action selection?**

A solving improvement is claimed only from completed levels.

**Scope.** All three games are exposed development games (v1 §3: closed-loop v1 and diagnostic v4 for all three, and
AEH v1 and the transition-evidence work for s5i5). This design was also informed by retained observations of them.
**Prior exposure limits every real-game claim:** results describe these three development games under this
protocol. They are not evidence of generalization, of performance on unexposed or holdout games, or of competition
performance.

## 2. Arms and treatment (unchanged from v1 §2)

| Arm | Receives |
|---|---|
| Baseline | the current observation (existing pipeline, reused unchanged through AEH v1's `observation_payload`), the legal controls, and the full-frame `transition_evidence_v2` evidence view |
| Candidate | the same bytes, plus the bundled treatment (below) |

**The bundled treatment:**
- the `PROCEDURE` paragraph;
- a required `hypothesis_test` block;
- the carried previous statement;
- a 640-token completion cap, against 128.

It is applied as one intervention. **No arm is added.** If the candidate helps, a later ablation can find which
component contributed. If it fails, first inspect whether the model used either component.

**The treatment is fixed before session 1.** It is not changed after block 1 is inspected. Session 2 runs the
identical package. Any change after inspection would be a new protocol version.

**Measured request sizes.** These come from the real offline engine through the live runner (`research/feedback_action_v1/
token_audit.py forms`). They are bytes, not tokens.

| Form | Request bytes |
|---|---|
| Baseline, first | 11,158–11,438 |
| Baseline, steady state | 30,964–31,188 |
| Candidate, first | 14,245–14,525 |
| Candidate, steady state | 34,400–34,625 |
| Candidate, carried statement at its text caps, ASCII | about 35,000 |
| Candidate, carried statement at its text caps, non-ASCII | about 39,000 |

The maximum, 39,039 bytes, is under the 262,144-byte request ceiling.

**Exact prompt-token counts and the completion-cap check are a TODO** for the pinned tokenizer stack (§12). Until they
exist, every token figure below is an estimate.

## 3. Cases and exclusions (unchanged from v1 §3–4)

**Cases:**
- s5i5 (coordinate-only);
- ls20 (directional only);
- sk48 (mixed).

All three are verified in the `development` list of `config/holdout_ledger.yaml`. Games were not selected for
favourable candidate results, and no candidate results exist.

**Exclusions:**
- H1, H2 and withheld partitions, never touched;
- ar25, cd82 and ft09;
- no masked arm or masked evidence;
- no outcome-based game replacement.

**s5i5 runs with full-frame evidence.** Its step bar makes every frame unique, so the repeat metric has no
opportunities there and is reported as undefined (§8).

## 4. Seeds, sessions and block order

**Seeds.** Environment seed 0. Temperature 0. Model seed 0. Prefix caching off.

**Two sessions, one block each, in fresh sessions.** Within each game, arm order alternates and reverses between
blocks:

| Session (block) | s5i5 | ls20 | sk48 |
|---|---|---|---|
| 1 | baseline, then candidate | candidate, then baseline | baseline, then candidate |
| 2 | candidate, then baseline | baseline, then candidate | candidate, then baseline |

Encoded in `research/feedback_action_v1/live/protocol.json`; the runner takes one session's pairs via
`policy.session_spec(block)`.

**Run-to-run variance (unchanged from v1 §5).** It is measured within each arm and game, between the blocks:
- the response to the byte-identical first request;
- the identical action prefix;
- the per-metric difference.

Session restart is part of the measured variance.

## 5. Horizon, caps and stop behaviour

| Limit | Value | What happens when it is reached |
|---|---|---|
| Actions per episode | 24 | the episode stops: `action_cap` |
| Decision calls per episode | 32 (24 plus 8 for invalid outputs) | **the episode stops: `decision_cap`.** Every call and output is retained; **the planned schedule continues** unless a separate technical or invalid-output stop rule (§10) fires |
| Completion tokens per call | baseline 128, candidate 640 | a truncated response (`finish_reason` other than stop) is an invalid output in both arms |
| Policy calls per session | 192 (6 episodes × 32) | technical failure: a call ceiling, enforced by the runner and the service |
| Terminal state | WIN or GAME_OVER | the episode stops: `win` or `game_over`. Nothing is called or dispatched after it. Terminal states are checked before the caps |
| Dispatch failure or unknown outcome | — | retained as a `failed` or `outcome_unknown` v2 raw transition. The episode stops with `dispatch_failure`; the schedule continues; §10 F5 applies |

**Invalid outputs.** An invalid output consumes a call and never an action. It never ends an episode on its own.

**What the horizon can and cannot show (unchanged from v1 §6).** 24 actions allow several prediction → feedback →
revision cycles, repetition after no observed change, and switches of action type. They may be too short to
establish solving capability.

In the CPU checks, s5i5's step budget ended the game at **action 50** under scripted play. No terminal state, level
change or reset occurred within 100 scripted actions on ls20 or sk48 (§11).

## 6. Model-facing content and retained evidence

**Unchanged from v1 §7.** The live runner additionally retains:
- every request's exact bytes and every raw response;
- every transition as a v2 raw transition, with `record_id` `<episode_id>#<action_index>`;
- every valid candidate block whose action was dispatched, as a v2 `model_statement` with `about_record_id`.

## 7. Model and decoding

| Setting | Value |
|---|---|
| Model | `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`, the AEH v1 service model |
| Decoding | temperature 0, seed 0, `enable_thinking: false` |
| Schema | guided-decoding schema per arm |
| Startup canary | one, 128-token cap |

## 8. Metrics, denominators and failures

The **unit of analysis is the episode**. Arms are paired within (game, block): 6 pairs. Pooled values are
descriptive. Each rate is computed by the independent evaluator (`research/feedback_action_v1/evaluate.py`,
`rates`/`aggregate`) as numerator, denominator and status:
- `undefined`: the denominator is 0. It is **never reported as 0**;
- `insufficient`: below the minimum;
- `defined`;
- `not_applicable`: a candidate-only rate in the baseline arm.

**Failure-inclusive rule (how cap-hit and failing episodes enter every metric).** Every model call is a decision and
enters the denominator of each rate whose opportunity it had. Opportunities are computed from the shown evidence and
legal actions alone, so an invalid output never removes an opportunity. An invalid output, or an invalid procedure
block, counts as the **unfavourable** outcome:
- as a repeat, for the repeat rate;
- as "not chosen", for untested-type choice;
- as "no citation", for citation supply;
- as incorrect, for prediction accuracy;
- as not recognized, for revision.

A capped episode keeps all 32 calls in every denominator. Actions it never took are not imputed, and it cannot gain
levels it did not complete.

**Therefore a candidate cannot earn behavioural advancement by making fewer valid actions because it repeatedly
failed.** This is property-tested: turning any decision into an invalid output never moves an advancement rate in the
favourable direction (`tests/test_feedback_action_v1_denominators.py`). The valid-only repeat rate *can* move that way,
so it is **descriptive only** and is never used for advancement.

| Rate | Numerator | Denominator (per episode) | Minimum when pooled per (game, arm) over both blocks |
|---|---|---|---|
| Repeat after no observed change (unfavourable) | repeats of an exact action whose latest same-state observation was `no_observed_change`, **plus invalid outputs at such an opportunity** | **repeat opportunities**: decisions where the shown window had at least one legal same-state `no_observed_change` exact action | 5 |
| (Repeat, valid only: descriptive) | repeats | valid decisions at repeat opportunities | 5 |
| Of which followed by a visible change or level | — | the repeats | reported beside the repeat rate, so repetition is not equated with waste |
| Untested action type chosen | valid decisions choosing an action id with no acknowledged transition in the window | **untested-type opportunities**: decisions with at least one such legal id | 5 |
| Citation supply (candidate) | decisions with a valid block citing at least one ref | **citation opportunities**: candidate decisions with a non-empty evidence window | 10 |
| Unsupported citations (candidate) | citations that are not `supported` | all citations. **No citations means undefined, not 0** | 10 citations |
| Prediction accuracy (candidate) | correct predictions | scoreable predictions plus decisions with an invalid output or block | 10 |
| Revision after a falsified prediction (candidate) | `recognized` | falsified predictions whose statement was in the next request (`previous_statement_absent` is excluded and reported) | 3 |
| Invalid actions | invalid outputs | model calls | 1 |
| Invalid procedure blocks (candidate) | invalid blocks | candidate model calls | 1 |
| Completed levels | `levels_completed` increases, or WIN | per episode (count) | — |
| Cost | prompt and completion tokens (provider usage), latency, wall time | per call and per episode | — |

**Citation supply is always reported:** how often the candidate cites evidence when evidence is available. Without
it, a low unsupported-citation rate is uninterpretable.

**s5i5.** Repeat opportunities are 0 by construction, so the repeat rate is undefined there. Raw consecutive repeats
and distinct coordinates are reported descriptively. Prediction accuracy is reported separately, because the frame
always changes.

## 9. Outcome and advancement rules (proposal)

1. **Technical validity first** (§10).
2. **Solving.** Unchanged from v1 §9.2. A solving improvement is claimed only from completed levels: more levels than
   the baseline in at least 2 of 3 games, in both blocks, and fewer in none.
3. **Action selection (exploratory).** A behavioural improvement is reported only if all of these hold:
   - for a failure-inclusive rate whose status is `defined` (minimums met);
   - in at least two games;
   - in the same direction in both blocks;
   - with the arm difference exceeding that arm's block-1/block-2 difference.

   Otherwise it is `inconclusive` or `within_run_to_run_variance`.
4. **Exploratory advancement thresholds, kept provisionally.** These are the candidate invalid-action rate ≤ the
   baseline's + 0.05, and unsupported citations ≤ 0.20 (with citation supply reported and the 10-citation minimum
   met).
   - They gate only whether an ablation or a larger study is worth proposing.
   - **They are not evidence that the candidate is reliably grounded**, and they are not a reliability
     certification.
   - If unsupported citations are undefined or insufficient, the threshold is not met.
5. Prediction accuracy and revision stay candidate-only and descriptive.

## 10. Failure rules

Unchanged from v1 §10, except where noted.

| Rule | Trigger | Action |
|---|---|---|
| F1 technical incompleteness | an episode missing, a lifecycle or cleanup failure, or a replay mismatch | `technically_incomplete`; no claims; no rerun |
| F2a invalid-output rate | either arm's invalid-action rate exceeds 0.25 over its first 24 calls in a session | stop that session (technical abort); retain everything |
| F2b decision-cap hits | 2 or more episodes of one arm end at `decision_cap`, across both sessions | **continue the schedule**; report the arm comparison as `inconclusive_reliability` |
| F3 holdout identifier | any H1, H2 or non-development id in a request, an environment open or a tag | stop immediately; quarantine; report; record the consumption event |
| F4 integrity | canary failure, lock mismatch, a v2 `verify_history` failure, the isolation check, or prefix-cache hits > 0 | stop the session; `technically_invalid` |
| F5 dispatch reliability | failed plus unknown dispatches exceed 0.10 of dispatched actions in a session | stop the session (technical abort) |
| F6 deadline | the internal deadline is reached | stop scheduling, finalize and clean up; F1 applies |

Session 2 does not start after a session-1 stop under F2a or F3–F6.

## 11. CPU implementation status (this pass; no model, no GPU)

| Piece | Commit | Evidence |
|---|---|---|
| Evaluator denominators, undefined vs zero, failure-inclusive rates, minimums | `88cd1b9` | `tests/test_feedback_action_v1_denominators.py`, 13 tests |
| Live runner derived from the reviewed AEH v1 stack; CPU fake server | `ceedf89` | `research/feedback_action_v1/derive.py` (`--check`); sources pinned to the AEH r3 review lock; `tests/test_feedback_action_v1_live.py`, 12 tests |
| Token audit of every request form | `20c1cf8` | `tests/test_feedback_action_v1_token_audit.py`, 5 tests. **Counts: TODO**, pinned stack |
| Terminal-aware dispatch checks | `cbe7cc5` | `tests/test_feedback_action_v1_dispatch.py`, 7 tests |

**The derived runner** (`research/feedback_action_v1/live/{runner,engine,evidence,service}.py`) consists of exact
copies of the reviewed files, with global renames and counted substitutions. The substitutions are:
- the 24-action and 32-call caps;
- invalid outputs never ending an episode;
- v2 raws and statement records;
- request validation delegated to `live/policy.py`;
- a 192-call session ceiling.

The CPU fake server sends every request through the derived service contract: canary, validation, tokenizer
admission and call ceiling.

**Dispatch checks on the real offline engine:**
- Both sessions played 24 scripted actions per game and arm: 288 dispatches, all acknowledged.
- Every episode started at its frozen initial hash.
- Continuity matched at every step.
- s5i5 reached GAME_OVER at action 50, on a check-only extended cap, with no call or dispatch after it.

**Level completion and WIN, GAME_OVER, environment reset, a rejected dispatch and an unknown outcome** were exercised
through the same runner with a synthetic adapter. These are synthetic diagnostics, not real-game data.

## 12. Package and sessions (a proposal; nothing reserved or approved)

**Every package section below states its session count, maximum reservation per session, admission cutoff, cleanup
reserve and retry policy.**

| Item | Value |
|---|---|
| Session count | **2**: one per block, each a fresh reservation running one block (6 episodes) |
| Maximum reservation per session | **3,600 s** provider timeout per session (proposal). That is at most 7,200 s for both sessions. |
| Internal deadline | 3,300 s per session |
| Admission cutoff | A pair is admitted only if at least **600 s** remain before the internal deadline (`pair_admission_seconds`). Unadmitted pairs are recorded and make the run incomplete. The model must be ready within the **900 s** startup ceiling, or the session stops. |
| Cleanup reserve | **300 s** per session, between the internal deadline and the provider timeout. Never spent on play. |
| Retry policy | **No retry allowance is approved.** No call, episode, pair or session is retried. A failed or aborted session produces a report. Any rerun needs a new approval. |

**Estimated runtime is not an authorization ceiling.** v1 §11's estimates (typical about 1,050–1,900 s per session,
worst case about 2,750 s) are planning figures, made from measured AEH v1 and ECv3 rates plus an assumed decode rate.
- The steady-state requests here are about 31–39 KB, against AEH v1's about 28 KB (about 26k tokens). Prefill per
  call is therefore expected to be modestly higher. **That is an estimate.**
- Admission control and the deadlines, not the estimate, protect the reservation.
- The authorization ceiling is a separate decision.

A GPU decode benchmark is **not** approved preparation. None is built or planned here without separate authorization.

## 13. Before an exact source and package lock

1. **Pinned token audit.** Run `python -m research.feedback_action_v1.token_audit tokenize --tokenizer
   .cache/phase4-tokenizer` in the pinned environment (transformers 4.57.6, tokenizers 0.22.2, jinja2 3.1.6). It
   must show:
   - every form within the 60,000 prompt-token ceiling and the 65,536 context;
   - whether the longest schema-valid candidate completion fits 640 tokens.

   The worst case is non-ASCII text at the 240-character caps, escaped, in pretty-printed JSON. If it does not fit,
   decide between a larger cap and tighter text limits *before* freezing. Truncation is an invalid output.
2. **Derive the launch harness** from AEH v1 the same way:
   - worker, model host, supervisor, monitor, resources and authority;
   - the launch, package, review and evaluation scripts.

   The AEH host and its transport only ever ran 128-token requests with the baseline schema. The candidate's extended
   guided-decoding schema and its 640-token cap must be re-verified through the host and the model server.
3. **Independent evaluation script** for live output:
   - verify the evidence manifest;
   - `verify_history` every episode against its raws;
   - recompute every rate with the evaluator;
   - apply §9–10.
4. **End-to-end rehearsal under the supervisor**, with the fault matrix (transport, slow calls, storage, cancellation,
   surviving child), as AEH v1's connected tests.
5. **Review package, source lock, compute authorization, reservation and approval.**
