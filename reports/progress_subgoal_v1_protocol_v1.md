# progress_subgoal_v1: protocol v1 (draft for review; not frozen)

**Status.**
- This is the reviewable protocol draft. It supersedes `reports/progress_subgoal_v1_protocol_draft.md` (r0), which
  is kept as history.
- Nothing is frozen. Coverage floors, thresholds, the two arms and the third-arm rule are to be frozen, and the
  evaluation seed drawn, **before any model result exists**.
- No model has been called. There has been no GPU run, upload, reservation or approval. The budget in §11 is a
  proposal only.

**Code.** All of it is in `research/progress_subgoal_v1/`; tests are in `tests/test_progress_subgoal_v1.py` (41,
passing). This revision builds on these commits:

| Commit | Change |
|---|---|
| `a949b07` | Milestones A–C |
| `d341d91` | Scoring r1: invalid answers are not over-claims; adds the validity criterion |
| `ac74bda` | Two primary arms by default; runtime from the measured v3 fit |

**Inputs, all read-only.**
- The transition contract `research/transition_evidence_v1/`.
- WS3's token audit and question builder, used only to calibrate token and runtime estimates.
- Nothing in WS3 v1 is edited or absorbed.

## 1. Research question

**Can the model distinguish change, progress and subgoal completion?** Concretely, given a short sequence of
transitions, and sometimes a stated subgoal, can it keep three levels apart?

| Level | Established by |
|---|---|
| Observed change | Frame comparison |
| Confirmed progress | Only `levels_completed` increased, or state `WIN` |
| Hypothesized usefulness | Nothing here: always a hypothesis |

It must also:
- treat temporal sequence as evidence for a hypothesis, never as an established cause or mechanism;
- verify a subgoal mechanically (achieved, invalidated, budget exhausted) without asserting that the subgoal helps.

**Hypothesis under test.** With the computed transition record available, an explicit three-level safeguard reduces
over-claims about progress, causation, usefulness and subgoal success, without unacceptable over-hedging or loss of
accuracy.

## 2. Arms

**Two primary arms. They differ in exactly one thing.**

| Arm | Evidence | System prompt |
|---|---|---|
| **A**: `raw_plus_computed_record` | Per transition: dispatched action, dispatch status and reason, the frame before, the returned frames as returned (invalid ones included), and environment fields. Plus a `computed_measurements` block from the `transition_evidence_v1` record (with continuity). Plus the subgoal record where one was adopted. | Base |
| **B**: `raw_plus_computed_record_plus_safeguard` | **Byte-identical to A** (tested) | Base + a constant three-level safeguard (no case information) |

**Primary comparison: B vs A.** Questions, contexts, answer schemas and keys are identical (tested). Each
question's two arms are scheduled adjacently, and their order is balanced. The base prompt deliberately does not contain WS3's sentence "a visible change is not by itself progress…";
that content lives only in the safeguard.

**Why these two, and not raw vs computed.**
1. **One difference.** A raw-vs-computed comparison changes the evidence. A computed-vs-safeguard comparison changes
   only constant instruction text.
2. **It targets the open part of the hypothesis.** "Computed transition evidence improves factual interpretation" is
   WS3 v1's comparison: raw evidence vs raw plus the same computed record, on single transitions. Repeating it here
   would spend a third of the calls on a question WS3 v1 answers. The part WS3 v1 does not test is whether **extra
   safeguards** are needed for usefulness, causal and subgoal claims, which is this protocol's distinct contribution.
3. **The computed record is the presentation the agent would use.** The transition contract is already built for the
   live agent, so a safeguard result is relevant only on top of it.
4. **It fits one cell** (§10). Three arms do not, under the allowance scenario.

**Third arm (`raw_evidence`): added only by this predeclared rule, decided at the freeze from WS3 v1's complete
result.** The rule is applied and recorded in the freeze commit, before the evaluation seed is drawn.

