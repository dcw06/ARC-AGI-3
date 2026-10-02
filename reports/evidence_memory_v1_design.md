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
| Targeted mutations of faithful memories (test inputs, not a checker) | `research/evidence_memory_v1/mutations.py` |
| Tests | `tests/test_evidence_memory_v1.py` (22), `tests/test_evidence_memory_v1_harness.py` (13), `tests/test_evidence_memory_v1_migration.py` (1) |
| Draft protocol | `reports/evidence_memory_v1_protocol_draft.md` |

**Format version: `transition_evidence_v2`.** This is the frozen format, `origin/transition-evidence-v2` at
`eeb11ba`, reviewed at `6b0a4ff`.
- **Read-only.** The contract is used read-only; records come from `research.transition_evidence_v2.transition.history`
  with no masks.
- **The masked view is never read.** Neither `masked` nor `masks.py` is used; masked evidence in memory would be a
  separately versioned experiment. A test checks this.
- **References.** Memory evidence references stay the record's identity pair (`episode_id`, `action_index`), and
  are resolved through the contract's `identity.record_id`.
- **Migrated in two commits:** a merge, then the adoption.
- **Nothing changed.** The migration changed no byte of any writer prompt, memory text, reader package or table.
  `tests/test_evidence_memory_v1_migration.py` pins the pre-migration digest.

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
| `counterevidence_mismatch` | For every entry kind, each counterevidence reference must be an observed, in-scope record of the same action (arguments per the claim) that contradicts the claim. |
| `status_rule` | Allowed kind/status combinations: an observation is `supported` (or retired) and lists no counterevidence; a `contradicted` hypothesis lists counterevidence; every entry cites evidence. |
| `dangling_reference`, `numeric_confidence`, `shape`, `vocabulary` | Structural rules. Exact fields; vocabulary; strict integers with bool excluded (ids, levels, segments, steps, revisions, action ids and arguments, cells); no non-integer number anywhere; non-empty id and reason; no repeated reference. |

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

**It is independent.** It imports only `json` and re-derives every record fact itself.

**How it checks each entry.**
1. **Structure first.** Every entry is validated with its own strict rules. A malformed entry is reported and not
   interpreted further.
2. **Then every non-retired entry, whatever its kind**, is checked for:
   - **evidence:** exists, was observed, shows the same action and value, and is in scope;
   - **counterevidence:** exists, was observed, concerns the same action, is in scope, and actually contradicts
     the claim;
   - **allowed kind/status combinations;**
   - scope violations, overclaims, ignored counterexamples and stale entries.

A fact counts as retained only if the observation holding it has no fault at all.

**Revision 2 (review finding P1).** Revision 1 validated counterevidence only for hypotheses, and never enforced
kind/status rules or strict types. So:
- **What a reviewer showed.** An observation citing its own supporting record as counterevidence, with the audit
  trail kept consistent, passed as faithful.
- **What the new mutation test found.** Revision 1 missed 285 of the 886 targeted mutations below, for example
  42/42 self-cited counterevidence, 42/42 duplicated evidence, 42/42 empty reasons and 23/42 boolean action ids.
- **How "0 disagreements" overstated independence.** It held only on the scripted writers, which never produce
  these faults.

**Agreement, recomputed** (`python -m research.evidence_memory_v1.study`, 42 development trajectories). "Faulty"
means: structural problems for retired entries; every check, at the final step, for the others.

| Case | Applied | Target entry flagged by schema.py | Target entry flagged by fidelity.py | Identical faulty-entry sets |
|---|---|---|---|---|
| Scripted writer runs (5 writers × gate on/off) | 420 | – | – | 420 |
| Targeted mutations of faithful memories (27 types) | 886 | 886 | 886 | 886 |

**The 27 mutation types:**
- **counterevidence** (6): self-cited, nonexistent, out-of-scope, different action, agreeing, unobserved;
- **kind/status** (6): tentative or contradicted observation; contradicted without counterevidence; live
  despite counterevidence; supported from one state; cross-level supported;
- **vocabulary** (2): kind, status;
- **evidence** (8): flipped value, widened scope, another state, nonexistent, empty, unobserved, duplicated, revived
  stale segment entry;
