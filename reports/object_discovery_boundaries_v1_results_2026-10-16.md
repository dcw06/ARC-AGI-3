# MolmoPoint: completed uncued object-discovery and boundary pilot

October 16, 2026. **The run completed, but this pipeline does not yet
demonstrate reliable independent object discovery and boundaries.** Against
the owner's 37 reviewed whole-object masks, 7 generated masks match at the
predeclared IoU threshold of 0.5 and 3 are exact. Five of six responses are
valid. ls20 reached its 4,096-token cap and receives no partial-output credit.

Runtime lifecycle and independent scientific replay pass. The separate
deployment identity check remains failed: Kaggle created a title-derived
notebook slug instead of the requested slug. The original warning and
consumed attempt are preserved; no full deployment clearance is asserted.

| Initial level-1 board | Reviewed whole objects | Valid mask proposals | IoU ≥ 0.5 matches | Exact masks | Valid response |
|---|---:|---:|---:|---:|---|
| ls20 | 3 | 0 | 0 | 0 | No: token cap |
| s5i5 | 7 | 6 | 2 | 0 | Yes |
| cd82 | 5 | 5 | 2 | 1 | Yes |
| ft09 | 6 | 2 | 0 | 0 | Yes |
| ka59 | 10 | 6 | 2 | 1 | Yes |
| sc25 | 6 | 3 | 1 | 1 | Yes |
| **Total** | **37** | **22** | **7** | **3** | **5/6** |

| Primary diagnostic, relative to this reference inventory | Result |
|---|---:|
| Mask detection recall | 18.9% (7/37) |
| Mask detection precision | 31.8% (7/22) |
| Exact-mask fraction over all reviewed whole objects | 8.1% (3/37) |
| Matched IoU sum / all 37 reference objects, unmatched objects zero | 0.170 |
| Boundary F1 sum / all 37 reference objects, unmatched objects zero | 0.160 |
| Unmatched proposals under the adopted reference inventory | 15 |

Matching maximizes eligible one-to-one matches, then total IoU. A large mask
or duplicate cannot earn credit for several objects. Invalid ls20 remains in
the six-board and 37-object denominators; its partial sequence is not decoded
or salvaged. The 57 reviewed parts are separate from the 37 whole objects and
are not pooled into a 94-object success rate. No automatic advancement
threshold or passing verdict was specified.

Inspection of ls20's retained raw text shows that it continued into a long
counting sequence instead of terminating the inventory. The leading point
tokens are not salvaged: the frozen rule rejects the length-limited response
as a whole. A new stopping/output condition would require a separate test.

## What this tests

The model received six plain 448-by-448 nearest-neighbor images of the original
64-by-64 boards, without overlays or human target names/counts. One fixed
generic prompt asked for distinct whole objects, including interface objects,
without listing internal parts. Native decoded points were mapped to board
cells by floor(pixel / 7).

The boundary stage is a deterministic pixel tool: each predicted seed selects
its same-color four-connected component. There is no reference-based
filtering, snapping, hole filling, duplicate suppression or semantic merging.
This is **model pointing plus a pixel-tool baseline**, not full masks emitted
directly by MolmoPoint. Its inability to combine colors/disconnected pieces is
part of the tested method and must not be attributed solely to the model.

The owner confirmed all 94 unchanged reference masks and six inventories
before inference. This remains a single-owner reference with a declared
whole/part hierarchy, not independently verified universal object truth.
Precision, recall and unmatched-proposal counts are relative to that adopted
inventory and granularity. Do not conclude every unmatched proposal is
semantically meaningless. Raw labels were not revised after seeing outputs.

## Pointing versus extent: post-hoc diagnostic

Distinct valid decoded seed cells land inside **18/37** listed whole
objects under one-to-one containment matching. This is a post-hoc diagnostic,
not a replacement for the frozen mask result or an advancement criterion.
It shows that entering an object's occupied area does not establish its full
extent. Incomplete discovery and deficient mask construction both need
attention. Point containment alone does not establish a semantic identity,
role, collision behavior or successful action.

The earlier 6/6 cued single-target hits remain valid. They do not establish
uncued inventory or mask competence. This broader task and its tool stage are
different; no controlled model-superiority comparison follows.

## Runtime and evidence

| Check | Retained result |
|---|---|
| Provider | COMPLETE; one submission, consumed and preserved, zero automatic retries |
| Actual hardware | One NVIDIA RTX PRO 6000 Blackwell Server Edition, checked at startup and cleanup |
| Worker lifecycle | 490.145 seconds through post-receipt witness, below 3,300 seconds; not total provider job time |
| Byte integrity | All 220 mounted files matched; seven separate uncued staging files also verified |
| Runtime | Same 48-package hash-pinned isolated installation and pinned MolmoPoint checkpoint, BF16/CUDA |
| Generations | Six; 4,377 completion tokens total, ≤4,096 each; ls20 accounts for 4,096 |
| ls20 | Length-limited after 87.533 seconds; retained invalid, no retry |
| Cleanup | 8 registered groups absent/reaped; no remaining GPU compute process; temporary environment removed |
| Finalization | Manifest hashes, post-write witness, saved-cell marker and provider COMPLETE verified |
| Independent replay | Complete local checkpoint rehashed; requests, processor IDs/metadata, raw tokens, native points, masks and scores rebuilt on CPU |
| Extra compute | No pretrained inference or GPU job during collection/evaluation; network disabled during replay |
| Game actions / scorecards | Zero / zero |
| Deployment identity | Warning remains failed; exact saved content and other available privacy/image/accelerator/attachment fields verified separately |

The independent evaluation SHA256 is `e13023d3e1ac904134a48147329ef4e1c66dcf5a7c5bda40119d1c4ba370609f`.
The retained collection manifest SHA256 is `56f2a2ba5c9a7ba3c2968202cf890d2e96707b0ca0aaf0633b70117e20117a9f`.
The reviewed source package SHA256 is
`870802de51d256b0a6f4c6511bfe789764c8daf6a4d5431b114efa24a438ff56`.
Raw outputs, masks, approvals and the interactive comparison remain private.

## Next work

Inspect missed/merged/partial proposals against the declared reference
granularity, preserving this first result. Separate seed discovery from
semantic component grouping in the next design, and address the ls20
length-limited inventory output. Any changed reference is a new revision;
any changed prompt or mask method is a new condition. No further GPU attempt
is authorized by this result. Gameplay, controls and first-level completion
remain outside this test.
