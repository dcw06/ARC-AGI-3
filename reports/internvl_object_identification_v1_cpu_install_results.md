# InternVL object-identification probe: Kaggle CPU installation result

October 16, 2026. **Passed:** one owner-approved private CPU-only installation check,
saved once, provider status COMPLETE. The attempt is consumed and preserved; no retry.
No GPU job, pretrained-weight loading, study request, game action or scorecard occurred.

| Check | Result |
|---|---|
| Reviewed source/configuration | Saved version 1 matches the authorized notebook source and immutable image; private, GPU/TPU/internet off; accelerator `None` |
| Immutable image | `gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461` |
| Mounted bytes, before install | All 216 SHA256 checks match: 27 model files, 12 input files, 174 publisher wheels and three publisher metadata files; 22,261,380,447 bytes total |
| Isolated installation | Fresh venv without ensurepip; host pip manages that interpreter; offline, binary-only, hash-required installation; unchanged 174 original pins plus pinned timm |
| Dependencies | `pip check` passed; all 175 installed distribution names/versions match the pinned requirements |
| Pinned model classes | Tiny random-weight InternVL vision/projector/Qwen3 CPU forward passed, 46,416 parameters; no pretrained checkpoint loaded |
| Tokenizer | Qwen2TokenizerFast, 151,678 tokens; image-token IDs match the local rehearsal; publisher tokenizer preserved with `fix_mistral_regex=False` |
| Real input preprocessing | All six boards produce the same BF16 tensors and preview hashes as the local CPU rehearsal; no real board passed through the model |
| CPU-only execution | CUDA-linked PyTorch build 12.8 imported successfully; CUDA remained uninitialized; synthetic model parameters stayed on CPU; no attempted socket connections during rehearsal |
| Cleanup | All four subprocess groups exited 0, with registered ownership and verified absence; no cleanup interruption/error; temporary venv/cache removed |
| Finalization | Receipt and post-write witness hashes match, final cell-output marker present, provider COMPLETE; independent retained-evidence audit passed |
| Worker time | 423.856 seconds (7m 4s), including byte verification, installation, CPU rehearsal, environment removal and receipt write; not total provider job time |
| Authorized CPU limits | Requested session-runtime timeout 1,800 s; worker budget 1,700 s including 120 s cleanup reserve; one attempt, zero automatic retries |

| Runtime package | Installed version |
|---|---|
| torch | 2.10.0 (CUDA-linked build 12.8, executed on CPU) |
| torchvision | 0.25.0 |
| transformers | 4.57.6 |
| timm | 1.0.20 |
| einops | 0.8.2 |
| pillow | 12.2.0 |
| safetensors | 0.7.0 |

The retained installation log contains a nonfatal `sitecustomize` import warning
for missing `wrapt`, plus the optional FlashAttention2 notice. All four commands
returned 0 and the strict dependency/version/model checks passed. No unpinned
package was added to suppress those diagnostics.

The pull API omits dataset-version suffixes. Intended versions were accepted at save
time; exact contents are established by the locked mounted-byte checks. This report
does not claim independent confirmation of the provider's attachment version labels.

Raw notebook, approvals, request/claim, provider receipts, logs, result, completion
witness and their collection manifest remain in the private git-ignored workspace.
Their hashes and the source lock were rechecked independently after collection.
The model revision remains `9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79`.

This resolves isolated installation and tiny CPU execution on the exact pinned
Kaggle image. It does **not** establish full pretrained-checkpoint loading, GPU
kernels, object/obstacle identification accuracy, or the enforced 3,600-second cap
for the entire GPU job including provider setup and mounting. That cap remains
unresolved. Any GPU test still needs its own reviewed package and authorization.

[Preparation and evidence limits](internvl_object_identification_v1_preparation.md).
