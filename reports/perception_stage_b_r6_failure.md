# Stage B R6 consumed attempt: prediction contract failure

**Disposition:** the one authorized R6 Kaggle attempt is consumed and
finished with `KernelWorkerStatus.ERROR`. Independent evaluation classifies
it as `verified_prediction_contract_failure`. This is an incomplete study,
not evidence for either arm's gameplay performance. No retry is authorized.

The split offline installation passed, the pinned model became ready in
589.409 seconds, and its startup canary passed. Both `ar25` development
episodes bootstrapped from the same canonical observation and both
scorecards were closed with zero actions. The first control-policy call
returned a valid click at `(16, 16)`. The sealed prediction call then
returned valid JSON with identical alternatives:

```json
{"prediction":"no_change","alternative":"no_change"}
```

The reviewed contract requires one `change` and one `no_change` value.
Strict validation correctly rejected the response as `ValueError:
prediction alternatives`. The response body, SHA-256, request identity,
tokenizer/server counts (8,569 prompt tokens each; 16 completion tokens),
and `finish_reason="stop"` survived into the trajectory. No action was
dispatched; no feedback or target-arm model call occurred. Independent
replay rejects the incomplete pair, as required.

All **27** downloaded provider files match the download manifest. The
monitor retained **2,238** samples. The first-cell runtime was about
728.511 seconds, under the 3,300-second internal limit. The dependency
trees and scratch were removed; the parent verified all owned process
groups exited, and independent cleanup recorded **zero remaining GPU
PIDs**. The provider did not give an exact per-attempt bill. Account-wide
GPU usage rose **737.858 seconds** between prelaunch and the final quota
observation; that delta is not an exact bill.

The next repair should be a separately reviewed prediction-output contract
change. A mechanically derived opposite value, or a supported schema that
permits only the two distinct pairs, would remove the redundant
failure mode without relaxing validation. Test the actual target
constrained-decoding path and preserve the original R9 source lock before
considering another authorization. This result says nothing about whether
the policy can make level progress. Phase 4 production certification and
exact billing reconciliation remain open.
