# Track 1 (feedback_action_v1), session 1: technical summary (sanitized)

**What this is.** The sanitized technical summary of session 1. The notebook and raw outputs stay private and
account-only. The study's outcomes come from `live_evaluation.evaluate_sessions` over both sessions (frozen protocol
§9); this summary reports technical status and cost only.

## Attempts

| Attempt | Outcome |
|---|---|
| `fa1-s1-8c598909fad24d9e96e71b7a482993eb` (October 11, 02:01 UTC; provider version 2) | **consumed, failed during installation**: Kaggle's `MPLBACKEND` reached the game interpreter's package checks. No model call, game action or study data. Preserved; never relaunched |
| `fa1-s1r-d1bc3d6ba0cc493d8d21e326d23b1d06` (October 11, 05:11 UTC; provider version 3) | **the one replacement under owner amendment A1** (frozen protocol §16), on the fixed package (public review snapshots r6; private lock `23cb7142…`): **technically complete under the original evaluator**; technically incomplete (F1, no finalization receipt) under the post-fix evaluator (`reports/feedback_action_v1_post_fix_audit.md`) |

## The replacement attempt

| Item | Value |
|---|---|
| Hardware | one NVIDIA RTX PRO 6000 Blackwell Server Edition (97,887 MiB), bound by the monitor before the worker was released |
| Provider status | RUNNING 05:12, COMPLETE 05:26 UTC |
| Lifecycle elapsed | 820.6 s (authorized 3,600 s; internal deadline 3,300 s) |
| Model-server requests | 145: 1 startup canary and 144 policy calls (72 per arm); ceiling 193 |
| Game actions | 144 on the local offline engine (6 episodes × 24); ceiling 144; zero online game calls and scorecards |
| Episodes | all 6 complete at the 24-action cap (s5i5, ls20 and sk48; both arms) |

## Independent evaluation (live mode, from the reviewed checkout)

| Item | Value |
|---|---|
| Review lock verified | private r7, `23cb7142c6e41ae408e05255f9f443b62e7a313de8c5c9da7e50c4c79908eb07` |
| Technically complete | yes under the original evaluator: lifecycle passed, run evidence verified, replay passed, 0 problems. Under the post-fix evaluator: F1, technically incomplete (no finalization receipt), all evidence-level checks passing |
| Failure rules F1–F6 | original evaluator: none fired; post-fix evaluator: F1 only (no finalization receipt). F2b decision-cap episodes 0 and 0 |
| Free text | `ascii_only` (gate A); 0 blocks outside the option |
| Carried statements | 72 checked (69 available), 0 mismatches |
| `session_2_permitted` | **true** under the original evaluator (session 2's gate used this record); false under the post-fix evaluator (F1) |
| Retained record | `reports/feedback_action_v1/session1_evaluation.json` in the private checkout, SHA-256 `869f3aad30e1dff739548046d6a67db88dc823fe7f5c6c227d900cfab5831ce0` |

## Cost per arm (frozen protocol §2.1)

| Arm | Calls | Prompt tokens | Completion tokens | Call seconds (total; max) | Episode seconds |
|---|---|---|---|---|---|
| Baseline | 72 | 1,818,859 | 1,801 | 114.1; 1.88 | 41.7, 39.4, 40.7 |
| Candidate | 72 | 1,848,502 | 15,643 | 229.1; 4.06 | 80.6, 72.1, 84.0 |

The candidate is a bundled treatment with a 5× completion allowance; the arms are not compute-matched (§2.1).

## What follows

Session 2 runs the same package once (amendment A1 permits no replacement for it). Its execution lock must bind the
record above by SHA-256, and the gate refuses it otherwise. **Session 2 is not authorized.**
