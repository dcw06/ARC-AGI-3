# Evidence-linked memory v1: design and local instrument results (Track 2, Milestones A–C)

**Status: development only.** Everything here runs locally on the CPU. The writers and readers are scripted;
no model was called. Every number below checks that the instruments work. None estimates model quality.

| Part | Location |
|---|---|
| Schema, update rules, mechanical checks, audited store | `research/evidence_memory_v1/schema.py` |
| Synthetic continuous trajectories (development partition only) | `research/evidence_memory_v1/trajectories.py` |
| Independent fidelity checker (imports nothing) | `research/evidence_memory_v1/fidelity.py` |
| Scripted writers and the writer harness | `research/evidence_memory_v1/writers.py` |
| Packages, readers and context pressure | `research/evidence_memory_v1/readers.py`, `render.py` |
| Tables in §8 | `python -m research.evidence_memory_v1.study` |
| Tests | `tests/test_evidence_memory_v1.py` (16), `tests/test_evidence_memory_v1_harness.py` (12) |
| Draft protocol | `reports/evidence_memory_v1_protocol_draft.md` |

The transition-evidence contract (`research/transition_evidence_v1/`) is used read-only. Records come from
`transition.history`. Memory evidence references are record identities (`episode_id`, `action_index`).

## 1. Question and treatment

**Question.** Under a bounded context budget, does evidence-linked memory keep useful information better than
recent raw history, while staying revisable?

**Hypothesis.** Structured memory helps when the relevant evidence has fallen outside recent history. It helps
only if observations and hypotheses stay distinguishable.

**This compares memory packages, not formatting.** The memory package is four things together:
- a writer;
- the audited store and its rules;
- a selection under the budget;
- a rendering.

The raw-history baseline is a recency window of transition records. Under the budget, the two differ in **what is
kept**, not only in how it is written. A result therefore cannot be attributed to the entry format alone.

**The isolated difference in a future comparison.** Only the context package changes. The model, the
instructions, the questions, the decoding and the character budget all stay the same. Packages:

| Package | Contents |
|---|---|
| `recent_raw` (baseline) | The last `WINDOW = 6` transition records. The window is frozen. |
| `state_keyed_raw` (control) | Raw records from the current exact state first, then the most recent others, in the same budget. |
| `memory` | Non-retired entries. Ranked first by how specifically their scope covers the current state, then by last review, in the same budget. |

**Why the control is needed.** It separates "retrieve by current state" from "structured memory". §8.4 shows
why it is required.

## 2. Memory entry

| Field | Values |
|---|---|
| `claim` | Structured: `{action: {action_id, action_data or 'any'}, predicate, value}`. Predicates: `visual_effect` (`no_observed_change`, `changed_then_returned`, `final_frame_differs`) and `environment_event` (`level_completed`, `terminal_state`, `reset_acknowledged`). The readable text is derived from the structure (`claim_text`). |
| `kind` | `observation` or `hypothesis`. Predictions and goals are not memory entries in v1. |
| `evidence`, `counterevidence` | Lists of record identities. |
| `scope` | `exact_state` (level and before-frame SHA-256); `segment` (state-dependent, ends at a reset, level change or terminal state); `object_instance` (level and cell set); `level`; `cross_level` (always tentative in v1). |
| `status` | `tentative`, `supported`, `contradicted`, `retired`. |
| `last_reviewed_step`, `revision`, `supersedes`, `reason` | Integers, an entry id or null, and text. |

**No number other than identifiers, levels, segments, steps and revisions.** A model-generated confidence cannot
be stored. A `confidence` field or any non-integer number is rejected.

**`segment` scope is an addition** to the four requested scopes. It carries state-dependent conclusions, such as
the "tried here without change" working set, so that a reset can invalidate them without touching mechanisms.
It is an open question for review (see the protocol, §7).

## 3. Update rules (the audited store)

- **Operations.** There are four: `add`, `revise`, `retire` and `review`. There is no delete.
- **Every operation records its history.** Each one needs a reason and the expected revision, bumps the
  revision, and appends a full before/after copy to the audit trail.
- **The trail is complete.** `replay(audit)` rebuilds the entries, and the checker detects an edit that has no
  audit row.
- **No silent overwrite.**
  - Adding an existing id fails.
  - A stale expected revision fails.
  - A kind never changes: retire the entry and add a new one with `supersedes`.
  - A retired entry is never revised.
- **Counterevidence is append-only.** Evidence may shrink only together with a change of scope or claim.
- **Resets and level changes delete nothing.** They make live `segment` entries stale, and those must be retired.

## 4. Mechanical checks (`schema.check`; codes are stable)

