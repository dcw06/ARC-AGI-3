# Automatic-arm provenance correction (preparation r2)

**The flag-only admission defect is fixed.** The original comparison was produced
by a private operator script, so the published preparation lacked its production
recipe. A hash protected the artifact's bytes but did not supply that recipe.
The old r1 records are preserved; they do not certify this changed preparation.

## Committed production and admission path

| Stage | What is checked or derived |
|---|---|
| Protocol | Explicitly pins `automatic_masks_sha256` (`baaf83…`) and the separate `automatic_provenance.json` hash |
| External provenance | Pins 11 retained input roots, including review, preparation, collection, native evaluation, SAM policy/seed manifest, result, witness and operator/stdout records; nested manifests bind their actual artifacts |
| Deployment | Revalidates the retained saved notebook, settings, attachments and authority against the original review package; does not accept the collection's deployment boolean |
| Pointing lifecycle | Rechecks provider COMPLETE, output manifest, completion witness, final return marker, cleanup and mounted-byte receipts |
| Native source | Replays all six retained MolmoPoint requests, prompt/token sequences, decoder outputs and board hashes with the pinned local processor/custom decoder, without loading weights for inference |
| Seed provenance | Requires each SAM seed list and PNG to match its independently replayed native case; invalid ls20 remains empty |
| SAM masks | Reconstructs masks from retained FP32 logits and quality scores: original seed scaling, independent bilinear expansion, highest predicted quality (earliest tie), and ≥25 foreground pixels per 7 × 7 cell |
| Reference evaluation | Checks the external owner-reference pin before scoring; references never select candidates or repair masks |
| Final artifact | Recreates the complete historical comparison, including its formerly trusted booleans, only after all checks; the output must match the protocol's SHA256 |
| Arm preparation | Calls that replay itself and compares the complete rebuilt/stored artifact before writing any inputs; the manifest binds provenance and replay source hashes |

The committed producer is
[`scripts/replay_initial_geometry_automatic_v1.py`](../scripts/replay_initial_geometry_automatic_v1.py),
implemented in
[`automatic_replay.py`](../research/initial_geometry_assistance_v1/automatic_replay.py).
It has no inference, launch or evidence-bypass option. A blocked network attempt
fails replay even if a dependency catches the exception.

## Verification

| Check | Result |
|---|---|
| Actual retained-evidence replay | Reproduced `sam-comparison-evaluation-r1.json` byte for byte: `baaf83f11b36343580a80e996c166e23bd2ece31a561173dbf02ace9d8290408` |
| Upstream native evaluation | Reproduced `32eae91f0e49ad7da71e87e2b82b24f16d1dba440fe115522b47d1d5d53600ff` after deployment/lifecycle/native replay |
| Mask results | Unchanged: 22 proposals, 12/37 matches at IoU ≥0.5, 6/37 exact masks |
| Real-data regression on `49475e8` | Accepted nine authenticated files (reference, comparison, source evaluation, six PNGs) despite absent raw SAM/provider evidence |
| Corrected admission, same thin inputs | Refuses before creating an output directory |
| Unit/regression suite | 43 Linux CPU tests pass, no skips, including raw-logit/quality/seed mutations and flag-only/deployment failures |
| Clean source export | The same 43 CPU tests pass and the full producer recreates `baaf83…`, without the private operator helpers |
| Private r2 preparation | Rebuilt through the full replay gate; all six PNGs and `cases.json` remain byte-identical to r1 |

| Preparation binding | SHA256 |
|---|---|
| Protocol r2 | `62ec32302ed034cb3eefcda742483a2f194862044e88597828a0325bf63c0d75` |
| External automatic-evidence provenance manifest | `42ffc04a09778d8b8733e991afd1cff9e6a333820c1c1b2683ee1984031dade4` |
| Private r2 input manifest | `9698045c8a65c94e31935c4139ec36dd47e397d9cc7d0bc04467e81c0d63f491` |

The input manifest changes to bind the corrected recipe and protocol. R1's
rehearsal and processor receipts remain r1-bound historical records, not relabelled
as fresh r2 executions; reuse is supported only for the unchanged seven data files
and unchanged request/episode code. R2's private snapshot records those equalities.

The real-data regression is retained as
[`scripts/check_initial_geometry_flag_only_regression.py`](../scripts/check_initial_geometry_flag_only_regression.py).
It reads baseline code from `49475e8` and uses the unchanged six-game schedule
from the current protocol; the old code ignored the added provenance pins. No
hash bypass or fabricated masks are used for that reproduction.

## Reproduction recipe

Use the retained CPU environment (Torch 2.10.0+cpu, transformers 4.57.1) and the
private retained evidence. Replace the paths below; the local MolmoPoint snapshot
is hash-verified before importing its native processor/decoder code. No pretrained
forward pass is performed.

```sh
python scripts/replay_initial_geometry_automatic_v1.py \
  --control-root /path/to/retained-short-prompt-control \
  --molmopoint-checkpoint /path/to/pinned-MolmoPoint-snapshot \
  --sam-acquisition /path/to/checkpoint-acquisition-r1.json \
  --output /path/to/new/replayed-sam-comparison.json

python scripts/prepare_initial_geometry_assistance_v1.py \
  --control-root /path/to/retained-short-prompt-control \
  --molmopoint-checkpoint /path/to/pinned-MolmoPoint-snapshot \
  --sam-acquisition /path/to/checkpoint-acquisition-r1.json \
  --output /path/to/new/inputs-r2
```

Both commands refuse existing outputs and block networking. The second repeats
evidence replay rather than trusting the first command's success record. OS-level
network isolation was also used for the retained local verification.

## Scope

This is a retrospective, published-code reconstruction from retained evidence.
It is not a new SAM/MolmoPoint inference run, independent re-execution of SAM's
neural network, or public release of the private raw artifacts. The public recipe
requires those retained private inputs to reproduce the result. Retained provider
evidence is rechecked locally; no fresh Kaggle availability check is implied.

No scientific design or mask is changed, and no GPU job, upload, reservation or
new model generation is authorized or performed. The bounded live launcher and
the final private launch-package review remain separate pending work.
