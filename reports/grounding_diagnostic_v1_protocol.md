# Observation-grounding diagnostic v1: protocol review draft

Status: **pending protocol review; zero model calls authorized**. This is an
offline case package, not a launchable notebook or a new solving experiment.
The transient-frame experiment is closed as **no demonstrated benefit** and must
not be repeated unchanged. Its consumed reservation supplies no new authority.

## Question and scope

Can the frozen model read spatial information in the numeric-grid representation
used by the policy: locate explicitly specified visible features, map coordinates
to cells, and identify supplied frame changes? These probes measure explicit
grounding under direct questions. Success would not demonstrate that an action
policy uses the information, understands game rules, or improves solving. Failure
would identify a concrete representation or grounding weakness to investigate.
This is not an image-vision benchmark: inputs remain integer grids, with no PNG
conversion, game source, winning moves, feedback hints, or action history.

## Retained-data construction and exact selection

Only `evidence/phase4-closed-loop-v1-r1-completed-v1.zip` is read. Its SHA-256 is
`994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d`.
Use the no-concrete-examples episode for each of `ar25`, `ft09`, `ls20`, and `sc25`,
in that fixed order. These are development observations, not unseen test games.
Twelve cases are fixed before any model output: three per game.

1. **Locate (four cases):** use the last frame of the initial observation. Select
   the least frequent present color ID, tie-breaking by smallest numeric ID.
   Request the number of matching cells, their inclusive bounding box, and the
   first matching cell in row-major order. The target is all cells of that color,
   not an inferred object or connected component. Disconnected cells count too.
2. **Coordinate lookup (four cases):** on that same frame, choose the first cell
   in row-major order whose x differs from y and whose transposed coordinate is
   in bounds with a different color. Ask for its color ID. No coordinate is
   derived from a winning move. Selection is deterministic and stresses axis
   confusion; it is not a representative accuracy sample.
3. **Changes (four cases):** scan acknowledged steps in order, then returned
   frames in order, comparing each with that step's prior final frame. For ar25,
   select the first identical pair; for the other three games, the first changed
   pair. Supply both frames and request changed-cell count, inclusive bounding
   box, first changed coordinate, and old/new color at that coordinate. The ar25
   control expects zero and null spatial fields. Frames are retained verbatim,
   including intermediate frames; no synthetic changes or source labels are used.

There is no cropping, resizing, rotation, recoloring, answer-dependent selection,
or post-result substitution. The build must fail if a specified case is absent.
All frames must be rectangular integer grids in the retained 0â€“15 palette, at
most 64 by 64; two-frame comparisons require identical dimensions. Coordinates
are zero-based, x rightward/column and y downward/row; bounds are inclusive.
The first cell is ordered by y, then x. Null fields are required when no cell
qualifies. Color IDs carry no semantic names.

`cases.json` contains model-visible tasks and exact message strings.
`answers.json` and `provenance.json` are evaluator-only: do not send them, game
identities, filenames, or source references to the model. Every source frame
records its archive member hash and index. An independent flattened-array check
verifies the mechanically generated answers. The review lock binds the generator,
protocol, cases, answer key, and provenance. Preserve this revision after review.

## Proposed execution contract, subject to later approval

Use the same frozen Qwen3-VL-30B-A3B-Instruct-FP8 model, tokenizer identity, and
vLLM stack as transient v2. Proposed decoding: temperature 0, seed 0, non-thinking,
maximum 128 completion tokens; one fresh independent request per case in case-ID
order. The diagnostic prompt is deliberately different from the action prompt:
it states the exact grounding task and coordinate convention, with no concrete
answer examples. No dialog history, action dispatch, reset, fallback, or retry.

Before launch, implement a strict per-task JSON schema with exact keys, required
integer types (booleans rejected), coordinate bounds, nullable spatial fields,
and no additional properties. Schemas may constrain structure and bounds but
must not encode the answer's color, count, coordinates, or change status. Do not
turn model output into permissive text parsing or coerce incorrect answers.

Proposed cap: 12 diagnostic completions plus at most one separately labeled
startup canary (13 total). This is not an authorization or a reservation. A future
runner must separately freeze a startup-inclusive compute budget, deadlines,
cleanup, and evidence limits before seeking explicit compute authorization.
No GPU-disabled notebook or live-run approval is implied by this protocol draft.

Before approval, audit the actual frozen tokenizer on all exact requests, with
truncation disabled, prompt plus output at most 65,536 tokens and compact/default
transport at most 65,536 bytes. If a case fails, revise and review a new package;
never silently truncate, crop, or drop cases. Actual tokenizer auditing is still
pending and cannot be replaced by character counts.

## Scoring and evidence requirements

Freeze an independent strict grader before model calls. Report each task family's
exact-case accuracy out of four, plus field-level errors: count, bounding box,
coordinate, color, old/new colors, and false-positive change on the unchanged
control. Report coordinate axis-swap matches separately as a descriptive error
pattern. Do not hide partial failures in a single aggregate score or infer a
population success rate from four hand-selected cases. Malformed answers are
incorrect, while infrastructure/token/evidence failures make the attempt
incomplete; retain them and report coverage rather than silently dropping cases.

Retain exact request identity/hash, bounded response body/hash and observed token
counts **before validation**, across process boundaries. Require independent
token parity, request/response bindings, complete case inventory, and final cleanup.
Independent replay must reconstruct answers from the archived frames, not trust
an edited answer key or model self-assessment. Raw output and invalid responses
must remain available for review. No model calls occur during this offline build.

## Interpretation and separate Phase 4 gates

Differentiate locating a feature, translating coordinates, and comparing frames;
do not infer a memory or scheduling remedy from a failure without inspecting the
specific inputs and errors. Conversely, a passing direct-question diagnostic
does not establish action relevance or warrant another solving run automatically.

Production **one-scorecard/110-distinct-game certification**, workload-specific
admission limits (including production `C_admit`), and accounting remain open.
Neither this diagnostic nor another solving experiment closes those gates.

Offline regeneration check (standard library only):

```bash
python scripts/build_grounding_diagnostic_v1.py --check
```
