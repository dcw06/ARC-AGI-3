# Evidence comprehension v3: protocol revision 2 (for review; no compute authorized)

**Status.** The question set, independent keys, conditions, scorer and decision rules are built, frozen and
tested offline (23 regressions). The question set is unchanged from revision 1, which is preserved at
`reports/evidence_comprehension_v3_protocol_r1.md` (`b9ac66f`). No model has been called. Still to come: the runner adaptation, the
GPU-disabled package and the budget proposal. No GPU run is authorized.

This revises the design draft `reports/evidence_comprehension_v3_design.md` (`2eec54f`), following the review of
that draft.

**Informed by the v2 result** (attempt `ecv2-65759c16`). v2's questions, including its withheld partition, are
development material. No v3 observation repeats any v1 or v2 observation; the build checks this.

## Changes in r2 (review of b9ac66f)

**Completeness is separated into three levels, and the policy is stated.** In r1, promotion used only original
questions, but the single `withheld_status` also counted counterfactual questions. A missing counterfactual answer
could therefore show `withheld_status: incomplete` alongside promotion verdicts. That contradicted r1's statement
that any missing withheld answer prevents promotion. The scorer now reports:

| Level | Complete when | Effect |
|---|---|---|
| Primary, per track | every withheld original-variant question of that track is answered in both passes | decides that track's verdict; incomplete makes the verdict `incomplete` |
| Secondary: history alteration | every withheld alteration pair (original and counterfactual, control track, both passes) is answered | none on any verdict; an incomplete comparison is reported as incomplete, never as evidence either way |
| Withheld schedule | every withheld question in both passes | reported |
| Whole schedule | every scheduled question under the repetition policy | reported |

**Policy.** The history alteration is non-gating. A complete primary result **may** support promotion when the
secondary comparison is incomplete. Each track's verdict depends only on its own primary completeness.

Regressions:
- a missing original answer, in either pass and for either track, makes only that track incomplete;
- a missing original answer in an altered context also leaves the secondary comparison incomplete;
- a missing counterfactual answer, in either pass, leaves both verdicts to the primary questions, marks the
  secondary comparison incomplete, and marks the withheld schedule and whole schedule incomplete;
- a missing development answer affects only the whole schedule.

## Changes from the draft (review of 2eec54f)

1. **Counterfactual histories are consistent and labelled.**
   - A matched variant replaces every ACTION6 event in the whole trajectory, shown or not, with one legal
     simple action. It keeps every frame, outcome, level and reset.
   - The observation is then rebuilt by the real record code, so every action reference (history entries and
     `recent_actions`) agrees with the alteration.
   - The build rejects a variant that changes anything else, still contains ACTION6, or has an inconsistent
     `recent_actions`.
   - Variants are labelled `synthetic_counterfactual_history`, and are resampled together with their original
     context in every bootstrap.
2. **The tool does not turn uncertainty into certainty.**
   - The B1 field is a qualification flag with a separate reason: `tool_history_rule` is `eligible` or
     `not eligible`, and `tool_reason` gives the reason.
   - "Not eligible" means only that the conservative rule does not count the entry. It never asserts that the
     frame differs.
   - The precedence is fixed: not delivered, then own outcome unknown, then own final frame differed, then the
     earliest later entry that changed the final frame or had an unknown outcome.
   - Its description says it is computed by a tool and does not establish that the current frame differs.
3. **Joined metadata is labelled computed control metadata.** It precomputes the relationship the target tests,
   which leaves extraction. Success is read as improved interface usability, not as evidence that the model
   learned the intersection.

**Decisions taken, as the review recommended:**
- `A0` stays the v2 intersect-instruction reference.
- The history alteration stays secondary and non-gating.
- B1 starts with the qualification flag plus its reason.
- Transient cases stay in regression coverage (`any_change`, `outcome_class` and `observed_effect` as components).
- Counts are frozen before budgeting (below).

## Track A: control

| Condition | Prompt | Observation | Reading of success |
|---|---|---|---|
| `A0_intersect` (reference) | v2 `control_candidate` prompt (baseline plus intersect instruction) | live fields; v2 baseline history | — |
| `A1_computed_control_metadata` | same | `A0` plus `computed_control_metadata`: each legal id with `"x and y, integers 0 to 63"` (6) or `"empty {}"`, computed from `legal_actions` and the control rules; never from the history | **Improved interface usability.** The field precomputes the tested relationship. |

- **Target:** `legal_coordinate_actions`.
- **Components (regression check):** `legal_actions`, `action6_legal`.

**Secondary, non-gating: matched synthetic counterfactual histories.**
- **Which contexts.** Every synthetic context whose legal set excludes ACTION6 and whose shown history contains
  it: 60 withheld and 13 development contexts.
- **What is asked.** These are also asked with the matched variant, under `A0` and under `A1`.
- **Why the keys match.** The control questions do not depend on the history, so keys are identical across
  each pair.
- **What is reported.** Per condition: paired counts of original against counterfactual on the same questions.
  An improvement means right only once ACTION6 left the history. A context-bootstrap interval is given.
- **What it can show.** Evidence for or against history interference in these synthetic cases. It is never a
  promotion gate.
- **Labels on variants are not interpreted.** Every variant's key is `[]`, so its single-condition labels are
  `not_diagnostic` by construction; only the paired comparison is used.

