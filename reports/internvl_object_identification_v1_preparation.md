# InternVL3.5-8B: object and obstacle-candidate identification probe

October 15, 2026. Private dataset staging and local CPU compatibility checks; no
pretrained-model result, notebook submission, reservation or GPU run.

## Question and evidence limits

Can `OpenGVLab/InternVL3_5-8B` identify and coarsely localize distinct visible objects and
barrier candidates in the six reviewed development games' first-level starting boards?

This is a prompted component test, separate from the unchanged agent baseline. It is not
an ARC competition submission. A good result would support bounding-box localization on
these exposed boards; it would not establish exact masks, control execution or solving.

| Part | Design |
|---|---|
| Images | Six initial 64-by-64 boards; anonymous board IDs; lossless 8x nearest-neighbor rendering to 512-by-512 PNG; CPU preprocessing checked as one full-frame 448-by-448 bicubic tile |
| Input | Plain image and the same inventory prompt; no game name, answer labels, target hints, later frames or history |
| Output | JSON list of visible regions, inclusive board-cell boxes, appearance descriptions and explicitly tentative roles |
| Requests | Six independent study requests; temperature 0; at most 4,096 output tokens each; no automatic repair/retry |
| Game interaction | Zero game actions, resets, scorecards or competition submissions |
| Reference | Owner-reviewed snapshot r174: 94 hierarchical regions, including background/UI/context; partial, not exhaustive ground truth |
| Obstacles | One region carries the owner's obstacle label; no independently verified collision labels are present |

## Model source

