# Track 3 runtime v2: successor package for review (r1)

**Status.** This is a GPU-disabled review candidate. It authorises nothing: no GPU time, provider call, upload,
reservation, approval, claim or submission. Its live gate refuses in this checkout.
- **What earlier work it replaces.** The R7 blocker was that the wheel dataset could not be accessed. The control-interface
  v1/v2 probes since verified the runtime it needed (`origin/wheelhouse-replacement-audit` at `5a21dd3`: one RTX PRO 6000,
  pinned CPython 3.12 image, version-1 publisher wheels from the trusted hash-pinned lock, dataset-backed model snapshot,
  full cleanup, zero game actions).
- **What changes.** This successor binds the unchanged protocol-v2 study to that runtime and adds what gameplay needs on
  top of it.
- **What is preserved.** Every historical Track 3 file at `bc19919` is byte-identical: protocol versions, review r1-r4,
  authorization r5/r6, the R5/R6 session-1 packages, R7 preparation, and the R6 submission, invalid-attachment,
  cancellation, consumed-claim and quota records. All 203 files are pinned in
  `stagnation_supervision_runtime_v2_historical_preservation.json` and tested.
- **The R6 attempt.** It stays consumed. Its rejected or cancelled submission is historical evidence, not a study result.
  The successor's gate refuses the R6 attempt id by name.

| Item | Location |
|---|---|
| Successor package | `research/stagnation_supervision_runtime_v2/` (derived files: `derivation.json`) |
| Review snapshot | `notebooks/stagnation-supervision-v1-runtime-v2-review-r1/` |
| Review lock SHA-256 | `84bf195d77c31d9a22075442838b109ba9486154103e146a6ff3acd3c83d4ec7` |
| Review check | `reports/stagnation_supervision_runtime_v2_review_check_r1.json` (passed) |
| Binding inventory | `reports/stagnation_supervision_runtime_v2_binding_inventory.md` |
| Runtime-only diff | `reports/stagnation_supervision_runtime_v2_runtime_diff.json` (generated; `--check` reproduces it) |
| Detector verification | `reports/stagnation_supervision_runtime_v2_detector_verification.json` |
| Staged rehearsals | `..._staged_interpreters_r1.json`, `..._staged_session1_r1.json`, `..._staged_session2_r1.json` |
| CPU suite receipt | `reports/stagnation_supervision_runtime_v2_local_checks_r2.json` (r1: a retained failed first run) |
| Owner/reviewer questions | `reports/stagnation_supervision_runtime_v2_owner_questions.md` |

## 1. Runtime-only diff

**Payload.**
- The successor embeds 159 files: the computed closure of the five process entry points plus every hash-bound science
  file.
- R4 embedded 1,111 files, R6 the same 1,111 with only `closed_loop/authority.py` swapped, and R7 1,118.
- All 131 files that the successor and R4 share are byte-identical (28 files are added, 980 R4 files are dropped).
- What changed is the runtime layer only:
  - nine runtime modules were replaced by successors: supervisor, worker, host, monitor, resources, target evaluator,
    launcher, installer and gate;
  - four runtime pieces were derived unchanged from the verified runtime: publisher preflight, install, process ownership
    and host facts, together with its trusted manifest, lock and proposal;
  - hand-written modules were added for model binding, mounts, closure, packaging, launch accounting, provider-receipt
    validation, verification and the post-run report.
- Each derived file inverts to its recorded source (commit, path and SHA-256) through its listed literal replacements. The
  tests check this without git, and `scripts/derive_stagnation_supervision_runtime_v2.py --check` re-derives every file
  from the git objects.

**Bindings.**

