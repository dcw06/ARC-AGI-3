# Phase 2 failure reproduction and treatment selection

Decision: **Phase 2 has no justified treatment**.

The frozen gate requires two matching, parent-only reproductions from distinct
runs on the same development game and seed. The downloaded Phase 1 evidence
proves that all 60 game-cell scores were zero and that policy failures occurred,
but it contains no transition-level proposals or retained frames. Consequently,
none of the six causal diagnoses can be established without inventing evidence.

## Frozen parent and prospective plan

Every candidate was reviewed against the exact E1S-R parent:

- Operational configuration SHA-256:
  `489765d436df7e0ae7c80b9494c3c1ab4b7153b46f8dc5951724b59561ebb709`
- Feature-manifest SHA-256:
  `65312c43d8499d86fb1a7262efc2ec483b4a4424cd180c14d7abd1a477d89eae`
- Model: `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8` at revision
  `d9748a51ae66354c4dad665aab2c71f26cf2c8cd`, `vllm==0.19.0`, non-thinking.
- Policy: one E1S-R action, R latest-final-frame observation, frozen minimum
  queue, and stateless visible compaction.

If a candidate had passed admission, its prospective comparison would use two
paired complete-workload blocks, require both block effects to be nonnegative,
at least +0.10 official RHAE percentage points overall, absence of the
reproduced parent failure in both treatment arms, overall reliability within
-0.02 points, no tail at or below -0.10, and all safety/resource gates.

Conditional compute was capped at four RTX PRO 6000 hours, four workload runs,
60 game plays, 80 actions per game, 4,800 model requests, and zero scored
submissions. Actual allocation is zero.

## Candidate dispositions

| Candidate | Sole conditional feature delta | Reproduced failure | Disposition |
|---|---|---|---|
| E2a | Advanced inter-action evidence | None: no matching transition proves a decision-relevant event missing from R | Not admitted |
| E2b | Advanced animation summary | None: no matching sequences prove action-relevant summary aliasing | Not admitted |
| E2c | Selective rich animation | None: no matching registered trigger proves summary insufficiency | Not admitted |
| E2d | Correspondence/identity tracking | None: no matching failure isolates lost identity after simpler causes are excluded | Not admitted |
| E3 | Durable scratch/rejected-hypothesis memory | None: no matching runs prove supported mechanics were forgotten and rediscovered | Not admitted |
| E4 | Exact historical retrieval/retrodiction | None: no matching transition proves older exact evidence resolves current ambiguity | Not admitted |

Futility is declared when neither the positive nor reliability rule passes
after the fixed two blocks. Regression stops immediately at the frozen -0.10
tail or any safety/resource failure. Parent drift, feature leakage,
evaluator/holdout access, unknown runtime revisions, ambiguous environment
outcomes, and queue/finalization breaches are immediate stops.

## Result

No treatment manifest is created, no treatment code is authorized, and E2a–E4
remain inactive. New parent diagnostics may justify a new prospective selection
record later; they do not retroactively change this decision.

```bash
make validate-phase2-selection
```
