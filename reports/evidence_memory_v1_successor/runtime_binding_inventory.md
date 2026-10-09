# Track 2 Stage 1: inventory of outdated runtime bindings

**Scope.** This inventory covers the Stage 1 run package as it stood on `track2-evidence-memory-v1` at `107d8b4`
(`research/evidence_memory_v1/run/`, derived from the WS3 questionnaire v1 stack). It is compared against the
verified runtime at `5a21dd3` (`origin/wheelhouse-replacement-audit`). That runtime is the control-interface v1 and v2
packages and the shared `certification/direct_publisher_smoke_v1/` controller they import, which ran on one RTX PRO
6000 with the CPython 3.12 image, issued 131 counted requests and completed cleanup.

**Method.** Every import, path and pin was read in the run package's live path and in its authority, launcher,
supervisor, worker, host, monitor, resources and evaluator. Each one was then checked against the verified runtime's
protocol and code.

**Not covered.** Nothing was run on a GPU or contacted on a provider; this inventory is from source only.

**Rows 1 to 4 would stop a live run.** The rest are bindings the verified runtime replaced or never ran.

| # | Area | Track 2 binding at `107d8b4` (where) | Against the verified runtime | Successor binding |
|---|---|---|---|---|
| 1 | Wheel installation path | `run/launch.py` live branch → `certification.phase4_integrated_v2.prepare` → `phase4_v6.target_install_probe.verify_wheelhouses`. That check requires a wheelhouse `SHA256SUMS` with SHA-256 `44029b36…` and a `wheelhouse-manifest.json` (`bc016164…`), 179 inventory entries, plus 31 game wheels from the competition mount `arc_agi_3_wheels`, checked against `reports/phase4_v2_offline_package.json` (scope `15_allowlisted_development_games_only`). Two interpreters (game and model), with a 450 s installation deadline. | **Fails on the verified dataset.** The publisher's flat version-1 mount has a different `SHA256SUMS` (`805388ef…`), no `wheelhouse-manifest.json`, and 174 wheels plus three metadata files. | The verified flat-mount integrity check (`install.verify_bundle` → `preflight.verify_mounted`) against `trusted_manifest.json` (`3691cb88…`) and `trusted_requirements.lock` (`ba80d350…`). Then an offline `pip --python <venv> install --no-index --no-cache-dir --require-hashes --only-binary=:all:`, `pip check`, exact versions, imports and the torch CUDA build, all in owned process groups. One venv; no game wheels. |
| 2 | Wheel dataset reference | `driessmit1/arc3-vllm-h100-wheelhouse-v3`, no version. The first existing of two mount paths is used (`run/launch.py:145-147`). The WS3 review metadata attaches the dataset without a version. | Unpinned; an ambiguous mount is accepted. | Version 1 is pinned, with publisher metadata hashes (`README.md` `d2e8da6d…`, `SHA256SUMS` `805388ef…`, `requirements.lock` `bb3e30ac…`). Exactly one unambiguous mount is required. |
| 3 | Model attachment | A Kaggle Model, `qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1`, mounted at `/kaggle/input/models/...` with tree `052ab27f…` (`config/operational_primary.yaml`). It is checked by `phase4_integrated_v2.model_artifact.verify_artifact` against `research/grounded_action_v1/artifact_contract.py`. | Not the verified attachment. | A dataset-backed private snapshot, pinned by `tree_sha256` `b480ad92…`, at revision `d9748a51`. Required files and four shards. The two Kaggle mount layouts are resolved unambiguously. Owner, dataset and mount stay `REPLACE_WITH_` placeholders. |
| 4 | Image and Python | No image pin. The WS3 review metadata has no `docker_image`, so Kaggle uses its latest image. The verified runtime's first GPU attempt failed on Python 3.13.15. Python 3.12 is asserted only inside the r5 install probe. | Unpinned. | `gcr.io/kaggle-private-byod/python@sha256:37c64f7d…`, pinning `original`. Host facts require CPython 3.12, glibc ≥ 2.34 and x86_64. |
| 5 | Server launch | `config/m0_launch_spec_q3vl30.json` argv, with `--enable-prefix-caching` swapped at run time (`host.derived_argv`). `required_packages.torch = 2.10.0+cu128`, the version string the verified runtime corrected to `2.10.0` plus a separate CUDA 12.8 check. | Equivalent flags, but outdated provenance and version string. | The protocol's own argv with `--no-enable-prefix-caching` written explicitly. The other model flags are identical (tensor parallel 1, `--generation-config vllm`, GPU memory 0.75, `--max-model-len 65536`), with offline env and TCP-only readiness. |
| 6 | Model readiness | `phase4_v6.target_install_probe_r5.MODEL_CHECK` (exec); `phase4_integrated_v2.tokenizer_binding.verify`; version asserts in the model interpreter: transformers 4.57.6, tokenizers 0.22.2, jinja2 3.1.6, vllm 0.19.0, torch 2.10.0. | Never ran on the verified runtime. | The verified `PACKAGE_CHECK` in the venv (versions, imports, torch CUDA build) and the model-tree pin. |
| 7 | Tokenizer during the run | `AutoTokenizer` loaded from the model directory in the model interpreter (`host.pinned_model_factory`), used for pre-transport admission and token parity. | The verified controller runs in the image interpreter, which has no pinned transformers. | An offline audit with the pinned tokenizer (transformers 4.57.6 / tokenizers 0.22.2 in an isolated environment, with pure-Python parity), bound into the protocol. Admission uses the audited count, and parity with the server is enforced on every call. |
| 8 | GPU binding and cleanup | `phase4_integrated_v2.{monitor, telemetry, async_telemetry, monitor_diagnostics}`, `evaluation.phase4_target.{bind_gpu, gpu_pids}`, and `run/resources.independent_cleanup`. | Never ran on the verified runtime. | Exactly one GPU whose name contains "RTX PRO 6000", `nvidia-smi` telemetry, and an independent GPU cleanup check. The launch metadata sets `machine_shape: NvidiaRtxPro6000`. |
| 9 | Process lifecycle | The WS3 supervisor/worker/monitor/host chain, plus `phase4_integrated_v2.{gated_exec, scratch.worker_environment, bridge (Unix socket), evidence}`, `scripts/run_grounded_action_v1_engine_local.terminate_group` and `evaluation.phase4_runner`. | A different lifecycle from the one verified. | The verified `run.py` (derived): one controller; owned process groups for every install command and the server; subreaper; cutoff alarm; cleanup reserve; final lifecycle deadline; evidence manifest. |
| 10 | Notebook and packaging | None for Track 2. Protocol v2 section 14.4 states that the package builder, notebook, review builder and snapshot test were not derived. `run/authority.py` names `notebooks/evidence-memory-v1-stage1-review-r1`, which does not exist. | Missing. | The verified `notebook.py` and package script, derived per session. GPU-disabled review snapshots `notebooks/evidence-memory-v1-session-{a,b}-review-r1`, and in-memory launch artifacts available only after the gate passes. |
| 11 | Authority and accounting | `run/authority.py`: one scope (`evidence-memory-v1-stage1`) for both sessions. It binds the phase4 config files. It has no account-attachment, direct-use permission or mounted-byte receipt, and no launch claim or receipt. `maximum_questionnaire_calls = 2896` for both sessions (B schedules 2,832). | Weaker than the verified gate. | The verified gate per session scope: account, permission and byte evidence; source and compute approvals; execution lock; reservation; exclusive claim; durable receipt. `LIVE_ENABLED = False` and the withheld-set check come before any approval is read. |
| 12 | Live import closure | The live path imports `certification.phase4_integrated_v2` (`bridge`, `evidence`, `model_process`, `model_artifact`, `tokenizer_binding`, `prepare`, `dependencies`, `scratch`, `telemetry`, `monitor`, `async_telemetry`, `monitor_diagnostics`, and `gated_exec.py` run as a script), `certification.phase4_v6.target_install_probe(_r5)`, `research.grounded_action_v1.artifact_contract`, `evaluation.phase4_{target,runner}` and `scripts.run_grounded_action_v1_engine_local`. It was never extracted from a payload and checked. | Not part of the verified runtime. | Listed in `successor/plan.STUDY_SOURCES`, source-gated, and imported from each extracted review payload alone (`scripts/check_evidence_memory_v1_session_{a,b}_embedded_inputs.py`). |
| 13 | Evaluator lifecycle receipts | `run/evaluate.lifecycle_errors` reads WS3 receipts: `control/outer.json`, `first-cell-supervisor-cleanup.json`, `notebook-cost.json`, `gpu-cleanup.json`, `monitor/ready.json`. | These receipts do not exist on the verified runtime. | `successor/evaluate.py` checks the verified `result.json` and evidence manifest. The call checks (`run/evaluate.call_errors`) are reused unchanged. |
| 14 | Rehearsal | The WS3 connected stack, with the fixture tokenizer (`action_effect_history_v1.rehearsal.FixtureTokenizer`) and an in-process fake vLLM. | Exercises the old lifecycle. | The verified lifecycle with fixture wheels in a real venv and a scripted stub process (`successor/stub.py`). The stub returns the audited pinned-tokenizer counts. |