| Binding | R6 launch | Runtime v2 launch |
|---|---|---|
| Wheel input | `driessmit1/arc3-vllm-h100-wheelhouse-v3` (unversioned) | `.../v3/1`, publisher metadata pinned |
| Wheel check and install | old `SHA256SUMS` plus `wheelhouse-manifest.json` (absent from the recreated v1 mount, so it fails closed); pins only | 174 trusted wheels plus 3 publisher files; `--require-hashes` trusted lock `ba80d350...`; `pip check` |
| Model | Kaggle Model, tree `052ab27f...` (81 files) | dataset snapshot, tree `b480ad92...` (20 files). The private reference and mount stay `REPLACE_WITH_`. The tokenizer, chat template, config, revision and layout are identical |
| Image | none (the latest image ran CPython 3.13.15 in the first smoke attempt) | `gcr.io/kaggle-private-byod/python@sha256:37c64f7d...`, pinning `original` |
| Machine and competition | `NvidiaRtxPro6000` in the request; competition attached | both in the launch metadata |
| Notebook interpreter | imported `agent -> arcengine` before installation | standard-library closure only. This was found by the staged rehearsal; the values are unchanged |
| Mounts | wheel: first existing path; competition: one hard-coded path | exactly one of the two layouts for each input |
| Gate | R6 approvals and the consumed reservation | new scope; separate source, compute and launch decisions with provenance; account/attachment, use-permission, byte and model evidence; `ssv1rt2-` attempts; the R6 id refused |
| Provider | R7 receipts for the old inputs | version-bound receipt validation for the new inputs, run immediately before the push. `invalid*Sources` means rejected, even with HTTP 200 |

**Unchanged.**
- The effective vLLM argv and environment equal the verified runtime's exactly.
- Lifecycle values: 450-s installation, 900-s startup, session limits 5,400/5,100 and 4,800/4,500 s, the 300-s cleanup
  reserve, 800-s group admission, 0.5-s telemetry, the evidence budgets and the no-retry rules.

## 2. Scientific configuration, reconfirmed from the frozen sources

All the files below are bound by hash in `protocol.json` (`science`), re-hashed by the gate in the extracted source, and
unchanged since `bc19919`.

**Games** (`closed_loop/protocol.json`, SHA-256 `dee4faa8...`), all at seed 0 with frozen initial hashes:

| Game | Role |
|---|---|
| ar25-0c556536 | stagnation case, design-informed |
| wa30-ee6fef47 | continuation case, Tier A |
| ls20-9607627b | continuation case, Tier B, retained with its display-novelty limitation (decision of 2026-10-02) |
| s5i5-18d95033 | declared blind spot, reported separately |

All are exposed development games.

**Horizon and schedule.**
- 40 actions per episode.
- Session 1: block 1 plus three continuation repeats, 15 episodes, at most 600 policy calls and 32 reflections.
- Session 2: block 2, 12 episodes, at most 480 policy calls and 32 reflections.
- Two sessions, each a separate package run.

**Arms.** Continuation (detector observes only), periodic (after every 10th action) and triggered (frozen detector). They
share a cooldown of 6, a cap of 4, an 8,000-token ceiling, 400 reserved output tokens, a minimum of 10 remaining actions,
a suggestion lifetime of 10 and 1,600 characters (`bridge.EXPERIMENT_POLICY`). Reflections use `max_tokens` 400; policy
requests use 128, temperature 0, seed 0 and no thinking.

**No-restart rule.**
- Play stops at WIN or GAME_OVER (`runner.py`, lines 241-245 and 319).
- The policy prompt forbids reset and action 0 (`contract.py`, line 26).
- Legal ids come from the reported actions, 1-7.
- The stop reasons contain no restart.

**Trigger** (`trigger_spec.json`, SHA-256 `8dc8d909...`): `state_action_recurrence = 2`, `tiny_effect_repeat = 10`,
cooldown 6, tiny cells 4.

**Endpoints** (`outcomes.py`, `closed_loop/evaluate.py`, frozen):

| Endpoint | Definition |
|---|---|
| Behavioural recovery (primary) | window 10, quiet period 5 |
| Completed levels (solving) | environment-reported level increases |
| Provisional false-interruption gate | 10% cap; at least 60 LC points, 2 games and 4 episodes; wa30 the only eligible control; ls20 exploratory |
| Realised cost | calls, tokens and latency per arm |
| Reliability | invalid, failed and unknown counts |

