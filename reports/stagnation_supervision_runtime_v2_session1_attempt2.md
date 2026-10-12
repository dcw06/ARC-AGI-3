# Track 3 session 1, attempt 2 (the one authorized replacement): technical failure before readiness (sanitized)

**Status: consumed and preserved; not retried.** No model was started, no game action was taken and no study data
exists (protocol §9). The owner authorized exactly one replacement, with no further replacement, so no further session-1
attempt is authorized.

| Item | Value |
|---|---|
| Attempt | `ssv1rt2-s1r-994053875c1c4a6ea06ab09be3e9c4bc`, submitted October 12, 2026, 02:12 UTC, in one push (provider version 3) |
| Package | private review r8, lock `e14c27cc…` (public review r5, lock `91522a95…`: r7 plus the monitor probe warm-up) |
| Provider status | RUNNING at 02:15:06, ERROR by 02:17:06 UTC |
| Independent live evaluation | technically incomplete; no run evidence; monitor failure receipt; the evaluating checkout's review lock verified |

## What happened

**Install.** Installation passed in 130.3 s.

**The warm-up.** The monitor then began the probe warm-up added after attempt 1, and the warm-up's RSS probe failed:
`ps -axo pgid=,rss=` exceeded its own 1-s subprocess timeout. The monitor stopped before readiness; the worker was never
released and the model host never started.

**Cleanup was certified.**
- Process groups were absent and child ownership was verified.
- Independent GPU cleanup was verified.
- Scratch was removed.
- Fail-closed finalization recorded the source as removed.

## Correction to the attempt-1 analysis

Attempt 1's report attributed the 5.45-s first RSS probe to a one-time cost in the first process creation. Attempt 2
shows that attribution was wrong. A full `ps` scan of the process table at this point in the lifecycle on these
machines can itself take longer than 1 s, so warming it up cannot help. The attempt-1 report is retained unchanged as
history.

**What is known:**
- the GPU probe in the same sample was fast (12 ms);
- Track 1's identical probe on the same machine type took 0.03 s twenty hours earlier;
- every CPU rehearsal is fast.

**What is not known:** why a full process-table scan is slow in these runs. For example, a process whose `/proc`
entries block readers, or many processes, would each produce this. The retained receipts hold no process census.

## Implication for any further attempt (none is authorized)

A repair should:
- stop measuring the worker group's memory with a full `ps` process-table scan;
- record, if any probe is slow, a bounded diagnostic census (process count, counts by state, slowest single read), so
  a failure explains itself.

The frozen limits stay unchanged: a 0.5-s interval, a 1-s gap, and the RAM, scratch and VRAM limits.

A further attempt needs new, separate owner decisions, because the replacement authorization excluded any further
replacement. Session 2 is not authorized.
