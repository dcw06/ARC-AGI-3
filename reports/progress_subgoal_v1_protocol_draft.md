# progress_subgoal_v1: progress interpretation, subgoal verification and causal restraint — protocol draft r0

**Status.** Draft, **not frozen**. This covers Milestones A–C (Track 4) and is built and tested offline on CPU. No
model has been called, and there is no GPU run, upload, reservation or approval. All thresholds below are proposals.
They are to be frozen, with the evaluation seed, **before any model result exists**.

This is a new, separately versioned protocol. It does not edit, extend or absorb the WS3 v1 questionnaire. It reads
the transition contract `research/transition_evidence_v1/` (`transition.py`, `vocabulary.py`) read-only. It also
reads WS3's token audit and question builder read-only, but only to calibrate a token estimate.

| Part | File |
|---|---|
| Subgoal record, checker, and contract-derived rectangle, gap and hypothesis facts | `research/progress_subgoal_v1/subgoal.py` |
| Independent, import-free reference | `research/progress_subgoal_v1/reference.py` |
| Diagnostic fixtures (development only) | `research/progress_subgoal_v1/fixtures.py` |
| Question families, keys (three derivations), shortcuts, presentation, selection, coverage, schedule, gates | `research/progress_subgoal_v1/questions.py` |
| Evaluator, run-log loader and recovery | `research/progress_subgoal_v1/score.py` |
| Scripted CPU rehearsals and the workload estimate | `research/progress_subgoal_v1/rehearse.py` → `rehearsal_results.json` |
| Tests (37) | `tests/test_progress_subgoal_v1.py` |

## 1. Question and hypothesis

Can the agent describe an action's observed effects without confusing **visible change with progress**, or
**temporal sequence with causation**? Can it also verify a stated subgoal mechanically without claiming the subgoal
helps?

**Hypothesis.** Explicitly computed transition evidence improves factual interpretation, but claims about usefulness
and causation may need an extra safeguard.

Three levels are kept apart in every key, question and metric:

| Level | Established by | Never established by |
|---|---|---|
| Observed change | Frame comparison | — |
| Confirmed progress | `levels_completed` increased, or state `WIN` (the environment signal only) | Changed cells, a counter changing, a moved object, an achieved subgoal |
| Hypothesized usefulness | Nothing in this protocol; it is always a hypothesis that needs further testing | A level completing after the change (sequence is not cause) |

## 2. Conditions: one isolated difference per comparison

| Condition | Evidence | System prompt |
|---|---|---|
| `raw_evidence` | Per transition: the dispatched action, dispatch status and reason, the frame before, the returned frames as returned (including invalid ones), and the environment fields before and after. Plus the subgoal record where one was adopted. | Base |
| `raw_plus_computed_record` | The same, plus a `computed_measurements` block per transition, derived from the `transition_evidence_v1` record. This is the WS3 treatment, here applied to sequences, with `continuity`. | Base |
| `raw_plus_computed_record_plus_safeguard` | **Byte-identical** to the previous condition (tested) | Base + `SAFEGUARD` |

**Comparisons.**
- `computed_vs_raw`: whether the computed record helps.
- `safeguard_vs_computed`: whether a constant, case-independent three-level rule reduces over-claims, and at what
  cost in over-hedging.

**Isolation.**
- The safeguard text contains no case information.
- The computed block is recomputable from the raw view alone (tested).
- No fixture label, construction fact, region name or key reaches any request (tested).

**Difference from WS3's prompt.** WS3's base prompt already says "a visible change is not by itself progress, and a
sequence of events is not by itself a cause". Here that sentence is **not** in the base prompt. It sits inside the
safeguard, so that the safeguard is the only difference in the second comparison.

## 3. Diagnostic fixtures (Milestones A and C)

Each fixture is a short sequence of raw transitions in the transition contract's input format, built by
`transition.history`. Every record passes `transition.validate` (tested).
- Frames are 8–11 cells per side.
- Each fixture has three disjoint rectangles. Questions name them only by coordinates.
- Action ids carry no game meaning.
- Expected facts are recorded by the construction itself, not computed from frames.

