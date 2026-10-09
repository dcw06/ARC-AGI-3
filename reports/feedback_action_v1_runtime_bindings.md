# Feedback-action v1: runtime-binding inventory (successor runtime v1)

Prepared October 8, 2026 on branch `track1-successor-runtime-v1` (from `track1-feedback-action-v1` at `687acc8`).
CPU-only preparation. Nothing here reserves, approves or authorizes compute.

Track 1's live runner was derived from the reviewed action-effect-history (AEH) v1 stack. The launch harness had
not been derived yet, so the runtime it would have inherited is AEH v1's, which ran live on September 25 (attempt
`aeh1-4c75150a`). This inventory lists every runtime binding on that path, whether it is still valid, and its
successor. The successor comes from the runtime verified on one RTX PRO 6000 by the control-interface
action-selection v1 and v2 probes. That runtime is on branch `wheelhouse-replacement-audit` at `5a21dd3`; the v2 run
used review lock `beeb6719…`.

**Status key:**
- **outdated:** would fail, or is no longer the reviewed binding;
- **unverified:** never checked against the new runtime;
- **unchanged:** still valid; kept.

## 1. Model interpreter (vLLM side)

| # | Binding | Old (AEH v1 path) | Status | Successor | Where |
|---|---|---|---|---|---|
| 1 | Wheel source | `driessmit1/arc3-vllm-h100-wheelhouse-v3`, version not pinned; `verify_wheelhouses` expects `SHA256SUMS` `44029b36…`, `wheelhouse-manifest.json` `bc016164…` and a 179-file tree | **outdated**: the publisher recreated the dataset on Oct 5 as a flat mount (174 wheels plus `README.md`, `SHA256SUMS`, `requirements.lock` with other hashes) | Version 1 pinned, with the three publisher metadata hashes. `verify_bundle` checks the exact flat inventory and every wheel's size and SHA-256 against `trusted_manifest.json` (`3691cb88…` canonical) | `runtime.json` `dataset`, `bundle`; `certification/direct_publisher_smoke_v1/preflight.py` |
| 2 | Install method | `phase4_v6.target_install_probe_r5.install_pair` (pip resolves 4 unhashed pins from `--find-links`) | **outdated** | The verified `install()`: fresh venv `--without-pip`, image pip `--python`, `--no-index --no-cache-dir --require-hashes --only-binary=:all: -r trusted_requirements.lock` (`ba80d350…`, 174 pins), `pip check`, exact versions, imports, torch CUDA build `12.8`, every command in an owned process group | `certification/direct_publisher_smoke_v1/install.py` via `runtime.prepare` |
| 3 | Interpreter runtime check | `MODEL_CHECK`: asserts `torch.__version__ == '2.10.0+cu128'`, runs a CUDA tensor op and imports `vllm._C` before start | **unverified** for the new torch wheel (`torch-2.10.0-3`, PyPI). The verified run checked the distribution version `2.10.0` and `torch.version.cuda == '12.8'` instead (runtime-version fix, Oct 7) | The verified package check, plus `model_host_packages` (exact jinja2, tokenizers, torch, transformers, vllm distributions) in the host before start | `install.py` `PACKAGE_CHECK`; `live/host.py` |
| 4 | Model artifact | Kaggle Model `qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1` at `/kaggle/input/models/qwen-lm/…/1` (`config/operational_primary.yaml`; `ARC_MODEL_PATH` override); tree `052ab27f…`; identity checked against `reports/m0_profiles` file count and bytes | **outdated**: not the attached snapshot of the verified runtime | Version-pinned dataset-backed snapshot `REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1`, mount `REPLACE_WITH_VERIFIED_MODEL_MOUNT` (both provider layouts, exactly one). Tree `b480ad92…` (arc3-artifact-tree-v1) is verified before loading. Same model id and revision `d9748a51…`; 5 required files, 4 shards | `runtime.json` `model`; `host.verify_model`; `live/host.py` |
| 5 | Tokenizer files | `certification/phase4_integrated_v2/tokenizer_manifest.json` (revision `d9748a51`) | **unchanged**: byte-identical to the upstream snapshot files in the verified runtime's attachment manifest and to `.cache/phase4-tokenizer` | Same manifest, verified before any count | `live/service.py` (derived, unchanged) |
| 6 | Server command | `config/m0_launch_spec_q3vl30.json` with **`--enable-prefix-caching`** | **outdated**: contradicts Track 1's "prefix caching off" (protocol v2 §4) and the verified argv | Verified argv: `--no-enable-prefix-caching` (exactly once, checked), served name, port, `--max-model-len 65536`, `--gpu-memory-utilization 0.75`, `--generation-config vllm`; server-log confirmation that `enable_prefix_caching=False` | `runtime.json` `server`; `runtime.verify_cache_disabled` (verbatim) |
| 7 | Server process | `phase4_integrated_v2.model_process.ModelService` (inherits the worker group; polls `GET /models`; legacy canary suppressed) | **outdated** | Verified `ModelServer`: own process group, TCP-only readiness, SIGTERM then SIGKILL, group absence verified. The pgid is recorded; the supervisor and the first cell also stop the recorded group. The single retained canary is the first HTTP request | `live/host.py`, `live/supervisor.py`, `scripts/feedback_action_v1_launch.py` |
| 8 | Transport | `OpenAICompatibleCompletionClient` (requests), 120 s | **unchanged**: ran live with vLLM 0.19.0 in AEH v1 | Same; the timeout comes from `runtime.json` | `live/host.py` |
| 9 | Guided decoding | vLLM default (`auto`: xgrammar, `any_whitespace=True`); only the baseline schema ran live | **unverified** for the candidate's extended schema | Unchanged flags. The candidate schema compiles in xgrammar 0.1.34 (trusted lock), and the grammar accepts all 145 scripted completions of the connected rehearsal, CPU only (§4). It has not been verified through a GPU server | `live/rehearsal.py` `GrammarCheck` |

