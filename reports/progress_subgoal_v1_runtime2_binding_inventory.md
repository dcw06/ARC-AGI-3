# progress_subgoal_v1: runtime-binding inventory of review r4 and its successor (runtime2)

Prepared 2026-10-08 on branch `track4-successor-runtime-v1` (from `origin/track4-progress-subgoal-v1` at `4cedb1f`).
CPU only. No GPU, provider call, upload, reservation, approval or compute authorization was made or recorded.

**Scope.** This inventories every runtime binding of the latest Track 4 package (review r4,
`notebooks/progress-subgoal-v1-review-r4/`, review-source-lock SHA-256 `e7e1518ba6e23b9b…`, 277 bound files) and states
what the successor binds instead. The successor binds the runtime that ran on GPU (`origin/wheelhouse-replacement-audit`
at `5a21dd3`: `certification/direct_publisher_smoke_v1/` and `research/control_interface_action_selection_v2/`).
Review r4 and every earlier revision stay byte-identical. The experiment itself (question set, prompts, arms, keys,
schedule, scoring, stop rules, package limits) is not touched; see `progress_subgoal_v1_runtime2_source_diff.md`.

## 1. Outdated bindings in review r4

| # | Binding | Review r4 (old runtime) | Why it is outdated | Successor (runtime2) |
|---|---|---|---|---|
| 1 | Wheel dataset reference | `driessmit1/arc3-vllm-h100-wheelhouse-v3`, **unversioned** in `dataset_sources` | The verified runtime pins **version 1** and the publisher metadata hashes (README.md `d2e8da6d…`, SHA256SUMS `805388ef…`, requirements.lock `bb3e30ac…`) | `driessmit1/arc3-vllm-h100-wheelhouse-v3` version 1 with those hashes; attached as `…/1` only once private bindings are resolved |
| 2 | Wheel mount path | `research/progress_subgoal_v1/launch.py`: first existing of `/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3` and `/kaggle/input/arc3-vllm-h100-wheelhouse-v3` | Ambiguity was not refused | `host.dataset_mount`: exactly one of the two layouts, else refused |
| 3 | Wheel integrity | `certification/phase4_v6/target_install_probe.verify_wheelhouses`: the **original wheelhouse metadata** (SHA256SUMS `44029b36…`, `wheelhouse-manifest.json` `bc016164…`, 179 listed entries) | The verified publisher mount is flat: 174 wheels plus README.md, SHA256SUMS `805388ef…` and requirements.lock; it has no `wheelhouse-manifest.json`. The old check refuses it at the first manifest hash | `install.verify_bundle` + `preflight.verify_mounted`: exact inventory, every wheel's size and streamed SHA-256 against the trusted manifest (`3691cb88…`, 174 artifacts), the publisher metadata hashes |
| 4 | Installation | `certification/phase4_integrated_v2/prepare.prepare` → `phase4_v6/target_install_probe_r5.install_pair`: **two** venvs (model: vllm/torch/transformers/numpy pins; game: arc-agi/arcengine from the competition mount `arc_agi_3_wheels`, 31 wheels per `reports/phase4_v2_offline_package.json`), 450 s deadline | The questionnaire plays no game; the game interpreter existed only for the old supervisor/worker/monitor stack. The model install resolved from the old wheelhouse layout | One venv (`--without-pip`, host pip `--python`), `--no-index --require-hashes --only-binary=:all:` from the flat mount with the trusted hash-pinned lock (`ba80d350…`), pip check, exact versions (torch distribution `2.10.0`, CUDA build `12.8`, vllm 0.19.0, transformers 4.57.6, numpy 2.2.6), imports; owned process groups; 900 s installation ceiling |
| 5 | Model attachment | Kaggle Model `qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1` in `model_sources`, mounted at `/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/30b-a3b-instruct-fp8/1`, tree `052ab27f…` (`config/operational_primary.yaml`, `reports/m0_profiles/m0-q3vl30-instruct.json`, `research/grounded_action_v1/artifact_contract.py`) | The verified runtime serves a **dataset-backed private snapshot** of the same model and revision, pinned by a different complete tree | `model.source_kind = dataset`, model `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8` revision `d9748a51…`, tree `b480ad92…` (`arc3-artifact-tree-v1`), 4 shards and required files; **`kaggle_source` and `mounted_path` stay `REPLACE_WITH_` placeholders** (private); mount resolved only among the bound dataset's two layouts |
| 6 | Notebook image / Python | No `docker_image` in kernel metadata (provider default image) | The default image moved to Python 3.13 (the direct-publisher attempt failed `python 3.13.15 is not 3.12.x`); the trusted wheels are CPython 3.12 | Pinned `gcr.io/kaggle-private-byod/python@sha256:37c64f7d…` (`original`); host check requires CPython 3.12, x86_64, glibc ≥ 2.34 |
| 7 | Notebook inputs | `competition_sources: [arc-prize-2026-arc-agi-3]`, `dataset_sources: [driessmit1/…-v3]`, `model_sources: [qwen-lm/…/1]`, id `daichongwei06/arc3-progress-subgoal-v1(-review-r4)` | Model and dataset sources no longer match the verified runtime; the account is written into public metadata | Competition retained; dataset sources `driessmit1/…-v3/1` + the private model dataset (review metadata carries only the placeholder until resolved); `model_sources: []`; kernel id `REPLACE_WITH_…` placeholders |
| 8 | GPU identity | `evaluation.phase4_target.bind_gpu` + a separate monitor process (VRAM telemetry, `nvidia-smi`) | Superseded by the verified controller | `host.gpu_facts`: exactly one GPU whose name contains `RTX PRO 6000`, before model serving; telemetry samples; independent post-cleanup GPU check |
| 9 | Server launch | `certification/phase4_integrated_v2/model_process.ModelService` from `config/m0_launch_spec_q3vl30.json` with `--enable-prefix-caching` replaced by `--no-enable-prefix-caching` | The argv is unchanged in content, but launched by the old model host | Identical argv from the protocol (`--no-enable-prefix-caching`, `--generation-config vllm`, `--gpu-memory-utilization 0.75`, `--max-model-len 65536`, same env), started by `server.ModelServer` in its own process group with TCP-only readiness |
| 10 | Canary and caching proof | `action_effect_history_v1.service.canary_request` (action JSON) validated by `phase4_transient_v2.action_contract`; prefix caching proven by per-call `/metrics` counters inside the host | Bound to the old model host and bridge | Verified runtime probes S1–S3 (health, models, canary) and I1–I4; caching proven by the argv and every retained startup configuration entry `enable_prefix_caching=False` (`runtime_controls.verify_cache_disabled`) |
| 11 | Lifecycle, ownership, cleanup | First cell → supervisor → worker (`phase4_integrated_v2/gated_exec.py`) + monitor process groups; Unix-socket bridge to the model host; 3,300 s internal | Superseded by the verified single-process controller | `direct_publisher_smoke_v1` lifecycle: phase ceilings, one clock, cutoff alarm, counted request ledger, server and installation process groups (SIGTERM→SIGKILL, subreaper), final deadline, evidence manifest; internal 3,300 s / admission 3,000 s / cleanup reserve 300 s (frozen package limits) |
| 12 | Authority and accounting | `research/progress_subgoal_v1/authority.py` (source/compute approvals, execution lock, reservation; R2-era record shapes); `scripts/progress_subgoal_v1_package.py` launch with `scripts/phase4_integrated_v2_launch.KaggleBackend` | No account-attachment, direct-use permission or mounted-byte receipts; launch backend from the old stack | Verified-runtime gate (`binding.require_live`): unresolved placeholders, reviewed sources, separate source approval and compute authorization bound to protocol and dataset, account-attachment / direct-use permission / byte-verification receipts, execution lock, unconsumed reservation, launch claim; durable claim/receipt (`launch.py`). New scope `progress-subgoal-v1-runtime2`; nothing inherited |
| 13 | Import closure / payload | 277 files: all tracked `config/*.json|yaml` (124), `agent/`, `evaluation/`, `certification/phase4_*` and other scopes' authority records (e.g. `reports/phase4_integrated_v2_{source_approval,compute_authorization,pilot_launch,pilot_prelaunch}.json`, `notebooks/phase4-integrated-v2-review-r3/review-source-lock.json`) | Old runtime's closure; other scopes' records were embedded | 60 files: the copied controller (17), the successor package (16), and the unchanged experiment sources (27, incl. `probes.json` and `decision_rules.json`); no other scope's records |