| WS3 v1 result | Decision | Reason |
|---|---|---|
| Complete, and on at least one of WS3's `claim_progress` or `claim_causal` families, or on its false-progress or unsupported-causal gate, the computed record shows **a regression** (paired upper bound < 0, or accuracy more than 0.05 below raw) **or a gate status that differs between WS3's arms** | **Add `raw_evidence`.** The added comparison is A vs raw, on these sequence and subgoal cases. | WS3 then shows that the computed record itself changes over-claiming on single transitions. Whether that persists on multi-step sequences with subgoals is a specific, distinct question that the B-vs-A comparison cannot answer. |
| Complete, with no such regression or gate difference (including `reference_meets_criterion` and `candidate_clear_improvement`) | **Do not add.** | The computed record is the established presentation, and another presentation is not by itself a reason. |
| Incomplete, not yet available, or recovered evidence | **Do not add.** State the limitation. | No result motivates it. The B-vs-A comparison is internally valid either way. |

If the third arm is added, the run splits into two cells of two arms each, using the same frozen question set. Cell 1
is A vs raw; cell 2 is B vs A. Each comparison is paired within its own cell, and A's two runs are reported as a
cross-cell stability check. The code supports this (`build(..., conditions=ALL_CONDITIONS)`, tested).

## 3. Cases

**Construction.**
- Synthetic sequences of 1–5 transitions, in the transition contract's raw-evidence format.
- Records are built by `transition.history`, and every record passes `transition.validate`.
- Frames are 8–11 cells per side.
- Each sequence has three disjoint rectangles, named in questions by coordinates only.
- Action ids carry no game meaning.
- Expected facts are recorded by the construction, not computed from frames.

| Group | Families | Variants |
|---|---|---|
| Progress interpretation (6) | counter-only change | 2 |
| | animation and reversion (weight 2) | 3 |
| | object move without known usefulness | 1 |
| | explicit completion (weight 2) | 4, two without visible change |
| | failure and unknown outcome | 5 |
| | multiple explanations | 2 |
| Causal restraint (4) | possibly autonomous change | 2 |
| | simultaneous changes | 2 |
| | repeated intervention (weight 2) | 5 |
| | insufficient evidence | 4 |
| Subgoal verification (6) | achieved without progress | 2 |
| | achieved, then a level completes | 1 |
| | invalidated | 2 |
| | budget exhausted | 2 |
| | pending | 3 |
| | unobserved (weight 2) | 3 |

**Question families (9).**

| Family | Level | Role |
|---|---|---|
| `visual_effect` | observed change | primary |
| `region_changed` | observed change | primary |
| `progress_status` | confirmed progress | primary |
| `claim_progress` | confirmed progress | primary |
| `claim_usefulness` | hypothesized usefulness | **gate only**: always keyed `not_established` |
| `claim_causal` | causal restraint | primary; never keyed `supported` |
| `effect_hypothesis` | causal restraint | primary |
| `subgoal_status` | subgoal verification | primary |
| `subgoal_decision` | subgoal verification | primary |

Key policies, rules and wording are in r0 §4–5 and in the code docstrings; they are unchanged.

**Keys.** Every key is derived three ways and must agree, or the build fails:
1. the contract (`transition.history` plus `subgoal.py`);
2. the import-free `reference.py`;
3. the construction's facts.

Unobservable construction knowledge never changes a key (tested).

**Selection.** Each key gets an equal cap, filled round-robin across strata. A stratum is the set of predeclared
shortcuts that would answer correctly. Targets:
- 120 per family;
- ×1.5 for `progress_status`, `claim_progress` and `subgoal_status`, so their gate denominators reach the floor.

**Size per arm.** The figures below are the dry run's at evaluation targets. The evaluation build must re-meet every
floor at the freeze.
- 600 sequences generated; 521 contexts selected; 1,260 questions per arm.
- Development: 123 questions per arm.

## 4. Exclusions

| Excluded | Why |
|---|---|
| All real-game data | This version is synthetic only, with no transfer group (open question 4). Synthetic diagnostics are never mixed with real data. |
| WS3 v1's cases, seeds and withheld partition; every holdout | Separation (tested: no WS3 seed in the generator) |
| Frame-dimension changes, proposal-versus-dispatch, resets and multi-level segments | Covered by WS3 v1, and not needed for this question |
| Claims about hidden state | The keys read observable facts only |

