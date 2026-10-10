# Track 2 Stage 1 successor packages: runtime-only diff

**Comparison.** The Track 2 Stage 1 package at `107d8b4` (branch `track2-evidence-memory-v1`) against the successor
session packages on `track2-successor-runtime-v1`.

**Runtime source.** The verified runtime at `5a21dd3` (`origin/wheelhouse-replacement-audit`). It is vendored byte
for byte:
- `certification/direct_publisher_smoke_v1/` and its nine test files at their own paths;
- the control-interface v2 package files and scripts, as derivation inputs, in
  `research/evidence_memory_v1/successor/verified_sources/`;
- `verified_sources/SOURCES.json`, which records the commit, origin paths and SHA-256 of all 40 vendored files.

**Amended at the protocol freeze (October 9, 2026; review snapshots r2).** The comparison below describes the
runtime-only successor at `9655dbf`. The owner's freeze decisions then changed exactly two reused Track 2 modules
and the two test files covering them; nothing else of `107d8b4` changed:
- `research/evidence_memory_v1/stage1.py`: the recall decoding schema drops `uniqueItems` (scoring unchanged);
- `research/evidence_memory_v1/protocol.py`: the three-way unsupported-claim margin reading;
- `tests/test_evidence_memory_v1_stage1.py`, `tests/test_evidence_memory_v1_protocol.py`: tests of both.

