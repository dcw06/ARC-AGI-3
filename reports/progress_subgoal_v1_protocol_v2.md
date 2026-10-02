# progress_subgoal_v1: protocol v2 (draft for review; not frozen)

**Status.**
- Supersedes `reports/progress_subgoal_v1_protocol_v1.md` (kept, as is the r0 draft). It applies the review of v1
  (`49b48f4`).
- Nothing is frozen. The arms, the third-arm rule's exact conditions, coverage floors, thresholds, and the evaluation
  seed are to be frozen **before any model result is examined**, including before WS3 v1's triggering result is
  looked at for the third-arm decision (§2).
- No model has been called. There has been no GPU run, upload, reservation or approval.
- **The runtime estimates below are estimates, not authorization ceilings.** The only limits are the ones a separate
  compute authorization states. A package's limits (§11) are hard stops enforced in code; they are not estimates.

**Commits of this revision** (branch `worktree-agent-a4f7bba37c003c145`):

| Commit | Change |
|---|---|
| `c3cd128` | Scoring r2: false "no progress" gate; 0.5% gate-member validity cap |
| `c7e1adb` | Third-arm branch accounting: two paired cells, A repeated |
| `c4a2871` | GPU-disabled runner derived from the reviewed WS3 v1 stack; request enumeration and token-audit helper |

**Tests.**
- `tests/test_progress_subgoal_v1.py`: 42 tests.
- `tests/test_progress_subgoal_v1_runner.py`: 12 tests. The connected CPU rehearsal is opt-in (`PSV1_CONNECTED=1`).

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

**Third arm (`raw_evidence`).** Accepted by review, provided its exact conditions are frozen before the triggering
result is examined.
- **When it is decided.** The rule below is frozen in the freeze commit. Only after that commit is WS3 v1's complete
  result read, and the rule is applied mechanically. The decision and the WS3 v1 values it used are recorded in a
  second commit, before the evaluation seed is drawn.
