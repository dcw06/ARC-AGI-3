# Redistribution decision worksheet: instructions for the designated reviewer

`reports/wheelhouse_redistribution_decision_worksheet.csv` has 174 rows, one per artifact in the approved R2 manifest (sha256 `7af2954d75b1…`).

**This worksheet is not the decisions file, and nothing in it is a decision yet.**
- The `proposed_*` columns are proposals prepared for you. They are not approvals.
- Every reviewer column is blank.
- Do not edit the context columns; validation reports any change to them.

## Order

| Tier | Rows | Meaning |
|---|---|---|
| 1 | 4 | Priority NVIDIA artifacts (cuFile, nvJitLink, NVSHMEM, CUTLASS DSL binaries). Applicability or grant is unresolved; qualified review or NVIDIA clarification is needed. |
| 2 | 19 | Other rows that need qualified review |
| 3 | 48 | Conditional candidates with obligations beyond shipping the licence files (see `additional_obligations`) |
| 4 | 103 | Conditional candidates |

## Filling in a row

Fill in a row only when you have decided it. A row left with a blank `reviewer_decision` stays `unresolved`.

| Column | Content |
|---|---|
| `reviewer_decision` | One of `approved`, `approved_with_conditions`, `restricted`, `excluded`, `unresolved` |
| `reviewer_rationale` | Required for any decision other than `unresolved` |
| `reviewer_required_notices` | The notices that must ship with the artifact |
| `reviewer_conditions` | Required for `approved_with_conditions`: each condition, separated by ` \| ` |
| `reviewer_conditions_satisfied` | One entry per condition, in the same order, separated by ` \| `: how and where each was satisfied. The build stays blocked until every condition has an entry. |
| `reviewer_resolved_questions` | Which unresolved questions you resolved, and how |
| `reviewer_name` | The reviewer |
| `reviewer_date` | ISO date (YYYY-MM-DD) |

## How decisions affect the build

`restricted` and `excluded` block the bundle. Every artifact is a required dependency, so nothing is silently omitted. An artifact that cannot be cleared needs an explicit alternative, which is the owner's decision.

## Return

Return the CSV as it is. Before anything is imported, it is validated for artifact bindings, required fields, recorded conditions and conflicts with existing decisions. The owner is then shown the proposed changes, and the import happens only after the owner confirms that exact preview.