Each amendment is recorded as an exact change from the baseline file (`FREEZE_AMENDMENTS` in the builder; each
session's `derivation.json`: `track2_amended_at_protocol_freeze`), and the tests apply it to the `107d8b4` blob.
The statements below that every baseline file is byte-identical, and that the schemas are unchanged, held until
then. Session B's launch tooling also gained the session-A condition (`successor/session_order.py`); the live gate
is unchanged. The full list is `freeze_change_list_r2.md`.

## Summary

- **No existing file was modified or removed.** The successor only adds files. Every file tracked at `107d8b4`,
  including protocol v1 and v2, the run package, its stand-in, its reports and the Linux verification record, is
  byte-identical (test `test_no_file_of_the_track2_baseline_was_modified_or_removed`).
- **The scientific configuration is reused, not copied or edited.** Prompts, arms, schemas, decoding, budgets, seeds
  and the seed procedure, the frozen-set builder, the schedule, admission and stop rules, scoring, the technical-only
  session report and the pooled analysis are imported from the baseline modules. Each session's `derivation.json`
  records their SHA-256 (`track2_reused_unchanged`), and a test compares each one with `107d8b4`.
- **The runtime changes**, as listed below.

**Derived files.** Each session package's lifecycle files are derived from the verified files by
`scripts/build_evidence_memory_v1_sessions.py`:
- `binding.py`, `run.py`, `runtime_controls.py`, `notebook.py`, `launch.py`, `evidence.py`, `rehearsal.py`;
- the package and embedded-input scripts.

The derivation applies exact-count substitutions with a residue check, and `--check` fails on any drift. The study
runner is `run/runner.py` with the frozen set passed as an argument, derived by the same builder.

## What changed (runtime only)

| Concern | Track 2 at `107d8b4` | Successor |
|---|---|---|
| Lifecycle | WS3 supervisor/worker/monitor/host over a Unix-socket bridge, two interpreters (`certification.phase4_integrated_v2`) | The verified single-controller `run.py`: host facts, bundle integrity, offline install, GPU facts, model artifact, server, startup and inference probes, **study phase**, cancellation probes, cleanup and evidence, on one first-cell clock |
| Installation | phase4 two-interpreter `prepare` against the old R2 wheelhouse manifest (fails on the publisher v1 mount) | Verified flat-mount integrity against the trusted manifest and hash-pinned lock (174 wheels), then an offline venv install with `pip check` and version, import and CUDA-build checks |
| Inputs | Unversioned wheel dataset; a Kaggle Model attachment; no image pin | `driessmit1/arc3-vllm-h100-wheelhouse-v3` version 1 with publisher metadata hashes; dataset-backed pinned model tree `b480ad92…` with `REPLACE_WITH_` owner, dataset and mount; image `python@sha256:37c64f7d…` (original pin); competition binding kept |
| Server argv | m0 launch spec with the prefix-caching flag swapped at run time | The protocol's argv with `--no-enable-prefix-caching` written explicitly; other flags identical |
| Live gate | `run/authority.py`, one scope for both sessions, `LIVE_ENABLED = False` | The verified per-scope gate: placeholders, review lock and sources, source and compute approvals, account, permission and byte evidence, reservation and claim. `LIVE_ENABLED = False` and the withheld-set check run first. Session A's authority cannot run B |
| Accounting | None at launch | The verified exclusive claim and durable receipt; any receipt spends the attempt |
| HTTP accounting | Only completions counted (2,896 ceiling) | Every request to the server is counted by the verified ledger: K0000, then Q/M/V per call (cap = worst case: 194,044 for A, 189,756 for B). The study service still refuses any completion beyond the schedule (2,896 / 2,832) |
| Tokenizer admission | `AutoTokenizer` in the model interpreter | The offline pinned-tokenizer audit (transformers 4.57.6; pure-Python parity on all 5,728 requests), bound into the protocol. Parity with the server is enforced on every call; a mismatch stops the session, as the reviewed bridge's cross-process audit did |
| Canary | The action-effect canary through the bridge | The verified S3 canary, then the startup counter check (K0000), after S3 and I1–I4 and before any study call |
| Probes around the study | None | The verified I1–I4 before the study and C1–C3 after it (counted; a few seconds) |
| Phase ceilings | Installation 450 s, startup 900 s | The verified ceilings: installation 900 s, model verification 600 s, startup 900 s. All are bounded by the unchanged admission cutoff (3,000 s) |
| Cancellation transport | The bridge's bounded exchange closes the socket at the deadline | The verified client's watchdog shuts the socket at the same deadline. Idle verification is unchanged (0.25 s polling, 15 s window), now through counted reads |
| Evidence layout | `control/`, `worker/`, `monitor/` receipts | The verified `result.json` and evidence manifest, plus `study/` (the reviewed append-only call log, server configuration, cancellations, technical summary) |
| Evaluator | `run/evaluate.py` reads the WS3 receipts | `successor/evaluate.py` checks the verified receipts and reuses `run/evaluate.call_errors`, `score_call` and `run/score.technical` unchanged |
| Pooled analysis | `run/final.py` (WS3 output layout) | `successor/final.py`: the same `refusals` and `pooled_analysis`, with inputs bound to the new layout and evaluator sources |
| Notebook | None (protocol v2 section 14.4) | The verified review notebook builder, per session: GPU, internet and TPU disabled; every source embedded and hash-bound; the live closure imported from the payload alone |
| Rehearsal | WS3 connected stack with the fixture tokenizer | The verified lifecycle with fixture wheels in a real venv and the scripted stub (`successor/stub.py`) returning the audited counts |

## What did not change (science), and what enforces it

| Element | Value | Bound and checked by |
|---|---|---|
| Prompts | `protocol.SYSTEM` (SHA-256 `033e7104…`), `question_text`, `reader_messages` | `protocol.py` reused; `experiment.system_sha256`; every request hash re-derived by `stage1.build_request` (token audit, service allow-list, evaluator) |
| Arms | `recent_raw`, `state_keyed_raw`, `memory`; `full_history` as reference | `experiment.arms`; `stage1.ARM_ORDER` |
| Schemas and decoding | Strict `json_schema` per kind; temperature 0, seed 0, `max_tokens` 64, thinking off | `stage1.build_request` reused; protocol `sampling` |
| Common token budget | The recent_raw block per trajectory (119–264 tokens) | `readers.packages`; real-tokenizer cross-check: 0 budgeted blocks over budget; identical selection under transformers on 336 of 336 trajectories |
| Seeds | Development `evidence-memory-v1-development`; repeat drawn from the run seed; bootstrap `evidence-memory-v1-stage1-bootstrap`; requests 0; withheld procedure unchanged | `stage1.py`, `protocol.py`; `freeze.py` implements section 5 steps 1–4 without changing the build |
| Frozen sets and schedule | A: groups 0–5, 2,592 + 304 calls; B: groups 6–11, 2,592 + 240; group-interleaved pass 1; whole-group repeat | `stage1.build` reused; A's stand-in is byte-identical to `run/probes.json`; B is a fresh build; `experiment.passes` |
| Admission and stop rules | Per-call bound 80 s (60 + 1 + 15 + 4) against the 3,000 s cutoff; stop after 2 consecutive timeouts; stop on transport failure, rejection, cancellation, server not idle or a cache violation | `run/schedule.py` reused; the runner logic is unchanged; `experiment.per_call_seconds` |
| Budgets | 3,600 s reserved, 3,300 s internal, 3,000 s cutoff, 300 s reserve, 1 attempt, 0 retries | `plan.STUDY_LIMITS` against each protocol |
| Scoring | Schema first; a truncated answer is invalid and never parsed; invalid answers are retained | `run/score.score`, `run/evaluate.score_call` reused |
| Per-session report | Technical only; the 2% invalid rule in every pass | `run/score.technical` reused |
| Analysis | Once, on A and B pooled, after both qualify | `run/final.refusals` and `pooled_analysis` reused |

## Protocol v2 sections affected (proposed text for a revision; not applied)

- **Section 11.** The runtime estimate's overheads are v3's. Add: "On the verified runtime the whole v2 lifecycle
  took 539.7 s for 131 requests; planning keeps the v3 allowances". See choice 6.
- **Section 12.**
  - The package is now `research/evidence_memory_v1_session_{a,b}` on the verified runtime.
  - The counted-request cap is the plan's worst case.
  - The 2,896 / 2,832 completion ceilings stay.
- **Section 13.** Replace the WS3-derivation description with this report's first table and the derivation records.
- **Section 14.** Items 1, 2 and 4 are now done:
  - the token cross-check passed;
  - the connected rehearsals were rerun on this runtime;
  - the package, notebook, review builder and snapshot test exist.

  Items 3 and 5 remain owner gates (`owner_gates.md`).

## Addendum r3 (October 9, 2026): review documents verified before launch and before evaluation

The r2 locks bind the frozen protocol, the independent evaluator and the pooled analysis as review documents. In r2
only the review check verified them; Track 4's review found the same gap in its package, and r3 applies the same fix.

- **`binding.check_sources`** (both sessions, derived through the builder) also verifies the lock's review
  documents. It requires `REVIEW_REQUIRED`: the frozen protocol, `successor/evaluate.py`, `successor/final.py`,
  `run/evaluate.py` and `run/final.py`.
- **Where the check runs.** The check applies wherever the documents exist by design:
  - the review check;
  - the launch tooling (`launch.claim`);
  - `launch-build` (`notebook.launch_artifacts`).

  Only the in-payload gate passes `review_documents=False` (`binding.consume` and `run.live_main`), because the
  runtime payload never carries the review documents. The launch package was built from a verified checkout.
- **`successor/evaluate.py`, live mode.** The evaluating checkout's latest review lock (sources and review documents)
  must verify, or the session is not technically complete. The output reports the verified lock
  (`review_lock_verified`).
- **Tests.** For both sessions, drift in each required document refuses `require_live` and `launch_artifacts` and is
  reported by the evaluator; the payload gate still passes; and a lock missing a required document is refused.

Review snapshots r3: A `fbad29c7f48f35025d849d6faee35de35368daae001a5356a16ecc58aaca669a`, B `84407411a1e054284adffb52a09d15561883b9aa1010c76442c463687e2601b6`. Nothing scientific changed, and `LIVE_ENABLED` stays False.
