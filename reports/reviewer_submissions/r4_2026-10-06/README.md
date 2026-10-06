# Returned r4 worksheet — 2026-10-06

Reviewer artifact only: no decision import, build, upload, reservation or GPU launch is authorized by this commit.

- `conditional_approvals.xlsx` is the unchanged workbook supplied by Chongwei Dai, originally named `wheelhouse_redistribution_conditional_approvals (1).xlsx`.
- `returned_r4.csv` is a value-only extraction of its `r4_review` sheet, in the issued column order. The workbook retains the supplementary notes and proposed regression cases.
- The user confirmed adoption of the original 107 conditional decisions and then the additional 52 conditional decisions in the accompanying conversation. This is adoption of 159 conditional decisions, not confirmation that their conditions are fulfilled. The workbook's generic reviewer attribution is preserved unchanged; normalization and the exact import preview remain separate work.

## Checks against source revision `5c65d78`

- 174 unique artifacts; all artifact hashes and issued r4 context fields match.
- 159 `approved_with_conditions` entries; 15 undecided entries.
- 107 entries have populated satisfaction records. This is a structural observation, not an independent finding that every obligation has been met.
- 52 conditional entries lack satisfaction evidence, including the 45 whose `PENDING` text was moved out of satisfaction fields. Those 52 and the 15 undecided entries keep the bundle blocked.
- Validation returned zero errors and 52 unsatisfied-condition warnings. No authoritative decisions were changed.

## Remaining gate

The existing validator can mistake nonempty `PENDING` prose for satisfaction evidence. The corrected data does not fix that code defect. The `Validator_Regression_Cases` sheet contains proposed cases, not executed tests. Fix and independently review the validator, then regenerate and inspect a complete import preview. Import requires the owner's confirmation of that exact preview hash; no previous preview hash authorizes this artifact.

## SHA-256

```text
4225a48aad058068db1f81da825084bea230bf414f79634ddfe683dd748e5821  conditional_approvals.xlsx
d9c51321bcd0f67bc7408df886b1e804a7f3e9020268e3d7f01adda3f56cc5bd  returned_r4.csv
```

The issued blank r4 worksheet and `reports/wheelhouse_redistribution_decisions.csv` are not replaced by these files.
