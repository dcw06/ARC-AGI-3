# Track 3 session 1: technical summary (sanitized)

**What this is.** The sanitized technical summary of session 1. The notebook and raw outputs stay private and
account-only. Outcome endpoints are not reported here: the protocol's comparisons pool both sessions and require the
amendment-S1 self-review to be drawn, annotated and committed first (frozen protocol §7, §8).

## Attempts

| Attempt | Provider version | Package | Outcome |
|---|---|---|---|
| `ssv1rt2-s1-c5ebca7f…` | 2 | private r7 | consumed: failed before readiness (monitor's first RSS probe, 5.45 s) |
| `ssv1rt2-s1r-99405387…` | 3 | private r8 | consumed: failed before readiness (warm-up `ps` probe timed out) |
| `ssv1rt2-s1a3-615924ad…` | 4 | private r13 (public review r10, lock `e2ad0c97…`) | **technically complete; target accepted** |

**Attempt 3 approvals.** These were the owner's four separate decisions on October 12:
- Gate 4, reusing the version-1 Quick Save as attachment evidence;
- source, launching without a separate independent review of this exact package and before its running verification
  finished (that verification later passed in full: CPU suite r14 and the private review check of the launched
  package);
- compute for one further attempt;
- launch.

## Attempt 3

| Item | Value |
|---|---|
| Provider status | QUEUED 07:45, RUNNING 08:48, COMPLETE 09:17 UTC (63 min waiting for a GPU) |
| Hardware | one RTX PRO 6000, bound by the monitor before the worker was released |
| First-cell lifecycle | 1,746.7 s (authorized 5,400 s; internal deadline 5,100 s) |
| Installation | 146.9 s (window 450 s) |
| Model startup | 560.3 s (ceiling 900 s) |
| Monitor readiness | worker released at 148.3 s; the bounded `/proc` probes sampled throughout and the monitor completed |
| Study work | 1,034 s for 600 actions (about 1.7 s per step, reflections included); every one of the 7 game groups complete |
| Model requests | 600 policy calls + 20 reflections + 1 canary = 621 (ceilings 600 / 32 / 1) |
| Game actions | 600 on the local offline engine (15 episodes × 40); 0 dispatch failures; 0 online game calls or scorecards |
| Reflections | 12 periodic and 8 triggered, all valid; none failed |
| Tokens | policy 14,983,893 prompt + 15,364 completion; reflections 26,788 prompt + 4,481 completion |
| Failure rules | none fired; the reflection interface was never stopped |
| Cleanup | process groups absent with child ownership verified; independent GPU cleanup found 0 GPU processes; scratch removed; fail-closed finalization certified with the extracted source removed |

## Independent live evaluation

| Item | Value |
|---|---|
| Technically complete / target accepted / lifecycle verified | yes / yes / yes; 0 problems |
| Evaluating checkout's review lock | verified (private r13) |
| Retained record | `reports/stagnation_supervision_runtime_v2_results/session1_attempt3_evaluation.json` in the private checkout, SHA-256 `7689ccf8df06fec0aceb47ff0bfd02ce4b94c347be28bc4a2db1f2a36969b523` |

## What follows

Session 2 runs block 2 (12 episodes) once on the same package. It needs its own owner decisions and a fresh
reservation. Its execution lock must bind the record above by SHA-256, and the gate refuses it otherwise.
**Session 2 is not authorized.**
