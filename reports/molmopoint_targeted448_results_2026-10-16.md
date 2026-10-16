# MolmoPoint-8B: completed six-board cued localization test

October 16, 2026. **All six responses are valid and all six decoded points land
inside their predeclared target objects.** The authorized attempt completed on
the requested hardware, and independent CPU replay and lifecycle checks pass.
The result establishes successful cued localization on these six exposed
development frames. Object discovery, obstacle mechanics, clicking, movement
and level completion remain untested.

| Runtime/evidence check | Result |
|---|---|
| Review lock | `b30d8fe9916192fc8d5ed92bf8c6e8330bac4c57a51bcfd0107a9411a472be9c` |
| Model | `allenai/MolmoPoint-8B`, revision `188130f961c8e0888a34e11121a1423c461a01ba` |
| Provider / attempt | COMPLETE; one submission, no automatic retry; consumed and preserved |
| Actual hardware | One NVIDIA RTX PRO 6000 Blackwell Server Edition, checked at startup and cleanup |
| Worker lifecycle | 307.486 seconds through the post-receipt-write witness, below 3,300 seconds; not total provider job time |
| Mounted integrity | All 220 hashes matched before installation: 34 model files, nine inputs and 177 publisher files including all 174 wheels |
| Installation and loading | Isolated 48-package hash-pinned installation and dependency check succeeded; pinned pretrained checkpoint loaded in BF16 on CUDA |
| Calls / tokens | Six generations; 4,654 prompt tokens and 148 completion tokens total; each below the 1,024-token limit |
| Generation time | 4.161 seconds summed across six calls; longest 1.053 seconds |
| Completion format | Six normal stops; one complete native point per response; no fragments or multiple-point responses |
| Cleanup | Eight registered process groups reaped/absent; no GPU compute processes left; temporary environment removed |
| Finalization | Output hashes, post-write witness, saved-cell marker and provider COMPLETE all verified |
| Independent replay | All frozen requests, prompt IDs, image metadata, generated IDs, native decodings, admissions and token bounds verified on CPU |
| Actions / scorecards | Zero |

| Level-1 board | Valid response | Exact target hit | Generated tokens |
|---|---|---|---:|
| ls20 | Yes | Yes | 20 |
| s5i5 | Yes | Yes | 26 |
| cd82 | Yes | Yes | 24 |
| ft09 | Yes | Yes | 25 |
| ka59 | Yes | Yes | 23 |
| sc25 | Yes | Yes | 30 |
| **Total** | **6/6** | **6/6** | **148** |

The model received plain 448-by-448 nearest-neighbor renderings of the original
64-by-64 boards, with no grid overlay, added margin or crop. It received one
fixed text cue per board. References and target masks stayed outside its inputs.
Its provided native point decoder returned image-pixel coordinates, which were
mapped to cells with `floor(pixel / 7)`. Credit required membership in the frozen
occupied-cell target mask, without clipping, repair or a distance tolerance.
The prompts requested centers, but this scoring rule tests containment rather
than exact center accuracy.

The independent replay reverified the complete local checkpoint bytes and
reconstructed the processor inputs and native point results. It loaded no model
weights for inference, used no CUDA and attempted no network connection.
The private evaluation SHA256 is
`491d8fa63353e5b37c5c5bd826e75a99d3224f8dd175ce0e65e58f0450788c6a`;
its retained collection manifest SHA256 is
`8e62fa5f3d6c31f1ee2b6020dbfad8cdee236a1d2a22e7ffc8a68533024636b3`.

These are six selected, previously exposed frames in one attempt, with human
target descriptions. They do not estimate performance on new frames, uncued
objects, similar-object groups or obstacles. They also do not form a controlled
comparison with the earlier InternVL inventory probe: the prompting task,
rendering and output contract differ. No model superiority or solving claim
follows from this result.

A useful next study is whether native pointing remains accurate on new frames
and can identify all instances of a described object class before gameplay
integration. Obstacle candidates would require a separate visual test, and
blocking behavior would require transition evidence. No further compute is
authorized by this report.

Raw tokens, point coordinates, masks, private notebook details and the offline
visual review remain in the git-ignored workspace. This report contains sanitized
results only. No new job was launched while collecting or evaluating this run.