## Not outdated: reused unchanged

These bindings are runtime-independent and are reused byte for byte from `107d8b4`:
- the frozen-set builder and request builder (`stage1.py`), prompts, arms, schemas and budgets (`protocol.py`,
  `readers.py`, `render.py`, `writers.py`, `fidelity.py`, `schema.py`, `trajectories.py`, `tokens.py`);
- the call order, admission and stop rules (`run/schedule.py`, which is v1's reviewed rules);
- the append-only run evidence and recovery (`run/evidence.py`);
- scoring and the technical-only session report (`run/score.py`);
- the call checks (`run/evaluate.py`);
- the pooled analysis (`run/final.py`).

`successor/derivation.json` records each file's SHA-256 in each session package, and a test compares each file with
`107d8b4`.

The runner is the only reviewed module derived rather than imported. `successor/runner.py` is `run/runner.py` with
the frozen set passed in as an argument (the session's, not `run/probes.json`) and absolute imports.

## Verified-runtime properties that remain unverified for Track 2

- **Strict JSON-schema decoding.** The verified runs used `json_object` decoding; Track 2 requests strict
  `json_schema` (structured outputs). The trusted lock includes xgrammar 0.1.34, llguidance 1.3.0 and outlines_core
  0.2.11, but no run on this runtime has exercised strict schemas.
- **Prompt-token parity with this server build.** The parity between vLLM's prompt-token count and the pinned
  tokenizer was established on the earlier v3 runtime (`ecv3`), not on this one. The successor stops a session at the
  first mismatch.
- **Per-call prefix-cache counters.** `vllm:prefix_cache_queries_total` is read per call from vLLM 0.19's
  Prometheus endpoint. The verified runs confirmed caching off only from the server log, not from counters.
