# Evidence comprehension v3: design draft (for review; nothing built, no compute authorized)

**Informed by the v2 result** (attempt `ecv2-65759c16`, `reports/evidence_comprehension_v2_results.md`). v2's
questions and answers, including its withheld partition, are now development material.

## Question

Two narrow questions, kept in separate tracks:

1. **Control.** Does presenting each legal action already joined with its argument requirement raise
   legal-coordinate accuracy to the criterion? Separately: are the remaining errors caused by ACTION6
   appearing in the history (the v2 association), when tested with a matched history alteration?
2. **History (tool-assisted).** If a deterministic tool marks, per entry, whether it left the still-current
   frame with no net final change, can the model then produce the deduplicated set of such actions? This
   measures **tool-assisted reasoning**. Success would not show improved unaided comprehension.

Unchanged scope: no action is chosen and no game is played. Subgoals, hazards, recovery and restarting stay
out.

## Track A: control availability

### Conditions

Each differs from the reference by exactly one registered change.

| Condition | System prompt | Observation |
|---|---|---|
| `A0` (reference) | v2 `control_candidate` prompt (baseline + intersect instruction; v2 best, 0.883) | live fields, v2 baseline history |
| `A1` joined metadata | same as `A0` | `A0` plus one field, `available_actions`: for each id in `legal_actions`, `{"action_id": k, "action_data": "x and y, integers 0 to 63"}` for 6, or `"empty {}"` otherwise. It is derived from `legal_actions` and the control rules only; no history is used. |

`A1` joins two facts the model already reads correctly (v2 components: legal ids 0.992, ACTION6 legality
0.992, coordinate rule 1.000). Only the intersection is joined, so this is a representation change, not an
answer: the target question still asks which *legal* actions require coordinates.

### Matched history alteration (tests the v2 association)

- **Pairs.** Every control context whose history contains ACTION6 while 6 is not legal gets a matched copy.
  In the copy, each ACTION6 entry becomes an entry for a legal simple action, with identical outcome fields
  (status, frame comparisons, level and reset fields) and the same step numbers. Nothing else changes.
- **Why the pairs are clean.** The control questions do not depend on the history, so every key is identical
  across a pair.
- **Where it is asked.** Under both `A0` and `A1`: history as-is (`H+`) against history altered (`H−`).
- **What it estimates.** The effect of ACTION6's presence in the history on control answers, within these
  cases.
- **Status.** A preregistered secondary comparison, with paired counts and a context-bootstrap interval. It
  informs the interference hypothesis; it is not a promotion gate.

### Families

| Family | Role |
|---|---|
| `legal_coordinate_actions` | target (v1/v2 wording) |
| `legal_actions`, `action6_legal` | components (regression check) |

## Track B: tool-assisted cross-entry status

### Conditions

| Condition | History field | Label |
|---|---|---|
| `B0` (reference) | v2 normalized records (`history_candidate`) | unaided |
| `B1` tool status | `B0` plus one per-entry field, computed by a deterministic tool from the shown entries | **tool-assisted** |

The field is `tool_status_on_current_frame`, with these values:
- `"left the still-current frame unchanged"`, when the entry qualifies under v2's frozen rule;
- `"not on the still-current frame"`, when a later entry changed the final frame or had an unknown outcome;
- `"changed the frame"`;
- `"not delivered"`;
- `"outcome unknown"`.

Its description says: "computed by a deterministic tool, not the model".

**What the tool does and does not do.** The tool applies the cross-entry rule, which is v2's bottleneck:
`frame_since_step` 0.45, `qualifying_steps` 0.42, `tried_unchanged` 0.53. The model must still select the
qualifying entries, deduplicate exact actions (coordinates included) and answer in the schema. A second
option would give the tool's final list directly. That would make the target a copy task, so it is excluded.

### Families

| Family | Role |
|---|---|
| `tried_unchanged` | target (v1/v2 wording) |
| `qualifying_steps` | component; expected to become near-copy under `B1`, reported as such |
| `outcome_class`, `observed_effect`, `step_action_match` | components (regression check) |

## Cases

- **Generation.** v2's generation rules and templates (`trajectories.py`) with **new seeds**: a fresh
  withheld partition and a development partition.
- **Enrichment for the interference test.** The case with ACTION6 in history but not legal is enriched:
  about half the control contexts, against 34 of 120 in v2.
- **Enrichment for Track B.** The stale-unchanged and same-frame-repeat templates are enriched, so the
  number of questions where `tried_unchanged` shortcuts are wrong clears the minimum with room to spare.
- **Keys.** Dual keys, as in v2, extended so the independent derivation also recomputes the tool field from
  raw frames. A test checks that the tool field, the primary key logic and the independent derivation all
  agree.
- **Transfer.** The six archived contexts are kept as a descriptive transfer check.
- **Proposed size**, to be fixed before freezing: roughly 160 withheld contexts. Track A: 3 families × 2
  conditions × (1 + the matched copy where applicable). Track B: 5 families × 2 conditions. That is well
  under v2's 8,004 calls.

## Decision rules

These are v2's frozen rules, unchanged unless the review decides otherwise:
- the per-family labels;
- both-correct scoring over two withheld passes;
- the context bootstrap;
- the 0.05 regression tolerance;
- the verdict order.

For Track B, every verdict carries the suffix `_tool_assisted`.

| Result | Next step |
|---|---|
| A: `candidate_clear_improvement` | Joined metadata becomes the control presentation for a later action-selection protocol. |
| A: anything else | Report it. The matched alteration result says whether history interference is supported. |
| B: `candidate_clear_improvement_tool_assisted` | Pursue a tool-assisted agent (plan step 8, second branch). No claim of unaided comprehension. |
| B: `improved_below_criterion_tool_assisted` or `no_clear_improvement_tool_assisted` | Cross-entry selection or deduplication itself is limiting. Investigate before planning. |
| Either track `incomplete` or `mixed` | Report it as such; no promotion. |

## Decisions for the reviewer

1. **Track A reference.** `A0` builds on v2's best condition (the intersect instruction). The alternative is
   comparing `A1` against the plain v2 baseline, which tests joined metadata alone.
2. **Status of the history alteration.** A secondary, non-gating comparison, as proposed; or a gated one.
3. **Tool field granularity.** A five-value status per entry, as proposed. The alternative is a binary
   qualifies/does-not flag, which offloads slightly less.
4. **Transient readings.** Excluded from this narrow comparison (v2's remaining per-entry errors); they would
   be a separate question.
5. **Size and budget** once the case counts are fixed, with the same one-attempt, ≤ 3,600 s shape.