| Code | Rule |
|---|---|
| `observation_not_reconstructable` | Every record an observation cites must show the same action, value, level and exact state. |
| `unknown_outcome_as_evidence` | A failed, unknown, missing or indeterminate outcome never supports or contradicts a claim. |
| `scope_violation` | Any of: an observation beyond its exact state or with 'any' arguments; evidence outside the claimed scope (for example a level-1 rule citing only level-0 records); a cross-level mechanism marked supported. |
| `overgeneralization` | A hypothesis is `supported` beyond its exact state only from at least two distinct states. With 'any' arguments, it also needs at least two distinct argument values. **Three failed clicks in one state can never become a supported "clicking never works".** |
| `counterexample_ignored`, `contradiction_unaddressed` | An in-scope conflicting record, or one that is listed, while the status is still live. |
| `stale_state_dependent` | A live `segment` entry after its segment ended. |
| `dangling_reference`, `counterevidence_mismatch`, `status_rule`, `numeric_confidence`, `shape`, `vocabulary` | Structural rules. |

**When the check runs.** It uses the records seen by the entry's `last_reviewed_step`, which is how the write gate
uses it. An end-of-trajectory audit passes the final step instead.

**Why the end-of-trajectory audit matters.** A writer that never revisits an entry must not escape its
counterexamples. The first draft of the checker had this gap, and the gated over-claiming writer exposed it.

## 5. Diagnostic trajectories (synthetic; one continuous episode each)

**How they are built.** Each trajectory is built in the raw input format of `transition.build` and turned into
records by `transition.history`. Every record passes `transition.validate`.

**Delay.** `delay` places distractor transitions between the relevant evidence and the question, or the decisive
later evidence.

**Expectations are kept apart.** Evaluator-only expectations come from the construction and are kept apart from
the raw evidence. A test checks that the raw evidence carries no family label, answer or "confidence".

**Two independent derivations.** The checker's `gold` answers are derived independently from the records, and
they equal the construction-derived answers for every question.

| Family | What it tests |
|---|---|
| `early_crucial` | An effective click in state S0, then distractors, then a reset back to S0. **Retention.** |
| `supported_then_contradicted` | One action changes the frame in two states, then does not in a later one. **Revision.** |
| `similar_states` | Two states that differ in one cell, with the same action giving different outcomes. **Exact-state scoping.** |
| `coordinate_specific` | Three coordinates do nothing and a fourth changes the frame. **No "clicking never works".** |
| `reset_keeps_mechanism` | A reset changes the state but not the level-scoped mechanism. **Knowledge kept; segment entries retired.** |
| `level_change` | A rule supported in level 0 fails in level 1. **No silent universalisation.** |
| `unknown_outcome` | A failed dispatch and an unknown outcome. **No factual claim from them.** |

**Partitions.** Only a development partition exists (seed `evidence-memory-v1-development`). An evaluation
partition is deliberately not implemented. It must use a fresh seed, be generated after the protocol is frozen,
and stay withheld.

## 6. Independent fidelity checker (`fidelity.evaluate`)

**It is independent.** It imports only `json` and re-derives every record fact itself. On every scripted writer
and trajectory tested, it agrees with `schema.check` on which entries are faulty: 0 disagreements over 420 writer
runs in development, and the agreement is also a test.

**What it reports:**
- **Supported facts retained:** required exact-state observations, held by a non-retired observation whose cited
  records show them.
- **Unsupported claims introduced.**
- **Counterexamples retained.**
- **Contradicted claims:** still live, revised, or never held. "Never held" is reported apart, so a writer
  cannot score by never forming hypotheses.
- **Required mechanisms lost:** after a reset or a level change.
- **Faults:** scope violations, overclaims, ignored counterexamples, stale state-dependent entries, numeric
  confidence.
- **Memory size:** entries and characters.
- **Update cost:** operations by type.
- **Audit consistency.**

## 7. Writer-versus-reader separation

**(a) Writer evaluation.**
- **Inputs and outputs.** A writer sees the records so far and the current memory. It returns text,
  `{"operations": [...]}`.
- **Charging.** Every call is charged: calls, input characters (the new record plus the rendered memory) and
  output characters.
- **Retention.** Unparseable outputs and rejected operations are kept in the log.
- **Optional gate** (a separate treatment). Each `add` or `revise` is checked mechanically before it is stored.

