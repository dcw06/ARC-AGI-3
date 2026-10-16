# InternVL3.5-8B: object and obstacle-candidate identification probe

October 15, 2026. Preparation only; no model result, upload, reservation or GPU run.

## Question and evidence limits

Can `OpenGVLab/InternVL3_5-8B` identify and coarsely localize distinct visible objects and
barrier candidates in the six reviewed development games' first-level starting boards?

This is a prompted component test, separate from the unchanged agent baseline. It is not
an ARC competition submission. A good result would support bounding-box localization on
these exposed boards; it would not establish exact masks, control execution or solving.

| Part | Design |
|---|---|
| Images | Six initial 64-by-64 boards; anonymous board IDs; lossless 8x nearest-neighbor rendering to 512-by-512 PNG |
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
the separately published `-HF` conversion. Small pinned configuration/source files were
downloaded privately and inspected as text/AST; none were imported or executed, and no
weights were downloaded. The vision module unconditionally imports `timm.layers.DropPath`;
the existing trusted 174-wheel requirements contain no `timm` pin. Reusing that environment
unchanged is therefore insufficient for this repository's Transformers loading path.
Optional FlashAttention/Apex imports must not be mistaken for mandatory dependencies.
Runtime/dependency and mounted-byte checks remain necessary before inference; an identifier
in a response does not prove its origin. No CPU model-installation pass is claimed.

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
| `references/` | Owner labels, full coordinate sets and provenance; **never mount in the model sandbox** |
| `review.html` | Local image review with optional reference boxes; no model predictions |
| `model_pin.json` | Intended model repository/revision; explicitly not a mounted-byte receipt |
| `kaggle-review/` | Private, GPU/TPU/internet-off metadata and notebook that refuses before any inference |
| `review-lock.json` | Artifact and preparation/evaluator source hashes; not a compute approval |
| `STATUS.json` | Prepared only; zero model calls, game actions and GPU runs |

The private directory is reported locally by the builder. Raw boards, labels and responses
stay off GitHub. Public source and synthetic unit fixtures contain no human reference data.

```powershell
python scripts/object_identification_v1.py prepare --snapshot "<private-reviewed-snapshot>" --output "<new-private-bundle>"
python scripts/object_identification_v1.py verify --bundle "<private-bundle>"
python -m unittest tests.test_object_identification_v1
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
The local review notebook requests no accelerator and always refuses. Nothing is uploaded.

Actual inference remains blocked until the private model/input attachments and compatible
runtime are verified, and provider enforcement covers the entire GPU job, including mounting
and platform setup. A worker deadline or a timeout field alone does not establish that.
Keep the run account-holder-only. Any launch package must bind its exact source, scope,
total requests including runtime checks, fresh authorization and single-use attempt record.
The six study requests do not silently include unbudgeted canaries or polling.

The next step is source/runtime and full-job-cap validation, not an attempted GPU launch to
discover whether a cap works. Existing consumed attempts and prior study results stay intact.

## CPU verification record

- 23 tests passed across `tests.test_object_identification_v1` and
  `tests.test_manual_strategy_worksheet` on Python 3.11.9.
- Checks include matching reassignment, one-to-one credit, full-board-box rejection for
  small objects, strict outputs, partial/hierarchical references, missing answers, wrong
  request/revision bindings, mutated images/source snapshots and refusal to overwrite.
- The real private r174 snapshot builds six images and retains all 94 reference regions.
  Every image round-trips to its original grid; the bundle hash verification passes.
- The exact generated private notebook's first code cell was executed on CPU: it refused
  with `REVIEW ONLY` before imports or inference. Its metadata is private with GPU, TPU
  and internet disabled. This is a refusal check, not a Kaggle-image installation check.
- Model calls: **0**. Game actions: **0**. GPU jobs and Kaggle uploads: **0**.
