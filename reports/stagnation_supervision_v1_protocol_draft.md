# Stagnation supervision v1: draft budget-matched comparison protocol (DRAFT, not frozen)

Status: **draft for review. It authorises nothing.** It grants no GPU time, no Kaggle run, no model inference,
and no holdout or withheld-partition access. Every number below is a proposal. A frozen version needs its own
review, lock and approval. The detector evidence is in `reports/stagnation_supervision_v1_detector_results.md`.

## 1. Hypothesis and the isolated treatment difference

- **H1.** Reflection triggered by mechanical evidence of stagnation improves how reasoning effort is allocated.
  Compared with reflection on a fixed schedule at the same budget, it should lead to more detected loops being
  left for actual progress, and fewer interruptions of productive behaviour.
- **H0 (the competing risk).** Any benefit comes from spending more model calls. Alternatively, false alarms (see
  `delayed_effect` in the benchmark) interrupt productive behaviour enough to cancel the benefit.

The arms differ in exactly one thing: **when** the same reflection request is made.

| Arm | Reflection calls | Shared components |
|---|---|---|
| continuation | none; the detector still runs as an observer, so loops are measured | same policy model, prompt, action budget and episode length |
| periodic | after every P-th action | same request template (`intervention.PROMPT`), same output schema, same validation, same cooldown, cap and token ceiling |
| triggered | when the frozen detector (`trigger_spec.json`) fires | as for periodic |

- **Arm label.** It is metadata and never appears in the prompt (tested).
- **Detector signals.** Both reflection arms send them, filled by the same code, so any content difference comes
  only from timing.
- **Choice of P (proposal).** P = episode actions ÷ intervention cap. With the 40 actions and cap of 4 proposed
  below, P = 10, so the periodic arm can use its whole cap.

## 2. Bounded intervention interface (`intervention.py`, implemented and tested)

**The request** is built only from:
- `transition_evidence_v1` records 0..t, keeping the last 12 transitions as fingerprint prefixes, actions,
  dispatch status, visual effect, changed-cell count, events and progress status;
- the frame shape;
- the available actions;
- the detector signals at t.

It has no parameter through which game source, rules or solutions could enter. A test injects sentinel
environment and source strings into the raw evidence and checks that they never reach the request.

**The output** must be exactly:

| Field | Content |
|---|---|
| `observed_pattern` | What repeats or stalls in the shown evidence (≤ 300 characters) |
| `evidence_refs` | Shown action indices only |
| `assumption_to_reconsider` | Which belief the behaviour seems to rest on (≤ 300 characters) |
| `distinguishing_test` | A `description` plus 1–3 `actions`, each valid under the frozen control contract `arc_action_v12` (ACTION6 needs integer `x` and `y`; every other action has empty `action_data`), using an available id in 1–7, with clicks inside the observed frame |

**Validation** rejects:
- non-JSON, extra or missing keys, and outputs longer than 2,000 characters;
- citations of unshown or future indices;
- references to source code, environment files or game identifiers;
- solution claims ("solution", "will complete …");
- test plans longer than 3 actions;
- test actions that violate `arc_action_v12`. This rule is checked by the repo's own validator
  (`certification.phase4_transient_v2.action_contract.validate_action`, imported read-only, the same one
  `grounded_action_v1` uses). Booleans are not accepted as integers.

An invalid output is retained exactly as received, is charged, counts toward the cap, and is never delivered. The
agent sees only `render()`: the four validated fields in a fixed template, labelled as a hypothesis.

**Known weakness.** The lexical checks are a second line of defence only. They cannot detect a correct solution
phrased as an innocuous "test". The primary guard is that the request contains no privileged material.

## 3. Policy limits (`supervision.py`, implemented and tested)

| Limit | Rehearsal default | Proposal for the experiment |
|---|---|---|
| Cooldown between calls | 6 actions | 6 actions |
| Interventions per episode (valid, invalid and failed all count) | 4 | 4 |
| Supervisor-token ceiling per episode (estimated input plus reserved output must fit before a call) | 8,000 | to be fixed from pilot request sizes; equal across reflection arms |
| Call while the current state is unobserved (unknown outcome or missing frames) | deferred, retained | same |
| Retries of a failed call | none | none |

- **Charging.** Rehearsal charges use a declared estimate of 4 characters per token. A live run must charge the
  serving tokenizer's counts and wall time, including invalid outputs and exceptions.
- **Event log.** Every decision is logged with its outcome: `not_due`, `deferred_unobserved_state`,
  `suppressed_cooldown`, `suppressed_intervention_cap`, `suppressed_token_budget` or `called`.

## 4. Budget matching

- **Common ceiling.** Each episode has a common total compute ceiling: the same action count (proposal: 40
  actions per episode) and the same total token ceiling covering policy and reflection calls. Reflection calls
  are charged inside that ceiling, not on top of it.
- **Matched cap.** Periodic and triggered share the same cap (4) and the same supervisor-token ceiling.
- **Realised use.** Each arm's realised reflection tokens, calls and latency are reported. If triggered uses fewer
  reflection tokens than periodic, any result is reported as "at lower cost". It is never converted into a
  per-token rate.
- **Continuation.** It spends no reflection tokens. The comparison against it measures the value of reflecting at
  all. The comparison against periodic isolates the value of timing.

## 5. Metrics (per episode; the episode is the unit, never the step)

