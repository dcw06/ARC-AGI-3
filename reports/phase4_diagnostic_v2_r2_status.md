# Diagnostic v2 R2 submitted

Update: observed ERROR at 2026-09-19 06:32:00 UTC. All 45 requests and the
canary completed; cleanup passed. A floating-point request-window comparison
caused evaluator failure. The separately frozen v3 offline evaluator accepts the
retained evidence; historical notebook status remains failed. See
`reports/phase4_diagnostic_v2_r2_failure.md` and
`reports/phase4_diagnostic_v3_replay.json`. The submission summary below is historical.

The user explicitly replied "Yes I approve" to the frozen-source approval and
separate one-hour diagnostic GPU authorization question. Separate R2 approval
receipts and a fresh local reservation were created; withdrawn R1 records and
package remain historical and must not be submitted.

- Frozen source lock: `4c3cbe6204b310fcf1111604b7bccc7417f283220709619f02f62be4cb20d82c`.
- Attempt: `p4-diagnostic-v2-r2-20260919T034421Z`.
- Package: `notebooks/phase4-diagnostic-v2-pilot-launch-ready-r2/`.
- Notebook SHA-256: `3a59c03192acc781ab528ffa8bc6e53fcd9bd0ded483aa098cc12456db6a16f6`.
- Local source/package checks and unpacked authority check passed; 659,090-byte notebook.
- Kaggle accepted version 1 at 2026-09-19 03:45:27 UTC, without upload errors or invalid attachments.
- Observed at 03:45:43 UTC: `KernelWorkerStatus.QUEUED`; no failure message.

Run: https://www.kaggle.com/code/daichongwei06/arc3-phase4-action-diagnostic-v2-r2

The external launch claim is consumed. No retries are authorized. Scope remains
one private offline RTX PRO 6000 diagnostic, maximum 3,600 provider seconds,
3,300 startup-inclusive internal seconds, 45 diagnostic completions and one
canary. This is not a full pilot. Target results, cleanup verification, evaluation,
and usage reconciliation remain pending; upload acceptance is not evidence of
successful execution or exact billing.

Monitor from the repository root in PowerShell:

```powershell
& .cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_diagnostic_v2.py
```

The launch receipt is `reports/phase4_diagnostic_v2_r2_pilot_launch.json`.
Provider observations are retained under
`reports/runs/phase4-diagnostic-v2-r2-pilot/provider-observations.jsonl`.