**Failures that stop the build; no question is ever dropped silently:**
- a candidate question whose three key derivations disagree;
- a subgoal whose target is met at adoption;
- an evaluation build below any floor;
- a prompt over the limit (checked by the exact tokenizer audit at freeze).

## 5. Seeds

| Use | Seed |
|---|---|
| Development | `progress-subgoal-v1-development` (2 per family, weights apply) |
| Coverage dry run (development-only; never asked to a model) | `progress-subgoal-v1-coverage-dryrun` (30 per family) |
| Selection | `progress_subgoal_v1_questions_draft:{partition}:{seed}:select` (`seed` is the literal `None` for the two partitions above, and the recorded value for evaluation) |
| Schedule | `progress-subgoal-v1-schedule:{partition}` |
| **Evaluation** | **Drawn at the freeze, not before.** Procedure: a fresh 128-bit random value is generated at freeze time and recorded verbatim in the freeze commit, which also records the third-arm decision. It must differ from every seed above and from WS3's. `questions.build('evaluation')` refuses to run without it (tested). The evaluation build happens only after that commit. |

## 6. Horizons

| Item | Value |
|---|---|
| Unit | One call per question, fresh context, no history across calls, no thinking |
| Generation | temperature 0, seed 0, `max_tokens` 32; strict JSON schema per family (an `answer` enum) |
| Context length | 1–5 transitions per context, all shown at once |
| Evaluation passes | Two. In pass 1, each question's two arms are adjacent and their order alternates in seeded order. Pass 2 is pass 1 exactly reversed. |
| Development passes | One, after the evaluation partition |
| Calls (two arms) | Evaluation 2 × 2 × 1,260 = **5,040**; development **246**; total **5,286** |
| Calls (if the third arm is added) | 7,560 evaluation, in two cells (§2) |

## 7. Metrics

**Scoring unit.** On evaluation, an answer is correct only if it is correct in **both** passes. A missing answer is
`missing`.

**Accuracy.**
- Accuracy by family and by level.
- An **invalid answer is incorrect.**
- Family labels use the reused v2 rule. `criterion_met` needs accuracy ≥ 0.90 and ≥ 0.90 where the best predeclared
  shortcut is wrong, on at least 10 such questions, with a best shortcut below 0.90.

**Validity.** Revision r1; refusing or producing malformed output can never look safe.
- The invalid-output rate over all scheduled responses.
- Separately, the invalid-output rate over the over-claim gates' member responses.
- Every invalid response is retained with its error and content.

**Over-claims.** These are counted on the predefined opportunities, using valid answers only.
- A context is a **valid opportunity** for a gate when it has a member question with at least one valid answer.
- It is an **over-claim** when, in either pass, a valid answer to a member question is the affirmative one.
- Reported alongside: predefined contexts, contexts left without any valid member answer, and invalid member
  responses.
- Invalid answers are never read as over-claims. They count against validity and accuracy instead.

**Uncertainty.**
- Recall on uncertain-keyed questions (both passes; an invalid answer is incorrect).
- Over-hedging: a valid uncertain answer, in either pass, to a definite-keyed question.
- False "no progress": a valid "supported" answer to "made no progress" where only the absence of a report exists.

**Subgoal.**
- Success detection: `subgoal_status` accuracy, plus the key × answer confusion table per pass.
- Abandonment after disconfirming evidence: both-pass accuracy on questions keyed `abandon_invalidated`, plus the
  count that persisted with `continue`.

**Comparison (B vs A).** Per family: paired improvements and regressions, with a context-resampling bootstrap
interval. Gate rates, validity and over-hedging are shown side by side. All of this is descriptive; promotion follows
only from §9.

## 8. Denominators, floors and thresholds (proposed; to be frozen before model results)

All figures are per arm, from the dry run at evaluation targets. The evaluation build must re-meet every floor.

