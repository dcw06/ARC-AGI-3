# InternVL identification: preparation before the real model test

October 16, 2026. **Local preparation complete for a review-only candidate. Not ready
for GPU submission.** No new Kaggle call, upload, reservation or inference occurred
during this preparation. Both earlier CPU attempts remain consumed and preserved.

| Preparation step | Status and evidence |
|---|---|
| Trusted inputs and isolated installation | Complete: both previously authorized Kaggle CPU checks passed; 216 mounted hashes, 175 installed versions, tokenizer/classes and cleanup verified on the pinned image. [CPU result](internvl_object_identification_v1_cpu_install_results.md) |
| Scientific design | [Design r1](internvl_object_identification_v1_protocol_r1.md) records six fixed first-level image cases, partial hierarchical references, preprocessing, prompt/template, raw-output policy, scoring and inference limits |
| Inference worker candidate | Implemented: verify frozen requests independently; exact isolated runtime; local-only BF16 load; one RTX PRO 6000; greedy generation with strict admission and token caps; preserve raw tokens and both decodings, no JSON repair or retries |
| Supervision candidate | Implemented: owned groups for installation, GPU queries and model worker; work/model/per-request deadlines, post-termination GPU census, temporary environment removal and provisional finalization witness |
| Independent replay | Implemented: reconstruct template/tokenization from pinned metadata/code without loading weights; compare requests, image hashes, prompt tokens, generated token decoding, responses and counters before scientific scoring |
| Pinned API rehearsal | Passed locally: save/load a 46,416-parameter synthetic checkpoint with the intended loading kwargs; pinned custom generation returns a four-token continuation with structured generation output; no target checkpoint or real board inference |
| Actual prompt/token audit | Passed locally for all six inputs: 601 prompt tokens each, including 256 image-context tokens; EOS 151645; 601+4096 fits the pinned 40,960-token context; no weights loaded |
| Linux regressions | 77 tests passed, no failures/skips: original probe/privacy/mount/install/finalization groups plus twelve inference/admission/replay/refusal tests |
| Private review candidate | Built and audited: all artifact/source hashes match, independent rebuild byte-identical, exact image/dataset bindings and retained CPU evidence; notebook and supervisor refuse before GPU queries or model imports |
| Licence/use packet | Draft prepared privately: 23 retained wheel-use texts, two model licence texts and timm licence, with hashes/provenance; account-only facts carried over; new permission outcome and reconfirmation left blank |

The candidate notebook is GPU/TPU/internet off and contains a first-cell refusal.
It is a review artifact, **not the final executable live notebook**. The full worker,
supervisor, replay and dataset bindings are present for source review. When the
provider mechanism is known, the operational release must be built and reviewed
with its exact live configuration; the present candidate lock cannot approve a
changed live artifact automatically.

| Still required | Why this cannot be marked complete |
|---|---|
| Provider-enforced whole-job cap | The owner's requirement is 3,600 s from GPU allocation through release, including setup and mounts. The [official CLI reference](https://github.com/Kaggle/kaggle-cli/blob/main/skills/references/kernels.md) documents a runtime timeout, without establishing this full coverage. No provider confirmation is retained. The [support request](internvl_object_identification_v1_platform_cap_support_request.md) is ready and remains unsent. |
| Scoped-use outcome and exact live source approval | The current private draft is reviewable, but historical CPU/Qwen approvals are not a new permission decision or approval of changed GPU source/configuration. |
| Fresh GPU authorization and one-use claim | One RTX PRO 6000, ≤3,600 s full-job cap, ≤6 generations, ≤24,576 generated tokens, zero actions/scorecards, one attempt and no retries are proposed; none is authorized for this test. A fresh read-only availability/configuration preflight follows approval. |

This test's full pretrained checkpoint loading and GPU execution remain untested;
the real attempt would exercise them. No pre-test GPU trial is authorized. The
CPU synthetic check is API compatibility evidence, not object-identification evidence.
There are still **zero pretrained image responses**, so no detection score or
obstacle-mechanics claim can be reported.
