# Evidence-linked memory v1: Stage 1 protocol, version 1 (DRAFT for review, not frozen)

**Status: draft for review.**
- Nothing is scheduled, reserved or approved.
- The budget in §12 is a proposal.
- Every number here comes from CPU-only measurement on development cases, with exact readers standing in for a
  model. None is a model result.
- The earlier `reports/evidence_memory_v1_protocol_draft.md` stays as history; this document supersedes it for
  Stage 1.

**Instruments:**
| Part | Location |
|---|---|
| Prompt frame, evidence classes, recent controls, scoring, metrics, case plan, runtime estimate | `research/evidence_memory_v1/protocol.py` |
| Offline pinned tokenizer | `research/evidence_memory_v1/tokens.py` |
| Packages under a token budget | `research/evidence_memory_v1/readers.py` (`packages(..., measure=...)`) |
| Tests | `tests/test_evidence_memory_v1_protocol.py` |

## 1. Research question

> Does evidence-linked memory preserve access to action-relevant facts when those facts fall outside the
> recent-history window?

**What Stage 1 tests: memory access and representation.** The memory is written by the **deterministic faithful
writer** (`writers.Faithful`), and the model is **the reader only**.

**What Stage 1 does not test:**
- the model's ability to write faithful memories;
- the model's ability to complete levels.

**What is compared:** context packages (store, selection, rendering) at a common token budget. Prompt formatting
alone is not what is compared.

## 2. Arms

**What is the same in every arm:**
- the model and decoding (temperature 0, a fixed request seed, `max_tokens` 64, prefix caching off);
- one system message (`protocol.SYSTEM`), which describes both package formats;
- the question text and answer form (`protocol.question_text`);
- the response schema, validated before scoring (`readers.validate_response`).

**What differs:** only the evidence block.

| Arm | Evidence block | Budget | Role |
|---|---|---|---|
| `recent_raw` | The last `WINDOW = 6` transition records (frozen) | Defines the budget | Primary: the baseline |
| `state_keyed_raw` | Raw records from the current exact state first, then the most recent others | The common budget | Primary: the retrieval control |
| `memory` | Faithful-writer entries, non-retired, ranked by how specifically their scope covers the current state, then by last review | The common budget | Primary: the treatment |
| `full_history` | Every record of the trajectory | **More context** (unbudgeted) | **Diagnostic reference only, excluded from every primary comparison** |

**The common token budget, per trajectory:**
- **Definition.** It is the token count, under the pinned tokenizer, of that trajectory's rendered `recent_raw`
  block.
- **How the other blocks are filled.** Each other primary arm keeps the longest priority-order prefix whose
  rendering fits the budget (`readers.packages(measure=tokens)`); a test checks this.
- **Its size on development cases.** 119–264 tokens: mean 188 at delay 0, about 251–256 at delays 4–16.

**The tokenizer.**
- **Pinned files.** The pinned Qwen3-VL-30B-A3B-Instruct-FP8 tokenizer files (revision `d9748a51`) are available
  offline in the main checkout (`.cache/phase4-tokenizer`).
- **What is missing.** `transformers` and `tokenizers` are not installed in this environment.
- **The replacement.** `tokens.py` reimplements the parts these prompts use, in pure Python: NFC, the ASCII
  pre-tokenizer, byte-level BPE, special tokens, and the string-only chat template. It refuses anything else.
- **Verification.** It reproduces the committed `transformers` audit (`reports/ws3_questionnaire_token_audit.json`)
  **exactly: 3,116 of 3,116 prompt counts and key-completion counts.**
- **Character proxy, for reference only.** Measured chars per token: `recent_raw` 3.23, `state_keyed_raw` 3.21,
  `memory` 3.42, `full_history` 3.23.

**Prompt sizes** (development dry run, 12 groups per family; mean / max prompt tokens per call):