**Stop rules.**
- Reflection interface: more than 50% invalid after at least 10 attempts.
- Dispatch failures above 10%.
- Zero detector firings in `b1-ar25` continuation at 40 actions.
- A token-audit mismatch is a technical failure.
- Admission cutoff with a cleanup reserve.
- No retries.

`report.py` arranges the frozen evaluator's output so that recovery (loop exit), novelty inside the windows, completed
levels, false interruptions and cost stay separate. It adds the descriptive ls20 display/oscillation report that the
retention decision requires. Nothing in it feeds an endpoint.

No scientific element required a change, so no amendment is proposed. The two owner questions are analysed with options
in `stagnation_supervision_runtime_v2_owner_questions.md`.

## 3. Detector and integration verification (CPU)

From `stagnation_supervision_runtime_v2_detector_verification.json`, which is recomputed by the tests and must match:

**Causality.** Prefix replays over all 152 fixture trajectories (1,692 steps) show that transition records, detector
signals, triggers, reflection requests and supervision decisions at step t depend only on records 0..t.

**Thresholds.**
- Recurrence fires at the 2nd exact (frame, action) repeat, never the 1st.
- The tiny-effect streak fires at the 10th identical action of at most 4 cells.
- A failed dispatch neither extends nor breaks a streak; an unknown outcome restarts it.
- 4 cells count as tiny; 5 do not.
- With cooldown 6, triggers fall at 1, 7 and 13.

**Ordinary continuation.**
- On held-out hard negatives: 4/76 trajectories, all `delayed_effect`, reproducing the retained evaluation.
- On archived real development play (action-effect-history v1, 12-step episodes, mechanical labels):

| Game | Triggers / steps | LC points | Triggers at LC |
|---|---|---|---|
| wa30 | 1 / 48 | 48 | 1 (a wall-bump repeat) |
| ar25 | 8 / 48 | 0 | 0 |
| s5i5 | 2 / 48 | 0 | 0 |

**Terminal states and failures.**
- No reflection at a terminal state (0 remaining actions), at a reset or level change, after index 29, or with an
  unobserved state. Detector statistics restart after a boundary.
- Failed dispatches never fire.
- Transport-failed and `length`-finished reflections are charged, invalid and deliver nothing; only a later valid one
  delivers.
- Windows that end in a terminal state are censored; an unknown outcome inside a window makes it indeterminate.
- At the runner level, a fault matrix runs through the successor stack: transport, model start-up, monitor exit and
  storage faults fail without a result, while a surviving child and invalid reflections still complete. Each case retains
  its evidence, cleans up and is not retried.

**Display versus progress.** A synthetic moving display during oscillation gives 40/40 new full frames, 39 playfield
revisits, all points LC, no firing and 0 levels. On ls20 with the real engine:

| Scripted policy | Full frames new | Playfield revisits | LC | Detector firings | Levels |
|---|---|---|---|---|---|
| alternate 1,2 | 40/40 | 39 | 40/40 | 0 | 0 |
| rotate 1,2,3,4 | 40/40 | 38 | 40/40 | 0 | 0 |
| repeat 1 (a blocked move repeats the whole frame) | — | — | — | triggers at 7, 13, ..., 37 | — |

- A counter-only loop stays `not_recovered` although every window frame is new.
- A genuine exit followed by a reported level is `recovered` and counts one completed level.
- Display-driven novelty never becomes recovery or solving credit.

## 4. Rehearsals and checks (CPU only; scripted model; injected GPU; not target evidence)

**Review check.** It verified all 159 bindings and compiled every embedded file. The live cell refused at the gate, giving
exactly "unresolved placeholders" and "no review source lock". There was no `nvidia-smi` call, no leftovers and no
`/kaggle` access. The embedded cell's rehearsal (`b1-ar25`, three arms) replayed as technically complete with verified
cleanup.

**Staged interpreters**, from the extracted review payload on `/usr/bin/python3` 3.12.3:
- All 174 wheels were byte-verified and installed in 208 s from the trusted lock (249 s overall).
- Every game-side module and every model-side module imported in its own venv, including
  `vllm.entrypoints.openai.api_server`.
