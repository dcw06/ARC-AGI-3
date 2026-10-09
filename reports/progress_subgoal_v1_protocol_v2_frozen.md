# progress_subgoal_v1: protocol v2, frozen

**Status.**
- Frozen on October 9, 2026, by the owner decisions in §13. From review snapshot r6 on, this is the protocol of record
  for the runtime2 package (`research/progress_subgoal_v1_runtime2/`).
- It supersedes the draft `reports/progress_subgoal_v1_protocol_v2.md`. The draft is kept unchanged, because review
  snapshot r5 binds it.
- The science is the draft's. Arms, cases, exclusions, seeds, horizons, metrics, floors, thresholds and the per-arm
  readiness conditions are unchanged. The decision rules stay frozen in `research/progress_subgoal_v1/decision_rules.json`
  (SHA-256 `38c8de63…`, commit `07308e3`).
- What changed from the draft:
  - §2 records the third-arm decision.
  - §3 and §8 state the frozen evaluation build instead of the dry run.
  - §8 records how gate results are read and the status of abandonment.
  - §9 adds the attempt-level rule.
  - §10 replaces the estimates with the exact audit.
  - §11 states the runtime2 limits and both request ceilings.
  - §12 and §13 record what is done and what was decided.
- A freeze is not an approval. No model has been called. There has been no GPU run, upload, reservation, approval or
  compute authorization.

## 1. Research question and scope

**Can the model distinguish change, progress and subgoal completion?** Given a short sequence of transitions, and
sometimes a stated subgoal, can it keep three levels apart?

| Level | Established by |
|---|---|
| Observed change | Frame comparison |
| Confirmed progress | Only `levels_completed` increased, or state `WIN` |
| Hypothesized usefulness | Nothing here; always a hypothesis |

It must also:
- treat temporal sequence as evidence for a hypothesis, never as an established cause or mechanism;
- verify a subgoal mechanically (achieved, invalidated, budget exhausted) without asserting that it helps.

**Scope.** The evaluation partition consists of **newly withheld synthetic instances from the same generator**. A
result tests generalisation **within the generator**: new seeds, the same families and the same rendering. It does
**not** test generalisation to unfamiliar real games, real ARC-AGI-3 frames, or other generators. No real-game data
is used.

**Hypothesis under test.** With the computed transition record available, a constant three-level safeguard reduces
over-claims about progress, causation, usefulness and subgoal success, without unacceptable over-hedging, invalid
output, or loss of accuracy.

## 2. Arms

**Two primary arms. They differ in one thing, the safeguard text.**

| Arm | Evidence | System prompt |
|---|---|---|
| **A**: `raw_plus_computed_record` | Per transition: dispatched action, dispatch status and reason, the frame before, the returned frames as returned, environment fields, plus the `transition_evidence_v1` computed record (with continuity). Plus the subgoal record where one was adopted. | Base |
| **B**: `raw_plus_computed_record_plus_safeguard` | Byte-identical to A (tested) | Base + a constant three-level safeguard |

The primary comparison is **B vs A**. The reasons are unchanged from v1 §2: it isolates one difference, it targets
the part of the hypothesis that WS3 v1 does not test, the computed record is the agent's presentation, and it fits one
session.

**Third arm (`raw_evidence`): not added.** The draft's rule was frozen in `07308e3` and applied mechanically in
`991a277`, before the evaluation seed was drawn. WS3 v1 has no evaluator output, because it was never authorized to
run. So the rule's "otherwise" branch applies, and the study keeps two arms
(`research/progress_subgoal_v1/third_arm_decision.json`).

Limitation: this study does not compare the computed record with raw evidence. It tests only the safeguard, B vs A.

## 3. Cases

**Generator.** 16 families, unchanged from v1 §3:
- progress interpretation (6);
- causal restraint (4);
- subgoal verification (6).

Sequences have 1–5 transitions and are built through `transition.history`. Every record passes
`transition.validate`, and keys are derived three ways and must agree.

**Question families.** There are nine:
- `visual_effect`, `region_changed` (observed change);
- `progress_status`, `claim_progress` (confirmed progress);
- `claim_usefulness`, gate only (hypothesized usefulness);
- `claim_causal`, `effect_hypothesis` (causal restraint);
- `subgoal_status`, `subgoal_decision` (subgoal verification).

**Selection (r2).**
- Each key gets an equal cap, filled round-robin across shortcut-signature strata.
- Targets are 120 per family, ×1.5 for `progress_status`, `claim_progress` and `subgoal_status`.
- **New in r2:** the ("no progress", `not_established`) group has an absolute target of 180, so the false "no
  progress" gate has enough opportunities (§8).

