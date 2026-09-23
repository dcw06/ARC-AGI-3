# Multimodal preflight v3: image-input compatibility verified

Kaggle version 1 completed. Frozen independent archive replay passed with no
errors and verdict **`image_input_verified`**. All four probes completed with
`transport_attempted=true`, `finish_reason=stop`, and exact agreement between
server and processor prompt counts. No behavioural or arithmetic review flags
were raised. Final cleanup and notebook finalization passed.

This clears the compatibility prerequisite for reviewing the proposed
text-versus-image diagnostic. It does not authorize that study, demonstrate
general perception accuracy or solving improvement, promote a policy, or
complete Phase 4.

## Probe results

| Probe | Server / expected prompt tokens | Processed image | Result |
|---|---:|---|---|
| T0, no-image control | 352 / 352 | none | Correct: no quadrant or colour |
| I1, small colour canary | 394 / 394 | 256 x 256, grid 1x16x16 | Valid but incorrect: colour 11; expected 12 |
| I2, first board | 1378 / 1378 | 1024 x 1024, grid 1x64x64 | Correct: top_left, colour 8 |
| I3, different board | 1378 / 1378 | 1024 x 1024, grid 1x64x64 | Correct: bottom_right, colour 9 |

I1 contributes 64 image tokens; I2 and I3 each contribute 1,024. The measured
I2-minus-T0 prompt delta is **1,026**, exactly image expansion plus two vision
markers. I2 and I3 returned different, correct answers. I1's wrong answer is
retained as an outcome; correctness was not a technical acceptance condition.
These tiny probes do not establish reliable colour reading, object grounding,
control competence or planning. No probe was retried or repaired.

The mounted Qwen3VLProcessor / Qwen2VLImageProcessorFast loaded successfully;
both processor configuration hashes matched. Target package versions were
transformers 4.57.6, torch 2.10.0, torchvision 0.25.0, Pillow 12.2.0. The
supported PyTorch-tensor path now has actual server evidence on this stack.

## Lifecycle and accounting

- Model startup: **651.112 seconds**, including 509.043 s artifact hashing,
  0.802 s processor loading, 115.089 s server readiness, and 23.790 s canary.
- Notebook elapsed: **789.925 seconds**, within 1,680 internal / 1,800 provider
  seconds. The startup ceiling remained 900 seconds.
- One text startup canary plus four probes, **five completions** in total.
  Probes used 3,502 prompt tokens and 54 completion tokens; the canary added
  46 prompt and 29 completion tokens. No environment actions or scorecards.
- Independent cleanup verified absent owned process groups and **zero remaining
  GPU processes**. Dependency trees and extracted source were removed.
- Account SDK usage rose from 9,081.192 to 9,881.173 seconds: **799.981 seconds**.
  This is account-wide observation, not exact per-attempt billing. Exact billed
  seconds remain null. Raw quota allowance and SDK conversion disagree; both
  are retained rather than silently reconciled.

Attempt `mm3-708c716d007d43dcb1a0ba70c510698a` remains consumed. No additional
attempt or representation comparison is authorized.

## Verified archive and replay

All **24 downloaded files** (23 outputs and the console log, 2,851,589 bytes)
were verified against `phase4_multimodal_preflight_v3_download.json`. The archive
also retains provider observations and approval/reservation/launch receipts:

`evidence/phase4-multimodal-preflight-v3-r1-completed.zip`

SHA-256: `648fe38e9391e2d3282c3e1a1257fedca898cd076076863ecf885b120b7d28d6`

Read-only replay with the project's Linux CPU dependencies:

```sh
python scripts/replay_phase4_multimodal_preflight_v3_completed.py
```

This checks the frozen source/notebook lock, archive and every member hash,
then independently evaluates the evidence including final cleanup. The result
is in `phase4_multimodal_preflight_v3_pilot_evaluation.json`; the clean-copy
verification is in `phase4_multimodal_preflight_v3_completed_replay.json`.

## Next development step

Review the local perception fixtures and scoring against these measured input
dimensions/counts, then construct matched raw-grid/image requests, audit the
actual tokenizer and maximum output budgets, and package the supervised
zero-action diagnostic. Freeze its own protocol, interpretation and compute
proposal before approval. No additional compatibility rerun is needed for the
unchanged verified configuration. The failed I1 colour answer remains relevant
to the planned diagnostic. Production certification, workload-specific
admission limits and exact billing remain open.
