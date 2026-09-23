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

### Scoring (each dimension reported separately; no composite)

1. **Detection.** Predicted objects are matched to reference objects by bbox
   IoU. Report recall and precision at IoU ≥ 0.5, and whether a declared
   non-object distractor (stripe, border) was reported as an object.
2. **Localization.** Bbox IoU per matched reference object, and exact-bbox
   rate.
3. **Contour.** The 3×3 occupancy, scored against the reference object's own
   mask (block occupied if at least half its cells belong to the object) as
   exact match and cells correct out of 9. It is scored for matched objects
   only, so it stays independent of localization error.
4. **Colours.** Set equality with the reference colours.
5. **Same shape across colours.** Accuracy of `same_shape` per reference pair.
6. **Reflection versus rotation.** The transform is correct if it lies in the
   pair's valid D4 set. On chiral pairs (P2, P3), also report the coarse class:
   rotation versus reflection.
7. **Markings.** `has_markings` correct, and marking colours correct.

Every metric is computed per case × representation. With five boards this is
**descriptive**, with no significance claim.

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

The preflight is one minimal private run: zero actions, zero study calls, same
model, engine and launch spec. It must:

1. Inventory the mount: every file name and size, plus hashes of the small
   configs. Require the preprocessor config to be present and record whether it
   matches the pinned hash.
2. Start the server unchanged and send one text canary, expecting
   `finish_reason=stop`.
3. Send one image canary: a lossless 4×4-cell rendered grid with a known
   answer (for example, the colour index of a stated cell). Record the exact
   response and whether it is correct. Correctness is informative, not a pass
   condition.
4. Record server prompt tokens for the image request against the offline count
   (text tokens plus the computed image tokens). A mismatch is recorded and
   blocks freezing R-image until explained.
5. Verify independent process and GPU cleanup, as in every earlier run.

Proposed budget: one attempt, 1,800 provider seconds, no retry, with its own
review lock, source approval and compute authorization. If the preflight fails,
the perception experiment proceeds text-only (R-text plus the interface probe),
and R-image is recorded as unsupported on this stack rather than as a
perception result.

## After perception

Only once grounding meets the frozen threshold: one action, then a predicted
change, then the observed change, then a revised hypothesis. After that, short
action sequences. Each stage is separately scoped and authorized. Production
certification, admission limits and exact billing remain open. Phase 4 remains
open.