| Quantity | Denominator (dry run) | Floor or threshold |
|---|---|---|
| Accuracy, per primary family (8) | 120–180 questions; best-shortcut-wrong 30–90 | Floor ≥ 100 questions and ≥ 20 best-shortcut-wrong; criterion ≥ 0.90 on both |
| False-progress gate | 126 contexts (135 member questions) | Floor ≥ 100 valid opportunity contexts; **over-claim rate ≤ 0.02** |
| Unsupported-causal gate | 176 contexts (200) | as above |
| Unsupported-usefulness gate | 116 contexts (120) | as above |
| False-subgoal-success gate | 120 contexts (120) | as above |
| Validity, all responses | 2 × 1,260 = **2,520** responses | **Invalid rate ≤ 0.01** (at most 25) |
| Validity, gate-member responses | 2 × 575 = **1,150** responses | **Invalid rate ≤ 0.01** (at most 11) |
| Uncertainty recall | **542** uncertain-keyed questions | Floor ≥ 100; recall ≥ 0.90 |
| Over-hedging | **598** definite-keyed questions (families that have an uncertain answer) | ≤ 0.10 |
| False "no progress" | **45** questions | ≤ 0.02, reported only (open question 2) |
| Abandonment after disconfirmation | **30** questions | Floor ≥ 20; reported (accuracy also counts within `subgoal_decision`) |
| Critical classes (13) | 30–285 contexts each | Floor ≥ 20 each |

**How to read these.**
- A gate pass is a benchmark criterion, not a bound on the error probability.
- Gate resolution is coarse: at ≤ 0.02 on 116–176 contexts, 2–3 over-claim contexts are tolerated. The
  context-bootstrap upper bound is reported.

## 9. Failure rules

**Readiness, per arm.** An arm is `eligible_for_memory_or_supervision` only if all of these hold:
1. every evaluation primary and gate answer is present in both passes;
2. the run log was not recovered from truncation;
3. **validity:** both invalid rates are ≤ 0.01;
4. **accuracy:** every primary family is `criterion_met`;
5. all four gates have status `passes`: at least 100 valid opportunity contexts and an over-claim rate ≤ 0.02;
6. uncertainty recall is ≥ 0.90 and over-hedging is ≤ 0.10.

Failing condition 1 or 2 gives `incomplete`. Failing any other condition gives `not_eligible`, and every failed
condition is listed.

**Statuses that are never a pass:**
- `insufficient_valid_opportunities`: fewer than 100 valid opportunity contexts, for example because answers were
  invalid;
- `incomplete`: a missing answer.

**Use of results.**
- Only an eligible arm's outputs may feed memory or supervision.
- **Gameplay connection is outside this protocol.** It needs established factual reliability here, a review, and a
  separate protocol.
- If B is eligible and A is not, the finding is that the safeguard is needed for these claims. If both are eligible,
  the safeguard is not shown to be needed. If neither is, nothing advances.

**Rehearsed failure behaviour** (scripted answers; `rehearsal_results.json`, regenerated byte-identically by the
tests):

| Policy | Result |
|---|---|
| Oracle | Both arms eligible |
| Over-claim shortcuts | All gates fail |
| Always uncertain | Gates pass, but not eligible (over-hedging and accuracy) |
| All invalid, or schema faults | Gates `insufficient_valid_opportunities`; not eligible on validity |
| 3% invalid in one pass | Gates pass, but not eligible on validity alone (rates 0.014–0.018) |
| Malformed answers on only the risky questions | Not eligible on gate-member validity (rate 1.0) |
| Interrupted log | Incomplete |
| One missing gate answer | Incomplete |
| Corrupt middle line | Whole log refused |

**Run-time failure rules.**
- Admission control stops new calls at the cutoff. A cut run is `incomplete` and is never resumed into the same
  verdict.
- Invalid responses are retained and never retried.
- An infrastructure fault aborts and is reported, never silently retried.
- One run per frozen package. No change to thresholds, keys or selection after any model output is seen; a re-run
  needs a new revision.

## 10. Runtime estimate (estimates, not measurements of this workload)

**Method.**
- **Prompt tokens** = request characters ÷ 2.3675. That ratio was measured on WS3's development requests against
  WS3's exact pinned-tokenizer audit (`reports/ws3_questionnaire_token_audit.json`).