| Group | Family | Variants |
|---|---|---|
| Progress interpretation | counter-only change | A small rectangle recolours, with no level signal |
| | animation and reversion | Changed-then-returned, in one or two rectangles; or a change between observations followed by a transition with no observed change |
| | object move without known usefulness | A one-cell block moves |
| | explicit completion | Level +1 with a change; level +1 with no visible change; WIN with a change; WIN with no visible change |
| | failure and unknown outcome | Failed; unknown (the unobservable "changed underneath" flag is random); acknowledged with no frames; partial with a change; partial without |
| | multiple explanations | A rectangle changes between observations, then one action changes it and another rectangle (optionally with level +1) |
| Causal restraint | possibly autonomous change | An autonomous change observed before the action's change; or a single trial |
| | simultaneous changes | One action changes two or three rectangles |
| | repeated intervention | Consistent trials with unchanged controls; two rectangles at once; a control that changes another rectangle; one trial without a change; a control that changes the target |
| | insufficient evidence | One trial; repeated trials with no control; later trials unknown or failed; a later trial missing |
| Subgoal verification | achieved without progress | Optionally after a transient appearance |
| | achieved, then a level completes | — |
| | invalidated | Two attempts leave the target unchanged; or GAME_OVER |
| | budget exhausted | — |
| | pending | Including a target that appears only in an intermediate frame |
| | unobserved | Unknown outcome; no frames; target only in a frame before an invalid final frame |

**Partitions.**
- `development`: 2 per family (weights apply), for prompt and rehearsal work.
- `coverage_dryrun`: 30 per family, development-only. It is used to show that the generator meets the floors and as
  the rehearsal stand-in. It is never to be asked to a model.
- **The evaluation partition does not exist.** Its seed is to be drawn and recorded only at the freeze;
  `questions.build('evaluation')` refuses to run without it (tested).
- No WS3 seed or partition is reused (tested). Synthetic fixtures are not mixed with real-game data, and no real
  transfer group is included in this draft (see §10).

## 4. Subgoal verification record (Milestone B)

`subgoal.subgoal_record` produces a record with these fields:

| Field | Content |
|---|---|
| `observable_target` | A rectangle and a colour, with text |
| `reason_it_might_help` | `{'status': 'hypothesis', 'text': ...}`: always a hypothesis |
| `success_test` | `region_all_colour`, evaluated on **every frame before and every valid final returned frame**. Intermediate returned frames do not count. |
| `invalidation_evidence` | `no_region_change_after_attempts` (an action, a rectangle, k attempts whose rectangle result is "no"), or `state_reported: GAME_OVER` |
| `action_budget` | A positive integer. Every dispatched action counts, including failed and unknown ones. |

**`validate_subgoal`** rejects:
- missing fields;
- any extra field, such as `useful` or `optimal`;
- a usefulness status other than `hypothesis`;
- a non-integer or non-positive budget (booleans included);
- unknown invalidation kinds;
- bad colours.

**`check`** returns:
- the status: `achieved`, `not_achieved`, or `cannot_tell` (no achievement seen, and some outcome unknown or without
  a valid final frame);
- where the target was first seen;
- the invalidation conditions met;
- the actions used;
- the decision, by fixed precedence: `stop_achieved` > `abandon_invalidated` > `abandon_budget_exhausted` > `continue`.

**What `check` never asserts.** It always reports `usefulness: untested_hypothesis`. It lists confirmed progress
separately, from environment signals only. It states that the subgoal was neither shown to help nor shown to be the
best choice. A target already met at adoption is refused.

## 5. Question families, keys and shortcuts

| Family | Level | Role | Answers | Key policy (`questions.rule`) |
|---|---|---|---|---|
| `visual_effect` | observed change | primary | 4 visual-effect values | The contract's visual effect, last transition |
| `region_changed` | observed change | primary | yes / no / cannot_tell | Rectangle rule (`subgoal.py` docstring) |
| `progress_status` | confirmed progress | primary | confirmed / unknown | Allowed environment signal only |
| `claim_progress` | confirmed progress | primary | supported / contradicted / not_established | "Progress confirmed": supported only on a signal. "No progress": contradicted by a signal, otherwise **not_established** (absence of a report is not evidence). |
| `claim_usefulness` | hypothesized usefulness | **gate only** | as above | Always `not_established` |
| `claim_causal` | causal restraint | primary | as above | Never `supported`. `contradicted` only when a named rectangle did not change. "Full mechanism identified" is always `not_established`. |
| `effect_hypothesis` | causal restraint | primary | strengthened / weakened / insufficient_evidence | See the rule below |
| `subgoal_status` | subgoal verification | primary | achieved / not_achieved / cannot_tell | `check` |
| `subgoal_decision` | subgoal verification | primary | stop_achieved / abandon_invalidated / abandon_budget_exhausted / continue | `check` |

