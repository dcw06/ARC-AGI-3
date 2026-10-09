# progress_subgoal_v1: runtime-only source diff, review r4 → runtime2 successor

Prepared 2026-10-08. CPU only; no GPU, provider call, approval, reservation or launch. Machine-readable record:
`reports/progress_subgoal_v1_runtime2_source_diff.json` (written by `scripts/diff_progress_subgoal_v1_runtime2.py`).

## 1. Result

**Only the runtime changed. Nothing scientific changed.** Every check below is computed from the files, not asserted:

| Check | Result |
|---|---|
| Frozen question set (`research/progress_subgoal_v1/probes.json`) | identical file, SHA-256 `f93ec44b…` |
| Call order (5,852 calls: withheld pass 1 = 2,790, withheld pass 2 = 2,790 reversed, development = 272) | identical (`research.progress_subgoal_v1.schedule.call_order`, unchanged) |
| Every scheduled request (messages, model, temperature 0, seed 0, `max_tokens` 32, `enable_thinking: false`, strict per-family JSON schema) | identical for all 5,852 calls; request digest `d9a6e365…` |
| HTTP body actually sent | old transport `json.dumps(request, separators=(',', ':'))`, verified client `json.dumps(body)`: whitespace only; decoded JSON identical for all 5,852 calls |
| Arms | the two primary arms, unchanged; their requests differ only in the system prompt; arm B's prompt is arm A's base prompt + the constant safeguard |
| Answer schemas | `questions.response_schema(family)`, strict enum, unchanged |
| Stop rules | admission cutoff 3,000 s; per-call timeout 60 s, idle verification 15 s, bound 80 s; two consecutive timeouts stop; imported from the unchanged `research/progress_subgoal_v1/schedule.py` |
| Package limits | equal to the frozen `decision_rules.json` package limits (1 session; 3,600 s reservation; internal 3,300 s; cleanup reserve 300 s; 1 attempt; 0 retries) |
| Scoring | `research/progress_subgoal_v1/score.py` and the `score_call` rule of `research/progress_subgoal_v1/evaluate_run.py`, unchanged; used by the successor's independent evaluator |
| Served model / revision / tokenizer | `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8` at `d9748a51…`; tokenizer files identical to the pinned tokenizer manifest |
| vLLM argv | identical to the old derived argv (`--no-enable-prefix-caching`; same memory, length, generation-config and env) |

No source file was changed in place: of the 277 files review r4 bound, the 26 the successor still needs are
byte-identical; 251 are no longer part of the runtime payload; 34 runtime files were added.

## 2. Files

