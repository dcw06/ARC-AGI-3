# V14 offline evaluator hardening

Both review findings are fixed in a new evaluator revision. The v13 target run, notebook, verdict, and frozen sources are unchanged. V14 wraps the complete v13 evaluator and adds direct rejection when `independent_gpu_cleanup_verified` is missing or not exactly `True`, when worker `action_output_contract` / `policy_parent` differs from `arc_action_v12` / `E1S-R`, or when any client `action_output_contract` / `parent` differs from those bindings. Any rejection clears the capacity candidate and leaves `C_admit` unset.

The successful configuration is **E1S-R-derived `arc_action_v12`**, not unchanged historical E1S-R: the prompt and constrained decoding were revised. The archived worker and all 110 clients carry the expected labels. These new checks close validation gaps; they do not indicate a wrong-policy or failed-cleanup event in the actual run. Labels alone are not cryptographic proof of behavior: replay also verifies archived file hashes and the frozen source bindings, while retaining all existing action, lifecycle, token and resource checks.

Five regression tests passed against the portable v13 archive, covering the original passing run and 19 negative mutations: six cleanup-flag cases, four worker-binding cases, eight client-binding cases and an unrelated policy-failure case. Missing and changed bindings fail; false/absent/non-boolean cleanup values fail without adding a supervisor error. Every rejected case withholds capacity. The full positive replay independently passes with the same measured capacity candidate.

Records: `reports/phase4_v14_replay.json`, `reports/phase4_development_capacity_disposition.json`, and `reports/phase4_attempt_accounting_reconciliation.json`. New evaluator/test/replay hashes are bound in the replay receipt. This revision is offline evaluation only: no GPU session, notebook replacement, admission, or new spending authority.

## Development-capacity disposition

Accepted for descriptive development planning only; rejected as production admission authority. The configuration exercised 110 clients repeating 15 development games on separate scorecards.

| Quantity | Measured value / interpretation |
| --- | --- |
| Nominal measured rate | 1.986001987 requests/second |
| Nominal projection | `C_nominal = 39,322` requests over 19,800 service seconds |
| Conservative empirical rate | 1.411523016 requests/second: 0.8 times the minimum rate among eight equal wall-time windows |
| Separate service headroom | 20% of 19,800 seconds = 3,960 seconds |
| Effective service time | 15,840 seconds |
| Conservative development projection | `floor(1.411523016 × 15,840) = 22,358` requests |

The rate haircut and time headroom are distinct reductions. The rate is an empirical single-run margin, not a confidence interval or deterministic bound. Candidate units are requests, not games, wins, or levels. No projection establishes future trajectory lengths, production throughput, or useful solving; `C_admit` remains null. No observed allocation problem justifies advanced scheduling.

## Attempt-accounting disposition

The consolidated reconciliation lists all 16 Phase 4 attempt ledgers and hashes their receipts. Thirteen have terminal receipts (three COMPLETE and ten ERROR); two v11 submissions have explicit HTTP 400 rejections; the initial v10 upload timed out without a confirmed launch outcome. Its absence of a successful launch receipt is not proof of zero usage. The first v11 rejection did not retain its body, so its precise size-error cause remains inferred; R2 retained the explicit size rejection.

Latest provider observation: 2026-09-18 11:23:06 UTC, account usage 51,377.099 seconds and provider-reserved time zero. V13's retained before/after delta is 4,509.597 seconds. These are aggregate observations, not exact attempt billing. Historical quota resets and potentially overlapping observation intervals prevent summing deltas as an invoice. Local reservations are conservative authorization ceilings, not evidence of billed time or currently reserved provider quota.

Outcome reconciliation is complete to available receipts. Financial attribution remains open: per-session provider usage/allocation history is needed to resolve exact billing and the ambiguous v10 submission. Preserve consumed claims and original ledgers; do not transfer retained ceilings to new attempts. No reservations were released, no exact zero charge was inferred for rejected uploads, and no new spending was authorized.