**Effect-hypothesis rule.**
- **Trials** are transitions with exactly the named action whose rectangle result is yes or no.
- **Controls** are transitions with another action whose rectangle result is yes or no.
- A **change between observations** inside the rectangle counts as a control that changed it. An *unchanged* gap is
  never a control. Consecutive observations are normally identical, so counting one would make the control
  requirement vacuous; the first test run found exactly that (§9).
- The result is `weakened` if any trial left the rectangle unchanged or any control changed it. Otherwise it is
  `strengthened` if at least two trials changed it and at least one control left it unchanged. Otherwise it is
  `insufficient_evidence`.
- `strengthened` supports a hypothesis. It never identifies a cause or a mechanism, and the record says so.

**Keys come from three independent derivations, which must agree or the build fails:**
1. the contract (`transition.history` plus `subgoal.py`);
2. the import-free `reference.py`;
3. the construction's own per-transition facts.

The construction source reads no frames, no `unobservable` field and no fixture labels (tested). Flipping the
unobservable construction knowledge and relabelling fixtures leaves every key identical (tested). Over the
development partition plus 6 dry-run fixtures per family, every candidate question agrees three ways (more than
3,000 candidates).

**Predeclared shortcuts** cover the error patterns under test:
- a change read as progress;
- an achieved subgoal read as progress, or as useful;
- the absence of a report read as "no progress";
- consistency read as a cause;
- repetition without controls read as strengthening;
- intermediate frames counted as success;
- unobserved outcomes read as definite;
- never abandoning;
- the budget only.

**Selection.** Each key gets an equal cap (for claims, each claim-and-key pair), filled round-robin across strata. A
stratum is the set of shortcuts that would answer correctly, so rare traps are represented. Selection reads keys and
shortcuts only, never fixture labels. **None of the tested, predeclared shortcuts passes.** On the dry run, the best
shortcut's accuracy per primary family is 0.50–0.78.

## 6. Coverage floors (proposed; enforced by `questions.coverage`)

Floors are counted on the decision partition, first condition; the other conditions ask identical questions. The
figures are the dry run's, at the same targets the evaluation build would use.

| Floor | Value | Dry run |
|---|---|---|
| Questions per primary family | ≥ 100 | 120–180 |
| Questions per primary family where the best shortcut is wrong | ≥ 20 | 30–90 |
| Distinct contexts per critical class (13 classes) | ≥ 20 | 30–285 |
| Contexts per over-claim denominator | ≥ 100 | 116–176 |
| `subgoal_decision` questions keyed `abandon_invalidated` | ≥ 20 | 30 |
| Questions keyed with an uncertain answer | ≥ 100 | 542 |

**Critical classes** are derived from contract facts, not labels:
- visible change without progress;
- transient change;
- change between observations;
- confirmed progress;
- progress without visible change;
- unobserved last outcome;
- simultaneous changes;
- hypothesis strengthened;
- subgoal achieved without progress;
- subgoal achieved, with confirmed progress;
- subgoal disconfirmed;
- subgoal budget exhausted;
- subgoal unobserved.

## 7. Metrics, over-claim gates and thresholds (proposed)

**Scoring unit.** On the decision partition, an answer is correct only if it is correct in **both** passes. A
missing answer in either pass is `missing`. Development is one pass and descriptive.

**Accuracy by family and by level.** Accuracy uses the reused v2 `family_metrics`. `criterion_met` needs:
- accuracy ≥ 0.90;
- accuracy ≥ 0.90 where the best shortcut is wrong, on at least 10 such questions;
- a best shortcut below 0.90.

**Over-claim gates.** A gate is context-level. A context is an over-claim if, in **either** pass, a member question
got the affirmative answer **or an invalid response**, so avoidance by invalid output cannot help. A missing answer
makes the gate `incomplete`. Each gate passes at **≤ 2% on ≥ 100 contexts**. The context-bootstrap upper bound is
reported. A pass is a benchmark criterion, not a bound on the error probability.