- **Trigger (all values read from WS3 v1's frozen evaluator output, withheld partition):** add the third arm if
  WS3 v1 is `technically_complete` and **any** of the following holds:
  1. on family `claim_progress` or `claim_causal`, the candidate−reference paired 95% upper bound is < 0;
  2. on either of those families, the candidate's both-pass accuracy is more than 0.05 below the reference's;
  3. the `false_progress` or `unsupported_causal_claim` gate status differs between WS3's two arms.
- **Otherwise, keep two arms.** This includes WS3 v1 being incomplete, recovered, unavailable or not technically
  complete; the limitation is then stated.
- **If added: two sessions, each a paired two-arm comparison** (§10, §11):
  - session 1 runs `raw_evidence` vs A;
  - session 2 runs A vs B (the primary comparison, unchanged);
  - A is repeated, so the branch has **2 × 5,580 = 11,160 evaluation calls**, plus 272 development calls per session;
  - each comparison is paired within its own session; A's two runs are reported as a cross-session stability check.

  The review's figure of 10,080 was 2 × 5,040, before r2 added false-"no progress" opportunities.

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

**Size per arm** (dry run at evaluation targets; the evaluation build must re-meet every floor at the freeze):
- 600 sequences, 547 contexts, **1,395 questions**;
- development: 136 questions.

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

## 6. Horizons

| Item | Primary design (one session) | Third-arm branch (two sessions) |
|---|---|---|
| Unit | One call per question; no history; temperature 0, seed 0, `max_tokens` 32, strict JSON schema, thinking disabled | same |
| Evaluation passes | 2 (pass 2 is pass 1 reversed; the two arms adjacent, order alternating) | 2 per session |
| Development passes | 1, after evaluation | 1 per session |
| Evaluation calls | 2 arms × 1,395 × 2 = **5,580** | 2 × 5,580 = **11,160** |
| Development calls | 2 × 136 = **272** | 272 per session |
| Scheduled calls | **5,852** (the code's call ceiling) | 5,852 per session |

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

## 8. Denominators, floors and thresholds (provisional; frozen before model results)

All figures are per arm, from the dry run at evaluation targets.

| Quantity | Denominator | Floor or threshold | One error costs |
|---|---|---|---|
| Accuracy, per primary family (8) | 120–315 questions; best-shortcut-wrong ≥ 30 | ≥ 100 questions and ≥ 20 best-shortcut-wrong; criterion ≥ 0.90 overall and where the best shortcut is wrong | 0.3–0.8 points |
| **Validity, overall** | 2 × 1,395 = **2,790 responses** | **invalid ≤ 1%** (≤ 27) | 0.036 points |
| **Validity, gate members** | 2 × 755 = **1,510 responses** | **invalid ≤ 0.5%** (≤ 7) | 0.066 points |
| False progress | 126 contexts | valid opportunities ≥ 100; over-claims ≤ 2% (≤ 2) | 0.79 points |
| Unsupported causal claim | 176 contexts | ≥ 100; ≤ 2% (≤ 3) | 0.57 points |
| Unsupported usefulness claim | 116 contexts | ≥ 100; ≤ 2% (≤ 2) | 0.86 points |
| False subgoal success | 120 contexts | ≥ 100; ≤ 2% (≤ 2) | 0.83 points |
| **False "no progress"** | **180 contexts** (was 45 questions) | **≥ 150; ≤ 2% (≤ 3)** | **0.56 points** |
| Uncertainty recall | 677 uncertain-keyed questions | ≥ 100; recall ≥ 0.90 | 0.15 points |
| Over-hedging | 598 definite-keyed questions | ≤ 10% | 0.17 points |
| Abandonment after disconfirmation | 30 questions | ≥ 20; reported (also inside `subgoal_decision` accuracy) | 3.3 points |
| Critical classes (13) | 30–285 contexts each | ≥ 20 each | — |

**Why false "no progress" was expanded.** With 45 opportunities, a 2% threshold permits zero errors (1/45 = 2.2%),
and each error moves the rate by 2.2 points. At 180 contexts, three errors pass (1.7%) and four fail (2.2%). That is
usable resolution, and it fits within one session (§10).

**Reading the gates.** A gate pass is a benchmark criterion, not a bound on the error probability. Gates with 116–126
contexts still tolerate only two over-claims. The context-bootstrap upper bound is reported.

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

**Connected CPU rehearsal.** This runs through the derived runner with the fake server over HTTP:
- 5,852 of 5,852 calls answered; lifecycle passed; evidence verified; technically complete.
- Both arms are `not_eligible`, correctly: the fake server's scripted invalid and truncated answers (about 4%) fail
  both validity criteria.

## 10. Runtime estimate (estimates; not authorization ceilings)

**Method** (unchanged from v1 §10):
- Prompt tokens = characters ÷ 2.3675, measured against WS3's exact pinned-tokenizer audit.
- Per-call time = 0.03944 + 1.4210e-5 × prompt tokens + 0.006418 × 20 completion tokens. This is the least-squares fit
  to evidence_comprehension_v3's 6,054 measured cache-disabled calls, which had shorter prompts, so the per-token cost
  is extrapolated.
- Overheads before the first question are 961 s measured and 1,540 s with allowances.
- **The exact tokenizer audit replaces the token estimate before freeze** (§12).

| Session | Calls (evaluation + development) | Estimated prompt tokens, evaluation (largest) | Evaluation ends: measured overhead | Allowances | Allowances, 2× slower |
|---|---|---|---|---|---|
| **Primary (A vs B)** | 5,580 + 272 | ~15.9 M (~5.6 k) | ~2,124 s | ~2,703 s | ~3,866 s: **cut, incomplete** |
| Branch session 1 (raw vs A) | 5,580 + 272 | ~12.0 M (~5.3 k) | ~2,068 s | ~2,647 s | ~3,754 s: cut |
| Branch session 2 (A vs B) | 5,580 + 272 | ~15.9 M (~5.6 k) | ~2,124 s | ~2,703 s | ~3,866 s: cut |

**Headroom.** The primary session fits the 3,000 s admission cutoff up to about **1.26× the fitted call rate** with
allowances, or about 1.75× with measured overhead. Development (about 57 s) runs after evaluation and may be cut
without affecting the decision. Admission control, not the estimate, protects the deadline. A cut session is
`incomplete`.

## 11. Proposed packages (proposal only; nothing requested or authorized)

**Primary package** (`progress-subgoal-v1`, one scope):

| Item | Value |
|---|---|
| Session count | **1** |
| Maximum reservation per session | **3,600 s** (`authorized_seconds`; internal limit 3,300 s) |
| Admission cutoff | **3,000 s** (no call starts after it; per-call bound 80 s) |
| Cleanup reserve | **300 s**, never spent on questions |
| Retry policy | **No retry allowance is approved.** `automatic_retries` 0, `maximum_attempts` 1, one canary. A failed, cut or interrupted session is reported as `incomplete`; it is never retried or resumed into the same result. A new attempt would need a new authorization. |
| Call ceiling | 5,852 (enforced by the host's allow-list ceiling) |
| Game actions, scored submissions, holdout runs | 0 |

**Third-arm branch, only under §2:** two packages (two scopes), each with the same rows as above:

| Item | Value |
|---|---|
| Session count | **2** (one per package; each package is one session) |
| Maximum reservation per session | **3,600 s** |
| Admission cutoff | **3,000 s** per session |
| Cleanup reserve | **300 s** per session |
| Retry policy | **No retry allowance is approved.** 0 retries and 1 attempt per package. A failed session is not re-run, and the other session's result stands alone and is labelled as such. |
| Call ceiling | 5,852 per session (11,160 evaluation calls in total) |

**Expected account-counter rise:** about 2,100–2,800 s per session (estimate). This is not a billing figure and not a
ceiling.

## 12. What remains before an exact source and package lock

1. **Review decisions** on the open questions; freeze the arms, the third-arm conditions, floors and thresholds
   (freeze commit).
2. **WS3 v1's result**, read only after the freeze commit; apply the third-arm rule and record it.
3. **Evaluation seed** drawn and recorded; build the evaluation partition; confirm every floor.
4. **Write `research/progress_subgoal_v1/probes.json`** from the evaluation build. It is the frozen question set that
   live mode reads; the rehearsal stand-in can never reach live.
5. **Exact token audit** with the pinned tokenizer, via `research.progress_subgoal_v1.probes.scheduled_requests`, or
   `research.progress_subgoal_v1.token_audit.audit(tokenizer)` on the frozen file. Confirm that every prompt
   satisfies prompt + 32 ≤ 65,536 and ≤ 60,000, and that the 32-token cap covers every answer. Then replace the
   estimates in §10.
6. **Packaging, not yet derived.** Still needed: the review-package builder, the notebook and notebook review, the
   check script, and the review source lock (`notebooks/progress-subgoal-v1-review-r1/review-source-lock.json`). Each
   should be derived from the WS3 v1 r2 scripts the same way, but those targets sit outside this track's file scope
   (`scripts/`, `notebooks/`). The lock must bind every file in `authority.REQUIRED_SOURCE`, including `probes.json`.
7. **Full connected fault matrix.** Only the normal run is rehearsed here. Before the lock, the derived equivalents of
   WS3's slow-pass, cancellation, monitor-loss, storage and late-reply faults need running. WS3's slow-pass latencies
   (0.13 s and 0.06 s) were sized for 2,500 calls per pass; they need re-checking at 2,790.
8. **A fresh-clone check** of the frozen commit (WS3 r2's procedure).
9. **Approvals**: source approval and a separate compute authorization naming the limits in §11.

## 13. Open questions

1. **Third-arm trigger.** Are the three conditions in §2 the right ones, and is reading only WS3's withheld-partition
   evaluator output correct?
2. **Smaller gates.** Is the 2% cap acceptable on gates with 116–126 contexts, where only two over-claims are
   tolerated? Or should those gates also get larger opportunity targets, as false "no progress" did, at the cost of
   headroom (now about 1.26×)?
3. **Headroom.** Is about 1.26× (allowances) acceptable for one session? The alternative is to trim the per-family
   targets toward the floors.
4. **Packaging location.** Should the package scripts be derived under `scripts/` by the main session (outside this
   track's scope), or kept as package modules as the runtime is?
5. **Abandonment floor.** Should abandonment after disconfirmation (30 questions) become a readiness condition of its
   own?
6. **Previously open, carried over:** real-game transfer (out of scope as stated in §1); a shared subgoal schema;
   intermediate frames; and contract fields in `transition_evidence_v2`.