| Arm | Delay 0 | Delay 4 | Delay 8 | Delay 16 |
|---|---|---|---|---|
| recent_raw | 498 / 573 | 557 / 597 | 558 / 593 | 562 / 595 |
| state_keyed_raw | 498 / 573 | 545 / 578 | 541 / 580 | 550 / 578 |
| memory | 476 / 570 | 521 / 580 | 525 / 570 | 534 / 570 |
| full_history (reference) | 498 / 573 | 664 / 744 | 833 / 907 | 1,175 / 1,249 |

**Why memory is not compared with full history.** Full history grows with the delay and is not under the budget.
That is why it is a reference only.

## 3. Cases

- **Families.** The seven synthetic families of `trajectories.py`: early_crucial, supported_then_contradicted,
  similar_states, coordinate_specific, reset_keeps_mechanism, level_change, unknown_outcome. Each is one continuous
  episode built through `transition_evidence_v2`, with no masks.
- **Groups.** A **group** is one (family, group index). It is generated at every horizon in §6. The construction
  seed depends on family and index, not on the delay, so a group's horizons share their starting state and early
  actions; a test checks this.
- **Proposed size.** 12 groups per family: 84 groups, 336 trajectories, 1,296 scheduled questions per arm. The
  sessions are in §12.
- **Questions per trajectory.**
  - **Family questions:** 2–4 per trajectory, recall and decision, from the construction.
  - **One recent-control question** (`protocol.recent_control`): the latest observed fact whose evidence lies
    entirely in the window. On development it existed in 336 of 336 trajectories.
- **Withheld.** The run uses **newly generated withheld trajectories** (§5). Every development-generated
  trajectory, including all used in this document and in earlier Track 2 reports, stays development material.

## 4. Exclusions (fixed before the run)

| Level | Excluded | Where it goes instead |
|---|---|---|
| Trajectory | Fails `transition_evidence_v2` `verify_history`; or gold ≠ construction answer; or the faithful writer's memory is not faithful under the independent checker; or any prompt fails to encode or exceeds 4,096 tokens | Excluded **before the run**, not replaced, and reported. On development: 0 of 336. |
| Question | Evidence class `mixed` (some evidence inside the window, some outside) | Reported, never primary. On development: only decisions at delay 4. |
| Question | Recall whose truth is `no_evidence` | Uncertainty metrics only |
| Question | Decision questions | Secondary metric only |
| Horizon | Delay 4 | Diagnostic only |
| Arm | `full_history` | Diagnostic reference only |

**Two families have no old-evidence factual question by design:** supported_then_contradicted and level_change
test revision, so their decisive evidence is always recent.
- **Where they count:** recent-evidence accuracy, recent controls, reading accuracy, unsupported claims and
  uncertainty.
- **Where they don't:** the forgetting effect.

## 5. Seeds

| Use | Seed |
|---|---|
| Development (design, dry runs, all reports so far) | `evidence-memory-v1-development` |
| Withheld run cases | `evidence-memory-v1-stage1-withheld/` + nonce |
| Bootstrap | `evidence-memory-v1-stage1-bootstrap`, 10,000 resamples |
| Model requests | One fixed request seed for every call |

**The withheld nonce:**
1. **Choosing it.** A person draws a 32-hex nonce at freeze time (`secrets.token_hex(16)`).
2. **Committing to it.** Only its SHA-256 goes into the frozen protocol.
3. **Generating cases.** The run package generates the cases (groups 0–11, all horizons) after approval.
4. **Not inspecting.** Nobody looks at the answers or the case contents before the run, beyond the automated
   exclusion checks in §4.

`trajectories.build(..., seed=, partition='withheld')` supports this. With its defaults, development output is
unchanged byte for byte; the pinned migration test checks this.

## 6. Horizons

**Delays:** distractor transitions between the relevant evidence and the question, at 0, 4, 8 and 16, with the
window frozen at 6.

**Evidence classes.** The horizon labels evidence by construction. `protocol.evidence_class` then classifies each
question from the records:

| Class | Meaning |
|---|---|
| `recent` | Every observed outcome bearing on it is in the last 6 transitions |
| `old` | None is |
| `mixed` | Some are |
| `none` | No observed outcome bears on it |

**Recent and old questions.** Recent-evidence family questions come from delay 0. Old-evidence family questions
come from delays 8 and 16.