## 2. Python and environment assumptions

- Old: the notebook interpreter was whatever the default image provided; installation created two venvs from that
  interpreter with host pip. The questionnaire ran in the "game" interpreter and the model host in the "model"
  interpreter.
- Successor: the notebook interpreter must be CPython 3.12 (pinned image; checked before anything else). The controller
  and questionnaire stage are standard-library only. One venv holds vLLM/torch/transformers/numpy for the server only.
- CPU rehearsals need a host Python with pip ≥ 22.3 (the verified runtime's rule). The development environment
  `dev-env` has no pip, so the rehearsals name `/usr/bin/python3` (pip 24.0) through `PSV1R2_REHEARSAL_HOST_PYTHON`.
- Token audit: `tok-env-4576` (transformers 4.57.6, tokenizers 0.22.2) with the pinned tokenizer files, each matching
  `certification/phase4_integrated_v2/tokenizer_manifest.json` (these equal the upstream snapshot's tokenizer files).

## 3. Import closure of the successor

`research/progress_subgoal_v1_runtime2/runtime_controls.EXPERIMENT_SOURCES` lists the 27 unchanged experiment files the
runtime and rehearsal paths import or read (plus the package and the controller). The builder recomputes it from every
import of the successor's runtime modules and the controller (including function-level imports) and every import-time
import of the reused modules. All of these files have exactly the SHA-256 that review r4 bound, except
`research/progress_subgoal_v1/decision_rules.json`, which r4 bound as a review document and which matches its pinned
hash `38c8de63…`.

Function-level imports in reused modules that are deliberately **not** packaged (paths the successor never executes;
recorded in `derivation.json`): `action_effect_history_v1/contract.py` → `agent/representation.py`,
`phase4_transient_v2/action_contract.py`; `action_effect_history_v1/service.py` → `phase4_integrated_v2`
transport/response/tokenizer modules (the successor uses only `request_hash`); `evidence_comprehension_v2/fake_server.py`
→ `evidence_comprehension_v2/probes.py` (overridden by Track 4's `ScriptedAnswers`). An isolated run of the extracted
payload (`scripts/check_progress_subgoal_v1_runtime2_extracted.py`) confirms the executed paths need nothing else.

## 4. What this inventory does not establish

It does not establish that a future Kaggle session will provision the pinned image, attach the dataset version or the
private model dataset, or allocate an RTX PRO 6000. The private bindings (consuming account, model dataset reference and
mount path) are unresolved by design. CPU rehearsals are control evidence only.
