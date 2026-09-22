# Grounding diagnostic v1: source review candidate

Status: GPU-disabled, pending explicit source approval and separate compute
authorization. No model calls, GPU runs, reservations, actions, or scorecards have
been made. The earlier `grounding_diagnostic_v1` draft is preserved. The new
implementation lives in `certification/phase4_grounding_v1`.

## Frozen question, cases, and correlation

Can the current model extract numeric spatial/change information from its raw
grids when directly asked? There is one fixed prompt per task type and no policy
or representation comparison. The twelve cases use only retained development
observations from ar25, ft09, ls20, and sc25, three per game. Original source is
the archived closed-loop v1 run, SHA-256
`994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d`.
The builder reads only observation/trajectory records, never game source.

Grid reading uses the first row-major off-diagonal cell whose transposed location
has a different numeric color. Localization uses a unique four-neighbor connected
region specified by color and area. Flood-fill all same-color components; eligible
regions have area at least 2 and less than half the frame, with no other component
sharing that color and area. Choose smallest area then smallest color. Ambiguous
or missing regions are rejected, not guessed. The independent evaluator uses
union-find rather than the builder's flood fill.

Change cases compare a prior final frame with a retained returned frame: first
unchanged pair for ar25, first changed pair for ft09/ls20/sc25. The ft09 case
includes an intermediate transient change. No pixels are synthesized or edited.
Scan acknowledged steps and returned frames in order; fail if no case qualifies.
Answers contain changed-cell count, inclusive bounding box, row-major first
changed coordinate, and old/new colors. Unchanged means count zero and null
spatial/color-change fields. Every source member is hashed with a frame index.

Coordinates are zero-based `(x,y) = (column,row)`, right/down; bounds inclusive;
grids remain rectangular integer arrays in palette 0–15 and at most 64 by 64.
No holdout data, game labels in requests, winning moves, coordinate history,
cropping, rotation, color names, or source-derived targets are included.
Related cases are conservatively grouped by source episode: **four source
groups**, not twelve independent observations. The exact inventory and requests
are in `certification/phase4_grounding_v1/cases.json`; expected answers and source
metadata are never included in the model request.

## Model and scoring contract

Keep the frozen Qwen3-VL-30B-A3B-Instruct-FP8 artifact, tokenizer files, vLLM
0.19.0, transformers 4.57.6, raw numeric grids, temperature 0, seed 0, and
non-thinking decoding. There is one request per case, in fixed order, with 128
completion tokens and strict task-specific JSON schemas. Schemas encode only
types/bounds, not correct colors, coordinates, counts, or whether a change exists.
The existing one-shot transport canary is retained separately; its ACTION6-shaped
JSON is never dispatched and is not scored as a grounding answer.

Independent scoring recomputes answers from the retained grids. Report exact
accuracy by task and source game, source-group membership, field errors, axis-swap
matches, malformed answers, transport failures, unattempted cases, prompt/output
tokens, and service latency. Per-game/task denominators remain the full planned
inventory, with incomplete coverage explicitly reported. Do not interpret these
small purposive samples as independent population estimates.

**Correctness is an outcome, not technical acceptance.** A structurally valid but
wrong answer remains a complete response with an incorrect score. Malformed
content is counted as incorrect/malformed and does not itself fail the lifecycle.
Transport, token-parity, deadline, evidence, or cleanup failures cause technical
failure; partial responses and metrics remain available. No retry, repair prompt,
fallback, or case substitution is allowed. Actual vLLM support for these schemas
still needs target validation during the separately authorized attempt.

## Supervised path and new budget proposal

Reuse the verified split model/control interpreters, independent monitor before
GPU readiness, process-group supervisor, bounded logs, exact tokenizer audit,
Unix process bridge, and independent cleanup probe. No Arcade environment is
instantiated and no scorecard is opened. The control environment still installs
its frozen dependencies; competition attachment provides those wheels, not live
game interaction. Requests are retained before transport and bounded responses,
hashes, request identity, and observed counts before token/answer validation,
including across bridge errors and expired replies.

Proposed **one 1,800-second provider attempt**, not another hour or reused authority:

| Limit | Frozen value |
|---|---:|
| Diagnostic / canary / total completions | 12 / 1 / 13 |
| Completion cap / total generated-token ceiling | 128 / 1,664 |
| Startup-inclusive internal deadline | 1,680 seconds |
| Absolute admission cutoff / cleanup reserve | 1,380 / 300 seconds |
| Install / model startup stage caps | 450 / 750 seconds |
| Request window / individual request timeout | 300 / 120 seconds |
| Provider margin beyond internal deadline | 120 seconds |
| Context / serialized request limit | 65,536 tokens / 65,536 bytes |
| Retained response / total evidence | 8 KiB / 64 MiB |
| RSS / GPU memory / scratch ceilings | 128 GiB / 86 GiB / 4 GiB |
| Actions / scorecards / retries | 0 / 0 / 0 |

The previous measured install was 130.872 seconds, model startup 408.948 seconds,
and first workload readiness 542.453 seconds. The prior 120-call window took
207.762 seconds. The new proposal allows a 300-second window for twelve diagnostic
calls with explicit startup margins, then cleanup. These observations inform a
proposal, not a guarantee: grids and schema differ. Stage maxima are clamped by
the global cutoff and need not all fit; slow startup fails closed. See the exact
proposal in `phase4_grounding_v1_budget.json`.

Pinned CPU tokenizer audit covers all thirteen exact messages: 135,258 total
prompt tokens including canary; largest diagnostic prompt 17,128 tokens. Every
request passes byte/context limits without truncation. This is not a new model
inference or a target vLLM validation. Runtime checks repeat tokenization/parity.

## Review and reproducibility

The local suite exercises coordinate swaps/boundaries, unchanged/transient frames,
ambiguous regions, malformed/duplicate JSON, missing/duplicate cases, request
drift, response retention across token mismatches/bridge, correct/incorrect/failing
responses, deadlines, evidence exhaustion, monitor failure, and cleanup rejection.
Local lifecycle evidence includes correct, all-incorrect, malformed, transport,
and mismatch fixtures, explicitly marked as scripted and never target evidence.

From a clean checkout with the project's Python 3.12 CPU dependencies:

```bash
python scripts/build_phase4_grounding_v1.py --check
python scripts/check_phase4_grounding_v1.py --replay
```

The replay command is read-only, verifies archive member hashes, regenerates cases
from the committed observation archive, and recomputes scores. No ignored downloads,
model weights, credentials, game source, or GPU are required. Local archive and
test/token/package receipts are under `reports/phase4_grounding_v1_*`.

The new private/offline notebook is GPU-disabled. Its unpacked source must verify,
compile, and reject absent authority before installation. Separate source/compute
receipts bind the review lock and exact budget; consumed/mismatched authority is
rejected. A deterministic launch packager, exclusive pre-upload claim, and runtime
marker permit only one managed launch after approval. Manual replay in a fresh
provider session cannot be prevented by local files; it is not authorized.

**Stop here for review.** No source or compute approval is inferred from this
implementation request. After approval, separately record both decisions, reserve
once, package/verify, and launch privately and unscored. No full-game run follows
automatically. Localization errors suggest grounding/representation investigation;
accurate diagnostic perception with ineffective gameplay suggests inspecting
action selection/planning, without claiming causality from this small sample.

The transient comparison stays closed as no demonstrated benefit. Production
one-scorecard/110-distinct-game certification, workload-specific admission limits,
and accounting remain open. Neither diagnostic outcome promotes a policy or
completes Phase 4.