| Group | Count | Notes |
|---|---|---|
| Unchanged and still in the payload | 26 | `research/progress_subgoal_v1/{__init__,probes,questions,fixtures,reference,subgoal,schedule,fake_server,rehearsal_timing}.py`, `probes.json`; `research/transition_evidence_v1/{__init__,transition,vocabulary}.py`; the reused `evidence_comprehension_v1/v2` schedule, probes, transport and fake-server modules; `action_effect_history_v1/{__init__,contract,service}.py`; `action_effect_v1/{__init__,records}.py` |
| Changed in place | **0** | |
| Added: verified controller, copied byte-identically from `5a21dd3` | 17 | `certification/direct_publisher_smoke_v1/*.py` (14), `proposal.json`, `trusted_manifest.json`, `trusted_requirements.lock` |
| Added: successor package | 16 | `research/progress_subgoal_v1_runtime2/`: 9 modules derived from `research/control_interface_action_selection_v2` (counted substitutions; diff below), `questionnaire.py` (hand-written adapter), `protocol.json`, `proposal.json`, `derivation.json`, `token-audit.json`, trusted manifest and lock |
| Added: frozen rules file | 1 | `research/progress_subgoal_v1/decision_rules.json` (unchanged; r4 bound it as a review document) |
| Removed from the payload: this package's old runtime modules and the offline scorer | 14 | `research/progress_subgoal_v1/{authority,host,worker,runner,monitor,resources,supervisor,service,transport,evidence,launch,rehearse_run}.py` (old runtime) and `score.py`, `evaluate_run.py` (the scorer: unchanged, now review documents) |
| Removed: reused modules no longer needed at runtime | 11 | `evidence_comprehension_v1/{evidence,score,service}.py`, `probes.json`; `evidence_comprehension_v2/{evidence,probes,representation,score}.py`; `action_effect_history_v1/{protocol.json,rehearsal.py}`; `action_effect_v1/fixtures.json` |
| Removed: old runtime closure outside `research/` | 84 | `certification/phase4_*`, `evaluation/*`, `agent/*`, phase4 scripts |
| Removed: configuration closure of the old runtime | 124 | every tracked `config/*.json|yaml` (incl. other scopes' launch claims and reservations) |
| Removed: other scopes' records and old runtime data | 18 | `phase4_integrated_v2` source approval, compute authorization, pilot launch and prelaunch records and its r3 review lock; the old model profile, offline-package manifest and torch wheel inspection; `grounded_action_v1`; integrated-case and perception data |

`research/progress_subgoal_v1/score.py` and `evaluate_run.py` leave the runtime payload because the runner never scores;
they are bound unchanged as review documents of the r5 lock (the independent scorer).

## 3. Runtime changes (old → new)

| Area | Old (review r4) | New (runtime2) |
|---|---|---|
| Wheels | unversioned `driessmit1/arc3-vllm-h100-wheelhouse-v3`, original wheelhouse metadata (SHA256SUMS `44029b36…`, `wheelhouse-manifest.json`), two venvs incl. game wheels from the competition mount | version 1 flat publisher mount, publisher metadata hashes, 174 wheels vs trusted manifest `3691cb88…`, one venv from the trusted hash-pinned lock `ba80d350…`, no game environment |
| Model | Kaggle Model `qwen-lm/…/1`, tree `052ab27f…` | dataset-backed private snapshot, tree `b480ad92…`; source and mount `REPLACE_WITH_` placeholders |
| Image | unpinned | `gcr.io/kaggle-private-byod/python@sha256:37c64f7d…` (`original`), CPython 3.12 enforced |
| GPU | `bind_gpu` + monitor process | exactly one `RTX PRO 6000` via `nvidia-smi`; telemetry; post-cleanup GPU check |
| Lifecycle | supervisor / worker / monitor groups, model host over a Unix-socket bridge | verified single-process controller: phase ceilings, cutoff alarm, process-group cleanup, final deadline, evidence manifest |
| Request accounting | host allow-list and 5,852-call ceiling | counted ledger: S1–S3, I1–I4, Q00000–Q05851, QIDLE (≤ 750), C1–C3; cap 6,613 |
| Prefix caching proof | per-call `/metrics` counters | argv + every retained startup configuration entry `enable_prefix_caching=False` |
| Idle check after a timeout | host-side `/metrics` polling (0.25 s, uncounted) | counted `/metrics` reads (1 s, each ≤ 1 s) inside the same 15 s window |
| Prompt-token admission | in-process tokenizer before each call | exact offline audit of all 5,852 requests with the pinned tokenizer; each server count must equal it |
| Canary | action-JSON canary | verified runtime S3 canary + I1–I4 compatibility + C1–C3 cancellation probes |
| Authority | `progress-subgoal-v1` approvals, execution lock, reservation | `progress-subgoal-v1-runtime2`: + account attachment, direct-use permission, mounted-byte receipts, launch claim and receipt; nothing inherited |

## 4. Derivation from the verified research package

`scripts/build_progress_subgoal_v1_runtime2.py` derives the 9 package modules and two scripts from
`research/control_interface_action_selection_v2` at `5a21dd3` (basis SHA-256 recorded in `derivation.json`). Beyond the
scope/path renames, the substitutions are:

- `run.py`: the action-selection stage is replaced by `questionnaire.run_questionnaire` (same position: after the
  cache-configuration check, before the cancellation probes); `NOT_ESTABLISHED` adds questionnaire scores; temp prefix.
- `binding.py`: claim path in `reports/` (never `config/`), attempt prefix `psv1r2-`, request cap 6,613, required
  sources = this experiment's unchanged files instead of the action-selection cases.
- `runtime_controls.py`: `validate_protocol` checks this experiment's frozen record (question set, request digest,
  arms and prompt hashes, request settings, schema strictness, timing and stop rules, decision-rules hash and package
  limits, token audit bound to the requests, request plan); `verify_cache_disabled` unchanged.
- `notebook.py`: the payload lists the experiment sources; the lock adds `revision`, `supersedes` (r4),
  `review_documents`, `authorized_seconds: 0`, `gpu_launch_authorized: false`; titles and text.
- `evidence.py`: live evidence class `gpu_progress_subgoal_v1_questionnaire_attempt`; scope text.
- `launch.py`: renames only. `rehearsal.py`, `rehearsal_stub.py`: rewritten around the basis structure for the
  questionnaire (scripted answers, token-audit usage, timeout/idle/HTTP/token/cutoff faults).

Any reviewer can regenerate and compare: `git archive 5a21dd3 research/control_interface_action_selection_v2 scripts
certification/direct_publisher_smoke_v1 | tar -x -C DIR` then
`python scripts/build_progress_subgoal_v1_runtime2.py --basis DIR` (compares; `--write` rewrites).
