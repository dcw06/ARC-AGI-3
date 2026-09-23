# Perception diagnostic v1: provisional protocol

**Status: provisional draft; not frozen and not authorized.** Cases, scoring,
limits and budget below are proposals. They will be frozen only after the
multimodal preflight (last section) passes on Kaggle and this protocol is
revised to match its measured facts. No model call, reservation or upload has
been made for this experiment.

## Question

Can the model identify the relevant objects, locate them accurately, and
recognize their geometric relationships from the observation it actually
receives?

Integrated v2 motivated this. Its compact inventory was well-formed, but all
four regions sat on the colour-10 stripe at x=30..32, which the reviewer
annotation marks as a non-object region. None overlapped objects A, B or C. The
first decision then declared a reversed span. Changing span syntax alone could
fix that rejection, but it would not explain or fix the wrong object boxes.
Perception is therefore the primary measurement here, and actions are out of
scope.

## Design

This is a zero-action diagnostic: no game environment, no scorecard, no
dispatch. Each request is independent, with no history, at temperature 0 and
seed 0. There is one response per request, and no retry, repair or fallback.
Invalid output is retained and scored as invalid. It is distinct from a wrong
answer and from a technical failure. `finish_reason` is retained, and any
non-`stop` finish makes the response invalid.

### Cases (5 boards, 64×64, development and synthetic only)

No holdout games and no solution hints. Nothing states what any object does or
what the goal is.

| ID | Source | Content | Main dimension |
|---|---|---|---|
| P1 | ar25 frozen initial frame (existing reviewer reference) | A (colour 5, five internal colour-0 markings), B (4), C (11); same L-shape; colour-10 stripe; borders | Localization, contour, markings, same shape across colours, distractor stripe |
| P2 | Synthetic | Chiral F-shape and its 90° rotation, different colours | Rotation |
| P3 | Synthetic | Chiral F-shape and its left–right mirror, different colours | Reflection versus rotation |
| P4 | Synthetic | F-shape with internal markings; full-height 3-cell stripe distractor | Markings, distractor rejection |
| P5 | Synthetic | Two different shapes in the same colour | Same colour is not the same shape |

Synthetic boards are deterministic, generated from a hash-locked script. Each
has a machine-generated reference: boxes, 3×3 occupancy, colours, markings and
the valid D4 transform set per pair. P1 uses the existing
`reports/integrated_case_v1/geometry_reference.json`. For P1, A→B is ambiguous
between rotation and reflection (the reference accepts both), so P1 is
excluded from reflection-versus-rotation scoring. P2 and P3 carry that
dimension. The F-shape `[[0,1,1],[1,1,0],[0,1,0]]` was checked to be chiral,
with four distinct rotations.

### Observation representations (the comparison)

- **R-text:** the current representation, the JSON integer grid as sent today.
- **R-image:** a lossless rendering of the same grid. Each cell is a uniform
  16×16 px block in a fixed 16-colour palette, giving 1024×1024 px. That is
  exactly one 16 px vision patch per cell (patch 16, merge 2), so the pinned
  processor does not resize it. The legend (colour index to RGB) and a
  statement that coordinates are cell indices are sent as text. Offline
  arithmetic from the pinned preprocessor puts this at 1,024 image tokens per
  board, against about 8,700 text tokens for the grid.

The system prompt, task instruction and output schema are **byte-identical**
across the two representations; only the observation block differs.
Coordinates are always grid cells (`grid[y][x]`, x = column).

### Fixed output contract

A strict schema with every array and string bounded:

- `objects`, at most 6, each with:
  - `id`
  - `bbox` `[xmin,ymin,xmax,ymax]`
  - `colors`, at most 3
  - `occupancy`: a 3×3 0/1 mask over the object's own bbox
  - `has_markings`, `marking_colors`
  - `description`, at most 48 characters
- `non_object_regions`, at most 3: `bbox`, `description`.
- `relations`, at most 6: `a`, `b`, `same_shape`, and `transform` from the
  eight D4 elements (`rotate_cw_0/90/180/270`,
  `mirror_left_right_then_rotate_cw_0/90/180/270`), plus `different_shape` and
  `uncertain`.

There is no span enumeration. The worst-case output will be tokenized with the
pinned tokenizer before freezing, as was done for integrated v2.

