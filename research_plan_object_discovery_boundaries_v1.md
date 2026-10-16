# Independent object discovery and boundaries

October 16, 2026 · Draft v1 · Local preparation only; no GPU authorization.

**Research question:** given only a game board, can the agent find its distinct
visible objects and return the complete set of cells belonging to each one,
without human object descriptions, object counts, target coordinates or masks?

The completed MolmoPoint test established 6/6 successful **cued point hits** on
six exposed frames. This study adds discovery and extent estimation. Its
references, prompts, outputs and scoring must be frozen separately; the earlier
six-call authorization is consumed and cannot cover this study.

## Intended interface

| Stage | Agent input | Output | Evidence of success |
|---|---|---|---|
| Uncued discovery | Plain 448×448 board; one fixed generic inventory instruction | Native decoded point for each proposed object; no supplied count | One-to-one coverage of the frozen object inventory, with duplicates and false detections reported |
| Boundary estimation | Original 64×64 color array and the agent's own discoveries | Exact cell mask for each proposed object; bounding box derived from it | Mask overlap, exact-mask agreement and boundary agreement with independently reviewed references |
| Hierarchy | The same visible evidence | Whole-object/part relationships where the method supports them | Whole objects and parts evaluated separately; parent and child credit never summed as independent discoveries |
| Output inspection | Retained outputs and private reference masks, after inference | Board overlays and error categories | Missing objects, merged objects, split objects, background leakage and boundary misses remain visible |

**Working implementation:** following the recommendation and the owner's request
to continue, independence permits the agent's pixel-processing tools while
withholding human object hints and answers. This remains a draft design rather
than a frozen inference protocol. The reference audit is useful under either
tool-assisted or model-only investigation.

The verified MolmoPoint interface decodes **points**, so a point is not treated
as a segmentation mask. If tools are allowed, the first transparent boundary
baseline takes the same-color, four-connected component containing each model
point. It receives no reference mask, color name, object role or correct seed.
Keep duplicate detections and background seeds in the record. A color component
is a pixel fragment: adjacent objects can merge, and a multicolor or disconnected
object can be split. These are failures to measure, not assumptions to hide.

Grouping several components into a whole object would be a separately specified
agent operation. Its membership rule, inputs and budget must be fixed before
inference. It is not yet implemented or validated. A successful tool-assisted
mask would establish pipeline performance, not MolmoPoint-only segmentation.
If the owner selects MolmoPoint alone, a separate boundary-output contract and
decoder rehearsal are needed; the existing native point API is insufficient to
certify complete masks by itself.

## Reference gate before another model run

The retained six-frame reference set has **94 regions: 37 whole regions and 57
parts**. The local audit found:

| Existing label type/property | Count | Consequence |
|---|---:|---|
| Rectangle labels | 75 | Review whether each is an exact object mask or an enclosing interaction/target area |
| Explicit cell masks | 15 | Review object membership, holes and hierarchy; explicit coordinates alone do not establish semantic correctness |
| Group unions | 4 | Preserve gaps and disconnected members; review whether the group is one object or a container of parts |
| Multicolor labelled regions | 34 | A single-color flood fill cannot be assumed to recover the whole labelled region |
| Labels exactly matching one same-color component | 53 | Useful diagnostic property of existing labels, not a measured segmentation success rate |
| Exhaustive frame inventories verified | 0 | Precision/false-positive denominators and a whole-frame discovery verdict are not ready |

None of these counts changes the earlier target-hit score or its frozen masks.
Some filled rectangles may be correct. Their suitability for segmentation must
be established rather than inferred from their usefulness as click targets.

Before scoring discovery or boundaries:

1. Review every visible instance at a fixed granularity. Keep top-level objects,
   repeated elements and parts separate. Declare which backgrounds, display
   regions and interface groups are included. Do not infer gameplay roles from
   appearance alone.
2. Store exact visible cell membership. Decide whether each interior area is
   object material or a hole/background. Black is not automatically background.
   Bounding boxes are derived summaries; never fill them to invent a mask.
3. Bind labels to the exact frame/grid hash. Declare ambiguous groupings and
   admissible alternatives before viewing new model outputs. Do not exclude
   difficult regions after seeing errors.
4. Mark whether each frame's inventory is exhaustive under that policy. Until
   then, unmatched predictions are **unadjudicated**, not established false
   positives. No complete-discovery passing verdict is available.
5. Keep references, roles, counts and masks outside the model/agent inputs.
   Human review happens privately; current account-only permissions do not
   authorize sharing private boards or raw evidence with collaborators.

## Conditions and measurements