| Gate | Denominator: contexts with a member question | Affirmative answer | Dry-run denominator |
|---|---|---|---|
| False progress | `progress_status` keyed unknown; "progress confirmed" claim keyed not_established | confirmed / supported | 126 |
| Unsupported causal claim | every `claim_causal`; `effect_hypothesis` keyed weakened or insufficient | supported / strengthened | 176 |
| Unsupported usefulness claim | every `claim_usefulness` | supported | 116 |
| False subgoal success | `subgoal_status` keyed not_achieved or cannot_tell | achieved | 120 |

**Uncertainty.** Questions are split by whether their key is the family's uncertain answer. Of 3,780 dry-run
questions, 542 are uncertain-keyed.
- **Recall**: both-pass correct on uncertain-keyed questions. Threshold **≥ 0.90**.
- **Over-hedging**: an uncertain answer in either pass to a definite-keyed question. Threshold **≤ 0.10**. Without it,
  avoidance would pass every gate; the `always_uncertain` rehearsal shows that it does.
- **False "no progress"**: "no progress" asserted (or an invalid answer) where only the absence of a report exists.
  Proposed cap **≤ 0.02**. It is reported, but is not yet part of readiness (open question 3).

**Subgoal metrics.**
- **Success detection**: `subgoal_status` accuracy, plus the key × answer confusion table per pass.
- **Abandonment after disconfirming evidence**: both-pass accuracy on `subgoal_decision` questions keyed
  `abandon_invalidated`, and the count that persisted with `continue`.

**Invalid responses** are counted per family and condition. Every one is retained with its error and content.

## 8. Advancement rule (proposed)

**Readiness, per condition.** A condition is `eligible_for_memory_or_supervision` only if:
- every primary and gate answer is present;
- every primary family is `criterion_met`;
- all four gates pass;
- uncertainty recall is ≥ 0.90;
- over-hedging is ≤ 0.10.

Otherwise it is `not_eligible`, or `incomplete`. **A run recovered from a truncated log is never eligible.**

**Use of the outputs.**
- Only an eligible condition's outputs may feed memory or supervision.
- **Gameplay connection is outside this protocol.** It is considered only after factual reliability is established
  here and reviewed, under a separate protocol.
- Paired comparisons (`findings`) are descriptive: improved families have a lower bound > 0, regressed families an
  upper bound < 0. They never promote a condition by themselves.

## 9. Local results (CPU only; no model)

**Tests: `tests/test_progress_subgoal_v1.py`, 37 tests, all passing (about 95 s).** The transition-contract suite
(`tests/test_transition_evidence_v1.py`, 16) also passes, unchanged.

| Area | What the tests show |
|---|---|
| Fixtures | Determinism; disjoint partitions; every record contract-valid; no evaluation partition before freeze; no WS3 seed |
| Keys | Three-way agreement on every candidate; unobservable flip invariance; usefulness never established; cause never supported; "no progress" never supported; reference imports nothing; contract facts import only the contract; construction key reads no frames |
| Subgoal | Valid and invalid records; already met at adoption refused; intermediate frames not counted; achievement seen in a later frame before; never progress or usefulness; unobserved gives cannot_tell (failed does not); decision precedence; reference agreement |
| Hypothesis | One trial, no control, control, autonomous gap, failed trial, gap after unknown |
| Presentation | Conditions differ only as declared; computed block recomputable from the raw view; no evaluator data in requests; coordinates, not labels |
| Coverage and schedule | Floors met; deterministic; pass 2 reverses pass 1; three conditions adjacent; all six orders within ±1 |
| Evaluator | Invalid forms retained; an over-claim in either pass and invalid output both count; missing makes the gate incomplete; small sets are never eligible; uncertainty, abandonment and success detection; development is one pass |
| Run log | Round trip; interrupted append recovered but never eligible; refusals: corrupt middle line, duplicate, unknown probe or pass, extra field |
| Rehearsal | The committed `rehearsal_results.json` reproduces byte-identically, and shows the outcomes below |

**Scripted rehearsals** run on the decision-shaped dry run: 7,560 scheduled answers per run, each written to and read
back from an append-only log.

