# Multimodal preflight v1 r2: startup timeout before any probe

Kaggle reported **ERROR** for version 1 (attempt `mm1-bf1b6c23089f4b588da394ba8195c909`).
The model host did not become ready within the frozen **750-second model
startup ceiling**. The supervisor stopped it with
`TimeoutError: model startup ceiling` at 907 s of the 1,680-second lifecycle.
**No probe was sent:** no text control, no image request, and no mount
inventory or processor record reached the worker.

The outcome class is **`lifecycle_failure`**. It says nothing about image
support in either direction, and it is not `dependency_missing`,
`image_rejected_by_server` or any other image outcome. The perception
comparison stays **blocked**. The attempt is consumed and no retry was launched.

## What was verified

- **Cleanup.** Independent process and GPU cleanup passed: process groups
  absent, zero remaining GPU processes, and the probe took 0.05 s. Dependency
  trees and the extracted source were removed.
- **Downloads.** All **20 downloaded files** (19 outputs plus the console log,
  2,775,903 bytes) were hash-verified and archived in
  `evidence/phase4-multimodal-preflight-v1-r1-completed.zip`, SHA-256
  `a0c8011f48851b1683efbb20caee716f6a8100d42766b7d4e873f9056996f9c2`. Member
  hashes are in `phase4_multimodal_preflight_v1_completed_archive.json`.
- **Independent evaluation.** The frozen `replay()` requires
  `worker/state.json`, which does not exist because the worker never reached
  the probes. The frozen `evaluate()` was therefore applied to the retained
  supervisor report and monitor telemetry. It reproduces the target's own
  evaluation exactly: verdict `lifecycle_failure`, with the same error set
  (`phase4_multimodal_preflight_v1_pilot_evaluation.json`).

## Where the time went

The console log and bounded worker logs show only the usual interpreter
warnings and one `transformers` import warning. There is no vLLM server output
and no mount-inventory line; the service prints that line after loading the
processor. The resource monitor retained 2,843 samples. Compared with
integrated v2, which used the same model host path and mount:

| | Integrated v2 | Preflight r2 |
|---|---|---|
| Worker start | 122.5 s | 156.5 s |
| Flat pre-server phase (RSS flat, no VRAM, no scratch growth) | ~125 → ~510 s (**~385 s**) | ~159 → 907 s (**>748 s**, then killed) |
| RSS during that phase | 1,045–1,065 MiB | 976–990 MiB |
| vLLM weights on GPU | at ~527 s | never |

The two phases look like the same stage. Before the server starts, the
model host verifies the full **64.5 GB model tree hash**, then the tokenizer,
then (new in this package) the small-file mount inventory, and then the
processor load. The ~70 MiB RSS difference is explained by v2's game worker
importing the agent packages. That worker also wrote a 59 KB cache file
within its first second, which the preflight worker, having no game side, did
not.

The RSS stayed flat for 748 s. That fits a slow, streaming hash better than a
hang inside the processor load, whose imports would have raised RSS. But
nothing inside this stage was timestamped. **The retained evidence cannot
distinguish** slower mount reads on this host (the hash would have needed
roughly twice v2's time) from a stall after hashing and before the processor
imports. The cause is therefore **not isolated**. Earlier startups on this
stack measured 404 s (integrated v1), 409 s (grounding), 492 s (coordinates)
and 525 s (integrated v2). This package inherited grounding's 750 s cap rather
than integrated v2's 900 s cap.

## Accounting

Notebook elapsed was 909.08 s. Account SDK usage rose from 7,385.136 s (last
observation, after integrated v2) to 8,303.717 s, a change of 918.581 s. That
figure is account-wide, not exact per-attempt billing, and exact billing stays
null. No further run is authorized.

## Proposed next revision (not implemented, not authorized)

A future r3 would change only startup observability and the startup ceiling.
The probes, evaluator, outcome classes and blocking rules stay as they are.

1. **Stage markers.** Emit timestamped JSON markers from the model host before
   and after each startup stage: authority, runtime check, artifact hash,
   tokenizer, mount inventory, processor load, server launch, readiness and
   canary. Also periodically report artifact-hash bytes read, so that a
   future stall can be attributed.
2. **Startup ceiling.** Raise the model startup ceiling from 750 s to 900 s,
   the value integrated v2 used, within the unchanged 1,680 s internal and
   1,800 s provider budget. With install of about 160 s, startup of 900 s,
   probes under 60 s and the 300 s cleanup reserve, the total stays inside the
   lifecycle.
3. **Local tests.** Add a test that the markers are retained when startup times
   out.

A re-attempt would need a new review revision, source approval and a fresh
1,800-second compute authorization. Phase 4 remains open.