**Why the recent-control question is asked at every delay.** It is a same-trajectory, same-context check of
comprehension of recent evidence.

## 7. Metrics

**Each answer gets these flags** (`protocol.score`):
- **Truth-relative correctness:** against the full record history (`fidelity.gold`).
- **Package-relative correctness:** against what an exact reader of only that package would answer
  (`protocol.package_truth`).
- **Unsupported:** a recall answer asserts a value the package does not support.
- **Abstained:** exactly `["no_evidence"]`.

**Invalid outputs** (schema failures) are retained. They are never correct, unsupported or abstaining, and they
count in the denominators.

| Metric | Definition | Questions in the denominator |
|---|---|---|
| **Forgetting effect `F_arm`** (primary) | Per group, the arm's accuracy on its recent-evidence family recall at delay 0 **minus** its accuracy on its old-evidence family recall at delays 8 and 16; macro mean over families. Relative to the arm's **own** recent accuracy, so poor comprehension does not read as forgetting. | Groups with both (5 families × 12 = 60 groups); 252 questions per arm |
| Factual accuracy, old evidence | Truth-correct / scheduled factual recall, family, old class, delays 8 and 16 | 168 questions, 60 groups |
| Factual accuracy, recent evidence | Same, recent class, delay 0 | 108 questions, 84 groups |
| Recent control at old delays | Truth-correct / scheduled recent-control questions at delays 8 and 16 | 168 questions, 84 groups |
| Decision accuracy, old (secondary) | Truth-correct choices / decisions at delays 8 and 16 with class old or none | 120 questions, 60 groups |
| Reading accuracy | Package-correct / recall questions whose package holds evidence | Arm-specific (dry run: 540–768 of 960 recall questions) |
| **Unsupported claims** | Unsupported answers / all scheduled recall questions | 960 questions, 84 groups |
| **Uncertainty: correct abstention** | Abstentions / recall questions whose package lacks evidence | Arm-specific (dry run: 192–425) |
| **Uncertainty: overuse** | Abstentions / recall questions whose package holds evidence | Arm-specific (dry run: 535–768) |
| Invalid rate | Invalid / all scheduled questions | 1,296 per arm |
| **Cost** | Prompt tokens per call (exact, before the run; server-reported in the run), completion tokens, calls, and seconds per arm. Writer cost: 0 model calls (deterministic), CPU operations reported, and memory tokens unbounded versus budgeted. | Per call and per group |

**Unit of analysis: the group,** not the question. Questions within a group, and a group's horizons, share their
construction, so they are not independent.

**How each metric is computed:**
1. per group;
2. then averaged per family;
3. then macro-averaged over families, with equal family weight (`protocol._group_mean`).

**Intervals.** Paired cluster bootstrap over groups, stratified by family. Between-arm differences pair the same
group and question.

## 8. Availability ceilings (exact readers on development cases, 12 groups per family)

An exact reader answers exactly from its package. These ceilings show **what each package contains**, not what a
model reads.

| Metric | recent_raw | state_keyed_raw | memory | full_history (reference) |
|---|---|---|---|---|
| Forgetting effect | **1.00** | 0.10 | 0.00 | 0.00 |
| Factual accuracy, old | 0.00 | 0.90 | 0.90 | 1.00 |
| Factual accuracy, recent | 1.00 | 1.00 | 0.929 | 1.00 |
| Recent control at old delays | 1.00 | 1.00 | **0.321** | 1.00 |
| Decision accuracy, old | 0.40 | 1.00 | 1.00 | 1.00 |
| Unsupported, abstention overuse | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

**How to read this table:**
- **A forgetting problem exists at the information level.** The recent window holds none of the old facts.
- **`memory` and `state_keyed_raw` hold the same old facts** (0.90 each). So a *model* difference between them on
  old facts measures **representation**, not availability. This is the cleanest contrast in the design.
- **Memory keeps few recent facts about non-current states** (0.321). Its selection serves the current state. In
  the memory arm, the recent control therefore measures selection loss, not comprehension. That is why the
  comprehension precondition (§9) is **package-relative**.
