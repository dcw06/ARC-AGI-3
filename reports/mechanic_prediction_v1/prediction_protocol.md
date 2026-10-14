# Prediction Protocol v1

Status: offline protocol specification; not an execution authorization.

## Arms

| Arm | Receives |
| --- | --- |
| Reference | Common system instructions, evidence, proposed action, response schema |
| Candidate | Byte-identical user evidence/question/schema plus a short procedure to compare explanations and preserve uncertainty |

The candidate procedure does not enumerate the scenario's correct explanations or answer. Model, model revision, tokenizer, chat template, and actual model tokenization remain unresolved and must be locked before any call. Do not run an arm until an independent review and separate resource authorization are recorded.

## Matched Request Constants

- Identical evidence bytes and user question per paired scenario.
- Same model/revision, tokenizer, template, schedule, response schema, and completion ceiling.
- Temperature 0, seed 0, maximum completion 96 tokens.
- Scenario order fixed; within-scenario arm order alternates reference-first/candidate-first.
- 32 scenarios produce 64 requests: 32 development calls and 32 evaluation calls if later authorized.
- Duplicate rendered requests are rejected.

Rendered request sizes are currently 2,563-3,414 UTF-8 bytes (mean 2,907.375) against a 16,384-byte ceiling. No compatible tokenizer package or selected model tokenizer is installed; UTF-8 bytes are not token counts. `token_audit.json` records that limitation. Re-audit exact input tokens, model context, completion cap, and request ordering after model selection and before freezing an executable schedule.

## Response Contract

```json
{
  "prediction": "no_change|changed|delayed_change|transient_change|unknown",
  "evidence_ids": ["record-id"],
  "status": "determined|not_determined"
}
```

`unknown` must pair with `not_determined`; a determined category must pair with `determined`. Evidence references must exist in the rendered history, be unique, and be supported by acknowledged records. Invalid JSON or schema output is rejected without repair.

The proposed transition is never included in the request. Answers are evaluated against full returned-frame sequences, not only the final frame. Dispatch failure and unknown outcome are not no-change observations.

## Analysis

Score prediction accuracy only over determinable scenarios; separately report unsupported certainty over underdetermined scenarios. Report valid-output and supported-evidence-reference rates, then by family and split. Coordinate grounding and perception are elicited in separate diagnostic requests, not bundled into this prediction treatment. Aggregate repeated calls/questions by scenario before any inference.