# Workstream 3: factual transition questionnaire — design draft r2.2 (freeze candidate; not frozen; no compute)

**Status.** A revision of draft r0 (`5f54940`, `reports/ws3_questionnaire_design_draft.md`), applying the design
review of r0. It is built and tested offline on branch `ws3-action-effects`, in commit `93142fc`:

| Part | File |
|---|---|
| Question set | `research/transition_evidence_v1/questionnaire.py` |
| Scorer and decision rules | `research/transition_evidence_v1/score.py` |
| Tests | `tests/test_ws3_questionnaire_draft.py` (16), which pass with the 16 transition tests |
| Exact token audit | `scripts/audit_ws3_questionnaire_tokens.py` → `reports/ws3_questionnaire_token_audit.json` |

This is not a launch package: no runner, notebook or approval exists. It is submitted with its code and fixtures for
independent review.

## Changes in r2.2 (review of c8c0fd5)

| Finding | Fix |
|---|---|
| **P2: invalid responses counted as identical answers.** Two invalid responses both lack an answer field, so `None == None` counted as agreement. | Agreement is now counted **only over pairs where both responses are valid**. Each family reports `valid_pairs`, `identical_answers`, `invalid_pairs` and `missing_pairs`, which sum to n. Regressions: different invalid text in each pass for all 120 candidate causal questions now gives 0 valid and 120 invalid pairs; a missing pair is counted separately. |
| **P2: dropping transfer cannot fix completion of the withheld partition.** Transfer runs after both withheld passes. | The budget section now separates **whole-run savings** (development and transfer, which run last) from **primary-completion savings** (only the pre-question overhead and the withheld workload itself). The decision is stated explicitly (see Workload and budget). |
| **P3: superseded definitions and figures remained.** | Reconciled throughout: the false-progress gate includes "not observed"; its denominator is 178; prompt tokens total 10,390,311; the largest transfer prompt is 17,544. |

**Result.** 38 tests pass: 22 questionnaire and 16 transition.

## Changes in r2.1 (review of 93142fc and f7c97e4)

| Finding | Fix | Regression |
|---|---|---|
| **P1: a missing check-family answer crashed the evaluator.** The verdict indexed the confidence interval of an incomplete pair. | The verdict uses paired intervals only for families with complete evidence. A regression-check family with any missing answer is listed in `families_without_regression_evidence`, is **never read as showing no regression**, and withholds promotion (`candidate_improvement_unconfirmed_checks_incomplete`). | Missing one answer in **every family × both conditions × both passes** (40 cases): no crash, and the exact completeness consequence is asserted for each. |
| **P2: an allegedly non-gating check blocked the verdict.** A `level_completion_reported` "no" question is also an over-claim-gate question. | Completeness is declared at separate levels: `primary`, `over_claim_gates`, `checks`, `withheld`, `whole_schedule`, with an explicit policy. **Primary and over-claim-gate questions are required for any verdict**, including the check-family questions that belong to a gate. Other check questions are regression evidence. Development and transfer never change the verdict. | A missing gate question from a check family leaves primary complete, marks gates incomplete, and makes the verdict incomplete, by the stated policy. |
| **P2: the false-progress gate missed claims made without observed evidence.** It excluded `level_completion_reported` "not observed". | "not observed" joins the gate: a "yes" where nothing was observed is a false-progress claim. The denominator rose from 152 to **178** contexts. | Replacing every withheld candidate "not observed" answer with "yes" now fails the gate, counting each context. |
| **P2: the `any_frame_differs` wording disagreed with its key.** For partial observations where no valid frame differs, the literal question ("does at least one valid frame differ?") answered "no", while the key was "cannot tell". | The conservative measurement is kept and the question now states it: "yes" if a valid returned frame differs; "no" only if frames were returned, every one is valid and none differs; otherwise "cannot tell" (failed, unknown, no frame, or invalid frames with no valid change, since an invalid frame could hide a change). | Wording test, plus the partial-observation keys. |
| **The startup allowance.** v3's model startup took 819 s, about 2× v2's. | Budget overheads are now the worse of v2 and v3 per component, and per-call rates are fitted to v3's calls. The startup allowance is now 1,228 s (1.5 × 819). | See Workload and budget. |

**Result.** 36 tests pass: 20 questionnaire and 16 transition.

## Changes from r0 (design review)

