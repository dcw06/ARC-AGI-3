# Track 3 runtime v2 r7: the /proc budget bounds the caller's wait (second review of the attempt-2 repairs)

**Status.** This is a GPU-disabled source change. It authorises nothing. Both session-1 attempts stay consumed and no
further attempt is authorized. Only `research/stagnation_supervision_runtime_v2/procfs.py` and its tests change; the
frozen science, limits and derivation are unchanged.

| Review finding | Repair | Regression (`tests/test_ssv_runtime_v2_attempt2_repairs.py`) |
|---|---|---|
| **[P1]** The "hard budget" was checked only after the directory listing or a read returned. A blocked read held the caller past its budget (the reviewer's 20-ms budget was still waiting after 80 ms), and cleanup calls the probe before signalling, so a stalled operation could keep cleanup from its SIGKILL fallback | The scan runs in a daemon worker thread, and the caller waits at most the budget (`join(budget)`), then raises `ScanBudgetExceeded` with a census snapshot. A stalled worker is abandoned, and nobody reads its late result. A subprocess was rejected: killing a child stuck in an uninterruptible read can itself hang on `wait()` | `test_a_stalled_read_returns_within_the_budget` and `test_a_stalled_listing_returns_within_the_budget` (both return within 0.5 s of a 0.05-s budget); `StalledProcCleanup`: with every `/proc` read stalled, launch cleanup and `ownership.stop` both finish within their bounds, SIGKILL every owned group and do not certify absence |
| **[P2]** An interrupted scan could report `{"members": 0, "member_states": {"S": 1}}`, because the member count was updated only at the end | `members` and `member_states` are updated together as each member is observed. The census states `phase` (listing, stat reads or complete), `complete`, `stalled`, and `reads_started` against completed `stat_reads` | `test_an_interrupted_census_counts_the_members_it_observed`; the over-budget census test checks the full key set and `complete: false` |

The reason the target's `ps` scan was slow remains unknown. A stalled `/proc` read on the target would now fail the
probe within its budget, with a census naming the phase.
