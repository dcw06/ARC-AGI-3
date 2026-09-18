# V12: target action contract passed; stale evaluator rejected the canary

The target worker completed 110 clients and 7,582 real model requests. All 7,582 actions were acknowledged, including 5,262 ACTION6 actions. Policy failures, parser repairs, inference queue failures, inference transport failures, client errors and request errors were all zero. The constrained ACTION6 startup canary passed the frozen exact-integer/coordinate validator. This establishes target serving compatibility for the exercised contract, not general game competence or production certification.

The failure was an integration mistake in the v12 implementation: `certification/phase4_v12/evaluate.py` delegates to `certification/phase4_v4/evaluate.py`, whose canary check still requires at most eight completion tokens. The approved v12 protocol changed the canary ceiling to 128 tokens, and the real valid canary used 29. The inherited evaluator therefore emitted the misleading message `single audited canary evidence missing`. The subsequent notebook completion error follows from that rejected evaluation; it is not evidence of failed cleanup. The local scripted pilot did not exercise this live-only evaluator condition.

The canary audit records contract `arc_action_v12`, status `passed`, 46 prompt tokens matching the local tokenizer, and 29 completion tokens. Its body was not retained; the positive validation claim rests on the frozen service code and passed audit. Workload action acceptance additionally demonstrates that coordinate-bearing actions passed the strict response and action guards.

The notebook lifecycle lasted 4,301.395 seconds (1h11m41s). Process, scratch, source, dependency-tree, continuous-monitor GPU and independent GPU cleanup receipts passed; 15,370 GPU samples were retained. Account usage increased by 4,310.572 seconds, an aggregate account delta rather than exact per-attempt billing. The consumed 28,800-second local reservation remains retained pending exact reconciliation. No replacement run was launched.

Repair scope: introduce a newly reviewed evaluator revision that explicitly validates the v12 contract identifier, positive integer token counts, prompt-token equality, and the approved 128-token canary ceiling. Preserve all unrelated acceptance checks and historical frozen files. Add live-evaluator regressions for the real 29-token receipt and invalid/missing/mismatched/over-limit canaries, then replay the downloaded evidence locally before considering another GPU run. Do not overwrite this run's original failed verdict or silently discard the inherited error without validating the replacement contract.

Portable evaluation: `reports/phase4_v12_pilot_evaluation.json`.
Evidence archive: `evidence/phase4-v12-pilot-failed-v1.zip`.
SHA-256: `02d9da0a78c90e65a44ac8d9c5a066fd93efdff91f7918e3755d7216756285b8`.
