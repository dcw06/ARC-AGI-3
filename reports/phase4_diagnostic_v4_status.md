# Diagnostic v4 R1 submitted

Update: COMPLETE observed 2026-09-19 09:28:45 UTC. The target notebook and
independent archived-evidence replay passed, including final cleanup and deadlines.
All 45 requests plus the canary completed in 612.344 startup-inclusive seconds.
See `reports/phase4_diagnostic_v4_results.md` for results and accounting limits.
The submission summary below is historical; its pending tasks are now completed
except exact per-attempt billing reconciliation.

The user explicitly requested another GPU run of the same bounded diagnostic.
V4 integrates the offline-tested v3 evaluator correction into a new runtime,
preserving all earlier frozen revisions and unchanged three-arm request content.

- Source lock: `ed200b3403edf5550b033dc31d8400f1b681bce48dd43390200178ba8662c102`.
- Review notebook: `notebooks/phase4-action-diagnostic-v4-review-r1/` (GPU disabled).
- Launch package: `notebooks/phase4-diagnostic-v4-pilot-launch-ready-r1/`.
- Launch notebook SHA-256: `2577112a0143d691f127f1f83d73862c2afd30279d505dd7674860e9bc212e88`.
- Validation: 21 tests passed; retained 45-case CPU lifecycle passed with verified cleanup;
  historical hashes and unpacked launch authority verified.
- Attempt: `p4-diagnostic-v4-r1-20260919T071303Z`.
- Kaggle accepted version 1 at 2026-09-19 07:13:38 UTC; no upload errors or invalid attachments.
- Observed 07:14:05 UTC: `KernelWorkerStatus.QUEUED`, no failure message.

Run: https://www.kaggle.com/code/daichongwei06/arc3-phase4-action-diagnostic-v4-r1

The claim is consumed. Scope: one private offline RTX PRO 6000 job, maximum
3,600 provider seconds and 3,300 startup-inclusive internal seconds, 45 diagnostic
completions plus one canary, no automatic retry. No full pilot or production run.
Terminal download, independent evaluation, archive, cleanup verification and usage
reconciliation remain pending. Acceptance of upload is not evidence of GPU execution.
SDK account quota durations remain inconsistent; exact per-attempt billing is unknown.

PowerShell monitoring command from the repository root:

```powershell
& .cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_diagnostic_v4.py
```
