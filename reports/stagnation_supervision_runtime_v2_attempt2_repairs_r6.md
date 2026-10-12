# Track 3 runtime v2 r6: repairs after session-1 attempt 2 and its independent review

**Status.** This is a GPU-disabled source change. It authorises nothing. Both session-1 attempts stay consumed, and no
further attempt is authorized. The frozen protocol, science files, schedules, prompts, horizons, telemetry limits and
compute ceilings are unchanged. Generated files change only through the derivation, which still inverts.

| Review finding | Repair | Regression (`tests/test_ssv_runtime_v2_attempt2_repairs.py`) |
|---|---|---|
| **[P1]** A cleanup-query timeout could skip detached children: one `try` covered stopping the supervisor group, reaping it and reading the child ownership records, so a failed first query left only the supervisor group known (reproduced by the reviewer with injected query timeouts) | Each step is attempted on its own (`ATTEMPT2_REPAIRS`, `launch.py`): a failed stop of the supervisor group falls back to SIGKILL; reaping and recovery of the durable child records always run; every recovered owned group is stopped, with a SIGKILL fallback when its check fails; absence is reported only where a check verified it, and any failed check stays in `errors`, which withholds first-cell certification. `ownership.stop` (inside the supervisor) follows the same rules | `LaunchCleanupFaults` (first query fails; every query fails; children ignoring SIGTERM), `OwnershipCleanupFaults` (failed checks with no process handles) |
| **[blocker]** RSS measurement still scanned the process table with `ps -axo pgid=,rss=` and a 1-s timeout; the warm-up did not change that operation | New stdlib module `procfs.py`. It lists `/proc` once and reads only `/proc/<pid>/stat` (no cmdline, environ, status or maps, which take the target process's memory lock), with the same coverage as the `ps` scan: every member of the worker's process group, not only the leader or its descendants. A hard budget (0.4 s for RSS, inside the frozen 1-s gap) raises `ScanBudgetExceeded` with a bounded census. It never returns a partial, estimated or zero value. The 0.5-s interval, 1-s gap and RAM, scratch and VRAM limits are unchanged | `ProcfsProbes` (equal to `ps` at steady state across all three members and excluding another session; over-budget raises with its census; zombies are not live members; names with spaces and parentheses parse), `ResourceProbe` |
| **[blocker]** Cleanup used similar `ps` scans | `launch._group_exited`, `ownership.stop` and the supervisor's worker stop use the `/proc` check; no payload module imports the shared `ps`-based helper any more, which drops it and its own imports from the payload | `OwnershipCleanupFaults.test_no_payload_module_uses_a_ps_subprocess_for_cleanup_or_rss` |
| **[P2]** Warm-up failures kept neither the failed probe's phase nor its elapsed time (`{"phase": "binding"}` only) | Each warm-up call records `warmup_<probe>` as its phase and its elapsed time on an exception-safe path. A `/proc` census raised by the RSS probe is copied into the monitor's failure receipt, which stays within the 2,048-byte limit | `WarmupDiagnostics` (the actual subprocess-timeout case; a census over budget) |

The reason the target's `ps` scan was slow remains unknown. If the new reads are also slow there, the run fails closed
before readiness, and the receipt now says which probe failed and what the scan cost.

**Still required before any further attempt:**
1. fresh Linux verification of this revision (full suite, connected fault rehearsals, staged real-interpreter
   rehearsals);
2. a rebuilt public review snapshot and private package, with an independent review of the exact package;
3. reconciliation of both attempts' provider versions, statuses and accounting;
4. reconfirmed scope evidence, and separate source, compute and launch decisions with a fresh reservation.

Target throughput remains unverified; admission and deadline enforcement stay the protection against an incomplete
workload.