### Scoring (deterministic; each dimension separate; no composite)

Every metric is computed per case × representation, with explicit numerators
and denominators. With five boards this is **descriptive**, with no
significance claim.

**Invalid output.** A response that fails parsing, schema or bounds, or that
finishes with anything other than `stop`, is *invalid* for that case. It stays
in every denominator below as a failure (for example, recall 0 on that board).
Invalid counts are reported separately. Valid-only rates may be shown only
alongside the all-cases rate and their own denominators.

**One-to-one object matching.** Predicted objects are assigned to reference
objects as follows:

- Candidate pairs are those with bbox IoU > 0, using exact rational IoU.
- The assignment is the one-to-one choice that maximizes total IoU.
- Ties are broken deterministically by (reference order, prediction array
  order).
- A pair counts as *matched* only if its IoU is at least 0.5.
- A reference left without a match is a *miss*.
- A prediction left unassigned, or assigned below 0.5, is *extraneous*.
- An extraneous prediction with IoU ≥ 0.5 against an already matched reference
  is additionally counted as a *duplicate*.

**Metrics:**

1. **Detection.**
   - Recall = matched / reference objects (a fixed denominator per board).
   - Precision = matched / predicted objects; this is `null` when nothing was
     predicted, never 1.
   - Distractor error: any prediction with IoU ≥ 0.5 against a declared
     non-object region (stripe, border).
2. **Localization.** Bbox IoU for each matched pair, and exact-bbox count out of
   matched pairs.
3. **Contour, conditional on detection.** The reference mask is the 3×3
   occupancy of the reference object inside its own bbox. Block boundaries are
   `floor(i·size/3)`, and a block is occupied if at least half its cells belong
   to the object. It is scored only on matched pairs, as exact matches out of
   matched and cells correct out of 9 × matched. It is **not** independent of
   localization: an undetected object has no contour score. The joint rate,
   detected and contour exact out of reference objects, is reported too.
4. **Colours.** Set equality on matched pairs, out of matched.
5. **Markings.** On matched pairs: `has_markings` correct, and marking colour
   set equal, each out of matched. Plus the joint rate out of reference objects.
6. **Relations.**
   - Reference pairs are fixed per board, oriented in reference order.
   - A predicted relation maps to a reference pair only if both of its objects
     are matched. If it names them in reverse order, its transform is inverted
     before scoring.
   - The first predicted relation for a pair, in array order, is scored. Later
     ones for the same pair are *duplicates* and are ignored.
   - A reference pair with no mapped relation counts as *missing* and is scored
     incorrect.
   - A relation naming any unmatched object is *extraneous*.
   - Same shape: correct `same_shape`, out of all reference pairs.
   - Transform: in the pair's valid D4 set, out of reference pairs whose
     shapes are the same. On the chiral pairs (P2, P3), the coarse class
     (rotation versus reflection) is also reported over the same denominator.

Provisional working threshold for "grounding works" in a representation, which
gates the next stage:

- on P1, all three objects detected at IoU ≥ 0.5 and the stripe not reported
  as an object;
- at least 4 of 5 boards with all objects detected;
- contour exact on at least two thirds of matched objects.

The threshold is to be revisited and then frozen with the cases.

### Action-interface probe (separate from perception)

This tests knowledge of the interface, not discovery of what actions do. Two
text-only requests with no board:

- **I1:** the agent's actual action specification as sent today. Legal ids are
  1..7; ACTION6 takes integer x,y in [0,63]; the others take empty
  `action_data`.
- **I2:** I1 plus the official ARC-AGI-3 documented roles: 1–4 directional, 5
  interact, 6 coordinate click, 7 undo.

Each asks the model to:

- classify every legal action as coordinate-taking or not;
- emit one well-formed click at a given cell and one well-formed
  non-coordinate action;
- say which actions are directional.

For the directional answer, I1 accepts "not stated" as correct, because the
current spec does not say. Scoring is exact per item. Integrated v2's inventory
claimed ACTION1 and ACTION2 take x,y; this probe measures that failure directly.
No answer here is evidence about what any action does in any game.

### Proposed limits and budget (separate; zero authority)

