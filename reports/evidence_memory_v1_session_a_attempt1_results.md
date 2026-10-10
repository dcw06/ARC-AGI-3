# Track 2 Stage 1, session A, attempt 1: technical summary (sanitized)

**What this is.** The sanitized technical summary of session A's one authorized attempt (owner gate 6, October 10,
2026). The notebook and raw outputs stay private and account-only. A single session reports **no scientific
outcome**: outcomes come only from the pooled analysis of both technically valid sessions (frozen protocol §12).

## The attempt

| Item | Value |
|---|---|
| Attempt | `em1a-159d1a1cef334de3adc240970e58e6a7`, submitted once on October 10, 2026 at 19:00:58 UTC (provider version 2); no retry |
| Package | private review snapshot r9 (review lock `dbd63df6…`), frozen protocol `6f96dbe7…`, withheld draw 2 (commitment `d80505e2…`), frozen set `69b450c1…` |
| Hardware | one NVIDIA RTX PRO 6000 Blackwell Server Edition (97,887 MiB), as authorized |
| Provider status | RUNNING from 19:05 UTC, COMPLETE at 19:31 UTC |
| Lifecycle elapsed | 873.6 s (authorized 3,600 s; internal deadline 3,300 s met after cleanup and evidence finalization) |
| Cleanup | verified |
| Evidence manifest | 9 files, all hashes match |

## Requests against the authorized ceilings

| Quantity | Issued | Ceiling |
|---|---|---|
| Counted HTTP requests | 5,676 (= 12 + 2 × 2,832, the complete-session figure) | 189,756 |
| Generation requests | 2,839 (2,832 study completions + 7 runtime checks) | 2,839 |
| Ledger refusals | 0 | |
| Game actions, scorecards | 0, 0 | 0, 0 |

Every mandatory runtime probe (S1–S3, I1–I4, C1–C3) and the pre-study metrics read reconcile with their retained
evidence (the r7 evaluator check).

## Technical evaluation (independent evaluator, live mode)

| Item | Value |
|---|---|
| Technically complete | yes; lifecycle passed, no lifecycle or call errors |
| Calls | 2,832 of 2,832 scheduled answered (pass 1: 2,592; repeat pass 2: 240) |
| Schema-valid answers | pass 1: 2,591 of 2,592; pass 2: 240 of 240 |
| Invalid-output rule (at most 2% per arm in every pass) | met in both passes |
| Technical status | `session_technically_valid` |
| Retained record | `reports/evidence_memory_v1_session_a_technical_evaluation.json` in the private checkout, SHA-256 `45826b5f2ef57f63a3041919fd14f09677b5c1ed68e8cb2fe6338f091a19c651` |

Invalid answers per arm, as the frozen protocol §10 requires them reported:

| Pass | `recent_raw` | `state_keyed_raw` | `memory` | `full_history` |
|---|---|---|---|---|
| Pass 1 (648 per arm) | 0 | 0 | 1 (0.15%) | 0 |
| Pass 2 (60 per arm) | 0 | 0 | 0 | 0 |

The invalid answer is retained and counts in every denominator; it is never repaired.

## What follows

- Session B's launch condition (frozen protocol §12) is met: session B's tooling finds no reason against this record.
  The record shows session A live, on its registered withheld set, technically complete and valid in every pass.
- **Session B is not authorized.** Its compute authorization, if the owner grants it, names the record's SHA-256
  above. The pooled analysis runs only after both sessions qualify.