| Review point | Resolution in r2 |
|---|---|
| Experiment | **B kept**, with **A** as a possible follow-up. The reference is the raw transition evidence: dispatched action, dispatch status and reason, the frame before, the returned frames exactly as returned, and the environment fields. The candidate is the same plus `computed_measurements`. This measures **tool-assisted factual interpretation**, not independent visual reasoning. |
| The candidate may add only facts computed from the reference evidence | Tested. For every candidate context, rebuilding a transition record from the **reference's view alone** reproduces the candidate's computed field exactly. The computed view omits provenance (the progress source), and no fixture label, construction data or archive name reaches any request (tested). |
| Extraction versus combination | Each question is tagged `extraction_under_candidate`: the computed record states its answer directly for dispatch, availability, any change, final equality, count defined, level completion and progress, but not for the three claim families. Accuracy is reported separately for the two groups. |
| Primary families and checks | **Primary targets:** observation availability, any frame differs, final equals initial, progress status, descriptive claims, progress claims, causal claims. **Extraction checks:** dispatch status, level-completion reported. **Boundary check:** count defined. |
| Criterion | Per gated (primary) family: at least 0.90 accuracy, and at least 0.90 where the family's best predeclared shortcut is wrong, both-correct over two passes. Invalid and missing answers are reported separately. **Promotion requires a demonstrated paired benefit.** If the reference already meets the criterion and passes the gates, the verdict is `reference_meets_criterion` and nothing is promoted. |
| Over-claim gates (decision gates) | Two gates, each context-level, capped at 2%: **false progress** and **unsupported causal claims** (defined in the next section). |
| Coverage floors | Enforced by the build (it fails below them): per primary family, at least 100 distinct questions and 20 where the best shortcut is wrong; at least 20 contexts per critical class; at least 100 contexts per over-claim denominator. |
| Dimension changes | Enlarged to 30 contexts. A dimension change keeps "any frame differs = yes" and "final equals initial = no". Only the cell count is undefined; it does not make every effect field unknown (tested in the transition suite). |
| Repetition | Two withheld passes: pass 1 with the condition order balanced per pair (reference first for half the pairs), pass 2 exactly reversed. Development and transfer are asked once. Reported: both-correct accuracy, accuracy per pass, answer disagreement, over-claims in either pass, and context-level paired uncertainty. |
| Completeness | A missing primary answer makes the verdict `incomplete`. Missing check, development or transfer answers are reported and never change the verdict. Partial results are retained. |
| Transfer | A preselected group of complete archived real transitions (see Cases), labelled as previously exposed development evidence. It is descriptive, outside the gate, and nothing is reconstructed by inference. |
| Information boundary of the keys | The construction-derived key reads only observable expected facts (dispatch, availability, any/final change, counts, events, progress). This is tested by inspecting its source. Construction knowledge that is not observable, such as whether an unobserved action changed the game underneath, never enters a key: flipping it leaves every key identical (tested). A causal claim is `not_established` even where the generator knows the action caused the change. |
| Progress | **Confirmed only by an allowed, supplied signal:** an increase in `levels_completed`, or state `WIN`. Never by more changed cells, a disappearing object, a counter changing, or movement toward a goal. These environment fields are legitimate input: the live agent receives the same fields from the game after every action. |
| Wording | "No shortcut can pass" is replaced by "**none of the tested, predeclared shortcuts passes**". The heuristics cannot rule out every possible shortcut. |

## Over-claim gates (definitions)

| Gate | Denominator | An over-claim is |
|---|---|---|
| **False progress** | distinct withheld transitions (contexts) with a progress question whose key is not affirmative: `progress_status` "unknown", `claim_progress` "not established", or `level_completion_reported` "no" or "not observed" | an affirmative answer on such a question (`confirmed`, `supported`, `yes`) **or an invalid response**, in **either** pass |
| **Unsupported causal claim** | distinct withheld transitions with a causal claim (whose key is never "supported") | a "supported" answer or an invalid response, in either pass. Reported separately for claims that are **unsupported** (not established) and **disproven** (contradicted: no change occurred). |

- **Units.** Rates are contexts with an over-claim ÷ denominator contexts, not ÷ all questions.
- **What is reported:** counts, denominators and a sequence-resampling bootstrap upper bound.
- **Missing answers** make a gate `incomplete`.
- **Pass rule:** a gate passes at a rate of 2% or less on at least 100 contexts.
- **Meaning.** An observed pass is a benchmark criterion. It does not establish that the underlying error
  probability is below 2%.

## Cases

**Pool.**
- Withheld: 30 fixture sequences per construction family (18 families), seed `ws3-questionnaire-withheld`.
- Development: 3 per family.
- A sequence stays in one partition, and raw identifiers are opaque.

**Every key is derived three ways and must agree, or the build fails:**
1. the transition record;
2. the import-free reference;
3. the construction's observable facts.

**Selection.** Each answer key (for claims: each claim-and-key pair) is capped equally, and each cap is filled
round-robin across (visual effect, dispatch status) strata.

**Withheld coverage** (per condition). None of the tested, predeclared shortcuts passes.