- **Calls:** 10 perception calls (5 boards × 2 representations) plus 2
  interface calls, 12 study calls in total. Add one text canary and one image
  canary. Zero actions and zero scorecards.
- **Caps:** perception output 1,024 tokens (to be confirmed by audit),
  interface output 256 tokens. Prompt at most 16,000 tokens per request, with
  exact pre-inference tokenization including image tokens. No truncation.
- **Time:** provider 1,800 s, internal 1,680 s, 300 s per request.
  Integrated v2 measured 525 s model startup and 669 s total.
- **Attempts:** one attempt, no retry. Nothing is carried over from earlier
  reservations.

## Multimodal preflight (separately budgeted; must pass before freezing)

Locally verified:

- the pinned config is `Qwen3VLMoeForConditionalGeneration` with vision patch
  16 and merge 2;
- the pinned chat template handles image content;
- the vLLM launch spec does not disable images;
- `preprocessor_config.json` exists at the pinned Hugging Face revision
  (SHA-256 `6a970fd0…90f8`).

**Not verifiable locally:** Kaggle's model mount holds 81 files and 64.5 GB,
against 16 files and 32.3 GB at the pinned Hugging Face revision. It is
packaged differently, so its image-processor files cannot be inferred. No image
request has ever been sent through this stack.

The preflight is one minimal private run with zero actions and zero
scorecards, using the same model, engine and unchanged launch spec. The
implementation is `certification/phase4_multimodal_preflight_v1`.

1. **Mount inventory.** Record every file's name and size, and hash each small
   config. Record whether the preprocessor configs are present and match the
   pinned hashes.
2. **Text canary.** The existing canary, which must finish with `stop`.
3. **Probes.** Four calls, each attempted and recorded; a failure in one does
   not abort the rest:
   - **T0**, text control: the board question with no image.
   - **I1**, a 4×4-cell canary at 16 px/cell (64×64 px). This is below the
     processor's pixel minimum, so the resize must appear in the retained
     processed dimensions.
   - **I2 and I3**, two visibly different synthetic 64×64 boards at
     **1024×1024 px**, the intended perception size. Same question, different
     correct answers.
4. **Processor evidence**, computed in the model interpreter from the
   *mounted* processor. For each image request, retain:
   - `image_grid_thw` and the processed pixel dimensions;
   - the processor's expanded prompt count;
   - a manual count: template tokens − 1 + t·h·w/merge²;
   - the frozen local expectation.

   The server's prompt count must equal the processor count.
5. **Consumption evidence.** The server's I2 − T0 prompt-token delta must equal
   the processor's image expansion + 2. Only the vision-marker tokens separate
   those two requests. Correct answers do **not** substitute for this evidence.
6. **Behavioural sanity check.** The I2 and I3 answers are compared. Identical
   answers to visibly different images mark the result *review required*,
   even if the processor evidence passes. Correctness is recorded, not required.
7. **Cleanup.** Independent process and GPU cleanup, as in every earlier run.

**Outcome classes.** These are kept distinct; they are not collapsed into
"unsupported":

| Class | Meaning |
|---|---|
| `image_input_verified` | Accounting and consumption evidence pass for I1–I3 |
| `dependency_missing` | Preprocessor files are absent, or processor or image libraries fail to load. No image request is sent |
| `image_rejected_by_server` | Server returns an HTTP error for an image request; the body is retained |
| `token_accounting_mismatch` | Server prompt tokens differ from the processor count |
| `image_not_consumed` | Server delta differs from the expansion |
| `lifecycle_failure` | Startup, monitor or cleanup failure |

Separately, `arithmetic_revision_required` marks a verified run whose processor
counts differ from this document's arithmetic. The protocol is then revised,
but support is not denied.

**Any outcome other than `image_input_verified` without review flags blocks the
representation comparison pending review.** It does not automatically
establish that images are unsupported, and it does not launch a text-only
substitute. Proposed budget: one attempt of 1,800 provider seconds, no retry,
with its own review lock, source approval and compute authorization.

## After perception

Only once grounding meets the frozen threshold: one action, then a predicted
change, then the observed change, then a revised hypothesis. After that, short
action sequences. Each stage is separately scoped and authorized. Production
certification, admission limits and exact billing remain open. Phase 4 remains
open.