## Track B: history (tool-assisted)

| Condition | History field | Label |
|---|---|---|
| `B0_normalized_history` (reference) | v2 normalized records | unaided |
| `B1_tool_eligibility` | `B0` plus, per entry, `tool_history_rule` and `tool_reason` (above), and a description of the rule | **tool-assisted** |

- **What the tool applies.** v2's frozen conservative rule. Its eligible set is exactly v2's qualifying set,
  which is tested.
- **What the model still does.** It selects the eligible entries, deduplicates exact actions (coordinates
  included) and answers in the schema.
- **What was left out.** The tool never lists actions: that would turn the target into a copy task.
- **Target:** `tried_unchanged`.
- **Components:** `step_action_match`, `any_change`, `qualifying_steps`, `outcome_class`, `observed_effect`.
  `qualifying_steps` is expected to become near-copy under `B1` and is reported as such.

## Cases (frozen)

- **Generation.** v2's generation rules, templates and record code, unchanged. New seeds:
  `evidence-comprehension-v3-withheld` and `evidence-comprehension-v3-development`.
- **Withheld: 128 contexts.** Templates: mixed 12, near-miss clicks 12, transient 12, failed and unknown 12,
  same-frame repeats 16, stale unchanged 20, level boundary 12, reset boundary 12, long with omitted 12, empty
  history 8.
- **Development: 30 contexts** (3 per template).
- **Declared enrichment.** Every context whose legal set excludes ACTION6 (except empty-history ones) is redrawn
  until its shown history contains ACTION6. As a result, 60 of the 64 withheld non-legal control questions have
  ACTION6 in the history.
- **Transfer.** v1's six archived observations, without grids and without counterfactual variants.
- **Keys.** Primary keys come from the shown entries (v2's key functions). Independent keys come from raw frames
  (`research/evidence_comprehension_v3/independent.py`, which imports only v2's import-free module). The tool
  fields and the computed metadata are also recomputed independently. The build fails on any disagreement.
- **Frozen set.** `research/evidence_comprehension_v3/probes.json`, SHA-256 `d27e5eda…72dc`, with 3,390
  questions. A fresh build is byte-identical.

**Withheld coverage** (original variant, per condition):

| Family | n | Best shortcut (accuracy) | Questions where it is wrong |
|---|---|---|---|
| legal_coordinate_actions (target) | 128 | always `[]` (0.500) | 64 |
| tried_unchanged (target) | 128 | every unchanged entry (0.680) | 41 |
| legal_actions | 128 | all seven (0.086) | 117 |
| action6_legal | 128 | always "no" (0.500) | 64 |
| step_action_match | 128 | ignore coordinates (0.570) | 55 |
| any_change | 128 | final frame only (0.781) | 28 |
| qualifying_steps | 128 | transient excluded (0.609) | 50 |
| outcome_class | 128 | transient as no change (0.641) | 46 |
| observed_effect | 128 | ignore coordinates (0.859) | 18 |

The frozen minimums are enforced by the build:
- per target: at least 100 questions, 20 where the best shortcut is wrong, and 60 contexts;
- per component: at least 100 questions;
- at least 40 counterfactual contexts.

The predeclared shortcuts are v2's, unchanged. Under `B1`, copying the tool flags is the intended use of the
tool, not a shortcut: that is why the condition is labelled tool-assisted.

## Workload (frozen, for budgeting)

| Phase | Calls |
|---|---|
| Withheld pass 1 | 2,664 |
| Withheld pass 2 (exact reverse) | 2,664 |
| Development pass 1 | 618 |
| Transfer pass 1 | 108 |
| **Total** | **6,054** |

Each withheld question's conditions and variants are scheduled adjacently, in seeded order. The token audit and
runtime scenarios, including explicit first-cell overhead allowances as in v2, come with the budget proposal.
For reference only: v2 answered 8,004 calls in 837 s of question time.

## Decision rules

v2's rules apply unchanged, over original-variant withheld questions:
- the per-family labels;
- both-correct scoring over two identified passes;
- the context bootstrap;
- the 0.05 regression tolerance;
- the verdict order: `incomplete`, `baseline_meets_criterion` (the reference already meets it),
  `candidate_clear_improvement`, `mixed`, `improved_below_criterion`, `no_clear_improvement`.

Track B's verdicts carry the suffix `_tool_assisted`. A missing answer is never scored.

Completeness follows the r2 policy above:
- any missing primary answer makes that track `incomplete`;
- missing secondary or descriptive answers never change a verdict, and are reported.

"No regression detected" is not non-inferiority.

| Result | Next step |
|---|---|
| A: `candidate_clear_improvement` | Computed control metadata becomes the control presentation for a later action-selection protocol, read as interface usability. |
| A: otherwise | Report it. The secondary alteration comparison says whether history interference is supported in these synthetic cases. |
| B: `candidate_clear_improvement_tool_assisted` | Pursue a tool-assisted agent (plan step 8, second branch). No claim of unaided comprehension. |
| B: `improved_below_criterion_tool_assisted` / `no_clear_improvement_tool_assisted` | Selection or deduplication itself is limiting; investigate before planning. |
| `incomplete` or `mixed` | Report as such; no promotion. |

## Next

Runner adaptation (reusing v2's derived stack), the GPU-disabled package, the token audit and budget, then
package review. No GPU launch before separate approval.
