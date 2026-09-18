# V13 development pilot passed

Kaggle version 1 completed successfully. The downloaded final notebook verdict passed, its evaluation and cleanup hashes matched, and an independent local replay of the complete target evidence also passed. Frozen source and launch artifact hashes were verified.

- 110 clients completed 7,582 real model requests and acknowledged actions.
- 5,262 ACTION6 actions passed strict coordinate validation.
- Zero policy failures, parser repairs, inference queue failures or inference transport failures.
- The constrained startup canary passed with 29 completion tokens under the corrected 128-token gate.
- Notebook lifecycle: 4,500.288 seconds (1h15m00s).
- Monitoring retained 16,133 samples; maximum adjacent sampling gap was 0.281267 seconds.
- Process, scratch, source, dependency-tree, continuous-monitor GPU and independent GPU cleanup checks passed.

This completes the exercised development installation, serving, action-contract and lifecycle validation. It does not establish task-solving quality: the client results report zero levels completed. The workload repeats 15 development games across 110 clients; it is not production certification for 110 distinct games on one scorecard. Phase 4 remains incomplete under that broader definition.

The evaluator's capacity candidate is a development-only empirical projection, not a statistical or deterministic guarantee. It does not authorize subsequent admission or another GPU run.

Account GPU usage increased by 4,509.597 seconds. Kaggle reported zero reserved seconds at observation. This is aggregate account usage, not exact per-attempt billing; the local ledger records completion with accounting pending and conservatively retains its original 28,800-second reservation. No repeat launch is authorized.

Notebook: https://www.kaggle.com/code/daichongwei06/arc3-phase4-development-v13-pilot-r1

Evaluation: `reports/phase4_v13_pilot_evaluation.json`.
Archive: `evidence/phase4-v13-pilot-passed-v1.zip`.
Archive SHA-256: `114259a4fb2bcc650cda7dc79e5d16ff4f678ba037898eb232258900ed6d0b61`.
