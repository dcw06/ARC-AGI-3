# Feedback-probe checkpoint diagnostic: completed corrected attempt

The corrected attempt is technically complete under its frozen evaluator. This report contains descriptive aggregates only; notebook, raw requests, outputs, scope records and replay receipts remain private. All previous attempts, including the cancelled submission, remain consumed and preserved.

**The prompt intervention showed little behavioral difference in this pilot.** Seven of eight paired action sequences were identical, and neither condition completed a first level within four new actions. The model read recorded actions and listed controls correctly but missed every visibly changed checkpoint in the separate recognition test.

## Runtime and independent verification

| Check | Result |
| --- | --- |
| Provider | COMPLETE; exact approved saved source and version verified |
| Physical accelerator | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Worker lifecycle | 449.41 s / 3,300 s |
| HTTP requests / generations | 73 / 73 ceiling; 1 canary, 8 recognition, 64 policy |
| Offline actions | 116: 16 resets, 36 prefix dispatches, 64 continuation dispatches |
| Local scorecards | 16; online calls and leaderboard submissions: 0 |
| Evidence integrity | 43 downloaded files; all 41 runtime-manifest members verified |
| Independent native audit | All 73 prompt counts matched pinned Transformers 4.57.6 |
| Largest prompt / completion | 4687 / 8,192; 76 / 256 (canary cap 16) |
| Generation endings | All 73 ended with stop; no length truncation |
| Independent engine replay | All 16 restored conditions matched, with requests and totals reconstructed |
| Cleanup | Owned groups absent, 0 remaining GPU processes, extracted source and temporary environments removed |
| Additional compute during collection | CPU verification only; 0 new model generations or GPU jobs |

The CPU verifier used a hash-checked local Linux copy of the exact reviewed source, a fresh offline game interpreter, and a separate pinned Windows CPU processor receipt bound to every request hash. Earlier unsuccessful local verification attempts and partial logs are retained. They did not alter or rerun the completed GPU study. CPU replay costs are separate from the GPU study counts above.

## Separate factual recognition

One stateless question per checkpoint asked about the most recent displayed transition. Its answer was never fed into either policy condition. Unknown or invalid answers remain incorrect on the full denominator.

| Field | Correct / checkpoints |
| --- | ---: |
| current_matches_before | 4 / 8 |
| historical_action | 8 / 8 |
| historical_step | 8 / 8 |
| legal_actions | 8 / 8 |
| visible_change | 4 / 8 |

All five fields correct: **4/8**. Valid responses: 8/8.

| Game / source step | Stratum | Changed cells in latest transition | Correct fields / 5 |
| --- | --- | ---: | ---: |
| ls20 / 2 | changed | 52 | 3 |
| s5i5 / 2 | changed | 2 | 3 |
| cd82 / 2 | unchanged | 0 | 5 |
| cd82 / 3 | changed | 1 | 3 |
| ft09 / 2 | unchanged | 0 | 5 |
| ka59 / 2 | unchanged | 0 | 5 |
| ka59 / 3 | changed | 1 | 3 |
| sc25 / 2 | unchanged | 0 | 5 |

Visible change here means any differing cell, including interface/resource indicators. It does not establish object motion, usefulness or game progress.

## Paired policy continuations

Each condition starts from a fresh seed-0 reset plus the same verified recorded prefix, receives the same recent visual history and historical initial geometry, and takes at most four new actions. The intervention is one fixed instruction to test unresolved alternatives while allowing justified repetition. Condition order alternates across checkpoints.

| Measure | Baseline | Probe instruction |
| --- | ---: | ---: |
| Conditions | 8 | 8 |
| Legal, faithfully executed new actions | 32 / 32 | 32 / 32 |
| Invalid policy answers | 0 | 0 |
| First level completed within continuation | 0 / 8 | 0 / 8 |
| Visibly changed transitions | 18 | 18 |
| Distinct full actions, summed within conditions | 10 | 11 |
| Unknown visible-change predictions | 32 | 32 |
| Correct known visible-change predictions | Not estimable: 0 covered | Not estimable: 0 covered |
| Repeated full action after unchanged full observation | 14 / 14 | 13 / 14 |

The first action differs between conditions at **0/8** checkpoints. The complete four-action sequences are identical at **7/8** checkpoints.

| Game / source step | Baseline changed transitions / 4 | Probe changed transitions / 4 | Same full action sequence |
| --- | ---: | ---: | --- |
| ls20 / 2 | 4 | 4 | yes |
| s5i5 / 2 | 4 | 4 | yes |
| cd82 / 2 | 3 | 3 | yes |
| cd82 / 3 | 2 | 2 | yes |
| ft09 / 2 | 0 | 0 | no |
| ka59 / 2 | 3 | 3 | yes |
| ka59 / 3 | 2 | 2 | yes |
| sc25 / 2 | 0 | 0 | yes |

Per-action prediction and repetition denominators depend on the trajectory each condition produces. These counters are descriptive, and neither diversity nor changed pixels establishes informative exploration or learning.

## Interpretation and next diagnostic

Recognition always answered no visible change and current matches before. That was correct on the four unchanged checkpoints and wrong on all four changed checkpoints: changed-case detection was 0/4. Correct action/step metadata and legal-control reading do not establish visual comparison ability.

Both policies returned unknown for every prospective change prediction. Only ft09 changed its action sequence under the probe instruction, after the same first action; neither ft09 continuation produced a changed image. This is not evidence of useful exploration. All other paired sequences were identical, including complete click coordinates.

A useful next diagnostic would hold the policy and starting states fixed while comparing image-only feedback against an explicitly computed cell-change summary. That would test whether making observable differences explicit improves factual recognition and subsequent action choice. Such a summary must not supply hidden rules, target meanings or future outcomes, and any new run needs its own reviewed package and authorization. This pilot alone does not identify the cause of the missed changes.

## Scope and retained bindings

Eight exposed checkpoints across six development games are correlated, including overlapping cd82/ka59 prefixes. One deterministic attempt and four new actions per condition cannot establish generalization, full-game solving, or a causal cognitive mechanism. No outcome threshold or promotion rule was added after observing the results.

| Artifact | SHA256 |
| --- | --- |
| Approved private review lock | `20f77cde564724bab5b7f7a638a02d3b70428425ae329faff684c7f4b01f6452` |
| Independent evaluation | `3ab27ad7b7325f4ad80f004c89323235267a22c938acc675086b03318a3e2d74` |
| Complete retained run evidence digest | `6a2bf0e16c87deefccba80cf5d4665745d97f0585c545f444a9073815dc1be48` |
| Independent CPU lifecycle receipt | `02300048abe38410b4e54054617dc653fb4b09ac6caed0581b6bf7f410d39f82` |

Evaluation uses the unchanged [live evaluator](../research/feedback_probe_v1/live_evaluation.py), [content replay](../research/feedback_probe_v1/audit.py) and [recognition scorer](../research/feedback_probe_v1/scoring.py). The [submission record](feedback_probe_v1_submission_attempt2_2026-10-19.md) is retained separately. No new attempt is authorized by this completion.