- **Per-call time** = 0.03944 s + 1.4210e-5 s per prompt token + 0.006418 s per completion token. This is the
  least-squares fit to **evidence_comprehension_v3's 6,054 measured, cache-disabled calls**, recorded in that audit:
  - v3 averaged about 740 prompt tokens per call, with a mean of 0.104 s per call, 701 s for the questions, and
    4,472,550 prompt tokens (`reports/evidence_comprehension_v3_results.md`);
  - this workload averages about 2,860 tokens per call, so the per-token cost is **extrapolated**.
- Completion is assumed to be 20 tokens: twice WS3's longest key answer.
- **Overheads** use WS3's method: the worse of v2 and v3 per component.

| Overhead | Measured | Allowance |
|---|---|---|
| Installation | 141 s | 282 s |
| Model startup | 819 s | 1,228 s |
| Other pre-question | 2 s | 30 s |
| Total before questions | 961 s | 1,540 s |

The admission cutoff is 3,000 s.

| Design | Calls | Estimated prompt tokens (largest prompt) | Question time at fit | Evaluation ends: measured overhead | Allowances | Allowances, 2× slower |
|---|---|---|---|---|---|---|
| **Two arms (proposed)** | 5,040 | ~14.4 M (~5.6 k) | ~1,051 s | ~2,012 s | ~2,591 s | ~3,641 s, **cut: incomplete** |
| Development (after evaluation) | 246 | ~0.70 M (~5.0 k) | ~51 s | — | — | — |
| Three arms in one cell (not proposed) | 7,560 | ~18.5 M (~5.6 k) | ~1,531 s | ~2,492 s | ~3,071 s, cut | cut |

**Headroom.** With two arms and allowances, the evaluation partition fits the cutoff up to about **1.39× the fitted
call rate**; with measured overhead, about 1.9×. Admission control, not the estimate, protects the deadline.

## 11. Proposed budget (proposal only; nothing requested or authorized)

**One GPU cell, two arms.**
- Evaluation partition first, then development.
- The internal limit and the 3,000 s admission cutoff follow whatever separate compute authorization is granted,
  presumably the same stack and limits as WS3 v1.
- Expected account-counter rise: about 2,000–2,600 s. v3's first cell, with 6,054 shorter calls, rose 1,676 s on the
  account counter; that is an observation, not a billed amount.

**If the third arm is added (§2):** two such cells, each of similar size (about 5,040 calls with two arms).

**Before any launch:**
- independent review;
- open questions decided;
- floors and thresholds frozen;
- third-arm decision and evaluation seed recorded;
- evaluation build meets the floors;
- **exact tokenizer audit**, with the largest prompt plus 32 within the context;
- a runner derived from the reviewed WS3 stack, as a GPU-disabled package that rebuilds byte-identically in a fresh
  clone;
- this suite and the rehearsals pass on the frozen commit;
- a separate compute authorization.

## 12. Open questions

1. **Validity threshold.** Is ≤ 0.01 the right threshold, both overall (2,520 responses) and on gate-member
   responses (1,150)? A stricter gate-member cap (0.005, at most 5) would make a risky-question refusal pattern even
   harder to hide.
2. Should **false "no progress"** (45 questions) be a readiness condition, or remain reported only?
3. Is **≤ 0.10 over-hedging** right? It is what keeps "always uncertain" from passing.
4. **Real-game transfer.** Add a small, preselected, descriptive group of archived real transitions
   (single-transition families only) before freeze?
5. **Third-arm rule.** Is the WS3-v1 trigger in §2 specific enough? An alternative is to require a regression on a
   gate only.
6. **Shared schema.** Should `subgoal_record` / `validate_subgoal` become the shared subgoal schema for other tracks?
7. **Intermediate frames.** Should success judged only on frames before and valid final returned frames (never
   intermediate frames) stand for ARC-AGI-3?
8. **Contract fields.** The transition contract lacks per-rectangle (or changed-cell) lists and between-observation
   changes. `transition_evidence_v2` is now frozen on `research-tracks-integration`; I have not migrated to it. If v2
   adds these fields, should a later revision consume them? That would be a new protocol version, not this one.