| Condition | Purpose | Limits |
|---|---|---|
| Full-board uncued discovery + predicted-seed masks | Primary pipeline measurement | All seeds come from the model; missing objects count against end-to-end performance |
| Color-component proposals without the VLM | Low-level visual baseline | Components are not relabelled as semantic objects merely because their edges are exact |
| Frozen reference seed + boundary tool, CPU only | Separate boundary diagnostic | Uses privileged seeds; cannot count as independent discovery or agent performance |
| Later whole-object component grouping, if implemented | Test composite-object extent estimation | Separate condition, fixed procedure; not an unnoticed repair of the first condition |

The new input draft uses six generic whole-object requests, each proposing at
most 4,096 new tokens and 96 decoded points. Its separate inventory decoder
preserves full-sequence fragment, sentinel, coordinate and truncation checks.
The completed single-target decoder keeps its original 1,024-token contract.
The single-target scorer is not reused. Mask validation rejects invalid or
duplicate cells, empty individual masks, duplicate IDs and more than 96 objects.
Duplicate detections with distinct IDs remain and cannot earn repeated credit.
Empty inventories remain in the denominator. No clipping, snapping or retries.

| Metric | Required interpretation |
|---|---|
| Point discovery coverage | One-to-one matching to object masks; one point cannot earn credit for several instances at the same hierarchy level |
| Detection precision/recall | Available only with an exhaustive, adjudicated reference policy; duplicate predictions consume predictions without extra matches |
| Mask IoU | Intersection divided by union on exact board cells; missing reference objects receive zero in end-to-end summaries |
| Exact mask agreement | Predicted and reference cell sets are identical; especially useful for small controls and pieces |
| Boundary precision/recall/F1 | Four-neighbor edge cells at original 64×64 resolution; exact-cell agreement is primary, any tolerance is a separate declared diagnostic |
| Merge/split errors | Reported explicitly; a large enclosing mask cannot stand in for several objects |
| Whole objects vs parts | Separate matching and denominators; no combined 94-object success rate |

The implemented diagnostic matching maximizes eligible one-to-one matches,
then summed IoU. Its default match threshold is 0.5; this is distinct from an
advancement criterion and needs confirmation in the frozen protocol.
Report per-object macro results and
per-frame/per-game results so large panels cannot hide small-object failures.
Passing thresholds and the allowed object inventory must be fixed after the
reference review and before model outputs; this draft supplies no automatic
advancement verdict. Visual boundaries do not establish collision behavior.

## Development and later generalization

Use the six retained initial boards for method development and a transparent
first pilot. They are exposed examples, not a hidden benchmark. After the
method is frozen, select and label additional frames from retained logs without
looking at new model answers. Later frames must have their own masks; moved
objects cannot inherit starting coordinates. Transformations of these boards
are useful diagnostics, not independent new-game evidence.

Keep the supplied model image at 448×448 with no overlay for the discovery
condition. The mask tool can read the original 64×64 array. Any component-ID
overlay, crop, coordinate grid or extra description is a separately declared
information condition. Do not adjust the method on the evaluation frames and
then report those same frames as held-out success.

## Implementation and launch sequence

| Step | Status |
|---|---|
| Preserve completed cued-point result and its consumed attempt | Done |
| Audit retained geometry, masks, hierarchy and source hashes | Implemented and run locally; 5 synthetic audit checks pass |
| Tools-versus-model-only boundary scope | Proceeding with recommended model + pixel tools; not a frozen protocol |
| Complete exact masks and exhaustive inventory review | Owner confirmed all 94 unchanged masks and six complete inventories; original export and separate attestation preserved privately |
| Freeze prompts, inventory granularity, mask contract, matching and thresholds | Diagnostic pilot prompt, whole-object granularity, mask procedure and IoU matching bound by the private package; no advancement verdict |
| Prepare separate uncued inputs, inventory decoder, mask baseline and geometric evaluator | Implemented locally; completed six-target runtime remains unchanged |
| Rehearse synthetic geometry failures and source bindings | 50 relevant Python checks and 9 isolated browser control checks pass |
| Provide an exact-mask / exhaustive-inventory editor | Implemented: hover coordinates, cell/component editing, hierarchy and JSON export/import |
| Integrate new model-loading worker, admissions, lifecycle and raw-token replay | Implemented; expanded Linux suite passes all 178 checks without skips |
| Bound generations, output points, tokens, grouping and lifecycle | Draft proposes six generations × 4,096 tokens and 96 points; full runtime budget and grouping remain unfrozen |
| Build/review the exact new private package and source/use bindings | Private template assembled and checked; existing attachments unchanged; current lock and limits in launch preparation report |
| Fresh compute authorization, reservation, preflight and one submission | Not authorized by this draft |

No model request, game action, upload or GPU launch occurred while preparing
this draft. Public artifacts contain methods and aggregate audit counts only;
boards, masks and detailed audit records stay in the git-ignored workspace.

[Local implementation and review handoff](reports/object_discovery_boundaries_v1_preparation_2026-10-16.md).
