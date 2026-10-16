# Object discovery and boundaries: local preparation

October 16, 2026. Separate uncued inputs, an inventory decoder, color-component
mask baseline, geometric scorer and private reference editor are implemented.
No model requests, game actions, uploads or GPU jobs occurred. The completed
6/6 cued-point result and its consumed attempt remain unchanged.

| Deliverable | Current behavior |
|---|---|
| Uncued inputs | Six plain 448px boards with one generic whole-object prompt; no target labels, counts, masks or roles |
| Reference isolation | Seven input files only; references stay outside that directory |
| Proposed limits | Six generations, at most 4,096 new tokens and 96 points each; draft only |
| Native decoder | Separate inventory cap; full-sequence checks retained; old 1,024-token decoder unchanged |
| Boundary baseline | Same-color edge-connected region under each predicted point; no background filtering, hole filling, snapping, merging or duplicate suppression |
| Geometry scoring | Exact cells, IoU, exact-mask agreement, boundary F1 and one-to-one matching; missing labelled objects contribute zero |
| Reference protection | Unreviewed masks, removed source labels, changed grids, frame hashes, source or cued requests refuse evaluation |
| Incomplete inventory | Precision and false-positive claims unavailable; unmatched predictions unadjudicated |
| Hierarchy | Whole objects and parts scored separately; semantic grouping/parent prediction not implemented |
| Automatic passing verdict | None; geometry scoring supplies no model-run certification or advancement approval |
| Private editor | Hover coordinates, cell brush/eraser, component union/subtraction, parent/disposition selection, undo and JSON export/import |
| Verification | 50 relevant Python tests and 9 isolated browser control checks passed |
| Actual agent inference | Not executed; new worker/lifecycle/replay integration and launch package outstanding |

The existing 94 regions comprise 75 rectangles, 15 explicit masks and four
groups. They are not promoted into exhaustive segmentation truth automatically.
Every new mask review and inventory-completeness flag starts unconfirmed.
Edits invalidate confirmations. Browser tests use a throwaway profile and do
not create owner review evidence. Test pages are kept outside the served folder.

A same-color region can be only part of a multicolor object, or can join objects
that touch. Background seeds and duplicate masks are retained. Semantic
component grouping needs its own fixed procedure and remains outstanding.

## Local review workflow

1. Choose a board and object/part. Check exact cells, holes and parent relations.
   Use component addition for multicolor/disconnected objects and the brush for
   corrections. Add missing instances.
2. Mark regions included, ignored under the policy, or ambiguous. Preserve
   source regions with explicit dispositions instead of deleting them.
3. Confirm each reviewed mask. Enter a reviewer label. Confirm a complete
   inventory only after reviewing all visible objects under the policy;
   unresolved ambiguity prevents that claim.
4. Download `arc3-object-boundary-review.json`. Browser backup is a convenience;
   the exported JSON is the portable saved record. Import lets you resume.
5. Validate the export against the preparation before using it for evaluation.
   The scorer consumes supplied frame-bound masks; future model results also
   need separate raw-token, admission and lifecycle verification.

```sh
python scripts/prepare_object_discovery_boundaries.py --source <retained-target-preparation> --output <new-private-preparation>
python scripts/build_object_boundary_review.py --preparation <new-private-preparation> --output <private-folder>/index.html
python -m http.server 8772 --bind 127.0.0.1 --directory <private-folder>
python scripts/evaluate_object_boundaries.py --preparation <new-private-preparation> --review <exported-review.json> --predictions <frame-bound-predictions.json> --output <new-private-evaluation.json>
```

Detailed source-bound receipts, boards and masks stay git-ignored. The local
server serves only the review page on loopback, with no write API, cloud access
or inference endpoint. No prior approval or consumed attempt authorizes the
proposed inventory run.
