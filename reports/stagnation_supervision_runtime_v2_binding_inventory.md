# Track 3: outdated runtime bindings in the R6 and R7 packages

**Status.** CPU-only inventory, written for the runtime v2 successor. It authorises nothing: no GPU, no provider call, no
reservation, approval, upload or submission. The R6 single submission (HTTP 200 with `invalidDatasetSources`, then
`CANCEL_ACKNOWLEDGED` after the user's stop), its consumed claim and the quota snapshot after cancellation are historical
evidence of an attempt that produced no study result. They are left byte-identical
(`reports/stagnation_supervision_runtime_v2_historical_preservation.json` pins all 203 Track 3 files at `bc19919`).

**Packages inspected.**
- R6 launch: `notebooks/stagnation-supervision-v1-r6-session1-launch/`. This is the R4 payload (1,111 files) with only
  `closed_loop/authority.py` swapped, and its `SaveKernel` request came from `scripts/kaggle_stagnation_supervision_v1_r6_no_retry.py`.
- R7 preparation: `notebooks/stagnation-supervision-v1-preparation-r7/`. This is the R4 payload plus seven provider and
  launch scripts (1,118 files). Its entry point deliberately refuses.

Reference: the verified runtime on `origin/wheelhouse-replacement-audit` at `5a21dd3`
(`research/control_interface_action_selection_v2/protocol.json` and `certification/direct_publisher_smoke_v1/`). It ran on one
RTX PRO 6000 with the CPython 3.12 image and verified cleanup, and made zero game actions.

## Inventory

| # | Binding | R6 / R7 (R4 runtime) | Verified runtime | Effect on a run of R6/R7 against the verified inputs |
|---|---|---|---|---|
| 1 | Wheel dataset reference | `driessmit1/arc3-vllm-h100-wheelhouse-v3`, unversioned | `.../v3/1` (version 1) plus publisher metadata hashes | R6 got `invalidDatasetSources` for this reference. The dataset was recreated on 2026-10-05, and an unversioned reference names whatever is current |
| 2 | Wheel mount path | first existing of `/kaggle/input/datasets/driessmit1/...` or `/kaggle/input/arc3-vllm-h100-wheelhouse-v3`, no ambiguity check | `publisher_host.dataset_mount`: exactly one of the two layouts | An ambiguous mount was not refused |
| 3 | Wheel inventory check | `verify_wheelhouses`: `SHA256SUMS` = `44029b36...` (179 entries) and `wheelhouse-manifest.json` = `bc016164...` | flat mount: 174 trusted wheels plus `README.md`, `SHA256SUMS` = `805388ef...` and `requirements.lock` = `bb3e30ac...` | **Fails closed before installation.** The recreated version-1 mount has neither the old `SHA256SUMS` nor `wheelhouse-manifest.json`. The wheel bytes themselves are the same (the torch `98c01b8b...` and vLLM `2d0e5fae...` hashes match) |
| 4 | Model-interpreter install | pins `vllm/torch/transformers/numpy` resolved from `--find-links`, with no hashes | the trusted 174-pin lock `ba80d350...` with `--no-index --no-cache-dir --require-hashes --only-binary=:all:`, then `pip check`, imports and the torch CUDA build | The dependency closure was not hash-bound |
| 5 | Model attachment | Kaggle Model `qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1` at `/kaggle/input/models/qwen-lm/.../1`, tree `052ab27f...` (81 files, 64,526,033,084 bytes) | dataset-backed snapshot of revision `d9748a51`, tree `b480ad92...` (20 files, 32,268,935,715 bytes). The owner/slug/version and mount path are private `REPLACE_WITH_` placeholders | `verify_artifact` would reject the snapshot (different container), and the old Model mount is not the verified binding. The six tokenizer, chat-template and config files are byte-identical in both, and so are the model id, revision, layout requirements and four shards |
| 6 | Notebook model inputs | `model_sources: [qwen-lm/...]` | `model_sources: []`; the model dataset is in `dataset_sources` | input set differs |
| 7 | Kaggle image | none in the metadata or in the R6 `SaveKernel` request (latest image) | `gcr.io/kaggle-private-byod/python@sha256:37c64f7d...`, `docker_image_pinning_type: original` | The unpinned image ran CPython 3.13.15 in the smoke test's first attempt. The 174 wheels and the 31 competition game wheels are cp312, and `HeadlessEnvironment` asserts 3.12 |
| 8 | Python | implicit (image) | 3.12, glibc at least 2.34, x86_64 | as row 7 |
| 9 | Machine shape | `NvidiaRtxPro6000`, set only in the R6 `SaveKernel` request | in the launch metadata, together with the competition attachment | unchanged intent; now carried by the package |
| 10 | Competition mount | hard-coded `/kaggle/input/competitions/arc-prize-2026-arc-agi-3` | (game side; the probes attached the competition but played no games) | Only one layout was accepted. Runtime v2 accepts exactly one of `competitions/<slug>` or `<slug>`, the same rule as the dataset mounts |
| 11 | Notebook-interpreter import closure | the first cell imported `closed_loop.supervisor` (for `LIVE_INTERNAL_SECONDS`), which pulls `agent -> arcengine` into the image interpreter before any installation | the image interpreter only verifies and installs | **Fails with `ModuleNotFoundError: arcengine` on a base CPython 3.12 interpreter.** Reproduced by the staged CPU rehearsal on `/usr/bin/python3`. The action-effect-history v1 launcher, which did run live, never imported it. Runtime v2 takes the identical 5100/4500 values from the session limits |
| 12 | Payload closure | broad inventory: every `agent/`, `certification/`, `evaluation/` and `config/` file. 1,111 files (R7: 1,118, within 10 KB of the 900,000-byte guard). R7 also embedded the credential-reading R6 adapter | a computed closure of 159 files with an exclusion list for other scopes' authority records and credential helpers, proved by static scan, extracted-payload imports and staged rehearsals | No closure proof existed |
| 13 | Live gate | R6: bound to the consumed `ssv1-r5-session1-reservation-001` and the R6 approvals. R7: refuses | new scope `stagnation-supervision-v1-runtime-v2`, separate source/compute/launch decisions with confirmation provenance, account/attachment, use-permission, byte and model evidence, attempt id `ssv1rt2-...`. The consumed attempt is refused by name | R6 authority cannot be reused |
| 14 | Provider preflight | plan hard-codes the unversioned dataset and the Kaggle Model | version-bound plan for the wheel dataset v1, the model dataset and the competition; listed names must belong to the bound inventories | the R7 receipts cannot vouch for the new inputs |

**Unchanged and reconfirmed.**
- **Server.** The effective vLLM argv and environment (the m0 launch spec with `--no-enable-prefix-caching`) equal the
  verified runtime's exactly.
- **Packages.** Model packages are torch 2.10.0 (CUDA 12.8 build), vLLM 0.19.0, transformers 4.57.6, numpy 2.2.6,
  tokenizers 0.22.2 and jinja2 3.1.6. Game packages are arc-agi 0.9.8, arcengine 0.9.3, numpy 2.4.4, requests 2.33.1,
  pydantic 2.13.2 and python-dotenv 1.2.2.
- **Lifecycle values.** The installation deadline (450 s), startup ceiling (900 s), session limits and cleanup reserve are
  unchanged.

**Import closure for gameplay (verified on CPU, `reports/stagnation_supervision_runtime_v2_staged_interpreters_r1.json`).**
The CPU check covered these steps:
- Replica mounts were built from local hash-verified sources: the 174 trusted wheels and the three version-1 publisher
  files, plus the competition's 31 game wheels and 30 game files from the manifest-locked archive.
- The runtime v2 installer verified every byte, then built both venvs from host pip on `/usr/bin/python3` (3.12.3).
- In the game venv, every supervisor, worker, monitor, engine, agent and evaluation module imported, with no model package
  present.
- In the model venv, the host, model-service, token-bridge, model-process, tokenizer-binding and install-probe modules,
  torch, transformers and `vllm.entrypoints.openai.api_server` all imported, with no game package present. The
  effective argv equalled the verified runtime's, and the pinned tokenizer-library versions were accepted.

**Not verified here.** These need the target:
- CUDA initialisation and model loading;
- the private model dataset's existence, mount and bytes;
- fresh provider read receipts, and acceptance of the attachments by the provider;
- the real competition mount contents on the pinned image;
- target timing of the 450-second installation window. On WSL it took 211 s; the earlier target-side split install took
  133 s.
