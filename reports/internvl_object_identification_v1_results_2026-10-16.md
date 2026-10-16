# InternVL3.5-8B: completed object-identification probe

October 16, 2026. The successor GPU attempt completed. **All six original
responses fail the frozen coordinate contract**, so this probe does not establish
usable object localization or obstacle identification. Technical runtime evidence
and independent request/token replay pass. The attempt is technically complete;
successful identification is a separate requirement that it did not meet.

## Runtime and evidence

| Check | Result |
|---|---|
| Approved review lock | `03248a0d5566b9aad4831ee82e05997c288c5acab0ed86e9efc49283198189a3` |
| Provider | COMPLETE, one accepted submission, no retries |
| Actual GPU | One NVIDIA RTX PRO 6000 Blackwell Server Edition, checked at startup and cleanup |
| Worker lifecycle | 510.998 seconds through the post-receipt-write witness, against 3,300 seconds; not total provider job time |
| Mounted bytes | All 216 file hashes match: 27 model files, 12 input files and 177 publisher files including 174 wheels |
| Model execution | Pinned pretrained InternVL3.5-8B checkpoint loaded; six CUDA generations |
| Requests and tokens | Six calls, 601 prompt tokens each, 5,071 completion tokens total; every completion below 4,096 tokens |
| Longest generation | 130.906 seconds, below the 180-second cap; all six end normally with `stop` |
| Cleanup | Eight registered process groups reaped and absent, GPU process census clear, temporary environment removed |
| Finalization | Result/output hashes, post-write witness and final notebook stdout marker match; saved source and available settings match review |
| Independent request/token replay | All six frozen requests, templates, image bindings, prompt IDs, generated IDs, decodings and call records match; replay used CPU metadata/tokenizer only, no weights, network or CUDA |
| Actions and scorecards | Zero |
| Attempt history | First GPU attempt remains a consumed setup failure; this separate authorized successor is consumed and retained; both CPU attempts preserved |

## Frozen scoring

| Level-1 image | Reported regions before validation | Boxes outside 0-63 | Valid response | Whole-region coverage | Part coverage |
|---|---:|---:|---|---:|---:|
| ls20 | 7 | 7 | No | 0/3 | 0/3 |
| s5i5 | 7 | 7 | No | 0/7 | 0/4 |
| cd82 | 4 | 1 | No | 0/5 | 0/4 |
| ft09 | 68 | 4 | No | 0/6 | 0/36 |
| ka59 | 5 | 1 | No | 0/10 | N/A: no labelled parts |
| sc25 | 5 | 5 | No | 0/6 | 0/10 |

All six responses are parseable JSON and end normally, but each contains at least
one invalid inclusive board-cell bounding box. The unchanged scorer rejects the
whole response in that case. Thus **0/6 responses are valid**, and accepted
reference coverage is 0/37 whole regions and 0/57 parts. Whole regions and parts
overlap and must not be combined as independent object detections.

These zeros follow from response rejection; they do not mean every individual
object description or in-range box was independently shown wrong. Across the raw
inventories, 25 of 96 reported boxes contain out-of-range coordinates. Some values
extend into the hundreds despite the explicit 0-63 instruction. This suggests a
coordinate-scale/instruction-following problem, but no common scale conversion is
established. Nothing was rescaled, clipped, extracted, retried or relabelled to
improve the official result.

## Interpretation and next research question

The model/runtime path now works on the requested hardware. This prompt/model
combination has not passed the required interface for acting on board cells.
Visual descriptions alone cannot establish correct object localization, occupied
cell masks, semantic roles or collision behavior. The references are partial,
owner-reviewed labels on six exposed initial boards, not held-out or exhaustive
ground truth. Obstacle mechanics remain untested: no actions were taken, and the
reference set contains only one owner-labelled obstacle candidate.

A useful next question is: **Can the model reliably map a visible region into
the required board coordinate system, and then separate whole objects from
their components?** A new study could isolate coordinate compliance from visual
recognition with controlled boards and an explicitly declared coordinate aid.
It would need a new frozen design and authorization; no additional compute is
authorized by this result.

Raw responses, generated IDs, references, private notebook bindings and the
side-by-side diagnostic review page remain in the git-ignored workspace. This
report contains only aggregates and sanitized diagnostic findings.