Official repository: [OpenGVLab/InternVL3_5-8B](https://huggingface.co/OpenGVLab/InternVL3_5-8B).
The [publisher's metadata](https://huggingface.co/api/models/OpenGVLab/InternVL3_5-8B)
identifies revision `9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79` and Apache-2.0 licensing.
The selected repository uses custom model code; it is not silently interchangeable with
the separately published `-HF` conversion. After text/AST review, seven code/configuration
files were hash-pinned. Those exact classes were then exercised offline with a tiny,
random-weight model on CPU. All 24 upstream files, **17,072,800,269 bytes**, were downloaded
privately and verified against the pinned publisher tree: LFS SHA256 for weights and Git
blob hashes for ordinary files, with local SHA256 recorded for every file. Pretrained
weights have not been loaded or used to answer any question.

The vision module unconditionally imports `timm.layers.DropPath`, absent from the existing
trusted 174-wheel requirements. A separate `timm==1.0.20` wheel is now retained, with its
licence and hash-pinned supplemental requirements. Its five direct dependencies match
versions already present in that lock; none of the 174 original pins was changed.
Its wheel SHA256 is `f6e62f780358476691996c47aa49de87b95cc507edf923c3042f74a07e45b7fe`.
Optional FlashAttention/Apex imports are not treated as mandatory dependencies.

| Local check | Result and limit |
|---|---|
| CPU installation | Pass: PyTorch 2.10.0+cpu, torchvision 0.25.0+cpu, Transformers 4.57.6, timm 1.0.20, einops 0.8.2, Pillow 12.2.0 and safetensors 0.7.0 |
| Pinned model classes | Pass: tiny random InternVL vision/projector/Qwen3 forward on CPU, 46,416 parameters, BF16 image tensor; no pretrained inference |
| Actual board preprocessing | All six images yield finite `[1,3,448,448]` BF16 tensors; previews and tensor hashes retained; images were not passed through the model |
| Local model bytes | All 24 files match the pinned publisher tree; this is not a Kaggle mounted-byte receipt |
| Checkpoint structure and tokenizer | All 745 indexed BF16 tensors present across four shards; embedding dimensions agree with config; tokenizer/image-token IDs load offline and fit the vocabulary |
| Exact Kaggle image, CUDA kernels and full checkpoint loading | Not validated; CPU wheels are not the target CUDA runtime |

One full-frame tile is the proposed input policy; it differs from the publisher's default
dynamic tiling and must be bound in any executable launch package. Runtime/dependency and
mounted-byte checks remain necessary before inference. An identifier in a response does
not prove its origin.

The prompt now specifies board-cell coordinates independently of image resizing. Its
earlier 8-pixel cell-size instruction described the original 512px rendering but could
mislead after the 448px preprocessing step. The corrected private input dataset is
version 2; version 1 is preserved. Image and wheel bytes are unchanged, and no pretrained
inference used either prompt.

The tokenizer check triggered Transformers 4.57.6's Mistral-regex warning on the local
InternVL/Qwen configuration (`transformers_version: null`). Inspection of the installed
detection branch and the [upstream non-Mistral warning issue](https://github.com/huggingface/transformers/issues/42591)
supports treating this as a detection false positive, rather than applying a Mistral
tokenizer rewrite. With `fix_mistral_regex=False`, the pre-tokenizer remains identical to
the pinned `tokenizer.json`; encoding the inventory prompt, image-token expansion and a
mixed punctuation/Unicode sample exactly matches direct loading of that published file.
Both receipts are retained. This checks preservation of the publisher's tokenizer, not
generation quality, and the eventual launch must bind that explicit option.

## Scoring

- Strictly reject malformed JSON, duplicate keys, invalid coordinates, duplicate IDs and
  unfinished responses. Keep missing and invalid answers visible in the six-case inventory.
- Use inclusive grid-cell bounding-box IoU >= 0.5 and maximum-cardinality one-to-one
  matching. A full-board box cannot earn credit for a small object merely by containing it.
- Score whole annotated regions and nested parts separately. Their scores overlap and
  cannot be summed into independent object counts. Inspect matches by reference kind;
  covering a background region is not evidence of identifying the player or controls.
- Report reference coverage and unmatched predictions for review. Partial annotations
  cannot establish exhaustive recall or make every unmatched prediction a false positive.
- A box around a shape does not establish its occupied cells, holes or click hit region.
  Geometry matching also does not independently validate the model's prose description.
- Role guesses and spatial overlap with the owner's barrier candidate are descriptive.
  **Movement-blocking accuracy is unmeasured**, not zero and not a pass. Appearance alone
  cannot certify an obstacle's mechanics. A later functional test needs reviewed, relevant
  action-effect evidence and must handle blocked moves, modes and alternative explanations.
- There is no universal object-identification pass claim from an aggregate score. Report
  each board and matched region before choosing any subsequent mask or gameplay test.

If an apparently valid prediction exposes a reference error, retain the original labels
and score. Adjudicate using evidence, apply any correction to all affected predictions,
and publish a separately versioned evaluation; do not silently tune the key to the output.

## Private artifact layout

`scripts/object_identification_v1.py prepare` verifies source hashes, frame bindings and
annotation geometry, then creates a new private/git-ignored bundle without overwriting:

| Path | Use |
|---|---|
| `inputs/` | Six plain PNGs and image/prompt request specifications; no reference answers |
| `model-inputs-only.zip` | Deterministic archive of only `inputs/`, for a future private input attachment |
| `runtime-extra/` | Optional hash-checked timm wheel, supplemental requirements, licence and acquisition record |
| `kaggle-inputs.zip` | When `--runtime-extra` is supplied, deterministic archive of `inputs/` plus `runtime-extra/`; no references |
| `references/` | Owner labels, full coordinate sets and provenance; **never mount in the model sandbox** |
| `review.html` | Local image review with optional reference boxes; no model predictions |
| `model_pin.json` | Intended model repository/revision; explicitly not a mounted-byte receipt |
| `kaggle-review/` | Private, GPU/TPU/internet-off metadata and notebook that refuses before any inference |
| `review-lock.json` | Artifact and preparation/evaluator source hashes; not a compute approval |
| `STATUS.json` | Prepared only; zero model calls, game actions and GPU runs |

The private directory is reported locally by the builder. Raw boards, labels and responses
stay off GitHub. Public source and synthetic unit fixtures contain no human reference data.

```powershell
python scripts/object_identification_v1.py prepare --snapshot "<private-reviewed-snapshot>" --output "<new-private-bundle>" --runtime-extra "<private-verified-timm-folder>"
python scripts/object_identification_v1.py verify --bundle "<private-bundle>"
python -m unittest tests.test_object_identification_v1
```

Use a CPU-only environment for the compatibility rehearsal. It verifies pinned source
before importing custom code, disables Hub access and refuses socket connections. Its
receipt binds the validator/source hashes and installed versions. It deliberately refuses
CUDA builds; it cannot be used to claim validation of Kaggle's CUDA image.

```sh
python scripts/object_identification_v1.py cpu-runtime-check --source "<pinned-model-code-folder>" --cache "<private-HF-cache>" --inputs "<private-bundle>/inputs" --previews "<new-preview-folder>" --output "<new-CPU-receipt.json>"
```

After a separately validated inference run, retain raw completions without extracting
or repairing JSON. Each line of the response JSONL must have exactly:

```json
{"case_id":"board-01","model":"OpenGVLab/InternVL3_5-8B","model_revision":"9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79","request_sha256":"<SHA256 of canonical request row including its trailing newline>","content":"<unmodified assistant content>","finish_reason":"stop"}
```

```powershell
python scripts/object_identification_v1.py score --bundle "<private-bundle>" --responses "<private-responses.jsonl>" --output "<new-private-evaluation.json>"
```

Scoring binds the recorded request and revision and checks the bundle/source hashes.
It does not independently authenticate the responding model or certify a GPU lifecycle;
the future runner must retain actual requests, model-tree identity, usage and finalization.

## Kaggle readiness

The owner chose a private Kaggle test **keeping the enforced one-hour full-job cap**.
The local probe review notebook requests no accelerator and always refuses; it has not
been uploaded. The input dataset has been created privately, with version 1 preserved
and corrected version 2 verified ready. The private model dataset is ready at version 1.
Read-only provider checks confirm privacy and exact filenames/sizes for all 27 model
files and 12 input files. These are not mounted-byte receipts.

| Requirement | Current status |
|---|---|
| Missing timm dependency | Supplemental wheel pinned and CPU rehearsal passes |
| Model source bytes | Verified locally; private model version 1 ready, provider privacy/name/size checks pass; mounted bytes and notebook attachment unverified |
| Input attachment | Private version 2 ready; provider privacy/name/size checks pass; mounted bytes and notebook attachment unverified |
| Exact target runtime | CPU rehearsal only; Kaggle image, full loading and GPU compatibility remain unverified |
| Enforced 3,600-second entire-job cap | Unresolved; owner reports no provider confirmation |
| Executable launch package and authority | Not prepared or approved; current notebook always refuses |

Actual inference remains blocked until the private model/input attachments and compatible
runtime are verified, and provider enforcement covers the entire GPU job, including mounting
and platform setup. The installed ordinary-notebook API does send a session timeout, but
does not define its pre-cell coverage or GPU-release bound. A worker deadline or a timeout
field alone does not establish the owner's requirement. This is distinct from the earlier
scored-rerun timeout-inheritance question.

A [support request draft](internvl_object_identification_v1_platform_cap_support_request.md)
asks those precise questions. It has **not been sent**. No GPU experiment will be used as
a substitute for an enforcement guarantee.
Keep the run account-holder-only. Any launch package must bind its exact source, scope,
total requests including runtime checks, fresh authorization and single-use attempt record.
The six study requests do not silently include unbudgeted canaries or polling.

The next step is source/runtime and full-job-cap validation, not an attempted GPU launch to
discover whether a cap works. Existing consumed attempts and prior study results stay intact.

The separate Linux CPU byte checker in `research/object_identification_v1/mount_check.py`
uses only the standard library. It checks exact inventories, rejects symlinks and unsafe
filenames, and streams SHA256 with deadline checks before/after each chunk and at the end.
A prepared GPU/TPU/internet-off notebook will check the model and input files, all 174
publisher wheels and their three metadata files. It will install nothing and execute no
dataset code, pretrained inference or game action. Its reviewed manifest and provider
COMPLETE status are required alongside the byte receipt; file hashes alone do not certify
session termination. The private CPU review packet binds the verifier, immutable image,
three intended dataset versions, manifest and provider receipts. It proposes one attempt,
a 1,200-second session-runtime timeout and a 1,100-second worker budget; approval is
pending and no notebook has been submitted. This is not a GPU launch authorization or
an assertion that the timeout covers provider setup.

## CPU verification record

- 29 tests passed across `tests.test_object_identification_v1`,
  `tests.test_object_identification_mount_check` and
  `tests.test_manual_strategy_worksheet` on Python 3.11.9.
- Checks include matching reassignment, one-to-one credit, full-board-box rejection for
  small objects, strict outputs, partial/hierarchical references, missing answers, wrong
  request/revision bindings, mutated images/source snapshots and refusal to overwrite.
  Additional checks reject a modified supplemental wheel and modified model code before
  imports, and preserve a failed CPU receipt rather than overwrite it on a later attempt.
- The three mount-check tests cover same-size byte mutation, extra files/path traversal,
  and a deadline expiring at the final check after the last file read.
- A Linux end-to-end rehearsal of the CPU byte checker passed on tiny synthetic files.
  The exact private CPU review packet's hashes, embedded source/manifest, disabled GPU/TPU/
  internet flags, proposed limits and 216-file inventory also pass local review. Neither
  check reads actual Kaggle mounts or establishes compatibility of the inference runtime.
- The real private r174 snapshot builds six images and retains all 94 reference regions.
  Every image round-trips to its original grid; the bundle hash verification passes.
- The exact generated private notebook's first code cell was executed on CPU: it refused
  with `REVIEW ONLY` before imports or inference. Its metadata is private with GPU, TPU
  and internet disabled. This is a refusal check, not a Kaggle-image installation check.
- CPU setup history is retained: an initial temporary environment disappeared, and a
  float32 synthetic tensor failed against BF16 vision weights. The persistent environment
  and dtype correction then passed. These are CPU preparation records, not GPU attempts.
- Pretrained study calls: **0**. Game actions: **0**. GPU/CPU Kaggle jobs and notebook
  uploads: **0**. Dataset staging is separate from compute authorization.