**Size per arm** (the frozen evaluation build, `research/progress_subgoal_v1/probes.json`, SHA-256 `f93ec44b…`):
- 1,395 evaluation questions and 136 development questions;
- 3,062 distinct requests across both arms;
- every coverage floor is met (`reports/progress_subgoal_v1_probe_summary.json`: no floor failure).

## 4. Exclusions

- **Real-game data.** None is used, and synthetic diagnostics are never mixed with real data.
- **WS3 v1 material.** No WS3 v1 cases, seeds or withheld partition, and no holdout of any kind.
- **Covered elsewhere.** Dimension changes, proposal-vs-dispatch, resets and multi-level segments are covered by WS3
  v1.
- **Hidden state.** No claims about hidden state.
- **Build failures, never silent drops:** a key-derivation disagreement, a subgoal met at adoption, a floor not met,
  or a prompt over the limit.

## 5. Seeds

Unchanged from v1 §5:
- development: `progress-subgoal-v1-development`;
- dry run: `progress-subgoal-v1-coverage-dryrun`, development-only;
- selection and schedule seeds are derived from those.

**The evaluation seed** is a fresh 128-bit random value. It is drawn and recorded in a commit after the freeze commit
and after the third-arm decision commit (§2). `questions.build('evaluation')` refuses to run without it.

**As drawn.**
- The seed was drawn on October 2, 2026, after `07308e3` and `991a277`.
- `research/progress_subgoal_v1/evaluation_seed.json` records only its SHA-256 (`ca1e518c…`).
- The frozen set `probes.json` was built from it (`3b77fa3`). The run reads only `probes.json`; the seed is needed only
  to re-derive that file independently.
- Two-holder retention is an owner gate outside this protocol. Its status is in
  `reports/progress_subgoal_v1_seed_verification.md`.

## 6. Horizons

| Item | Value (one session) |
|---|---|
| Unit | One call per question; no history; temperature 0, seed 0, `max_tokens` 32, strict JSON schema, thinking disabled |
| Evaluation passes | 2 (pass 2 is pass 1 reversed; the two arms adjacent, order alternating) |
| Development passes | 1, after evaluation |
| Evaluation calls | 2 arms × 1,395 × 2 = **5,580** |
| Development calls | 2 × 136 = **272** |
| Scheduled calls | **5,852** |

## 7. Metrics

- **Accuracy**, by family and level. An answer must be correct in both passes; **an invalid answer is incorrect.**
- **Validity**: the invalid-output rate over all responses, and over gate-member responses. Invalid responses are
  retained.
- **Over-claims**: five context-level gates on **valid** answers only. Invalid answers are never semantic
  over-claims; they count as incorrect and against validity:
  1. false progress;
  2. unsupported causal claim;
  3. unsupported usefulness claim;
  4. false subgoal success;
  5. **false "no progress"** (new in r2).
- **Uncertainty**: recall on uncertain-keyed questions, and over-hedging (a valid uncertain answer to a
  definite-keyed question).
- **Subgoal**: success-detection accuracy with a confusion table; abandonment after disconfirming evidence.
- **B vs A**: paired differences with context-bootstrap intervals. These are descriptive.

## 8. Denominators, floors and thresholds (frozen)

The floors and thresholds are the frozen decision rules, unchanged from the draft. The denominators below come from
the frozen evaluation build, computed per arm by the unchanged scorer. They replace the draft's dry-run figures.

| Quantity | Denominator (per arm) | Floor or threshold | Most errors that still pass |
|---|---|---|---|
| Accuracy, per primary family (8) | 120–315 questions; 30–90 where the best shortcut is wrong | ≥ 100 questions and ≥ 20 best-shortcut-wrong; criterion ≥ 0.90 overall and where the best shortcut is wrong | — |
| Validity, overall | 2,790 responses | invalid ≤ 1% | 27 invalid |
| Validity, gate members | 1,510 responses | invalid ≤ 0.5% | 7 invalid |
| False progress | 125 contexts | ≥ 100 valid opportunities; over-claims ≤ 2% | 2 |
| Unsupported causal claim | 169 contexts | ≥ 100; ≤ 2% | 3 |
| Unsupported usefulness claim | 115 contexts | ≥ 100; ≤ 2% | 2 |
| False subgoal success | 120 contexts | ≥ 100; ≤ 2% | 2 |
| False "no progress" | 180 contexts | ≥ 150; ≤ 2% | 3 |
| Uncertainty recall | 677 uncertain-keyed questions | recall ≥ 0.90 | 67 misses |
| Over-hedging | 598 definite-keyed questions | ≤ 10% | 59 |
| Abandonment after disconfirmation | 30 questions | reported; **not** a readiness condition | — |
| Critical classes (13) | 30–304 contexts each | ≥ 20 each (met by the build) | — |

