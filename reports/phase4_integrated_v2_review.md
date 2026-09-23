# Integrated ar25 v2: compact-output contract repair

Revision of the integrated ar25 case after v1 stopped at an unusable inventory
response (see `phase4_integrated_v1_disposition.md`). The v1 run, evidence and
disposition are unchanged. This package repairs only the output contract and its
evidence path; it is not a repeat of v1, and it adds no memory, planning, policy
promotion or new game. Output burden and grounding difficulty both remain
plausible explanations for the v1 stop; this revision tests the first without
presuming it was the cause.

## What changed from v1

**Coarse inventory.** At most four regions, each a bbox `[xmin,ymin,xmax,ymax]`
with 48-character silhouette and markings; at most three relationships, seven
controls and two hypotheses. The inventory must not enumerate cells or row spans.
Detailed row-span masks appear only for the one selected target in a decision,
bounded to 12 spans. Every array has `maxItems` and every string `maxLength` in
the strict schema, and the parser re-checks them independently.

**Contour accuracy kept separate.** Inventory is scored only by bbox IoU against
the frozen reviewer masks (`localized` at IoU >= 0.8); its `contour_accuracy`
field points to the decision target instead. Each decision taken on the frozen
initial frame is scored cell-by-cell (IoU, precision, recall, exact) against the
reference masks. A bbox covering object B scores IoU 1 as a bbox but 45/81 as a
contour. Decisions on later frames stay `requires_current_frame_adjudication`;
reference masks are never tracked onto changed frames or sent to the model.

**Caps.** Control 128, inventory 2048, decision 2048 (was 1024), feedback 1024.
The decision increase follows the budget audit below: its worst case needs 1,764.

**`finish_reason` retained end to end.** Transport reads it from the provider
response; the model-process bridge checks it against the audit record; response
evidence stores it before validation; replay requires it on every call. Any
non-`stop` finish makes the call invalid even if its body parses. A missing
field fails replay. The startup canary must finish with `stop`.

## Output-budget feasibility

`phase4_integrated_v2_output_audit.json` tokenizes, with the exact pinned
tokenizer, a response for every stage in which every array is at maximum
cardinality and every string at maximum length. Each uses realistic English and
punctuation-stress text, in compact, normal and pretty-printed JSON (18 cases).
All fit with one end token. Worst cases: inventory 1,767/2048, decision
1,764/2048, feedback 688/1024. Full responses are in
`phase4_integrated_v2_output_examples.json`.

Calibration: re-tokenizing the actual v1 cap body offline gives 2,048 tokens,
equal to the server's recorded completion count. That body was 2,612 bytes, mostly
digits and `", "`, about 1.3 bytes per token. That density is why v1's
row-span inventory could not fit. The audit is not a proof over arbitrary Unicode
or unbounded whitespace. Whether vLLM 0.19's guided decoding enforces every
`maxItems`/`maxLength` is unverified locally; a violation is rejected by the
parser as `invalid_output`, never repaired.

## Partial and invalid responses

Supervised CPU fixtures truncate the inventory, decision and feedback stages
mid-JSON with `finish_reason=length`. A further mode replays the **actual v1
truncated body** (hash-checked from the committed v1 archive; 2,048 completion
tokens). In every case:

- the complete received body, hash, byte count and `finish_reason` are retained;
- the call is marked model-invalid and the structured episode stops as
  `invalid_output`;
- the partial JSON is not repaired, completed, or retried, and there is no
  fallback action;
- downstream stages are censored, not scored: no geometry, and no dispatch after
  a truncated decision; a truncated feedback keeps its already acknowledged
  action;
- the control arm is unaffected.

Deleting the retained `finish_reason`, or turning a valid body into a `length`
finish, fails replay. Transport, token-count mismatch and cleanup failures still
terminate as technical failures with verified cleanup.

## Input admission (unchanged limit, stated explicitly)

`phase4_integrated_v2_token_audit.json` tokenizes all 25 requests of the
full-cap scripted trajectory (557,140 prompt tokens, largest 28,944), the
canary and the initial inventory request (8,692). A feedback request carrying
eight returned frames needs 76,606 tokens and is rejected by the 60,000-token
guard. v1's retained ar25 observations each had one frame. A transition that
returns roughly six or more frames would therefore end the case as a technical
incomplete, without truncation. Approval should account for this.

## Local results

`phase4_integrated_v2_local_checks.json`: 27 tests passed. Eleven supervised CPU
modes behaved as expected. The eight technical-pass modes (correct, full cap,
incorrect, invalid, three partial stages, v1 body) passed. The three fail-closed
modes (mismatch, transport, cleanup) were rejected with cleanup verified. The
monitor-fault run was rejected with cleanup verified, and a checksum-bound
archive replay passed. No model calls, GPU, uploads or environment access to
remote services.

## Compute proposal, no authority

Same shape as v1, with a fresh proposal: one 3,600-second provider attempt;
3,300-second internal lifecycle, 3,000-second admission cutoff, 300-second
cleanup reserve, 1,200-second study window, 450 s install, 900 s model
readiness, 120 s per request. At most 25 study calls plus one canary, 16 actions,
27,776 generated tokens including the canary. The generated-token ceiling rises
from 19,584 because of the larger decision cap. Study prompt ceiling 1,500,000
tokens. Nothing from v1's consumed reservation carries forward.

## Review boundary

The notebook is private, offline and GPU-disabled; it refuses execution without
a source approval and separate compute authorization bound to this review lock,
plus an unconsumed reservation. User intent is recorded in
`phase4_integrated_v2_launch_intent.json` and is not an approval. These checks
do not show that the target accepts the new schemas, that the model will ground
objects correctly, or that the scaffold improves solving. Production
one-scorecard/110-distinct-game certification, admission limits and exact
billing remain open. Phase 4 remains open.