- The effective argv equalled the verified runtime's.

**Staged sessions.** Both ran the complete frozen schedule at 40 actions from the extracted review payload, on a base
CPython 3.12 notebook interpreter:
- the supervisor, worker and monitor ran in the real game venv (31 competition wheels);
- the host ran in the real model venv (174 trusted wheels) with the scripted transport;
- the offline engine and an injected GPU stood in for the target.

| Session | Episodes | First-cell lifecycle (s) | Installation (s) | Dependency trees removed | Cleanup verified | Target evaluator |
|---|---|---|---|---|---|---|
| 1 | 15 (7 continuation, 4 periodic, 4 triggered) | 504.5 | 236.9 | yes | yes | technically complete, lifecycle verified, no problems |
| 2 | 12 (4 per arm) | 486.1 | 248.0 | yes | yes | technically complete, lifecycle verified, no problems |

The scripted outcomes in these receipts reflect the fake server, which follows suggestions. They are plumbing evidence,
not results. In both sessions the false-interruption gate reports `not_certifiable_minimum_not_met`.

**Derivation.** On the Windows checkout, `scripts/derive_stagnation_supervision_runtime_v2.py --check` reports that all 16
derived files match and that 14 invert to their git sources.

**Full CPU suite** (`stagnation_supervision_runtime_v2_local_checks_r2.json`). 232 tests ran with 0 failures, 0 errors
and 0 skips, in 1,209 s on Linux CPython 3.12.3:
- 161 historical R4 tests;
- 71 `test_ssv_*` tests: 22 from the R5-R7 suites and 49 runtime v2 tests (binding 17, gate 13, runtime and
  connected 13, verification 6).

All seven read-only receipt checks passed:

| Check | Result |
|---|---|
| R4 derivation | 13 files match |
| R4 local-check receipt | passed |
| R3 token-audit input replay | 1,122 requests |
| R4 package review | reproduced |
| R7 package check | reproduced |
| Runtime v2 detector verification | reproduced |
| Runtime-only diff | reproduced |

`--check` confirms that the receipt binds the committed sources and tests.

The first suite run (`..._local_checks_r1.json`) is retained as **failed**, for two reasons:
- The harness discovered tests with the repository as the top level, which breaks the R4 suite's own
  `from test_stagnation_supervision_v1_connected import ...`.
- One runtime v2 gate test still expected "no review source lock" after the r1 snapshot existed.

Both were fixed: discovery now uses `tests/` as the top level (as R4 does), and the test accepts either refusal. No
product code changed between the two runs.

**Launch build.** In this checkout it refuses, citing the unresolved placeholders and the absent source approval.

## 5. What remains (owner, reviewer and target)

1. **Owner decisions.** The false-interruption claim (recommendation: keep it not certifiable). Reflection placement
   (recommendation: keep as frozen). The auditor's identity, role and strata, fixed before the run.
2. **Private binding.** In a private checkout, fill the model dataset owner/slug/version, the verified mount path and the
   consuming kernel ids. Then build a privately bound review successor, because new hashes need a new review.
3. **Evidence.**
   - Account and attachment evidence for the wheel v1, the model dataset and the competition.
   - A scoped direct-use permission for this study.
   - A mounted-wheel byte receipt.
   - A model snapshot verification receipt.
   - Fresh provider read receipts immediately before the push.
4. **Human decisions.** Separate source, compute and launch decisions with confirmation provenance, then an execution lock
   and a reservation per session. The consumed R6 attempt is not reusable.
5. **Target-only facts, still unverified.**
   - CUDA, model load and startup time.
   - GPU cleanup on the RTX PRO 6000.
   - Real per-step timing against the 5.1-6.1 s estimate.
   - The real competition mount on the pinned image.
   - The 450-s installation window (WSL took 208-249 s; the earlier target split install took 133 s).
6. **Limits that remain open.** The second qualified continuation control and Phase 4 closure.
