# Workstream 3: factual transition questionnaire — design draft r2 (for review; not frozen; no compute)

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
| **False progress** | distinct withheld transitions (contexts) with a progress question whose key is not affirmative: `progress_status` "unknown", `claim_progress` "not established", or `level_completion_reported` "no" | an affirmative answer on such a question (`confirmed`, `supported`, `yes`) **or an invalid response**, in **either** pass |
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

**Over-claim denominators:** false progress 152 contexts; unsupported causal claims 120.

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
| Prompt tokens | 10,354,131 scheduled. Frames tokenize densely: r0's character-based estimate of 2.7 M was wrong. |
| Largest prompt | withheld 3,215; development 2,951; transfer 17,520 (64 × 64 frames); all within limits |
| Completion cap | 32 tokens, which covers the longest valid answer (13 tokens pretty-printed) |

**Runtime scenarios.** These are fitted to v2's measured cache-disabled calls on shorter prompts. They include
installation, model startup, pre-question work and finalization, measured and with allowances; the 300 s cleanup
reserve is never spent.

| Scenario | Withheld done | First cell ends |
|---|---|---|
| v2's measured overhead | 1,267 s | 1,443 s |
| Allowances (2× installation, 1.5× startup) | 1,609 s | 1,812 s |
| Allowances, 2× slower | 2,358 s | 2,733 s |
| Allowances, 3× slower, every call at its cap | cut | cut |

**A caution from v3.** Its model startup took 819 s, about 2× v2's, which the 602 s startup allowance does not
cover. Before freezing, the allowance should be revised upward, or v3's measured overhead used. Admission control
protects the deadline in any case; it does not guarantee a complete experiment. Evaluator costs are CPU-only and
fall after the run.

## Next

Independent review of this draft, its code and its fixtures. Then comes the freeze (Milestone D):
- the final protocol;
- a runner derived from the Workstream 1 stack;
- a GPU-disabled package;
- the budget proposal, with a revised startup allowance.

No GPU run happens before separate approval.
