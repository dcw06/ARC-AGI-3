# Closed-loop v1 R1 complete; independent replay passed

The authorized closed-loop v1 R1 run completed on Kaggle and passed independent
replay of the archived evidence. All 15 matched game pairs completed their 20-action
episodes: 600 policy calls/actions plus the startup canary. Startup-inclusive
runtime was 1659.281 seconds (27 minutes 39 seconds),
within the 3,300-second internal deadline and 3,600-second authorized attempt.
Independent GPU/process cleanup, dependency/source removal, finalization hashes,
request/action bindings, initial-state equality, progress counters, and evidence
completeness passed. All 664 frozen source bindings still match.

See `reports/phase4_closed_loop_v1_results.md` for metrics, archived evidence and usage.
The pending statements below describe submission-time status only.

# Historical submission record

The user explicitly requested launch after the frozen notebook and separate
one-hour budget were presented and published. Source approval, compute authority,
fresh local reservation and exclusive launch claim are recorded separately.

- Attempt: `p4-closed-loop-v1-r1-20260919T113037Z`.
- Source lock: `078b1dc692e0a1a9580218e642f2329893593e0931959900a5ca565f5ce457f3`.
- Launch package: `notebooks/phase4-closed-loop-v1-pilot-launch-ready-r1/`.
- Launch notebook SHA-256: `3bfea198740061332ffcda949d72fe4c16a3c37b451c3c00f2e30abf1ff77e33`.
- Package size: 734,950 bytes; source/artifact/authority checks and unpacked authority check passed.
- Kaggle accepted version 1 at 2026-09-19 11:31:39 UTC with no upload error or invalid attachment.
- Observed 11:32:04 UTC: `KernelWorkerStatus.QUEUED`, no failure message.

Provider-returned URL:
https://www.kaggle.com/code/daichongwei06/arc3-phase4-action-closed-loop-v1-r1

Kaggle warned that the supplied title and requested slug differed. It returned
the URL above, which includes `action`; the observer follows that receipt URL.
No second upload was attempted to change the slug.

Scope remains one private offline RTX PRO 6000 attempt, maximum 3,600 provider
seconds and 3,300 startup-inclusive internal seconds, 30 matched development
episodes with at most 20 actions each, and 600 policy requests plus one canary.
No automatic retries, full pilot or production certification. The claim is consumed.
The original review notebook remains unchanged and GPU-disabled.

Terminal download, independent trajectory/finalization replay, archive and usage
reconciliation are pending. Provider acceptance is not evidence of execution or
progress. Account quota observations remain distinct from exact per-job billing.

Monitor from the repository root in PowerShell:

```powershell
& .cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_closed_loop_v1.py
```

The 20-action cap tests early progress; zero progress would not establish that the
prompt change can never help. Exact billing and production certification remain open.
