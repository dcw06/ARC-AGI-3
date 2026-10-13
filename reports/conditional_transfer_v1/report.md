# Conditional transfer construction results

The CPU benchmark demonstrates that keeping a rule's statement is insufficient: exact coordinates, boundaries and corrections can change the appropriate answer. The deterministic writer preserves all source evidence. Selection still loses evidence, especially when an atomic memory group exceeds a small prompt budget. These are scripted construction results, not model performance or learned mechanics.

## Construction

Eight families, six scenarios per family, and three distractor delays produce 48 independent scenario clusters and 144 dependent variants. Six tasks in three arms at two ceilings produce 5,184 dependent probes. Both independent key derivations agree on every task. Full-source and unbounded-store scripted verdicts agree throughout. All 144 source histories pass the existing transition contract; every faithful writer audit passes. There are zero answer-changing writer faults and zero scripted-reader errors against the package actually supplied.

The full-source transfer categories are 48 supported locally, 30 contradicted, 24 not applicable, and 42 unestablished. The conditions match in 120 variants and mismatch in 24. Update policy yields 114 retain, 18 narrow and 12 retire. Failed and unknown target receipts contribute uncertainty, not counterexamples. Returned intermediate frames are checked, so a transient effect cannot become no change just because the final frame returned.

## Budgeted availability

Each row has 144 transfer judgments. Contradiction/update incorporation uses 60 probes per arm: two tasks on the 30 counterexample variants. Percentages are descriptive; questions and delays are clustered.

| Prompt ceiling | Arm | Transfer category correct | Supported reuse coverage | Contradiction/update correct | Answer-changing selection losses across 864 tasks |
| --- | --- | --- | --- | --- | --- |
| 1,024 | Recent history | 73.6% | 27.1% | 90.0% | 180 |
| 1,024 | Retrieved evidence | 73.6% | 27.1% | 90.0% | 180 |
| 1,024 | Conditional memory | 45.8% | 0.0% | 0.0% | 360 |
| 1,536 | Recent history | 95.8% | 93.8% | 90.0% | 66 |
| 1,536 | Retrieved evidence | 95.8% | 93.8% | 90.0% | 66 |
| 1,536 | Conditional memory | 100.0% | 100.0% | 100.0% | 56 |

All three scripted arms make zero unsupported transfer claims in this construction. This alone does not establish usefulness: at 1,024 tokens, memory reuses none of the supported rules. Its latest unrelated rule fits first; the relevant atomic group then cannot fit, so selection stops. It conservatively answers without the missing evidence, creating selection failures rather than reader errors.

At 1,536 tokens, atomic memory carries the source support and its later counter together where the group fits. A raw record with 32 intermediate flash frames can instead occupy the first priority position and exceed the budget, producing an empty raw package. This occurs in the large-record distractor variants. It accounts for the remaining raw transfer failures, including three supported cases and three contradicted cases. The prefix-stop policy is retained deliberately and its failures are reported.

Perfect transfer categories do not mean all tasks pass: memory still loses source support needed to justify retaining a rule and records needed for complete evidence enumeration. Historical source groups can rank behind current-context groups; retaining a current target confirmation does not recover all historical qualifications. At the primary ceiling, source-relative mean reference precision/coverage are 84.3%/81.0% for memory and 85.8%/80.0% for each raw arm. These fail the frozen reference thresholds. No advancement claim is made.

Recent and retrieved raw arms have identical descriptive results here. Their selected packages can differ, but current-state/recency priority often retrieves the same deciding recent trials. This benchmark does not demonstrate a retrieval advantage. The full family and delay measurements are in `summary.json`; selected IDs, missing reference alternatives, and all four stage verdicts are preserved per probe.

## Shortcut controls

Shortcuts receive full source history so their errors cannot be blamed on a token budget.

| Shortcut | Transfer accuracy | Unsupported claims among unsupported cases | Supported reuse coverage |
| --- | --- | --- | --- |
| Always reuse | 33.3% | 100.0% | 100.0% |
| Never reuse | 16.7% | 0.0% | 0.0% |
| Always unknown | 29.2% | 0.0% | 0.0% |
| Latest entry | 45.8% | 0.0% | 0.0% |
| Ignore coordinates | 91.7% | 6.3% | 100.0% |
| Ignore boundaries | 79.2% | 31.3% | 100.0% |
| Repeated support means certainty | 50.0% | 75.0% | 100.0% |
| Support without corrections | 79.2% | 12.5% | 100.0% |

The strongest aggregate shortcut ignores coordinates. It fails 12 variants from four scenario clusters and scores only 33.3% in the coordinate family; it also exceeds the 5% unsupported-transfer threshold. All scripted packages solve that wrong subset because the common target and candidate action retain exact coordinates. That subset therefore tests grounding, not a memory advantage. Other shortcuts expose boundary and correction failures. No declared shortcut meets the complete review criteria, even though a shortcut can achieve a high aggregate score.

## Token and request audit

The pinned pure-Python ASCII tokenizer is hash-verified and reproduces the existing repository audit. Maximum complete prompts are 1,024 tokens at the small ceiling and 1,534 at the primary ceiling. Required canonical answers use at most 61 tokens. The longest useful schema-conforming answer using distinct resolved IDs is bounded by 98 tokens, below the common 256-token output cap. Arbitrary malicious long references remain invalid, not repaired.

The 5,184 development probes map to 3,354 unique request digests, with 1,830 duplicate aliases. Each individual ceiling has 1,692 unique requests; 30 are shared across ceilings. Executing every unique development draft once would entail 3,743,198 prompt tokens and at most 858,624 completion tokens, **before** separately counted schema probes and runtime overhead. None were executed. The primary-only development schedule is a rehearsal-size measurement, not the final evaluation count.

The six prepared schema probes add 3,374 prompt tokens and at most 1,536 completion tokens. Thus all development drafts plus those probes total 3,360 calls, 3,746,572 prompt tokens and an 860,160-token completion ceiling. This is an offline workload measurement; installation, startup time and cleanup still need a reviewed Linux runtime receipt. No latency, GPU duration or cost estimate is inferred from these CPU counts.

Evaluator keys, families, groups, delays, split labels and fault diagnoses are absent from requests. The reader parses actual request text; it cannot access fixture objects or keys. Metadata-poisoning tests confirm that hidden labels cannot alter selection. Duplicate aliases remain dependent observations. Semantic replay rejects forged source evidence and forged requests even if the attacker refreshes manifest hashes.

## What the milestone establishes

Construction, scoring, provenance, leakage checks and CPU token budgets are ready for independent review. The benchmark preserves its negative results: small-budget memory can lose more evidence than raw history, and the larger memory still fails reference coverage criteria. The scripted reader verifies availability and task construction only. Model-written memory, real-model interpretation, Linux runtime compatibility and behavioural transfer remain later separately reviewed studies.
