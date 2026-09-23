# Multimodal preflight v2: one attempt submitted

Final update: Kaggle COMPLETE; frozen independent replay passed. All three
image probes failed in local processor token accounting before being sent to
vLLM. Verdict `token_accounting_mismatch`; comparison remains blocked. See
[final disposition](phase4_multimodal_preflight_v2_disposition.md). The launch
observations below are historical; this attempt remains consumed.

The user authorized the reviewed source and one new 1,800-second attempt with
"OK now launch a new GPU run". Approval is bound to review lock
`998cb52d171582a2eac25c8f39837b9a3905bcfd05da52789d427c9079fa1825`.

Attempt `mm2-a4445329d2de4bec975d5b238a510ab9` was reserved, packaged, verified
and consumed before one upload. Kaggle accepted version 1 without attachment
errors at 2026-09-23 06:22:04 UTC. At 06:22:33 UTC its status was
`KernelWorkerStatus.RUNNING`, with no provider failure message.

[Private notebook](https://www.kaggle.com/code/daichongwei06/arc3-phase4-multimodal-preflight-v2-r1)

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_multimodal_preflight_v2.py
```

RUNNING is provider status, not model readiness or an image-support result.
The provider timeout requested is 1,800 seconds; internal ceiling 1,680,
startup ceiling 900, cleanup reserve 300. No automatic retry is authorized.
The original GPU-disabled review notebook is preserved.

Prelaunch SDK account usage was 8,303.717 seconds. Provider quota JSON and SDK
duration conversions disagree on allowance; both are retained in provider
observations. Exact per-attempt billing remains unknown. Completion requires
download verification, independent evaluation, archive and usage reconciliation.
The perception comparison remains blocked pending successful target evidence.
