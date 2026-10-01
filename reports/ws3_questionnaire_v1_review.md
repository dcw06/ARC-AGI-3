# WS3 transition questionnaire v1: runner and review package r2

**Revision r2** (review of 336348e). Package r1 (`notebooks/ws3-questionnaire-v1-review-r1`, lock
`c0be18a5…7b28`) is preserved but superseded.

**The r1 blocker.** r1 could not be reviewed from a clean checkout. Its lock bound an ignored, untracked
extracted archive member:
`reports/runs/phase4-grounded-action-v1-r8/download/phase4-grounded-action-v1/worker/trajectory.json`.
The dependency scanner added any literal file path that existed locally. The replay script names that file as a
string, so it entered the package from the author's workspace. The notebook embedded matching bytes, and every
runtime hash matched, so this was a reproducibility defect, not evidence corruption.

**The fix.**
- Literal file paths, config files and the runtime directory now count only when **tracked by git**.
- Any untracked file reaching the inventory is refused.
- The inventory is 280 files: r1's 281, minus the trajectory.

**Regressions.**
- Packaging is identical with and without the incidental file.
- Every packaged file is tracked.

**Fresh-checkout procedure (r2).**
1. The full local check ran in a **fresh clone** of the committed branch (`.cache/ws3_fresh_check.sh`), in which
   the R8 trajectory is absent.
2. The notebook review and the approval-path rehearsal also ran from a fresh clone of the r2 commit.

**Evidence recovery (found by the first fresh-checkout check).** When the monitor is lost, the supervisor stops the
worker with SIGTERM, which can land in the middle of an atomic evidence write. In the first fresh-clone check the
worker was killed while writing `manifest.json.tmp`. The committed state was consistent, but v2's strict loader
refused the whole run. The same race is latent in the v1–v3 stacks. The r2 loader recovers the last committed state:
- the manifest and every file it lists must verify;
- the committed prefix of the call log must match the manifest; later bytes are reported as ignored. This includes
  an interrupted first append, where the manifest still records zero calls;
- the only other files allowed are interrupted temporary files;
- the run index may be one write ahead of its manifest record, and is then used for metadata only.

A recovered run is always `incomplete` (`interrupted_evidence`). Tampering and unexpected files are still refused.

**Review of 95aef4f: two recovery gaps, fixed.**
- **P1.** A recovered run whose answers were all present was reported `technically_complete: true`. The evaluator now
  denies technical completion and promotion to any recovered run (see the substitutions in §1). The end-to-end
  regression adds an interrupted manifest write to a full 5,616-call rehearsal.
- **P2.** A kill during the first call-log append (log created, manifest still at zero calls) was refused as an
  unexpected file. It now recovers as an empty committed log, with the uncommitted bytes reported. It is tested with
  both a partial and a whole first line.

**Status.** GPU-disabled review snapshot. Authorized seconds are zero. There has been no reservation, upload or
model call. Source approval and a separately sized compute authorization would follow only after independent review.

| Item | Reference |
|---|---|
| Design | `reports/ws3_questionnaire_design_draft_r2.md` (draft r2.2, the freeze candidate) |
| Question set | `research/ws3_questionnaire_v1/probes.json` (3,116 questions, 5,616 scheduled calls), exported from `research/transition_evidence_v1/questionnaire.py` by `scripts/build_ws3_questionnaire_v1.py`; a fresh build is byte-identical |
| Scorer and decision rules | `research/transition_evidence_v1/score.py` (re-exported by `research/ws3_questionnaire_v1/score.py`) |

## 1. Reuse of the reviewed v3 stack

v3's runner and package files ran live as attempt `ecv3-089bf11f` and are reused, not edited.