- **The remaining 0.10 gaps** are questions about a state other than the current one (similar_states), which
  current-state selection omits.

## 9. Analysis and decision rules (proposed)

Rules are checked in order. Each step needs the previous one to pass.

1. **Technical validity (§10).** If it fails: no verdict.
2. **Comprehension precondition.** Both conditions must hold:
   - in each primary arm, reading accuracy (package-relative) ≥ 0.80;
   - in `recent_raw`, recent-evidence factual accuracy ≥ 0.80.

   If either fails: stop, with "comprehension, not forgetting".
3. **Forgetting exists for the model.** `F_recent_raw` ≥ 0.15, with the 95% interval excluding 0. If not: stop,
   with "no forgetting in this setting"; memory has nothing to fix here.
4. **Memory preserves access relative to recency.** `F_recent_raw − F_memory` > 0, with the 95% interval excluding
   0. Old-evidence accuracy is reported alongside.
5. **Representation versus retrieval.** `F_state_keyed − F_memory` and the old-evidence accuracy difference are
   reported with intervals.

   | Result | Wording |
   |---|---|
   | Memory higher, interval excludes 0 | Structured representation adds access beyond retrieval |
   | Interval includes 0 | No representation difference detected. Not "equivalent". The finding is then "retrieval by state preserves access". |
   | Memory lower, interval excludes 0 | The memory representation costs access |

6. **Safety, all required for a positive memory verdict:**
   - unsupported-claim rate for memory ≤ `recent_raw` + 0.02 (point estimate), with the interval's upper bound ≤
     +0.05;
   - abstention overuse for memory ≤ `recent_raw` + 0.05;
   - correct abstention for memory ≥ 0.80.

**Advancement.** Stage 2 (a model writer) or any closed-loop use advances only after steps 4 and 6 pass. It is
never advanced for concision or readability.

## 10. Failure rules (technical validity)

**A session is technically complete only if all of these hold:**
- **Calls.** Every scheduled call was answered or retained as failed, with 100% of scheduled groups complete.
- **Partial runs.** A partial run caused by admission control is retained and reported, and gives no verdict.
- **Invalid outputs.** At most 2% per arm. All are retained; none is retried silently.
- **Timeouts.** At most 1% of calls.
- **Prefix caching off.** Verified from server metrics: 0 prefix-cache queries and 0 hits.
- **Inputs.** The package's prompt-token counts match the pre-run exact counts (any mismatch is a technical
  failure), and the evidence and package checks pass (`verify_history`, faithful memory, and the frozen package
  hash).

**Repeatability subsample.** A pre-drawn 10% of groups is asked twice. Agreement is reported and does not gate.

**Early technical stops:**
- invalid outputs above 5% in the first 500 calls;
- model startup above 1,800 s;
- any prefix-cache hit.

**Scheduling.** Calls are interleaved **by group**: all arms and horizons of a group run together. A truncated
session therefore keeps complete, paired groups.

## 11. Runtime estimate (labelled estimates)

**Basis.** The fit is from the v3 live attempt (6,054 cache-disabled calls, same stack):
- 0.0394 s per call;
- 1.42 × 10⁻⁵ s per prompt token;
- 0.00642 s per completion token.

It is recorded in `reports/ws3_questionnaire_token_audit.json`. v3's prompts averaged about 739 tokens; Stage 1's
average 596, so the fit is measured in the same range.

**Overheads:**
- measured: installation 141 s, startup 819 s, other 2 s, finalization 4 s;
- planning allowances: 282, 1,228, 30 and 30 s;
- admission cutoff: 3,000 s.

**Completions.**
- **Typical:** twice the key answer's tokens (mean key 10.6 tokens, maximum 20), capped at 64.
- **Worst case:** every call at the 64-token cap.

**Workload, per full schedule (12 groups per family, four arms):** 5,184 calls, plus the 10% repeat. Estimated
question time at v3 rates is **953 s** (typical) to **2,378 s** (every call at the cap).

