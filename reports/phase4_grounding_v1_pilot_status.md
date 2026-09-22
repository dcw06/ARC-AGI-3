# Grounding v1 R1 launch status

## Completed grounding diagnostic: independent technical pass

Grounding R1 completed; all 24 downloaded files verified and frozen replay passed.
Exact diagnostic answers: grid reading 2/4, localization 0/4, changes 0/4; no
malformed responses or transport failures. Correctness is separate from technical
acceptance. The 1800-second reservation remains consumed; no follow-up run is
authorized. See [final disposition](phase4_grounding_v1_disposition.md).
Earlier status entries below are historical.


Latest check: 2026-09-22 01:39:40 UTC, `KernelWorkerStatus.QUEUED`, no failure
message. This is about 65 minutes after upload acceptance, not observed GPU
runtime. SDK-reported account usage remains 3,883.525 seconds, with zero provider
reserved seconds. No running/completion observation or diagnostic result is yet
available. The local attempt remains consumed; no resubmission was made.

The user authorized launch of the reviewed diagnostic with "OK now launch a new
GPU run" after the source review and separate 1,800-second proposal were presented.
Separate source and compute receipts bind review lock
`eb3e074882be085de238135b7bc10871cb6290abb085f946aee833c1dfd79370`.

Attempt: `og1-b98f644f0122470699224f74b5961d49`.
The reservation and pre-upload claim are consumed. One upload was submitted;
automatic retry remains unauthorized. Limits: 1,800 provider seconds, 1,680
internal seconds, 12 diagnostic calls plus one canary, zero environment actions,
zero scorecards. The frozen GPU-disabled review notebook remains unchanged.

Kaggle accepted version 1 at 2026-09-22 00:34:20 UTC, with no reported upload error:
https://www.kaggle.com/code/daichongwei06/arc3-phase4-grounding-v1-r1

At 00:36:18 UTC the read-only observation reported `KernelWorkerStatus.QUEUED`
with no failure message. Running/completion has not yet been observed.
The earlier status check was blocked by automatic approval review due to a usage
limit; the user's subsequent request to continue allowed the status check to resume.

Monitor from the repository root:

```powershell
.\.cache\kaggle-windows-client\Scripts\python.exe scripts/observe_phase4_grounding_v1.py
```

Provider observations are retained under
`reports/runs/phase4-grounding-v1-r1-pilot/provider-observations.jsonl`.
Queued quota observation: SDK usage 3,883.525 seconds, provider reserved zero.
Raw duration strings are malformed and raw allowance disagrees with SDK allowance;
exact billing remains unresolved. Zero provider-reserved seconds does not restore
the consumed local authorization.

After terminal status: download and hash retained outputs/logs, independently
evaluate technical acceptance separately from diagnostic correctness, archive,
and reconcile usage with its limitations. No full-game run, policy promotion, or
Phase 4 completion is implied.
