# Stage B R7 one-attempt disposition

**Disposition: failed, incomplete exploratory pair; no demonstrated solving
benefit.** The one-use R7 Kaggle reservation is consumed. Do not retry this
revision unchanged. This is not Phase 4 production certification.

Kaggle accepted private provider version 1 of
`daichongwei06/arc3-grounded-action-v1-r7` under attempt
`gab1-c507bf9ce1d54bc2ab34296a11d0f5f5`. Its final status was
`KernelWorkerStatus.ERROR`. The R10 source/protocol review lock was
`0b255babdcfd25d293342dc405cdbe154c5e7f8b6dc83988c630fe09792d82cd`.

The frozen model and startup canary passed. The control arm issued one
`ACTION6` at `(16, 16)` and received an acknowledged offline-development
engine transition. The retained pre- and post-action canonical observation
hashes match; the action produced no visible state change or level progress.
The committed sealed prediction was `no_change` and its mechanically derived
alternative was `change`.

The sealed feedback model response was retained in full:

```json
{"assessment": "contradicted", "changed_frames": [1, 2, 3, 4, 5, 6, 7, 1] }
```

Only one post-action frame exists, at index `0`. Every reported index is
out of range, and `1` is duplicated. `parse_audit` correctly rejected the
response with `ValueError: feedback fields`; the worker stopped without
repair or retry. The target arm made no policy calls or actions. The result
cannot compare the two arms or establish whether the target scaffold helps.
The response's `contradicted` assessment also disagrees with the observed
no-change transition, but correctness is not scored for this invalid output.

The independent evaluator verified all **26** downloaded files against the
provider-output hash manifest, exact control/prediction/feedback requests,
retained response hashes, token parity and `finish_reason="stop"`, one
acknowledged action journal, initial-state equality, both scorecard closures,
**1,806** monitor samples, and independent GPU/process/scratch cleanup.
The complete-pair replay correctly rejects this trajectory as incomplete.
No GPU processes or process groups remained; dependency trees were removed.

The first cell took **609.85 seconds**; model startup took **475.29 seconds**.
The account-wide GPU `time_used` counter rose from 12,356.213 to 12,975.5
seconds, a **619.287-second** difference. This is an account-wide observation,
not exact provider billing. The reservation remains consumed; no automatic
retry is authorized.

The immediate follow-up is a locally reviewed feedback-output contract
revision. The current constrained schema permits arrays containing repeated
indices and does not bind indices to the actual returned frame count; the
strict post-response validator caught this invalid answer. Any revision
should retain rejection of invalid, duplicated, or out-of-range indices,
and test realistic one-frame feedback on the pinned model before requesting
another separately authorized GPU attempt. That would be a new experiment,
not continuation of this consumed reservation.

Portable replay after checking out the project and retaining the archive:

```powershell
wsl -d Ubuntu -- /home/jingjing/.local/share/agi/dev-env/bin/python -m scripts.archive_grounded_action_v1_r7 replay
```