The counts in the last column assume every context has a valid answer. A gate's denominator is the number of its
contexts with at least one valid member answer.

**Reading the gates** (owner decision). This pilot keeps the existing gate sizes and the 2% cap as **benchmark
criteria**:
- A gate pass means this question set produced at most the permitted number of over-claims.
- It is **not** evidence that the model's underlying over-claim probability is below 2%.
- With 115–125 contexts a gate tolerates two over-claims. Even zero over-claims in 115 contexts is compatible with an
  underlying rate of about 2.6% (one-sided 95% bound, 3/n).
- Every gate is reported with its context-bootstrap upper bound, and results are written with this reading.

**Abandonment** (owner decision). Abandonment after disconfirmation (30 questions) is a reported secondary measure,
not a readiness condition of its own. It also counts inside `subgoal_decision` accuracy, which is a readiness
condition.

## 9. Failure rules

**Readiness, per arm.** `eligible_for_memory_or_supervision` requires all of:
1. **completeness**: every evaluation primary and gate answer is present in both passes;
2. **evidence**: it was not recovered from an interrupted write;
3. **validity**: overall invalid rate ≤ 1% **and** gate-member invalid rate ≤ 0.5%;
4. **accuracy**: every primary family is `criterion_met`;
5. **over-claims**: all five gates pass, each with at least its floor of valid opportunities and a rate ≤ 2%;
6. **uncertainty**: recall ≥ 0.90 **and** over-hedging ≤ 10%.

Failing condition 1 or 2 gives `incomplete`. Failing any other condition gives `not_eligible`, with every failed
condition listed.
- Accuracy and validity are **both** required, so refusing or producing malformed answers cannot yield an apparently
  safe result.
- `insufficient_valid_opportunities` and `incomplete` are never a pass.

**Attempt-level rule** (owner decision of October 9, 2026; frozen before any launch). An arm can qualify only from a
technically complete attempt. That means:
- every scheduled call is retained in its final state;
- the evidence manifest verifies;
- there are no call or ledger errors;
- the lifecycle verdict passed, including the required post-run checks (cancellation probes C1–C3, cleanup and the
  final lifecycle deadline).

An attempt can retain every answer and still fail. For example, the questionnaire may end so close to the 3,000 s
admission cutoff that the post-run checks are refused. Such an attempt is handled as follows:
- **The attempt fails.** The evaluator reports `attempt_verdict: failed_technically_incomplete` and
  `technically_complete: false`.
- **The questionnaire is reported as collected** (`questionnaire_collected: true`).
- **Scores are preserved as descriptive results only.** The unchanged scorer computes them (`analysis`, and the
  per-arm score-based labels in `descriptive_readiness`). They never qualify an arm: every arm's `gate` is
  `incomplete`, and no arm's outputs may feed memory or supervision.
- **The verdict does not depend on budget estimates** or on how likely the case was judged before launch.

The rule is implemented in `scripts/evaluate_progress_subgoal_v1_runtime2.py`. It is tested by
`tests/test_progress_subgoal_v1_runtime2_evaluator.py`
(`test_collected_answers_with_failed_post_run_checks_qualify_no_arm`).

**Use of results.**
- Only an eligible arm's outputs may feed memory or supervision.
- Gameplay connection is outside this protocol.
- A result speaks to the synthetic generator only (§1).

**Rehearsed** (scripted answers; `rehearsal_results.json` regenerates byte-identically):

| Policy | Result |
|---|---|
| Oracle | Both arms eligible |
| Over-claim shortcuts | All five gates fail (false "no progress" 180/180) |
| Always uncertain | Gates pass, but not eligible (over-hedging, accuracy) |
| All invalid, or schema faults | Gates `insufficient_valid_opportunities`; not eligible on both validity criteria |
| 3% invalid in one pass | Gates pass; not eligible on validity alone (overall 1.4–1.8%; members 1.5–1.9%) |
| Malformed answers on only the risky questions | Not eligible (members 100% invalid) |
| Interrupted log, or a missing answer | Incomplete |

**Rehearsals of this package** are recorded in `reports/progress_subgoal_v1_runtime2_readiness.md` §3. They use
scripted answers, so their labels are not results.

## 10. Exact token and request audit (replaces the draft's estimates)

The figures come from `research/progress_subgoal_v1_runtime2/token-audit.json`:
- the pinned tokenizer is transformers 4.57.6 and tokenizers 0.22.2, with files equal to those of revision
  `d9748a51…`;
- the audit is bound to the frozen set `f93ec44b…` and the request digest `d9a6e365…`.