| Family | Role | n | Best shortcut accuracy | Questions where it is wrong |
|---|---|---|---|---|
| observation_availability | primary | 120 | failed or unknown as complete | ≥ 20 |
| any_frame_differs | primary | 120 | 0.78 | 26 |
| final_equals_initial | primary | 120 | 0.78 | 26 |
| progress_status | primary | 120 | 0.58 | 50 |
| claim_descriptive | primary | 180 | 0.86 | 26 |
| claim_progress | primary | 120 | 0.83 | 20 |
| claim_causal | primary | 120 | 0.80 | 24 |
| dispatch_status | extraction check | 120 | always acknowledged | ≥ 20 |
| level_completion_reported | extraction check | 120 | 0.75 | 30 |
| count_defined | boundary check | 110 | 0.36 | 70 |

(Exact figures for every family are in the coverage report from `questionnaire.coverage`.)

**Critical classes** (distinct withheld contexts):

| Class | Contexts |
|---|---|
| failed dispatch | 56 |
| unknown outcome | 58 |
| acknowledged, missing observation | 46 |
| transient change | 76 |
| final-frame difference | 175 |
| progress without visible change | 30 |
| visible change without progress | 196 |
| dimension change | 30 |

**Over-claim denominators:** false progress 178 contexts; unsupported causal claims 120.

**Transfer.** 16 archived transitions were preselected by a written rule: steps 3 and 9 of each first-block
action-effect-history v1 episode, plus every Stage B R8 step. Identical archived transitions are asked once, which
leaves **12**. Each has its pre-action frame, dispatched action, dispatch status, returned frames and retained
environment fields. Keys are derived two ways (record and reference); no construction exists for real
transitions.

## Workload and budget (exact tokens)

These come from the pinned Qwen3-VL tokenizer, in `reports/ws3_questionnaire_token_audit.json`.

| Measure | Value |
|---|---|
| Scheduled calls | 5,616: withheld 2 × 2,500, development 376, transfer 240 |
| Prompt tokens | 10,390,311 scheduled. Frames tokenize densely: r0's character-based estimate of 2.7 M was wrong. |
| Largest prompt | withheld 3,215; development 2,951; transfer 17,544 (64 × 64 frames); all within limits |
| Completion cap | 32 tokens, which covers the longest valid answer (13 tokens pretty-printed) |

**Runtime scenarios (r2.1).** These are fitted to v3's measured cache-disabled calls. Each overhead component is
the worse of the v2 and v3 measurements: installation 141 s, **model startup 819 s**, other pre-question work 2 s,
finalization 4 s. The allowances are installation 282 s, **startup 1,228 s**, and 30 s minima for the other two.
The 300 s cleanup reserve is never spent.

| Scenario | Questions start | Withheld done | First cell ends |
|---|---|---|---|
| Worst measured overhead, v3 rates | 961 s | 1,701 s | 1,849 s |
| Allowances, v3 rates | 1,540 s | 2,280 s | 2,454 s |
| Allowances, 2× slower | 1,540 s | **3,019 s (cut in withheld pass 2: incomplete)** | — |
| Allowances, 3× slower, every call at its cap | 1,540 s | cut | cut |

**Headroom.** The withheld decision fits the 3,000 s admission cutoff up to about **2.8× the v3 call rate with the
worst measured overhead**, or **2.0× with the allowances**. Admission control protects the deadline, but a run
cut at the cutoff is reported incomplete.

**Two kinds of saving.**
- **Primary completion.** The withheld decision set runs first. Its completion time depends only on the
  pre-question overhead (installation, model startup, canary) and the withheld workload itself (2 × 2,500 calls).
  Only reducing those, or revising the authorized timing limits, can make it finish sooner.
- **Whole-run completion.** Development (376 calls) and transfer (240 calls) run **after** both withheld passes.
  Dropping them shortens the whole run, and changes nothing about when, or whether, the withheld partition
  completes.

**Budget decision (explicit; for the project owner to confirm or override when approving compute).**
- **Keep the frozen workload,** and accept the stated risk: the withheld partition may be cut, and reported
  incomplete, if the run is slower than about **2.0× the v3 call rate with the allowances** (about 2.8× with the
  worst measured overhead).
- **Rationale.** v3 ran this stack at its actual rates, with a first cell of 1,666 s including an 819 s startup.
  The 2×-with-allowances scenario already combines a 1.5× startup allowance with doubled call latency.
  Trimming the withheld targets to the floors (about 100 per family) would raise primary headroom only to roughly
  2.4×, at the cost of margin above every coverage floor. A longer internal limit would need its own compute
  authorization.
- **If a larger margin is preferred.** The lever for primary completion is the withheld workload or the timing
  limits, not development or transfer.

**Other costs.** Evaluator costs are CPU-only and come after the run. Evidence storage uses the append-only call
log that v2 and v3 exercised live.

## Next

Independent review of this draft, its code and its fixtures. Then comes the freeze (Milestone D):
- the final protocol;
- a runner derived from the Workstream 1 stack;
- a GPU-disabled package;
- the budget proposal, with a revised startup allowance.

No GPU run happens before separate approval.