1. **Detector:**
   - precision and recall against post-hoc labels where labelling is possible;
   - false interventions: triggers followed within the next 3 actions by a new (state, action) pair that the
     agent was already taking before the trigger. This is a proxy, and it is reported as a proxy.
2. **Loop exit:**
   - actions from a call to the first untried (state, action) pair in the segment (`supervision.escapes`);
   - the result: `progress`, `another_detected_loop`, `no_progress_before_end` or `did_not_leave`.
   - **Escaping into another loop is not success.** Only `progress` counts, meaning a confirmed
     `levels_completed` increase or WIN before the detector fires again.
3. **Completed levels:** per episode and per arm (expected to be rare, since the baseline has 0 so far).
4. **Cost:** intervention count, supervisor tokens, latency, and their share of the episode ceiling.
5. **Reliability:**
   - invalid-output rate;
   - call-failure rate;
   - dispatch failure and unknown rates;
   - cancellation or interruption rate;
   - episodes ended by the budget.
6. **Observer statistics in all arms:** detector firings per episode, and time spent in detected loops.

## 6. Design (proposal)

- **Games.** Development-partition games only, chosen and approved by the human. No holdout games.
- **Pairing.** Blocks of {continuation, periodic, triggered} on the same game and seed, in counterbalanced order.
- **Variance.** The action-effect history study found the serving stack was not deterministic at temperature 0.
  A byte-identical repeat of a continuation episode must therefore be included to estimate run-to-run variance.
  Without it, differences cannot be attributed to the arm.
- **Pre-check on CPU, no GPU.** Run the frozen detector as an observer over archived real development
  transitions (`scripts/replay_transition_evidence_v1.py` inputs). This shows whether loops occur at all and how
  often the detector fires. If it never fires on real development archives, a GPU comparison is uninformative and
  should not be requested.

## 7. Advancement rule (draft)

Triggered reflection advances only if **all** of the following hold:
- **Against periodic:** it achieves more `progress` loop exits per episode, by a margin frozen before the run.
  Its realised reflection tokens must not exceed periodic's, and it must have no more interruptions of productive
  behaviour than periodic.
- **Against continuation:** it achieves more `progress` loop exits per episode.
- **No regressions:** completed levels, invalid-output rate and failure rate are no worse than in either other
  arm.
- **Beyond variance:** the difference exceeds the run-to-run variance measured by the repeat episode.

The default result is **inconclusive**. Beating continuation alone does not show value beyond spending more model
calls.

## 8. Proposed GPU budget and stop rules (proposal only, nothing authorised)

**Scale reference.** In the action-effect history run, the accounted GPU use was 747.6 s for 144 policy calls,
of which model startup was 403 s.

**Pilot proposal:**
- **Size.** 3 development games × 3 arms × 2 blocks, plus 1 repeat episode, giving 19 episodes of 40 actions:
  - about 760 policy calls;
  - at most 48 reflection calls (4 per reflection-arm episode × 12 episodes).
- **Estimate.** Roughly 4,000–4,500 GPU-seconds including startup.
- **Request.** A ceiling of **5,400 GPU-seconds (1.5 h)** for one run, with no automatic reruns.

**Stop rules, fixed before the run:**
- Stop and report if invalid reflection outputs exceed 50% after the first 10 reflection calls. That would mean
  the interface itself is the finding.
- Stop if dispatch failures plus unknown outcomes exceed 10% of dispatches.
- Stop at the internal wall-time limit, keeping the startup and teardown margins of the earlier runs.
- Stop if the continuation arm's first block shows zero detector firings on every game. There would be nothing to
  intervene on.
- Never exceed the supervisor-token ceiling. Every call, including failed calls, is charged.

## 9. What the eventual experiment can and cannot establish

**It can establish:**
- whether timing (trigger versus schedule) changes loop exits with progress at matched reflection cost, on the
  chosen development games;
- the real false-alarm and blind-spot rates of this detector;
- whether the bounded interface produces valid outputs from the actual model.

**It cannot establish:**
- general solving improvement (there are too few games and episodes, and level completions are rare);
- causality at the step level (steps are not independent);
- anything about holdout or competition performance;
- that stagnation could not have resolved on its own: no detection is a statement about impossibility.

## 10. Dependencies and open items

- **Transition contract (Workstream 3), read-only here; now `transition_evidence_v2`.** Two fields were requested:
  - **available actions** per observation: *resolved* by `transition_evidence_v2`. Legal test actions are now
    taken from the reported available actions of the observation the agent holds
    (`environment.reported.available_actions_after`, or `context.available_actions_before` after a failed
    dispatch). Only when those are `absent` does the request fall back to action ids already shown. The source
    used is recorded with each request;
  - **a HUD or counter region marker** (or an action-independent-change field), to close the step-counter blind
    spot without the detector guessing from pixels. Still open here: v2 provides a declared masked view, but a
    masked fingerprint in the detector is a separately versioned experiment, and this track does not read it.
- **Track 1's prediction schema.** The detector accepts a provisional `{action_index, expects_change}` stream.
  The `prediction_failures` signal was not selected on development, but it should be re-evaluated once Track 1's
  schema is final.
- **History cost.** `Supervisor.observe` rebuilds `transition.history` at every step, so the cost grows
  quadratically with episode length. That is fine at 40–100 actions; an incremental history would be needed for
  longer episodes.
