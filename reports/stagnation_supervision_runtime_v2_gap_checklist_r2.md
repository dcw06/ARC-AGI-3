# Track 3 runtime v2: gap checklist against the Track 1, 2 and 4 lessons (r2)

**Status.** This is a GPU-disabled source change and review record. It authorises nothing: no GPU time, provider call,
upload, reservation, approval, claim or submission. It applies the frozen protocol
(`reports/stagnation_supervision_v1_protocol_v2_frozen.md`, frozen October 11, 2026 on the owner's decisions). It
changes no science file: every file bound under `science` in `research/stagnation_supervision_runtime_v2/protocol.json`
is byte-identical, and `scripts/derive_stagnation_supervision_runtime_v2.py --check` still re-derives every derived
file and inverts it to its source.

## 1. Checklist

| # | Lesson (where it came from) | Track 3 before r2 | r2 change | Regression |
|---|---|---|---|---|
| 1 | Bind and verify the review documents in the lock and in every repository-side gate; the in-payload gate skips them (Track 1, Track 2) | The lock bound 20 package files; the science files were bound through `protocol.json`; the frozen protocol text and the evaluators outside the payload were not bound | `authority.check_sources` (repository side) requires `review_documents`, listed as data in `research/stagnation_supervision_runtime_v2/review_documents.json` (so the payload does not embed the evaluators): the frozen protocol text, the owner-question record, this checklist, the ls20 decision, and the strict import closure of the independent evaluators (`report`, `target_evaluate`, `pooled`, `selfreview`, the evaluation scripts and the replay script). The in-payload `require()` checks embedded bindings only | `GateR2` |
| 2 | The evaluator verifies the evaluating checkout's review lock under the gate's rules (Track 1) | Not checked | `report.checkout_review_lock`; in live mode `study_report` records the lock and is technically incomplete if it fails | `GateR2.test_the_evaluator_verifies_the_evaluating_checkout` |
| 3 | The inventory is anchored to the reviewed notebook's embedded bindings, and the closure is strict (Track 1) | The lock had to contain only the 20 package files | The repository-side gate requires the complete computed payload closure (no unresolved repository module) and requires the lock bindings to equal the reviewed notebook's embedded `bindings`, after the notebook matches the lock | `GateR2` (inventory, deleted file) |
| 4 | Fail-closed finalization: source removal and final writes charged to the first-cell clock; durable barrier; `finalization_guard_version`, `lifecycle_finalized`, `extracted_source_removed` (Track 1, `3aeeb65`, `cfda982`) | Absent: the receipt was written once; source removal happened in the cell after the lifecycle | Launcher replacements in the derivation (`launch.py`); the cell's fallback removal tolerates an already-removed tree; only a tree carrying the cell's extraction prefix is ever removed (a rehearsal from a checkout removes nothing). The target evaluator requires the guard version, `lifecycle_finalized`, no pending barrier and, live, `extracted_source_removed` | `Finalization`, `PooledRehearsal.test_target_evaluator_rejects_uncertified_finalization_and_ownership` |
| 5 | Supervisor startup ownership (Track 1, `3aeeb65`) | An interruption between spawn and log-thread start could skip the kill and the receipt | Spawn and registration under `defer_startup_signals`; emergency cleanup with `BaseException`; an uncertain spawn never claims group absence; the receipt records `ownership` and `groups_absent`; the target evaluator requires `registered` and `groups_absent` | `StartupOwnership` (real POSIX process groups) |
| 6 | `MPLBACKEND=Agg` for installation checks (Track 1, session 1 attempt 1) | The game interpreter already used Agg (`HeadlessEnvironment`); the model install and its metadata check inherited the notebook's inline backend | Both now run with `MPLBACKEND=Agg` | `InstallationBackend` |
| 7 | Structured outputs checked through vLLM's own request path (Track 1, Track 2) | Not checked for this package | `scripts/check_stagnation_supervision_structured_outputs.py`: vLLM 0.19.0 (backend `auto`) accepts all five policy schemas (the four games' legal sets and the canary), selects xgrammar 0.1.34, and the compiled grammar admits exactly the study-valid answers (50/50 cases agree) | Receipt `stagnation_supervision_runtime_v2_structured_outputs_r1.json` |
| 8 | Canary token types and frozen bounds (Track 1, `d218567`) | Already enforced (integer types, 0 < prompt ≤ 60,000, 0 < completion ≤ 128, parity, `stop`) | None needed: 60,000 + 128 ≤ 65,536, so the context bound is implied | Existing |
| 9 | Replay reconstruction of every request, with mutation tests whose manifests are re-signed (Track 1, `3f140bb`) | Already present: the frozen evaluator reconstructs every policy and reflection request before consuming a response; re-signed mutation tests cover requests, observations, supervision decisions, smuggled suggestions and reflection evidence | None | `test_stagnation_supervision_v1_live_evaluator.py` |
| 10 | Pooled evaluation bound to canonical hashes; stale session evaluations rejected (Track 1, `3f140bb`) | No two-session evaluator existed, although the protocol pools both blocks | `pooled.evaluate_sessions` recomputes both session reports and requires canonical equality with the retained records; live, the session-2 execution lock must bind the session-1 record | `PooledRehearsal` |
| 11 | Session 2 depends on an accepted session-1 evaluation (Track 1) | Not required | `authority.session_dependencies`: a session-2 execution lock binds a technically complete, accepted, live session-1 evaluation made in a verified checkout; it travels in the launch package | `GateR2.test_session_two_binds_an_accepted_session_one_evaluation` |
| 12 | Deterministic decoding makes repeated blocks identical (Track 1 finding) | Anticipated in §5 ("byte-identical" repeats) but not reported | The pooled evaluation reports, for every repeat and every block-2 episode, whether it reproduces its counterpart, and the distinct trajectories per game and arm, with the limitation that intervals over identical episodes overstate precision. The frozen computation is unchanged | `PooledRehearsal` (the scripted rehearsal reproduces exactly) |
| 13 | Mandatory-probe ledger reconciliation (Track 2) | Not applicable: Track 3 has no withheld probes. The analogous checks exist: the exact scheduled episode inventory and order, and counter reconciliation | None | Existing |
| 14 | Check branch history before building or launching (Track 1 process error) | Process item | `git fetch` and `git log` before each build, request and launch; the operations record shows it | Operations |

