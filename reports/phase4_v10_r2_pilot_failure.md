# V10 R2: completed worker, failed policy acceptance

Kaggle version 1 ended in ERROR. Final notebook elapsed time was 8,029.080 seconds (2h13m49s). The worker completed all 110 clients and 7,650 real model requests. Its process returned zero; the independent evaluator then rejected 38 clients with nonzero `policy_failures`: 1,119 total. The notebook raises when evaluation fails, which explains the provider error despite completed worker execution.

The counters record zero inference queue failures and zero inference transport failures. `TerminalAwareLoop` increments `policy_failures` when `policy.propose` throws, then attempts the fallback. Completed execution with fallback does not satisfy the frozen zero-policy-failure acceptance requirement. The retained worker records do not include individual proposal exception messages or rejected response content, so the evidence does not establish whether parsing, schema, legal-action validation or another proposal-stage exception caused each rejection. Do not relabel these failures as successful model decisions or relax acceptance retroactively.

The asynchronous telemetry repair passed this run's monitoring checks: 29,155 retained samples, maximum adjacent gap 0.370981 seconds, below the unchanged one-second limit. Both continuous-monitor and independent post-termination GPU cleanup passed. Source, dependency trees, scratch and owned processes were removed. These are positive infrastructure results, but final acceptance remains failed and no capacity certification is claimed.

Next: examine the frozen proposal/parser/fallback path locally, add bounded exception-category and rejected-response evidence with request hashes, and reproduce representative failures before changing model policy or running another GPU attempt. Existing transport success and token audit do not establish semantic validity of an action proposal.

Account GPU usage increased by 8,038.225 seconds, an aggregate account delta rather than exact per-attempt billing. The consumed 28,800-second reservation remains retained pending exact reconciliation. No retry was launched.

Evidence archive: `evidence/phase4-v10-r2-pilot-failed-v1.zip`, SHA-256 `9b03280b63fb429b1d53f488540e73674dec8d1b41b87911de9215c0491fd57f`. Full file hashes, counts and accounting: `reports/phase4_v10_r2_pilot_evaluation.json`.
