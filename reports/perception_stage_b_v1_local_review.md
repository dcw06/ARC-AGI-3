# Stage B v1 local executable review

Status: **CPU-only scripted prototype; no source approval, provider reservation,
GPU notebook, or live launch authorization.** It implements the next local part
of [the Stage B draft](perception_stage_b_v0_protocol.md). The completed R2
perception evidence and all historical integrated/transient source locks remain
unchanged.

## Exact local question

On the already inspected `ar25-0c556536` development observation, can a
compact target commitment be recorded and checked separately from a legal
action and from contact with a reviewer-marked visible object? This local run
tests the *measurement machinery*, not the model or game outcome. Both arms use
the same frozen baseline raw-grid request builder and deterministic settings.
The target arm changes only the system instruction and JSON response schema to
add an inclusive `grid[y][x]` cell/box or `none`; a coordinate click requires a
non-null target. The control arm retains the exact historical `arc_action_v12`
request. The same sealed prediction and feedback calls are made for each arm;
their answers never enter later policy requests. A prediction is retained before
dispatch. No invalid answer is rewritten into a legal action.

Local cap: two isolated episodes, two actions per arm, twelve model calls
(policy/prediction/feedback per action), 128 completion tokens per call, a
32,768-byte response retention cap, and a 30-second local absolute deadline.
The synthetic adapter returns a transient changed first frame followed by the
unchanged final frame. Its click at `(0,0)` lands inside its declared target,
but outside the reviewer's visible object cells. This intentionally proves the
two scores are distinct. It is not evidence of game mechanics or progress.

## Implemented checks

- [Contract](../research/grounded_action_v1/contract.py): exact requests,
  bounded target coordinates, legal action validation, strict JSON keys,
  distinct binary predictions, and bounded feedback frame indices.
- [Runner](../research/grounded_action_v1/local.py): both arm bootstraps precede
  policy calls; initial canonical hashes must match the retained ar25 state.
  Requests and response bytes/hash/token counts/finish reason are durably
  written before parsing; committed action and prediction are written before
  dispatch. A transport or uncertain-dispatch failure stops the pair without
  retry. Cleanup is attempted for every opened adapter.
- [Independent replay](../research/grounded_action_v1/replay.py): reconstructs
  policy and audit requests, hashes, token parity, action/target bindings,
  fresh pre/post observations, frame changes including transient frames,
  timestamps, budgets, finalization and cleanup receipts. It scores incorrect
  but valid feedback as an outcome, not a technical failure. Reviewer geometry
  is used by replay only and never enters requests.
- [Regression suite](../tests/test_grounded_action_v1_local.py): covers complete
  and incomplete pairs, wrong/missing/out-of-bounds targets, coordinate swap,
  partial and oversized responses, token mismatch, transport loss, uncertain
  dispatch, deadline, cleanup failure, evidence tampering, and valid incorrect
  feedback.

The CPU-only scripted run replayed as 12 calls, four synthetic dispatches,
zero levels, and transient frame index 0 in each step. Its synthetic token
counts (120 prompt, 192 completion) are **fixture values**, not a tokenizer
audit or model-usage estimate. The standalone read-only replay command is:

```bash
python scripts/replay_grounded_action_v1_local.py /path/to/grounded-stage-b-v1.json
```

Generate a local fixture record with:

```bash
python scripts/run_grounded_action_v1_local.py --output /tmp/grounded-stage-b-v1.json
```

## Remaining launch gates

This prototype is not a reviewed live executable. The scripted adapter does
not prove real environment isolation, action receipts, hidden-state equality,
independent process/GPU cleanup or game progress. The local feedback predicate
checks changed frames but does not establish mechanics or feedback use; sealed
audits cannot affect later choices. The two-action limit is a contract test,
not an approved experiment horizon. A live successor still needs a real
development environment adapter, evidence and monitor integration, tokenizer
audit of *all exact and worst-case adaptive requests*, startup-inclusive
runtime sizing, provider budget, GPU-disabled notebook and independent unpacked
review. Only then seek explicit source approval and a **separate fresh compute
authorization**. No GPU attempt is reserved or authorized by this report.
