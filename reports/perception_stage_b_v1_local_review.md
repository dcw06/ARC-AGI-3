# Stage B v1 local executable review

Status: **CPU-only scripted answers with actual offline development-engine
transitions; no source approval, provider reservation, or live launch
authorization.** It implements the next local part
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
request. The same sealed prediction and feedback calls are made for each arm.
Feedback receives the exact committed prediction and its own instruction;
audit answers never enter later policy requests. A prediction is retained before
dispatch. No invalid answer is rewritten into a legal action.

The [case protocol](perception_stage_b_v1_case_protocol.json) freezes ar25 seed 0,
the initial canonical hash, control-then-target order, two actions per arm, and
environment-confirmed level delta as the shared primary outcome. Local cap:
two isolated episodes, twelve calls (policy/prediction/feedback per action),
128 completion tokens per call, and a 32,768-byte response retention cap.
The scripted-only path retains its 30-second local deadline.
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

## Real offline engine and token audit

The [development adapter](../research/grounded_action_v1/engine.py) restores
the committed development archive with SHA-256 checks, stages the
manifest-bound games, and opens two separate local ar25 scorecards. The
[external CPU supervisor](../scripts/run_grounded_action_v1_engine_local.py)
uses a 90-second startup-inclusive local deadline, samples worker RSS and
evidence size, terminates a failed process group, and verifies temporary-game
removal. The independent replay checks equal canonical initial states, action
journals, returned observations and both local scorecard closes.

The completed CPU check is [archived with member hashes](perception_stage_b_v1_local_archive.json).
Read-only clean-checkout replay:

```bash
python scripts/replay_grounded_action_v1_archive.py
```

It verifies twelve scripted calls, four real offline game actions, and zero
level progress in both arms. The scripted `(0,0)` click caused no visible
change in the actual engine. Scripted feedback incorrectly claimed change;
replay retains and scores that mistake rather than treating it as a technical
failure. This is **not model inference or solving evidence**.

Local validation: **20 tests passed** in the CPU WSL development environment,
including opposite predictions on the same transition, an incomplete pair,
token mismatch, uncertain dispatch, archive-backed isolated starts, monitor
evidence exhaustion, and process cleanup. The clean-checkout archive replay
verified all three retained member hashes.

The [pinned tokenizer audit](perception_stage_b_v1_token_audit.json) verified
the tokenizer files and package versions and tokenized every exact request
from this CPU record. The largest policy request used 25,798 prompt tokens;
maximum-cardinality compact and pretty response examples fit the 128-token
cap. For the retained initial grid, feedback with six returned frames used
59,569 prompt tokens and fit; seven used 68,061 and did not. Every returned
frame remains in evidence, but feedback with more than six frames fails
closed before transport. Different grids may tokenize more densely, so the
[token guard](../research/grounded_action_v1/model_service.py) must audit each
exact future live request. It performs no retries and returns raw transport
evidence for durable retention before parity validation.

The Stage A [overlay checker](../scripts/inspect_phase4_perception_stage_a_v1.py)
still requires the original committed PNG byte hashes. It compares decoded
RGB size and pixels for regenerated overlays; `analysis.json` remains
byte-exact. Encoder differences therefore cannot change the findings or
overwrite historical artifacts.

## Remaining launch gates

The [GPU-disabled review notebook](../notebooks/phase4-grounded-action-v1-review-r1/profile.ipynb)
is a hash-bound source snapshot with no launch cell. It is **not a reviewed
target executable**. A live successor still needs retention across the real
model-process bridge, a startup canary, target GPU monitoring and independent
GPU cleanup, a startup-inclusive provider budget with cleanup reserve, and
review of a launch-enabled notebook. The local canonical hash establishes
equal visible starting observations, not hidden-state equality. Fixed arm
order leaves order effects open. Sealed audits measure prediction and
interpretation, not learning from feedback. Only after those gates should
explicit source approval and **separate fresh compute authorization** be
requested. No GPU attempt is reserved or authorized by this report.