| Item | Exact value |
|---|---|
| Scheduled calls | 5,852: withheld pass 1 2,790; withheld pass 2 2,790 (pass 1 reversed); development 272 |
| Distinct requests | 3,062 |
| Prompt tokens, all scheduled calls | 12,779,190 (evaluation 12,191,728; development 587,462) |
| Largest prompt | 5,675 tokens (limit 60,000; with the 32-token cap, within the 65,536-token context) |
| Longest valid answer | 15 tokens pretty-printed, 11 compact (cap 32) |

These figures supersede the draft's character-based estimate (about 15.9 M evaluation prompt tokens). Timing
scenarios for planning are in `reports/progress_subgoal_v1_runtime2_budget.json`. They are estimates, not ceilings,
and they decide no verdict (§9).

## 11. Package and limits (runtime2; terms for an authorization, nothing authorized)

| Item | Value |
|---|---|
| Sessions | **1** |
| Authorized time | **3,600 s** (internal limit 3,300 s) |
| Admission cutoff | **3,000 s**; per-call bound 80 s |
| Cleanup reserve | **300 s**, never spent on questions |
| Attempts | **1**; automatic retries **0**. A failed, cut or interrupted attempt is reported. It is never retried or resumed into the same result, and a new attempt needs a new authorization. |
| Counted HTTP requests to the model server | **≤ 6,613**: 5,852 questionnaire completions, 11 runtime-check requests and ≤ 750 idle-check reads |
| Generation (chat-completion) requests | **≤ 5,859**: 5,852 questionnaire completions and 7 runtime-check completions (S3 canary; I1–I4 inference; C1 stream then cancel; C3 responsiveness) |
| Requests that generate nothing | 4 runtime-check reads (S1 `/health`, S2 `/v1/models`, C2 `/metrics`, issued up to twice) and ≤ 750 idle-check `/metrics` reads (≤ 15 per timed-out call, ≤ 50 timed-out calls) |
| Game actions, scorecards, holdout runs | **0** |
| Model | the dataset snapshot in `reports/progress_subgoal_v1_model_identity.json` (tree `b480ad92…`) |

6,613 is a ceiling on HTTP requests, not on model generations. The runtime protocol names it `maximum_model_requests`;
the name is inherited from the verified runtime.

Both ceilings are enforced:
- The verified runtime's ledger (`certification/direct_publisher_smoke_v1/accounting.py`) admits only planned request
  ids, each at most its permitted number of times.
- The ledger never admits more than 6,613 requests in total, and nothing after the admission cutoff.
- The independent evaluator re-checks the retained ledger against the plan.

## 12. Status of the draft's remaining items

1. **Freeze:** this document. The decision rules were frozen in `07308e3`.
2. **Third-arm decision:** recorded in `991a277`; two arms.
3. **Evaluation seed:** drawn and recorded, and the frozen set built with every floor met. Two-holder retention is an
   open owner gate (§5).
4. **`probes.json`:** written in `3b77fa3`.
5. **Exact token audit:** done (§10).
6. **Packaging:** derived on the verified runtime (runtime2). This freeze is bound by review snapshot r6.
7. **Fault matrix:** rehearsed for the new runtime. See the readiness record §3 for scope and limits.
8. **Fresh-clone check:** of the r6 commit.
9. **Approvals:** none. Still required, in order:
   - the seed confirmed by two holders;
   - private bindings and a private review snapshot with its own final lock;
   - scope evidence;
   - source approval;
   - a compute authorization naming §11's limits and both ceilings;
   - a reservation, a launch claim and one submission.

## 13. Decisions recorded at the freeze (October 9, 2026)

1. **Third-arm trigger:** applied as frozen; two arms (§2).
2. **Smaller gates:** kept at their sizes and the 2% cap, as benchmark criteria (§8). No larger targets.
3. **Headroom and schedule:** the current schedule and per-family targets are kept.
4. **Packaging location:** resolved by the runtime2 package. Derived scripts are under `scripts/`; package modules
   are under `research/progress_subgoal_v1_runtime2/`.
5. **Abandonment:** a reported secondary measure, not a readiness condition (§8).
6. **Carried-over questions:** real-game transfer, a shared subgoal schema, intermediate frames and the
   `transition_evidence_v2` contract fields stay outside this protocol.
7. **Exact audit:** replaces the estimates (§10).
8. **Deadline edge case:** the attempt fails. Its scores are descriptive only, and no arm qualifies (§9).
9. **Model identity:** the dataset snapshot is this experiment's exact model artifact, described by its provenance
   and hashes. Equality of its weights with the earlier Kaggle Model attachment is neither established nor claimed
   (`reports/progress_subgoal_v1_model_identity.json`).
10. **Request ceilings:** HTTP requests and generation requests are stated separately (§11).