## 2. Game interpreter (engine side)

| # | Binding | Old | Status | Successor | Where |
|---|---|---|---|---|---|
| 10 | Competition mount | Hard-coded `/kaggle/input/competitions/arc-prize-2026-arc-agi-3` | **unverified** on the pinned image: the verified runtime attached the competition but never read it | Both layouts (`competitions/<slug>`, `<slug>`), exactly one real directory, contents verified by hash before use | `runtime.competition_mount` |
| 11 | Game wheels | `arc_agi_3_wheels`: 31 wheels verified against `reports/phase4_v2_offline_package.json`, then pip resolves 6 unhashed pins | Verification **unchanged**; install method **outdated** | Same 31-wheel verification. Then the verified `install()` with `game_requirements.lock`: 31 hash pins, equal to the manifest. The 6 pins resolve to exactly these 31 | `live/game_requirements.lock`; `runtime.prepare` |
| 12 | Game files | `environment_files` staged by `game_assets.stage_games` (manifest-bound) | **unchanged** | Same | first cell |
| 13 | Import closure | `GAME_CHECK`: six packages import, and torch, vllm and transformers are absent | partial | Every module on each interpreter's live path is imported inside it: game 82 modules, model 34. The other side's packages must be absent | `runtime.import_check` |

## 3. Notebook, image, gate and lifecycle

| # | Binding | Old | Status | Successor |
|---|---|---|---|---|
| 14 | Image | not pinned (provider default; its Python changed, see the Oct 7 image failure) | **outdated** | `gcr.io/kaggle-private-byod/python@sha256:37c64f…` (`original`); `host_facts`: CPython 3.12, x86_64, glibc ≥ 2.34 |
| 15 | Notebook inputs | Model source plus an unversioned wheel dataset; kernel id with a real account | **outdated** | Version-pinned wheel dataset; model dataset (placeholder); competition source. Kernel id `REPLACE_WITH_KAGGLE_OWNER/arc3-feedback-action-v1`. The launch package (`enable_gpu`, `NvidiaRtxPro6000`) can only be built after the gate passes |
| 16 | Live gate | Track 1 had none; AEH's `authority.py` is scoped to AEH | n/a | `live/binding.py`, derived from the verified gate. It checks: placeholders; review lock; source and compute approvals bound to `runtime.json`, `protocol.json` and `owner_gates.json`; account, permission and byte evidence for the publisher dataset; a one-session reservation; launch claim. Session 2 needs session 1's independent evaluation, bound by hash |
| 17 | Installation deadline | 450 s for both interpreters (AEH) | **outdated** for a 174-wheel hash-verified install | 900 s from the first cell (the verified runtime's `installation_seconds`). CPU replica: 212 s and 278 s (the latter under concurrent load) for both interpreters plus closure checks |
| 18 | GPU binding | Monitor `bind_gpu` + `validate_sample`: one GPU, name contains `RTX PRO 6000`, VRAM ≤ 86 GiB | **unchanged** | Same (live probes need this study's authority) |
| 19 | Lifecycle | 3,300 s internal, 300 s cleanup reserve, 600 s pair admission, 3,600 s provider timeout | **unchanged** (experiment protocol) | Same; `runtime.json` must agree with `protocol.json` (checked by the gate) |

## 4. What was checked on CPU, and what was not

**Checked (WSL Ubuntu 24.04, CPython 3.12.3, no GPU):**
- The live installation code ran against local replicas of both mounts: all 174 trusted wheels (byte-identical to
  the trusted manifest), the three publisher metadata files, and the 31 competition wheels. Both interpreters
  installed offline with `--require-hashes`. `pip check` passed; versions and imports were exact; torch CUDA build
  `12.8`; the import closures passed; all installation process groups were verified absent.
- The pinned tokenizer and xgrammar 0.1.34 were used from the installed model interpreter, for the token audit and
  the connected rehearsal.

**Real offline-engine checks.** These ran in two interpreters, in WSL on CPU, on the three development games
restored or staged from the committed, manifest-verified archive:

- **Development environment** `/home/jingjing/.local/share/agi/dev-env`: arc-agi 0.9.9, arcengine 0.9.3, numpy
  2.5.2. This is where the track's earlier engine tests ran, and where all Track 1 suites pass.
- **Installed game interpreter**: the 31 competition wheels from the frozen manifest, installed by the live code
  path; arc-agi 0.9.8, arcengine 0.9.3, numpy 2.4.4. These are the versions a live session uses. The engine tests
  passed there: 41 tests, both sessions, frozen initial hashes, s5i5 GAME_OVER at action 50 with nothing after it.
  The connected rehearsals and the review rehearsal also ran there.

**About the `ModuleNotFoundError: No module named 'arcengine'`.** It did not come from either environment. I had
started the rehearsal driver with the system interpreter `/usr/bin/python3`, which has no third-party packages.
The driver imported `research.grounded_action_v1.engine` (`agent` → `arcengine`) only to restore the games. The
first cell itself is standard-library only and does not import it. The driver now stages the games with the live
staging code (standard library only) when a replica competition mount is given, and the rehearsals run under the
game interpreter. No engine check depended on that failed start.

**Not checked:**
- the provider mounts;
- account attachment;
- the pinned image;
- GPU, CUDA and model load;
- server startup;
- guided decoding on the server;
- cleanup on the target.

Records: `reports/feedback_action_v1/runtime_install_check.json`, `reports/feedback_action_v1_runtime_diff.md`.