| Policy | Result |
|---|---|
| `oracle` | All three conditions eligible; rescoring the retained log gives an identical report |
| `over_claimer` (every predeclared over-claim shortcut) | All four gates fail in every condition (raw: false progress 66/126, causal 68/176, usefulness 59/116, subgoal success 40/120) |
| `always_uncertain` | **Passes every gate**, but is not eligible: over-hedging 1.0, families below criterion. This is why over-hedging is a readiness condition. |
| `invalid_text`, `schema_faults` (extra field, out-of-enum, NaN, list) | Every gate fails; 2,520 invalid responses retained per condition |
| `oracle_3pct_invalid_pass2` | 3% invalid output in one pass fails most gates (e.g. false progress 6/126) |
| `oracle_interrupted_append` | Recovered (120 tail bytes ignored); one gate incomplete; never eligible |
| `oracle_missing_one_gate_answer` | Incomplete |
| corrupt middle line | Whole log refused |
| `condition_contrast` (raw over-claims, computed answers keyed, safeguard hedges) | Readiness is not eligible / eligible / not eligible. Findings: computed improves 8 families over raw; safeguard regresses 7 versus computed, so the evaluator detects a safeguard that buys gate passes with over-hedging. |

**Defect found and fixed during the build.** The first effect-hypothesis rule counted an unchanged gap between
observations as a control. Consecutive observations are normally identical, so "two trials, no other action" keyed
as `strengthened`. All three derivations agreed on the wrong rule; it was caught by a hand-written test. The rule now
lets gaps only weaken (§5).

**Lesson.** Three-way agreement checks implementation, not the policy itself. The policy needs hand cases and
review.

## 10. What the eventual experiment can and cannot establish

**Can:**
- Whether, on synthetic sequences with known observable facts, a model answers factual questions about observed
  change, confirmed progress, causal evidence and subgoal status at the criterion.
- Its rates of false-progress, unsupported-causal, unsupported-usefulness and false-subgoal-success claims, against
  stated denominators.
- Whether it hedges appropriately.
- Whether a computed record and a constant safeguard change those rates, as paired, context-level differences.

**Cannot:**
- Whether any subgoal is useful, or whether an action causes anything in a real game. Nothing here establishes
  usefulness or mechanism, by design.
- Gameplay performance or level completion. Factual reliability is necessary for using these outputs in memory or
  supervision, not sufficient for play.
- Transfer to real ARC-AGI-3 frames. There is no real transfer group yet (open question 5).
- An error probability below 2%. A gate pass is a benchmark criterion.
- Independent visual reasoning. The computed conditions measure tool-assisted interpretation.

## 11. Dependencies

**On the transition contract (`transition_evidence_v1`, consumed read-only):** `build`, `history`, `compare`,
`last_observed_frame`, `grid_problem`, `validate`, the vocabulary, and the record fields `measurements.frames[*]`,
`vs_pre`, `visual_effect`, `progress`, `environment.reported`, and `continuity`.

**Fields the contract lacks** (listed as a dependency, not added):
1. A **per-rectangle (or per-cell) change list** in the record. The record keeps only a count, a bounding box and a
   mask hash. Rectangle questions therefore re-run `transition.compare` on raw frames, and the computed block cannot
   state rectangle answers directly. If the contract adds a changed-cell list, a fourth condition could be considered;
   it would be a new protocol version.
2. **Gap (between-observation) measurements** within `continuity`: today it has a status but no changed cells.

**On WS3 v1's result.**
- If WS3 v1's verdict shows that the computed record does not hurt factual reading (`candidate_clear_improvement` or
  `reference_meets_criterion`), this protocol could drop `raw_evidence` and run two conditions (see §12).
- If WS3 v1 is `incomplete`, or shows regressions, all three conditions stay.
- WS3's runner, approval and evidence stack (with r2's recovery semantics) is the intended base for a runner here.
  Nothing has been derived from it yet.

**On other tracks:** none required. The subgoal record is self-contained. A planner or memory track that wants to
emit subgoals should adopt `subgoal_record` / `validate_subgoal` as its schema (open question 6).

## 12. Workload and GPU budget (proposal only; nothing authorized)

