# V11 R3: missing ACTION6 coordinates identified

The worker completed 110 clients and 7,565 real model requests in a final notebook lifecycle of 7,363.292 seconds (2h02m43s). The final evaluator rejected 1,128 policy failures across 41 clients. All diagnostic category counts are `invalid_action_data`.

Every one of the 208 retained rejection examples contains this complete, untruncated response:

```json
{"action":{"action_id":6,"action_data":{}}}
```

Each retained exception is `FeatureManifestError: ACTION6 requires exactly x and y`. The full response SHA-256 and request-ID/hash associations were verified. Replaying all 208 responses through the unchanged local parser and validator reproduced exactly that exception. There are no retained response bodies for the remaining 920 failures, so the exact same missing-coordinate payload cannot be asserted for all 1,128; their category counts do establish invalid action data.

This is a model action-contract violation: ACTION6 needs integer x/y coordinates. The frozen system prompt already states that requirement but illustrates only an empty-data simple action. The sampled request has no `response_format` constraint. The example may influence output, but the retained evidence does not establish why the model omitted the coordinates. The strict validator correctly rejects these proposals, and fallback allows the worker to continue; fallback completion does not satisfy zero-policy-failure acceptance.

The next repair should review the model action-output contract, including an explicit valid ACTION6 example and, if supported by the pinned serving path, constrained output that distinguishes coordinate-bearing ACTION6 from empty-data actions. Keep strict validation, legal-action checks, request bounds and zero-policy-failure acceptance. Do not silently invent coordinates or reinterpret malformed proposals as valid. A changed prompt or decoding contract is a policy/protocol change and needs a new reviewed snapshot; it is not a retrospective fix to v11's result. Reuse the retained response as a local regression fixture before another GPU attempt.

Infrastructure passed: 26,676 retained GPU samples with a maximum adjacent gap of 0.281158 seconds, zero inference queue or transport failures, and successful continuous-monitor and independent GPU cleanup. Source, dependency, scratch and process cleanup also passed. This is diagnostic progress, not an improvement in acceptance: v10 had 1,119 failures across 38 clients, compared with 1,128 across 41 here. The runs are not a controlled performance comparison.

Evidence and accounting: `reports/phase4_v11_r3_pilot_evaluation.json`; portable archive `evidence/phase4-v11-r3-pilot-failed-v1.zip`, SHA-256 `16889f6eb3d093ac9afc0b4cfc4e8b1978d562670f87ce63aed5be2ff72e8956`. Account usage increased by 7,373.181 seconds, not exact per-attempt billing. The consumed reservation remains retained, and no new GPU run was launched.
