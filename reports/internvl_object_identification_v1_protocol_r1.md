# InternVL object-identification probe — design r1

October 16, 2026. Frozen scientific design for a proposed private component test.
This document is not source approval or compute authority. Current review packages
have live execution disabled. A later operational revision must bind provider-cap
evidence, private scope and fresh authority before one GPU attempt can be submitted.

| Question | Evidence this test can supply |
|---|---|
| Can InternVL identify/localize distinct visible regions? | Coverage of partial owner-reviewed whole/part boxes on six exposed first-level starting boards |
| Can it locate obstacle candidates? | Appearance-based guesses and coverage of one owner-labelled candidate; no physical collision accuracy |
| Can it operate controls, infer rules or solve? | Not tested: no actions, history, engine calls or scorecards |

| Part | Frozen choice |
|---|---|
| Model | `OpenGVLab/InternVL3_5-8B`, revision `9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79`; original custom-code model, no silent `-HF` substitution |
| Inputs | Six initial boards from ls20, s5i5, cd82, ft09, ka59, sc25, anonymous board-01…06, in that fixed order; no labels, game names, later frames or demonstrations in model prompts |
| References | Existing r174 owner-reviewed partial hierarchical regions, 94 total; references remain outside the model sandbox; these are exposed development examples, not held-out validation |
| Image processing | Entire 64×64 board rendered losslessly at 512×512; one full-frame 448×448 bicubic tile, ImageNet normalization, BF16; no crops, dynamic tiling, masks or overlays |
| Prompt and template | Existing coordinate-resizing-independent inventory prompt, pinned publisher conversation template/system message; exactly 256 image-context tokens per image; no conversation history |
| Generation | Six separate greedy generations; `do_sample=False`, one beam, seed 0; maximum 4,096 new tokens per request and 24,576 overall; no separate generation canaries, server polls, repairs or automatic retries |
| Runtime | Validated unchanged 174 hash-pinned original wheels plus timm 1.0.20; fresh isolated offline venv, pip check and exact distribution/version comparison; FlashAttention disabled; publisher tokenizer with `fix_mistral_regex=False` |
| Loading | Local-only BF16 checkpoint load, then one CUDA device; full checkpoint loading and GPU behavior remain untested until the authorized real attempt |
| Outputs | Preserve generated IDs, full special-token decoding, untouched special-token-skipping continuation, token counts, rendered template, input token IDs, exact request/image hashes, durations and call-admission journal |
| Output syntax | Existing strict JSON inventory: distinct IDs, descriptions, inclusive board-cell boxes 0…63, tentative roles; at most 96 entries; no extracting, trimming or fixing JSON |
| Scoring | Existing scorer unchanged: maximum-cardinality one-to-one matching at IoU ≥0.5; whole objects and parts scored separately; unmatched predictions are unreviewed, not automatically false positives |
| Reporting | Per-board and per-stratum counts, coverage and invalid-output counts; no exhaustive precision, confirmed mechanics, held-out generalization or solving claim; no post-result label changes without retaining/versioning original evaluation |

Provider allocation must be exactly one RTX PRO 6000, independently checked both
through provider configuration and actual GPU identity; T4×2 and other fallback
hardware are refused. Account, exact private notebook, image digest and versioned
dataset bindings are in the private review packet. They are not public here.

The owner retains a provider-enforced 3,600-second cap for the **entire GPU job**,
covering allocation, setup, mounts, execution and release. That guarantee is still
unresolved. A configured timeout, worker timer or expected short runtime does not
establish it. No GPU run is allowed merely to discover whether enforcement works.

| Internal limit | Candidate behavior (additional to the provider cap) |
|---|---|
| Whole worker | 3,300 s, including GPU/process cleanup, environment removal and evidence finalization |
| Work deadline | 3,000 s; final 300 s reserved for cleanup |
| Installation | Complete by worker start +900 s; initial identity and byte checks also consume that time |
| Model loading | At most 900 s, also bounded by the work deadline |
| Each generation | At most 180 s; admit only with more than 180 s work headroom; recheck after durable journal write and before generation |
| Requests/attempts | At most six generation admissions; one provider submission; zero automatic retries; uncertainty consumes budget |
| Actions/scorecards | Zero |

Every mounted file is hash-checked before installation; publisher metadata alone
does not certify bytes. Actual attachment version labels may be absent from the
pull API, so distinguish requested versions from hash-verified contents.

Each generation admission is durably journalled before execution. An exception or
timeout preserves the partial journal and responses and fails the attempt; it is
not retried. A normally returned token-cap truncation, empty decoded answer or
malformed JSON is retained as a failed identification case by the unchanged
scorer. It does not justify a replacement response. Technical completion requires
six bound completed generations within the frozen caps, valid evidence and cleanup;
it does not require successful object identification.

The worker is a registered subprocess group, as are installation/import/GPU-query
commands. Cleanup terminates/reaps owned groups, checks no compute processes remain
on the bound GPU, and removes the temporary venv/cache. Uncertain ownership cannot
certify absence. Emergency cleanup remains possible after an overrun, which fails.

Final receipts are provisional. Independent collection must require provider
COMPLETE, exact saved source/image/private configuration, result/output hashes,
the post-write completion witness and its final notebook-output marker. Missing,
late, stale or interrupted finalization cannot pass based on a receipt alone.

Private output stays account-only. Teammates may receive sanitized metric/error
summaries; model weights, wheel files, credentials and copied package contents are
not exported. The private use-assessment draft must be reviewed for this new scope;
prior CPU or Qwen-study approvals do not themselves authorize this GPU probe.