## 2. Owner decisions implemented (frozen protocol §14)

**Amendment S1 self-review** (`research/stagnation_supervision_runtime_v2/selfreview.py`,
`scripts/stagnation_supervision_selfreview.py`). The frozen text fixes the seed, the quotas, the gate-eligible strata and
the separate ls20 stratum. These details were left open, and are fixed here before any run:
- **ls20 quotas.** The ls20 stratum uses the same quotas as the gate-eligible stratum.
- **Exclusions.** s5i5, the declared blind spot, is not sampled. The block-1 continuation repeats are excluded,
  because they duplicate their originals by design.
- **Reflections.** 20 are drawn from ar25, wa30 and ls20, 10 per reflection arm, with the other arm filling a short
  one.
- **Recoveries.** 20 are drawn from ar25, wa30 and ls20, from any arm.
- **Selection.** Candidates are ranked by SHA-256(seed, stratum, key), so the draw is order-independent. A short
  stratum is taken whole and the shortfall is recorded.

The pooled evaluation refuses to compute any comparison until the annotations, hashed from the committed record,
validate against the redrawn sample.

**Suggestion-following exits (P2).** This is computed in `pooled.suggestion_following`, per reflection arm and game,
with totals over the primary games. The suggestion in force at the exit step is the block the frozen evaluator already
verified against the replayed supervisor. Its first test action is taken from the stored valid intervention that the
block must render from exactly. The measure is descriptive only.

**False-interruption gate.** It is kept as frozen and is not certifiable. `pooled.advancement` evaluates every §8.6
condition and returns "inconclusive" unless all hold. The gate condition cannot hold with wa30 as the only control.

**How the pooled evaluation reads the protocol, fixed before any run:**
- **Primary comparison.** It uses the primary games ar25, wa30 and ls20 (§4 excludes s5i5) and the main episodes of
  both blocks. Repeats are kept out of the arm rates and used for run-to-run variance (§5). Intervals are the
  episode-cluster bootstrap with the protocol seed, with Wilson as a naive reference (§8).
- **Point differences** between arms are descriptive.
- **"Against periodic"** means a higher triggered rate in ar25 in each block.
- **"No regressions"** compares completed levels, the dispatch failed/unknown rate, invalid policy-output stops and
  the invalid-reflection rate.
- **"Beyond variance"** means both triggered differences exceed the largest repeat-episode rate difference. Under
  deterministic decoding that difference may be 0, which makes this condition weak; the report says so.

## 3. Budget reconciliation (per session; nothing authorised)

| | Session 1 | Session 2 |
|---|---|---|
| Episodes | 15 (block 1: 4 games × 3 arms; 3 continuation repeats) | 12 (block 2) |
| Policy calls (cap = structural bound: 40 per episode) | ≤ 600 | ≤ 480 |
| Reflections (4 per reflection-arm episode × 8) | ≤ 32 | ≤ 32 |
| Startup canary | 1 | 1 |
| Model requests in total | ≤ 633 | ≤ 513 |
| Offline game actions | ≤ 600 | ≤ 480 |
| Online game calls, scorecards, holdout runs | 0 | 0 |
| Reservation (proposal) / internal limit / study cutoff / admission | 5,400 / 5,100 / 4,800 / ≥ 800 s left | 4,800 / 4,500 / 4,200 / ≥ 800 s left |

**Time estimates** (labelled as estimates):
- The protocol's estimate (§10) predates the verified runtime: 5.1–6.1 s per step gives about 3,970–5,180 s for
  session 1 and 3,360–4,440 s for session 2.
- Track 1, on the same runtime with a similar prompt size (about 25,000 tokens), measured 1.6 s per baseline call and
  about 1.7 s per step all-in, with an 820-s first-cell lifecycle.
- Track 3 adds evidence persistence that grows with episode length (about 0.4 s per step in CPU rehearsal), and
  reflections of up to 400 tokens.

At 2.5–3.5 s per step, session 1 needs about 1,500–2,100 s of policy work, 64–256 s of reflections, 450–960 s for
installation and startup, and 300 s of cleanup: about 2,300–3,600 s, inside the 4,800-s study cutoff.

If the target is slower than estimated:
- The admission rule stops admitting game groups with less than 800 s left. In session 1 the repeats come last.
- A group that is not admitted makes the session technically incomplete for outcome comparison (§9).
- That is reported as such and never rerun without a new approval.

## 4. Verification in this record

- New regressions (`tests/test_ssv_runtime_v2_r2_gaps.py`, Linux CPython 3.12) cover startup ownership, finalization,
  the installation backend, the r2 gate rules, the session-2 dependency, the evaluating-checkout check, the self-review,
  the suggestion-following measure, and a two-session pooled rehearsal end to end (scripted model, offline engine,
  injected GPU; not target evidence).
- The structured-output receipt is listed above.
- The full runtime v2 suite and the review snapshot r2 check are recorded in their own receipts.
