# Coordinate diagnostic: first authorized attempt

## Coordinate attempt ended in tokenizer-manifest failure

Kaggle reports ERROR. All 23 downloaded files were verified and archived. A
revision-copy substitution corrupted the expected vocab.json digest; tokenizer
verification stopped startup before diagnostic responses. Capability results are
inconclusive. Independent process/GPU cleanup and source/dependency removal were
retained. The reservation remains consumed; no retry was launched. See
[failure report](phase4_coordinates_v1_failure.md). Older entries below describe
historical preparation and queue status.


User decision: "Yes start a new GPU run", following presentation of R2 source
and the separate 2,100-second compute proposal. Separate approval receipts bind
review lock `dee7b8c941e4961fe682005e6d8a926ca3cea714c80406f8fdbf7408a325918f`.

Attempt: `co1-2ecf020ad08b45b89f088509d1b18314`.
The local reservation and exclusive pre-upload claim are consumed. Exactly one
upload was submitted; no automatic retry is authorized. Limits: 2,100 provider
seconds, 1,980 internal seconds, 56 diagnostic calls plus one canary, zero
environment actions or scorecards. Historical reservations were not reused.

Kaggle accepted version 1 at 2026-09-22 15:53:13 UTC without an upload error:
https://www.kaggle.com/code/daichongwei06/arc3-phase4-coordinates-v1-r1

The provider slug uses r1 for the first launch attempt; its source is the reviewed
R2 notebook. The failed review R1 and corrected GPU-disabled review R2 are preserved.

At 15:53:36 UTC the status was `KernelWorkerStatus.QUEUED`, with no failure message.
Running or completion has not been observed. Monitor from the repository root:

```powershell
.\.cache\kaggle-windows-client\Scripts\python.exe scripts/observe_phase4_coordinates_v1.py
```

Observations are retained in
`reports/runs/phase4-coordinates-v1-r1-pilot/provider-observations.jsonl`.
The queued SDK account usage was 4,724.817 seconds, provider-reserved seconds zero.
Raw duration strings remain malformed and raw allowance disagrees with SDK
conversion; exact billing remains unresolved. Provider queue status and zero
reserved time do not restore local launch authority.

Pending completion: download and hash outputs/logs, independently replay source
provenance, requests, responses, scores, deadlines and finalization, archive and
reconcile usage. Apply the predeclared decision rules only to technically valid
complete evidence. No policy promotion, follow-up run, or Phase 4 completion is
implied by this launch.