**Proposed split into two sessions.** Each session is a balanced replicate: 6 groups per family, all families,
horizons and arms. Each has about 2,592 calls plus about 247 repeat calls.

| Scenario, per session (estimate) | First-cell seconds | Fits the 3,000 s admission cutoff |
|---|---|---|
| Measured overhead, v3 rates | ≈ 1,487 | yes |
| Allowance overhead, v3 rates | ≈ 2,092 | yes |
| Allowance overhead, 2× slower | ≈ 2,614 | yes |
| Allowance overhead, every call at cap, v3 rates | ≈ 2,872 | yes, barely |
| Allowance overhead, 3× slower, every call at cap | ≈ 5,476 | no. Admission control truncates; the session is technically incomplete. |

**A single session holding the whole schedule** would take about 2,614 s under allowance overhead at v3 rates. It
would not fit under a 2× slowdown (≈ 3,658 s). Hence the proposed split.

## 12. Proposed budget and stop rules (proposal only)

**Budget:**
- **Sessions.** Two sessions (A and B), one model startup each.
- **Expected GPU time (estimate).** About 0.8–1.2 GPU-hours in total: two sessions of about 1,500–2,100 s each.
  The exact billed time will again be unknown; only account-counter readings are available.
- **Proposed budget: 1.5 GPU-hours** for A and B.
- **Hard cap: 2.25 GPU-hours,** including at most one retry session, and only for a *technical* failure before any
  answer has been inspected.

**Stop rules:**
- **After session A, only technical failure rules (§10) may stop the experiment.** Outcome metrics are not looked
  at before B, so there is no optional stopping.
- **The analysis runs once,** on A and B pooled, after both are technically complete.
- **A technically incomplete session** may be retried once, within the hard cap. If the retry also fails, no
  verdict is given.

**Requirement.** Each session needs explicit approval, the frozen protocol, the committed nonce hash and the
frozen package.

## 13. What Stage 1 can and cannot establish

**It can establish:**
- whether the model forgets facts outside a frozen 6-transition window, on these synthetic cases;
- whether, at a common token budget, faithful evidence-linked memory or state-keyed retrieval preserves the model's
  access to those facts;
- whether the memory representation helps, hurts or makes no detectable difference relative to raw records with
  the same availability;
- each arm's unsupported-claim and abstention behaviour.

**It cannot establish:**
- anything about model-written memory, since the writer is deterministic;
- level completion, or closed-loop behaviour;
- real games or real perception;
- facts about non-current states under current-state selection (a known limitation of both keyed arms, §8);
- equivalence, when an interval includes 0.

## 14. Before freezing (implementation items, not yet done)

1. **The run package.** It needs:
   - a request builder over `protocol.reader_messages`;
   - a call log with server token counts and prefix-cache metrics;
   - group-interleaved scheduling and admission control;
   - an evaluator over `protocol.rows` and `protocol.metrics`, with the stratified cluster bootstrap.
2. **Exact prompt-token counts with `transformers`** in the pinned environment: one cross-check of `tokens.py` on
   the Stage 1 prompts. `tokens.py` already matches the WS3 audit exactly.
3. **The withheld nonce** drawn and its hash committed. The case-exclusion checks run automatically.
4. **Human review** of the thresholds in §9 and the budget in §12.

## 15. Open questions for review

1. **Thresholds.** Are 0.80 for comprehension, 0.15 for forgetting, and +0.02 / +0.05 for the safety margins
   right?
2. **Primary contrast.** Should memory versus `state_keyed_raw` (representation at equal availability) be co-primary
   with memory versus `recent_raw`? Or should it stay secondary, as drafted?
3. **Selection for non-current states.** Should a second memory selection be added as an arm, for example
   including the most recent non-current-state entries? It would trade budget for recent facts about other states,
   but it adds an arm.
4. **Repeatability.** Is one pass plus a 10% repeat acceptable, instead of two full passes? v1–v3 passes were
   identical.
5. **Group count.** Are 12 groups per family enough? The forgetting effect uses 60 groups. The expected baseline
   forgetting is large at the information level, but the memory-versus-retrieval contrast may be small.