| Kind | Files | Relation |
|---|---|---|
| **Derived** | `research/ws3_questionnaire_v1/{authority,host,worker,runner,resources,monitor,supervisor}.py`; the launch, package, review-build, notebook-review, rehearse, evaluate and check scripts; the connected, schedule, snapshot and diagnostics suites and fixtures | Exactly the v3 file, with v3's banner line dropped, the global v3 → WS3 renames, and counted per-file substitutions (`scripts/derive_ws3_questionnaire_v1.py`). A test fails on drift. |
| **Re-exported unchanged** | `schedule.py` (v2's call order; v1's admission rules), `transport.py` (v1's), `score.py` (the WS3 scorer) | The same objects, checked by identity. |
| **Re-exported writer, new loader** | `evidence.py`: v2's append-only call-log writer, unchanged (checked by identity); `load_verified` tries v2's strict check first and otherwise recovers the last committed state (see *Evidence recovery*) | Hand-written in r2. |
| **Adapters** | `probes.py` (loads the frozen set and builds each request from the frozen evidence), `service.py` (v1's service with the WS3 allow-list and a 5,616-call ceiling), `fake_server.py` (scripted answers; wrong answers are another valid enum value) | Hand-written. None loads the v2 or v3 question sets. |

**Substitutions of substance:**
- authority limits allow 5,616 calls, and the required sources list the WS3 runtime, the questionnaire and its record
  code, and the reused v1 and v2 modules;
- the evaluator's `gate_status` requires both primary and over-claim-gate completeness, and the verdict is reported
  under the key `questionnaire`;
- a run with recovered evidence is never technically complete: the evaluator reports `evidence_recovery`, sets
  `gate_status` to `incomplete` and the gate verdict to `incomplete`, and keeps the analysis for descriptive use only.
  Technical completeness now also requires the run's own status to be `complete`;
- rehearsal slow-latency faults (0.13 s and 0.06 s per call) are sized for a 2,500-call withheld pass;
- test numbers and report paths are updated.

**Provenance disclosure (v3 packaging slip).** v3's review-document list named the v2 diagnostics fixture files
instead of v3's (`tests/ecv3_diagnostics_*.py`), so v3's lock does not bind those two test-only files. They never
affected v3's runtime. For WS3 they are traced instead: they reproduce from v3's derivation, whose sources are bound
by v2's lock (test).

## 2. Notebook inventory

This is the import closure of the entry points, as in v2 and v3.
- **Byte-identical to what ran.** Every packaged file shared with v1's, v2's or v3's live-launch lock is
  byte-identical to what ran (test).
- **Closed.** Every repository import resolves inside the package (test).
- **No other question sets.** The v2, v3 and fixture question sets are not carried. v1's small set is carried,
  because v1's service constructor loads it.

## 3. What the tests show

| Requirement | Where |
|---|---|
| Keys derived three ways and agreeing; observable facts only; the candidate adds only facts recomputable from the reference evidence | `tests/test_ws3_questionnaire_draft.py` (Keys, Isolation) |
| Coverage floors; roles; extraction tagging; transfer labelled and descriptive | Coverage |
| Frozen schedule: withheld pass 1 with balanced condition order, pass 2 reversed, development and transfer once | Schedule, and `tests/test_ws3_questionnaire_v1_schedule.py` (derived) |
| Decision rules: reference meets, clear improvement, over-claim gates, invalid answers counting as over-claims, completeness policy, missing answers in every family × condition × pass, valid-only agreement | Rules, `ReviewOf93142fc`, `ReviewOfC8c0fd5` |
| Measurements, fixtures and the independent reference | `tests/test_transition_evidence_v1.py` |
| Every response retained and independently rescored; interruptions reported incomplete; fault handling | Connected suite (derived) |

## 4. Local results

**Pending.** The r2 fresh-checkout check has not yet completed on the fixed commit. The figures below are r1's.

Full local check (`reports/ws3_questionnaire_v1_rehearsal_results.json`, run `package-r1-check-2`, with per-test
diagnostics under `reports/ws3_questionnaire_v1_diagnostics/`): **all seven suites passed, 92 tests, 0 failures,
0 errors.**

| Suite | Tests | Result |
|---|---|---|
| Questionnaire: keys, isolation, coverage, schedule, decision rules, review regressions | 22 | passed |
| Transition records, fixtures and the independent reference | 16 | passed |
| Schedule, admission and interrupted withheld partition (derived) | 16 | passed |
| Transport, cancellation and cache metrics (v1's suite, reused unchanged) | 14 | passed |
| Diagnostics recorder (derived) | 6 | passed |
| Connected-path rehearsals (derived) | 10 | passed |
| Runtime derivation, inventory and allow-list | 8 | passed |

**The earlier run, retained.** Run `package-r1-check` failed one connected rehearsal. A timed-out regression-check
question left the evaluator's `gate_status` at `complete`, although the scorer correctly withheld promotion. The
evaluator now requires every withheld answer for technical completeness, and the derived rehearsal asserts that
nothing is promoted (`d57cbd5`). The rerun above passes.

A standalone full rehearsal answered all 5,616 calls in 61 s of first-cell time and was technically complete.

These are CPU rehearsals with scripted answers. Their verdicts are artefacts of those answers, not results.

## 5. Budget proposal (for a separate compute authorization; nothing is authorized here)

From `reports/ws3_questionnaire_token_audit.json`: exact tokens from the pinned tokenizer, and scenarios fitted to v3's
measured calls, with overheads taken as the worse of v2 and v3 per component.

| Item | Value |
|---|---|
| Attempts | 1, no automatic retry |
| Authorized seconds | ≤ 3,600, with a 3,300 s internal limit and a 300 s cleanup reserve that is never spent |
| Calls | 5,616; canaries 1; game actions and submissions 0 |
| Prompt tokens | 10,390,311 scheduled; largest prompt 17,544 (transfer) |
| First cell (planning) | 1,849 s with the worst measured overhead; 2,454 s with the allowances (startup 1,228 s) |
| Primary (withheld) headroom | about 2.8× v3's call rate with measured overhead, about 2.0× with the allowances. Beyond that the withheld partition is cut and reported incomplete (the explicit budget decision in the design). |

## 6. Residual risks (disclosed; none accepted)

- **Inherited from v1.** The `late_abort` rehearsal test depends on the host not pausing.
- **The closure inventory.** A file reached only through a dynamically built path on an unexercised live branch
  would be missing. It was checked as for v2 and v3.
- **Longer prompts.** Transfer prompts reach 17.5k tokens, longer than anything v2 or v3 sent. The runtime fit was
  measured on shorter prompts.
- **What a result could show.** This is tool-assisted factual interpretation on synthetic fixtures, plus a small,
  previously exposed transfer group. It establishes neither unaided visual reasoning nor solving.

## 7. How to verify

```sh
python -m scripts.derive_ws3_questionnaire_v1 --check
python -m scripts.build_ws3_questionnaire_v1 --check
python -m scripts.check_ws3_questionnaire_v1
python -m scripts.review_ws3_questionnaire_v1_notebook --folder notebooks/ws3-questionnaire-v1-review-r1
```
