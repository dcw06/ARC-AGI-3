# Track 3 runtime v2 r10: the gate refuses every consumed attempt (fourth review)

**Status.** This is a GPU-disabled source change. It authorises nothing. Both session-1 attempts stay consumed and no
further attempt is authorized.

**The finding [P2].** The runtime protocol's `consumed_attempts` listed only the R6 attempt. In temporary copies with
synthetic approvals, the ids of session-1 attempts 1 and 2 passed the full gate and produced launch packages.

**The repair.**
- **The derivation** (`CONSUMED_ATTEMPTS`) now records the complete history:
  - `ssv1-r5-session1-reservation-001` (R6);
  - `ssv1rt2-s1-c5ebca7f7b444bb3b63b6c90b3cf306b` (attempt 1, provider version 2);
  - `ssv1rt2-s1r-994053875c1c4a6ea06ab09be3e9c4bc` (attempt 2, provider version 3).
- **The gate** (`authority.REQUIRED_CONSUMED`) independently requires all three. A protocol that drops an entry is
  refused, and any of these ids is refused as an execution attempt.
- **A compute decision** must acknowledge the complete list.

**Regressions** (`tests/test_ssv_runtime_v2_consumed_attempts.py`):
- each consumed runtime-v2 id is refused by the live gate and by the package builder;
- a fresh id still passes the same synthetic gate;
- a protocol missing a consumed id is refused.

**The private use-assessment draft.** Before approval, its carried-over `proposed_conditions.scope` wording ("private,
account-only questionnaire", from an earlier scope) is corrected in the private package to describe Track 3's private,
account-only offline game study.

## r11: the completed session-1 attempt is consumed too (fifth review)

**The finding [P2].** The registry listed only failed attempts. Session-1 attempt 3
(`ssv1rt2-s1a3-615924add9624c5abec34e9de3c52ed0`, provider version 4, technically complete and accepted) passed a
synthetic session-2 gate as a reused id and produced a launch package.

**The repair.** The derivation's `CONSUMED_ATTEMPTS` and the gate's `REQUIRED_CONSUMED` now include it: a completed
attempt is as spent as a failed one.

**Regressions:**
- the completed attempt's id is refused for session 2 by the live gate and by the package builder;
- a fresh session-2 id with the same session-1 dependency passes;
- a protocol missing it is refused.

**Session 1 stays accepted; it is not rerun.** Because this change produces a new review lock, session 1's retained
evidence is re-evaluated read-only in the new private checkout. Session 2's dependency and the pooled evaluation then
share one verified lock. The original evaluation under private r13 is retained.