**(b) Reader evaluation.**
- **Inputs.** A reader gets a known-correct memory (the faithful writer's, verified faithful) and a question.
  It returns text: `{"values": [...]}` or `{"choice": action}`.
- **What it never sees.** The answer. A test checks this.

**Scripted writers:** faithful, lossy, overclaiming, scope_violating and invalid.

**Scripted readers:** faithful, status_blind and invalid.

**Oracle readers.** They answer exactly from what a package contains, so they measure **information
availability**, not reading ability.

## 8. Local instrument results (scripted; 42 development trajectories, delays 0/3/8, digest `0d0fff86…d174`)

### 8.1 Writers (fidelity checker, end of trajectory)

| Writer | Gate | Faithful trajectories | Facts retained | Unsupported | Overclaims | Ignored counterexamples | Contradicted still live | Scope violations | Stale | Mechanisms lost | Invalid outputs / rejected ops |
|---|---|---|---|---|---|---|---|---|---|---|---|
| faithful | no | 42/42 | 120/120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 |
| faithful | yes | 42/42 | 120/120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 |
| lossy | no | 10/42 | 45/120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 |
| overclaiming | no | 9/42 | 120/120 | 12 | 32 | 76 | 18 | 0 | 0 | 0 | 0 / 0 |
| overclaiming | yes | 33/42 | 120/120 | 0 | 0 | 15 | 6 | 0 | 0 | 0 | 0 / 134 |
| scope_violating | no | 9/42 | 120/120 | 0 | 0 | 0 | 0 | 14 | 61 | 12 | 0 / 0 |
| scope_violating | yes | 10/42 | 120/120 | 0 | 0 | 0 | 0 | 0 | 61 | 12 | 0 / 51 |
| invalid | no | 10/42 | 90/120 | 0 | 0 | 7 | 4 | 0 | 8 | 0 | 100 / 67 |

**Each faulty writer is caught by its own failure class.**

**The gate blocks bad writes but not omissions.** A claim the writer never revisits stays live. A segment entry
the writer never retires stays stale. A gate alone is not enough; the end-of-trajectory audit is required.

**Writer cost is real.** The faithful writer took 340 calls (one per transition) and 451,799 input characters
over 42 short trajectories. Its input grows with the memory.

### 8.2 Readers given a known-correct memory (120 questions: 78 recall, 42 decision)

| Reader | Unbounded memory | Memory at the budget |
|---|---|---|
| faithful | 120/120 | 112/120 |
| status_blind (treats any entry as fact) | 114/120 | 112/120 |
| invalid | 0/120, all 120 retained as invalid | 0/120 |

**Why answers are lost at the budget.** All 8 lost answers are recall questions:
- 6 ask about a state other than the current one (`similar_states`);
- 2 come from the smallest budget, 553 characters (`early_crucial`, delay 0).

### 8.3 Writer, then an oracle reader (unbounded memory)

| Writer | faithful | lossy | overclaiming | scope_violating | invalid |
|---|---|---|---|---|---|
| Correct | 120/120 | 78/120 | 102/120 | 120/120 | 96/120 |

**What this shows.** A scope violation does not reach the answers of a reader that reads only exact-state
observations; it would reach a status-blind reader. Fidelity therefore has to be measured on the memory itself,
and not only through downstream answers.

### 8.4 Context pressure (oracle availability; 14 trajectories per delay; frozen `WINDOW = 6`)

| Delay | All relevant evidence in window | Full history | recent_raw | state_keyed_raw | memory (budget) | memory (unbounded) | Budget (chars) | Unbounded memory (chars) |
|---|---|---|---|---|---|---|---|---|
| 0 | 1.00 | 1.00 | 1.00 | 1.00 | 0.905 | 1.00 | 606 | 937 |
| 2 | 0.57 | 1.00 | 0.905 | 0.952 | 0.952 | 1.00 | 799 | 1,367 |
| 4 | 0.00 | 1.00 | 0.726 | 0.952 | 0.952 | 1.00 | 818 | 1,838 |
| 8 | 0.00 | 1.00 | 0.536 | 0.952 | 0.952 | 1.00 | 818 | 2,899 |
| 16 | 0.00 | 1.00 | 0.536 | 0.952 | 0.952 | 1.00 | 822 | 4,458 |

In `early_crucial` alone, `recent_raw` falls from 1.00 (delay ≤ 2) to 0.667 (delay 4) and to **0.00 from delay
6**, while `state_keyed_raw` and memory stay at 1.00.

**What this establishes, at the information level only:**
1. **A forgetting problem exists for the recency window in these synthetic cases.** Beyond the window, recent
   raw history loses answers that the full history supports.
2. **Retrieving raw records by the current state recovers the same information as structured memory.** Any
   memory advantage must therefore be shown **against `state_keyed_raw`**, not only against `recent_raw`. The
   plausible advantages are in combining several entries and in revision (contradicted, retired and scoped
   claims). That matches the v3 finding that the model reads single entries well but fails to combine them.
3. **Memory pays for its structure in characters.** An entry line is longer than a record line. At the
   smallest budgets (delay 0), memory loses answers the window keeps.
4. **Selection keyed on the current state misses questions about other states,** for both keyed packages.

**What it does not establish:** anything about a model reading or writing these packages.

## 9. Dependencies on the transition contract (requests, not edits)

| Need | Current contract | What v1 does |
|---|---|---|
| A stable record identifier | `identity` = `episode_id` + `action_index` | Uses the pair as the reference. A string `record_id` would be cleaner. |
| The level of a failed or unknown transition | `environment.reported` is `None`, so `levels_completed_before` is not kept | Carries the level forward and marks it `level_derived`. Request: keep the before-observation's `levels_completed` in every record. |
| Object identity for the `object_instance` scope | None (frames only) | Uses a cell set of action coordinates. Real object instances need perception output (another track). |
| Exact-state identity | `before_frames_sha256` | Uses the last before-frame hash. It is brittle when animations or counters change pixels; see the protocol's open questions. |

## 10. Deviations and notes

- **Interpreter.** Tests ran with Windows CPython 3.11.9, not WSL. The worktree's isolation guard refused WSL
  invocations, and the package and its tests use only the standard library plus the read-only contract.
  `tests.test_transition_evidence_v1` also passes unchanged under this interpreter (16 tests).
- **Base commit.** The worktree started at `f4ee307` and was fast-forwarded to the stated base `c8f4c42` before
  any work.