- **types** (5): `confidence` field, float step, boolean action id, float argument, empty reason.

**Coverage.** Each type is applied wherever the faithful memory has a suitable target. A few types have few
targets: 4 unobserved counterevidence, 6 out-of-scope counterevidence, 6 unobserved evidence and 12 float
arguments.

**What the agreement is about.** It concerns *which entries* are faulty, not the fault class: the two checkers
name classes differently.

**What it reports:**
- **Supported facts retained:** required exact-state observations, held by a non-retired observation whose cited
  records show them.
- **Unsupported claims introduced.**
- **Counterexamples retained.**
- **Contradicted claims:** still live, revised, or never held. "Never held" is reported apart, so a writer
  cannot score by never forming hypotheses.
- **Required mechanisms lost:** after a reset or a level change.
- **Faults:** malformed entries, numeric confidence, unsupported claims, invalid counterevidence, kind/status rule
  violations, scope violations, overclaims, ignored counterexamples, stale state-dependent entries.
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
- **Response schema first (revision 2, review finding P2).** A response is scored only if it matches the schema
  exactly. Anything else is invalid, never correct, and retained with its error.
  - **recall:** exactly `{"values": [...]}`: one or more distinct values from the vocabulary, with `no_evidence`
    only on its own.
  - **decision:** exactly `{"choice": action}`. The action is exactly `{action_id, action_data}`. `action_id` and
    every argument are strict integers (`6.0` and `true` are rejected). The choice must be one of the question's
    candidates.
  - **JSON:** repeated keys and `NaN` / `Infinity` are rejected.

  Revision 1 compared parsed JSON with Python equality, so `6.0` and an answer with an extra field scored as
  correct. 25 regression cases now cover floats, booleans, extra and missing fields, wrong container types,
  vocabulary, duplicates, repeated keys, `NaN`, prose and non-text output.

**Scripted writers:** faithful, lossy, overclaiming, scope_violating and invalid.

**Scripted readers:** faithful, status_blind and invalid.

**Oracle readers.** They answer exactly from what a package contains, so they measure **information
availability**, not reading ability.

## 8. Local instrument results (scripted; 42 development trajectories, delays 0/3/8, digest `0d0fff86…d174`)

**These tables were recomputed with the revision 2 checker and scorer, and are unchanged.** The stricter checks
find nothing new in the scripted writers' memories: no scripted writer produces the newly covered faults. The
scripted readers emit only schema-valid answers or prose.

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

| Need | Contract (`transition_evidence_v2`) | What v1 does |
|---|---|---|
| A stable record identifier | **Resolved:** `identity.record_id` | The index is keyed by each record's `record_id`. A stored reference (the identity pair) is resolved by the contract's own `record_id()`. The independent checker matches references against the pair each record reports. |
| The level of a failed or unknown transition | **Resolved:** `context.levels_completed_before`, present for every dispatch | The level comes from context. The local carry-forward and `level_derived` are removed. Context equals the old carry-forward on every record of the 42 study trajectories, including the failed and unknown ones (tested). |
| Object identity for the `object_instance` scope | None (frames only) | Uses a cell set of action coordinates. Real object instances need perception output (another track). |
| Exact-state identity | `before_frames_sha256` | Uses the last before-frame hash. It is brittle when animations or counters change pixels; see the protocol's open questions. |

## 10. Deviations and notes

- **Interpreter.** Tests ran with Windows CPython 3.11.9, not WSL. The worktree's isolation guard refused WSL
  invocations, and the package and its tests use only the standard library plus the read-only contract.
  `tests.test_transition_evidence_v1` (16 tests) and `tests.test_transition_evidence_v2` (32 tests) also pass
  unchanged under this interpreter.
- **The construction side still uses v1's frame hash.** `trajectories.py` hashes constructed frames with
  `transition_evidence_v1.transition.frame_sha256`, the contract's helper; v2 does not export one. The synthetic
  raws report no available actions, so the v2 available-action fields are `absent`, and Track 2 does not use them.
- **Base commit.** The worktree started at `f4ee307` and was fast-forwarded to the stated base `c8f4c42` before
  any work.
