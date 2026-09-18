# V13 integrated pilot review

The corrected canary evaluator is now integrated into a complete v13 pilot. The live path in `certification/phase4_v13/pilot.py` imports `certification.phase4_v13.evaluate`, which calls the corrected base evaluator. The previously reviewed evaluator files are unchanged, preserving their bindings in `reports/phase4_v13_v12_replay.json`.

The action contract remains `arc_action_v12`: identical prompt, per-observation JSON schema, strict integer/coordinate validation, and one constrained startup canary. This is an evaluator correction, not a new model/prompt policy. The evaluator deliberately reuses the frozen v12 telemetry validation and GPU-binding helpers; those dependencies are included in the notebook source lock. The split offline environments, monitor-through-cleanup supervision, resource/deadline limits, 110-client workload and separate authority gates are preserved.

43 Linux tests passed, including malformed canary regressions, unchanged acceptance-check comparisons, schema transport, strict action validation, diagnostics, lifecycle cleanup and GPU-disabled notebook execution. The latter confirms the notebook rejects absent authority before installation or GPU access. Target evidence replay remains a separate diagnostic result: the original v12 target notebook is still recorded as failed.

Frozen review notebook: `notebooks/phase4-lifecycle-v13-review-r1/profile.ipynb`. GPU and internet are disabled. No source-approval sidecar, GPU reservation, launch package or GPU run was created. A future launch must bind separate source and compute authorization to this new snapshot; the consumed v12 attempt cannot be reused.

The final CPU pilot passed the 300-second smoke gate: 110 clients, 7,722 scripted requests, 115.386 seconds, unchanged scripted actions. Its historical 60-second comparison remains failed as reported. The notebook is 509,327 bytes; source-lock SHA-256 is `b7acedd48bb452debf7a0a1fa0ecc04f96126b2976745cdd301b3d4177bc0e05`. All v7-v13 source and artifact bindings were verified, as were the earlier evaluator replay bindings.

The CPU archive is `evidence/phase4-v13-local-review.zip`, SHA-256 `f072675a71827e64fa7f4a80484bd8fd39ba4f3751bfe370935543cd8f688a84`. Full verification is recorded in `reports/phase4_v13_integration_receipt.json`. This CPU evidence and the retained target replay do not establish a newly executed v13 GPU notebook or production certification.
