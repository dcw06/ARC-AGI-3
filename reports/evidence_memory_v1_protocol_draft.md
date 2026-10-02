# Evidence-linked memory v1: diagnostic protocol (DRAFT, not frozen)

**Status: draft for review.**
- No GPU run, upload, reservation or approval is requested by this document.
- Every threshold and budget below is a proposal.
- The design and local instrument results are in `reports/evidence_memory_v1_design.md`.

## 1. Question and claim boundary

**Question.** Under a bounded context budget, does evidence-linked memory keep useful information better than
recent raw history, while staying revisable?

**This compares context packages, not formatting.** Each package is a writer, a store, a selection and a
rendering.

**What changes between conditions.** Only the context package changes:

| Package | Role |
|---|---|
| `recent_raw` | The baseline: a frozen window of `WINDOW = 6` transitions. |
| `state_keyed_raw` | A required control. |
| `memory` | The treatment. |

**What stays fixed:**
- the model and decoding;
- the instruction frame and the question text;
- the character budget, which is the rendered length of the frozen window for that trajectory.

**Writer calls are charged to the memory condition.**

## 2. Advancement rule

**Never advance because memory is concise or readable.** Advance only in this order. Each stage must pass before
the next one is run.

### Stage 0: instruments (done locally, scripted)

- **Checker.** The independent checker separates faithful, lossy, overclaiming, scope-violating and invalid
  writers, and agrees with `schema.check`.
- **Oracles.** Oracle readers show where information is available.

### Stage 1: does a forgetting problem exist for the model?

- **Setup.** The model reads `recent_raw` and `full_history` on `early_crucial` and `similar_states` at delays
  {0, 4, 8, 16}, with the window frozen at 6.
- **Pass.** The model loses at least 0.15 accuracy beyond the window relative to full history, with the paired
  95% interval excluding 0.
- **Stop.** If not, memory has nothing to fix in this setting. Record the result and stop.

### Stage 2: faithful retention and correction by a model writer

- **Setup.** The model writes memory, one charged call per transition, on fresh development trajectories. The
  independent checker scores it.
- **Proposed floors, all required:**
  - facts retained ≥ 0.95;
  - unsupported claims ≤ 1% of entries;
  - overclaims = 0;
  - ignored counterexamples = 0 in `supported_then_contradicted` and `level_change`;
  - stale state-dependent entries = 0;
  - required mechanisms lost = 0;
  - invalid outputs ≤ 2% of calls (retained and counted, never retried silently).
- **The gate, if used.** Run the gated writer as a separately named treatment. The ungated result is reported
  too.

### Stage 3: does the retained information affect decisions?

- **Setup.** The reader is the model. It is given a known-correct memory (deterministic faithful writer) and,
  separately, the Stage 2 model-written memory. Each is compared with `recent_raw` and `state_keyed_raw` at equal
  budget.
- **Primary target.** Decision accuracy on beyond-window questions.
- **Pass, all required:**
  - memory beats `state_keyed_raw` with the paired 95% interval excluding 0;
  - there is no regression beyond tolerance on within-window questions.
- **If memory only beats `recent_raw`.** The finding is "retrieve by state". It is not "structured memory".

### Stage 4: closed-loop gameplay (later, and not part of this protocol)

- **When.** Only after Stage 3 passes.
- **Where.** Only in situations where the raw baseline was shown, in Stage 1 or by replay, to lose relevant
  information.

## 3. Cases and partitions

- **Development cases.** Development trajectories (seed `evidence-memory-v1-development`) are design material
  only.
- **Evaluation cases.** They come from a new seed, generated after this protocol is frozen, and are withheld until
  the run. Every family is covered at every delay.
- **No other material.** No real-game data, holdout or withheld partition of any other workstream is used.
  Synthetic diagnostics stay separate from real-game data.
- **Proposed size.** 20 trajectories per family per delay (7 families × 4 delays = 560 trajectories). Questions
  are fixed per family (2–4 each).

## 4. Measurements

**Writer** (`fidelity.evaluate`), per trajectory:
- facts retained;
- unsupported claims;
- counterexamples retained;
- contradicted claims still live, revised or never held;
- required mechanisms lost;
- scope violations, overclaims, ignored counterexamples, stale entries;
- size (entries, characters) and update cost (operations, calls, input and output characters);
- invalid outputs and rejected operations.

**Reader**, per question: valid, correct, and the package's characters.

**Analysis.** Paired comparisons by question across packages, with bootstrap intervals over trajectories. Two
passes measure repeatability only.

**Retention.** Every raw output, including invalid ones, is retained with its prompt hash.

## 5. Proposed GPU budget and stop rules (proposal only)

**Basis.** v3 answered 6,054 calls in 701 s of question time, after 819 s of model startup.

| Stage | Calls (estimate) | Proposed cap |
|---|---|---|
| 1: forgetting | 2 families × 4 delays × 20 trajectories × about 3 questions × 2 packages × 2 passes ≈ 1,900 | 1 session, ≤ 1 GPU-hour including startup |
| 2: writer | About 20 transitions × 560 trajectories ≈ 11,000 writer calls, with longer outputs and growing inputs | 1 session, ≤ 2 GPU-hours. Stop at the cap with partial results retained. |
| 3: reader | About 3 questions × 560 trajectories × 3 packages × 2 memories × 2 passes ≈ 20,000 short calls | 1 session, ≤ 1.5 GPU-hours |

**Stop rules:**
- **Technical.** Stop on any of: invalid outputs above 5% in the first 500 calls; a timeout rate above 1%;
  startup above 1,800 s; prefix caching not off.
- **Stage 1.** Stop on no forgetting.
- **Stage 2.** Do not run Stage 3 with model-written memory if any floor fails. Stage 3 with the known-correct
  memory may still run, labelled as a reader-only result.
- **Stage 3.** Stop the memory track if memory does not beat `state_keyed_raw`.

**Requirement.** Each stage needs its own approval, frozen package and evaluation cases.

## 6. What the eventual experiment can and cannot establish

**It can establish:**
- whether the model forgets beyond a frozen window in these synthetic cases;
- whether a model writer keeps evidence-linked memory faithful and revisable;
- whether, at equal budget, a known-correct or a model-written memory changes decisions relative to recency and
  to state-keyed retrieval.

**It cannot establish:**
- performance on real games or with real perception;
- that structure rather than selection causes a gain, unless memory beats `state_keyed_raw`;
- unaided reasoning, since the faithful writer is mechanical;
- token-exact budgets, since characters are a proxy;
- anything about closed-loop level completion.

## 7. Open questions for review

1. **Is the `segment` scope acceptable?** It is a fifth scope for state-dependent conclusions, retired at a reset
   or level change.
2. **Should the first model experiment use the deterministic faithful writer, with the model as reader only?**
   It is cheaper, and it removes writer risk. Stage 2 would then become a separate question.
3. **Should the budget be in characters (now) or tokens?** A tokenizer-based audit on CPU would make budgets
   token-exact.
4. **Writer granularity.** One call per transition, or a batch every k transitions? The choice trades update
   cost against staleness.
5. **Thresholds.** Are the Stage 1, 2 and 3 thresholds above acceptable?
6. **Exact-state identity.** It is the before-frame hash, which is brittle under animations and counters. Should
   a perception-derived state key replace it when one exists?
7. **Contract fields.** Should the contract add a `record_id` and keep `levels_completed` for failed and unknown
   transitions?