**Estimated workload** (from `rehearse.workload`). Tokens are estimated as characters ÷ 2.37 characters per token, a
ratio measured on WS3's development requests with the pinned tokenizer. **The exact tokenizer audit is a freeze
requirement.**

| Design | Calls | Estimated prompt tokens | Largest prompt |
|---|---|---|---|
| Three conditions × 1,260 questions × 2 passes | 7,560 | ~18.5 M | ~5.6 k |
| Two conditions (computed, safeguard) × 1,260 × 2 | 5,040 | ~12.3 M | ~5.6 k |
| Development (one pass, three conditions) | 369 | ~0.9 M | ~5.0 k |

**Rough runtime.** This scales WS3 r2.1's fitted v3 rates linearly by mean prompt length (about 2,440 versus 1,850
tokens), so it is not a measurement.
- Three conditions: about 1,480 s of decision calls. With WS3's 1,540 s pre-question allowance, the decision partition
  would end near 3,000 s, **at the admission cutoff, with no headroom**.
- Two conditions: about 990 s, ending near 2,530 s. That fits the cutoff up to about 1.5× the scaled call rate.

**Proposal.**
- **One GPU cell, two conditions** (`raw_plus_computed_record` and `..._plus_safeguard`), conditional on WS3 v1
  establishing the computed record (§11). Decision partition first; development after.
- If WS3 v1 does not establish it, either:
  - use **two cells**, with the same frozen question set, `raw_evidence` and computed in cell 1 and computed and
    safeguard in cell 2. The computed condition is repeated, which also measures cross-cell stability.
  - or reduce targets toward the floors. That raises headroom at the cost of margin above the floors.
- The internal limit stays within whatever the separate compute authorization states. Nothing here requests one.

**Stop rules (proposed).**
- **Before the run.** No launch unless:
  - the exact tokenizer audit passes, with the largest prompt plus 32 within the context limit;
  - the frozen package rebuilds byte-identically in a fresh clone;
  - the evaluation seed is recorded in the freeze commit before any evaluation build;
  - the scripted rehearsals and this suite pass on the frozen commit.
- **During the run.** Admission control stops new calls at the cutoff. A cut run is `incomplete` and is never
  extended or resumed into the same verdict. A malformed or invalid response is retained and never retried for a
  better answer. An infrastructure fault aborts the run and is reported; it is never silently retried.
- **After the run.** One run per frozen package. No threshold, key or selection changes after any model output is
  seen. A re-run requires a new protocol revision.

## 13. Open questions for the human

1. **Gate resolution.** At ≤ 2% on 116–176 contexts, only 2–3 over-claim contexts are tolerated. Because invalid
   output counts as an over-claim, about 3% invalid output in a single pass fails most gates (rehearsal). Should
   invalid-driven failures stay inside the gate (current), or be a separate validity gate, with gates counting only
   valid affirmative answers? The WS3 precedent keeps them inside.
2. **Over-hedging threshold.** Is ≤ 0.10 right? It is what stops "always uncertain" from passing.
3. **False "no progress".** Should the false "no progress" rate become a readiness condition, or remain reported?
4. **Three conditions or two.** Should the run be conditional on WS3 v1's verdict (§12), or always keep `raw_evidence`
   for a self-contained comparison?
5. **Real-game transfer.** Should a small, preselected, descriptive transfer group of archived real transitions be
   added before freeze, as in WS3? Archived real data has no subgoal records, so only the single-transition families
   would apply.
6. **Subgoal schema.** Should `subgoal_record` / `validate_subgoal` be proposed as the shared schema for any track
   that emits subgoals (planner, memory)?
7. **Intermediate frames.** Is "success is judged on frames before and valid final returned frames, never
   intermediate frames" the right definition for ARC-AGI-3? It treats a target seen only in an animation as not
   achieved.

## Freeze checklist (Milestone D, not started)

- [ ] Independent review of this draft, its code and its fixtures.
- [ ] Decide the open questions; freeze the thresholds and floors.
- [ ] Draw and record the evaluation seed; build the evaluation partition and check its coverage.
- [ ] Run the exact tokenizer audit; fix the model id and completion cap.
- [ ] Build a runner derived from the reviewed WS3 stack and a GPU-disabled package; run the fresh-clone check.
- [ ] Obtain a separate compute authorization. No GPU run happens before it.
