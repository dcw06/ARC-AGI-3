# Local perception, control and transition groundwork

Implemented under `research/perception_v1/`, independently of the preflight.
No model calls, environment actions or scorecards. The original provisional
perception protocol remains historical; this local fixture lock does not freeze
or authorize a model comparison, choose a final token budget or promote a policy.

## Fixtures and scoring

`reports/perception_v1_local/fixtures.json` contains the retained ar25 initial
board P1 and four deterministic synthetic boards P2-P5. Each carries a source
group, grid hash, visible object cells/boxes, coarse occupancy, colours,
markings and mechanically computed D4 relations. P1's existing reviewer masks
are visible-geometry annotations, not game entities or winning moves. No game
source is read. Human reference answers stay separate from observations.

P2 is chiral rotation; P3 is chiral reflection; P4 has markings and a stripe;
P5 has different shapes of the same colour. Ambiguous P1 transforms are accepted
as a set and excluded from rotation-versus-reflection scoring. The lossless
PNG and raw grid depict exactly the same palette-index cells; this renderer
check is not evidence that the model or server consumes them correctly.

The scorer implements the proposed bounded output fields and reports separate
numerators/denominators for detection, localization, contour, colours, markings
and relations. Matching maximizes exact rational bbox IoU with deterministic
reference/prediction-order ties and a 0.5 match threshold. Duplicate and
extraneous objects/relations are counted. Reversed relation directions invert
the D4 transform. Contour is conditional on detection with a separate joint
detected-and-contour metric. Invalid/omitted answers contribute zero to fixed
reference denominators; zero predicted objects gives null precision, never 1.
There is no composite score or automatic promotion threshold.

## Controls

Two no-board interface fixtures use the existing `arc_action_v12` schema.
I1 supplies only the schema; directional roles are correctly answered as
unstated. I2 additionally supplies the provisional protocol's interface-role
descriptions. Checks cover arguments for IDs 1-7, a specific off-diagonal click,
one empty-data action and directional IDs. Bounds 0/63, swapped coordinates,
boolean/out-of-range coordinates and illegal arguments are tested.
Correct issuance is not knowledge of a particular game's action effects.

## Transition record v1

`transitions.commit` creates a copied prediction record with episode/game/seed,
step, request and received-response hashes, the full prior observation and its
hash, legal actions, chosen action, intended target, prediction, alternative
and commitment timestamp. A future runner must durably retain its hash before
dispatch; this module does not dispatch or prove external persistence.

`finalize` requires that commitment, an identical acknowledged action, ordered
dispatch/return timestamps, all returned frames, progress counters and an
update citing valid frame indices. It computes per-frame changes against both
the prior observation and previous frame, so transient changes survive even
when the last frame is unchanged. Shape changes are explicit with null cell
counts rather than fabricated comparisons. `verify` recomputes everything and
can bind the next record to the same episode/seed and exact preceding observation.

Prediction, target and update text are bounded model claims, not automatically
true explanations. The module verifies bindings and visible deltas; it does not
infer causal mechanics, adjudicate goal hypotheses or add a live memory policy.
Level-counter deltas are separate from descriptive correctness.

## Verification and boundary

Eleven local tests pass, including gold fixtures, ambiguous/chiral transforms,
inverse relations, malformed and incomplete answers, omissions, duplicate
objects/relations, wrong contours/markings, distractors, coordinate swaps,
invalid controls, transient changes, shape changes and tampered commitments.
The generated fixture artifacts and sources are checksum-locked. Read-only
regeneration and tests:

```sh
python scripts/build_perception_v1_local.py --check
```

The actual model request pair construction, tokenizer/output-cap audits,
supervised perception runner and final study budget are still future work,
after compatibility evidence permits review. None is silently authorized by
the local fixtures. No result here demonstrates solving improvement or closes
Phase 4.
