# Multimodal preflight v2: lifecycle passed; image requests blocked locally

Kaggle version 1 completed. Frozen independent archive replay passes with no
errors, including token evidence, deadlines, monitoring, finalization and
independent GPU/process cleanup. This is technical acceptance of a classified
failure, not verification of image support. The frozen verdict is
`token_accounting_mismatch`; the perception comparison remains blocked.

## Observed results

- The model became ready in **624.321 seconds**, within the 900-second ceiling.
  The text startup canary passed, followed by a correct text control T0:
  352 expected/server prompt tokens, 14 completion tokens, `finish_reason=stop`.
- The mounted processor loaded successfully: `Qwen3VLProcessor` using
  `Qwen2VLImageProcessorFast`, transformers 4.57.6. Both processor config files
  were present and matched their pinned hashes.
- Each image probe (I1, I2, I3) failed in the local expected-token calculation:
  `Only returning PyTorch tensors is currently supported.` The frozen helper
  calls the processor with `return_tensors='np'`. It catches this ValueError
  before calling the completion transport, retains it, and classifies it as
  `token_accounting_mismatch`.
- **No image request reached vLLM.** This is not an observed disagreement
  between server and processor counts: image counts and server responses are
  absent. It establishes neither image acceptance nor image rejection.
- Only two completions were sent: the startup text canary and T0. No
  environment actions, scorecards, repair or retry occurred.

## Startup timing

The new timestamped markers and cumulative hash progress survived in the
retained model log. Measured stage durations:

| Stage | Seconds |
|---|---:|
| Model artifact hash, 64,526,033,084 bytes / 81 files | 482.438 |
| Tokenizer verification | 0.014 |
| Mount inventory | 0.143 |
| Processor load | 0.797 |
| Tokenizer load | 0.179 |
| Server readiness after launch | 115.089 |
| Startup text canary | 23.813 |

Hashing dominated this run's startup. This does not retrospectively isolate
the previous run's uninstrumented stall. This run also finished startup below
750 seconds, so it does not prove that extending the ceiling alone fixed the
earlier failure.

## Cleanup, archive and accounting

Notebook elapsed: **767.771 seconds**. Independent cleanup verified zero
remaining GPU processes and absent owned process groups; dependency trees and
extracted source were removed. The worker cleanup interval was 0.373 seconds.

All **24 files** (23 outputs plus console log, 2,845,276 bytes) were verified
against `phase4_multimodal_preflight_v2_download.json`. The archive also retains
provider observations and approval/launch/reservation receipts:
`evidence/phase4-multimodal-preflight-v2-r1-completed.zip`, SHA-256
`8e7ae575c8c3b8782f23df9a4a7a2d0acd71447d2c01c5237cbcd2966bdf27c6`.

Read-only replay from a checkout with the project's Linux CPU dependencies:

```sh
python scripts/replay_phase4_multimodal_preflight_v2_completed.py
```

The script verifies source/notebook locks, archive and every member hash before
calling the frozen evaluator. It needs neither ignored downloads nor model
weights. `phase4_multimodal_preflight_v2_completed_replay.json` records the
clean-copy replay check; `phase4_multimodal_preflight_v2_pilot_evaluation.json`
records the independent result.

Attempt `mm2-a4445329d2de4bec975d5b238a510ab9` remains consumed. Account SDK
GPU usage increased from 8,303.717 to 9,081.192 seconds: **777.475 seconds**.
This is an account-wide observation, not exact per-attempt billing; exact
billing remains null. Raw quota allowance and SDK-converted allowance disagree
and both observations are retained. No further attempt is authorized.

## Next boundary

Prepare a separately versioned local repair of the processor expectation path
using PyTorch tensors, and test with the actual pinned processor rather than
only the permissive fake processor used in local tests. Check image dimensions,
patch geometry, token expansion and full/manual count parity before proposing
another target attempt. Preserve this frozen revision and its evidence.
That repair still needs review and separate compute authorization. Do not
launch the representation comparison or infer a model capability result from
this local API incompatibility. Production certification, admission limits,
exact billing and Phase 4 remain open.
