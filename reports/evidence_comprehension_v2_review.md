# Evidence comprehension v2: runner and review package r1

**Status:** GPU-disabled review snapshot. Authorized seconds are zero. There has been no reservation,
upload or model call. This package is for independent review. Source approval and a new, separately sized
compute authorization would follow only after that review. The unused v1 authorization is not available.

The protocol is `reports/evidence_comprehension_v2_protocol.md` (revision 2, unchanged by this package).

## 1. Reuse of the v1 stack

v1's supervised questionnaire stack ran live (attempt `ecv1-4458251e`) and is hash-locked by its r3 review
lock, so it is reused, not edited. Three kinds of v2 file make up the package:

| Kind | Files | How it relates to v1 |
|---|---|---|
| **Derived** | `research/evidence_comprehension_v2/{authority,host,worker,runner,resources,monitor,supervisor}.py`; `scripts/*evidence_comprehension_v2*` launch, package, review-build, notebook-review, rehearse, evaluate, check; `tests/test_evidence_comprehension_v2_{connected,schedule,snapshot,diagnostics}.py` and the diagnostics fixtures | Exactly the v1 file, after a fixed set of global renames (v1 → v2 names, paths, attempt prefix `ecv2-`, rehearsal environment `ECV2_`) and that file's own substitutions, each required to match an exact number of times. `scripts/derive_evidence_comprehension_v2.py` holds the derivation. A test fails if any derived file drifts from it, or if a v1 source differs from the hash its r3 lock bound. |
| **Re-exported unchanged** | `transport.py`; `schedule.py`'s timing and admission rules; `service.py`'s proxy, validation and error types; `fake_server.py`'s server | The same v1 objects, imported. Tests check that they are the identical objects. |
| **New for v2** | `schedule.call_order` (the frozen schedule); `service.QuestionnaireService` (a v1 subclass whose only change is the v2 allow-list and a call ceiling of 8,004); `fake_server.ScriptedAnswers` (scripted answers for v2's families); `evidence.py` (§2); and the question-set modules | Hand-written and reviewed here. |

**Derived substitutions of substance** (everything else is renaming):
- the runner and the evaluator take the call order from the frozen schedule;
- authority limits allow 8,004 questionnaire calls, and the required sources include v2's modules and the v1
  modules it reuses;
- the evaluator reads the withheld status and the track verdicts;
- rehearsal timing is sized for 8,004 calls (900 s rehearsal lifecycle; 600 s for the cutoff cases;
  slow-latency faults of 0.08 s and 0.04 s per call, so the cutoff falls in withheld pass 1 and in pass 2);
- the test numbers are updated (8,004 answered; the withheld pass has 3,472 calls; the outcome_class
  answer flipped in the rescoring check);
- the monitor's mid-study handshake waits for the call log instead of the first call file.

## 2. One infrastructure change, with its concrete need

**The need, found in rehearsal.** v1 kept one evidence file per call. The shared output store
(`certification/phase4_integrated_v2/evidence.py`) walks and stats the whole output tree, under its lock,
on every write, and the resource monitor writes several times a second. With one file per call, each scan
grew with the run.

In the first full v2 rehearsal:
- the worker's per-call slot rose from 13 ms at the start to 450 ms by call 2,700, while host-side time
  stayed at about 3 ms per call;
- only 3,070 of the 8,004 calls fitted before the rehearsal cutoff (the run was reported
  `incomplete`, correctly).

v1's own writer, benchmarked in isolation, stays at 10 to 18 ms per call. The growth comes from the shared
scan contending for the lock. v1's 1,308 calls absorbed it; v2's 8,004 would not.

**The change.** `research/evidence_comprehension_v2/evidence.py` appends each call as one fsynced line of
`calls.jsonl`, so the output tree stays at a few files. The runner's interface and `load_verified`'s result
are unchanged, and v1's guarantees are kept:
- **Each call is durable before the next starts.** The line is written and fsynced, then the manifest (the
  log's SHA-256, byte length and line count) is atomically replaced.
- **A crash cannot pass for complete evidence.** A crash between the two leaves a log longer than its
  manifest, and a torn or edited line fails verification.
- **The final index always fits.** The byte budget keeps a reserve for it.

Regressions: round trip; out-of-order and reserved writes refused; crash between log and manifest; torn and
edited lines; budget exhaustion with room for the index; consistent forgeries
(`tests/test_evidence_comprehension_v2_derivation.py`).

**Effect.** A full rehearsal of all 8,004 calls finished in 161 s of first-cell time. It was technically
complete, and the lifecycle, evidence and call checks all passed.

## 3. Notebook inventory

v1's review notebook carried whole directories (1,081 files, 822 kB), which left no room for the v2
question set under the 900 kB upload guard. The v2 notebook carries the **import closure** of its entry
points: the launcher, evaluator, rehearsal script, engine-local helper, the gated exec and every v2 module.

The closure follows imports statically, including function-level imports and module names or repository
paths written as strings. It adds v1's explicit data-file list and `config/`.

Checks:
- **Shared files are what ran live.** Every file shared with v1's live-launch lock (225 files) is
  byte-identical to the hash v1 bound (test).
- **The closure is closed.** Every repository import of every packaged Python file resolves inside the
  package (test).
- **No hidden imports.** The only non-literal dynamic import is `exec` of `MODEL_CHECK`, which imports
  third-party packages only.
- **Directory-built paths are on unused branches.** Paths built from directory names occur only in other
  experiments' lock validators (`phase4_integrated_v2.authority.source_snapshot` and
  `phase4_v1.lifecycle.validate_freeze`). The questionnaire path never calls them; v1 ran live without
  their inputs.
- **Rehearsal from the payload.** The notebook-review script runs the full connected rehearsal from the
  extracted payload itself.

## 4. The required regressions, and where they are

| Requirement (plan step 6) | Where it is shown |
|---|---|
| Conditions differ only in their registered intervention | For every pair, the control-candidate request equals the baseline request except for the system prompt, which differs by exactly the inserted instruction. The history-candidate request differs only in the history field, and its entries are information-equivalent (`tests/test_evidence_comprehension_v2.py`, `Isolation`). |
| No answer keys, future observations or evaluator annotations enter requests | Each request carries only `{observation, question}`, with no keys, strata, shortcuts, trajectories, partition names or grids. Observations are rebuilt from past events only. The runtime allow-list is derived from the same frozen requests (`RequestContent`, `AllowList`). |
| Failed or unknown dispatches never become "no effect" | Their change keys are `not_observed`; they never qualify; the candidate shows "none observed" (`Evidence`). |
| Reset and level boundaries are respected | Earlier entries are hidden and their steps keyed `not_shown`, in both derivations (`Evidence`). |
| Every response is retained and independently rescored | Each call is logged before the next starts. The evaluator re-derives every request hash from the frozen set and binds calls to the frozen schedule. Editing one retained response changes the score by exactly one. Forged hashes, orders, metadata and cache counters are rejected, and nothing is scored from them (connected suite). |
| Missing answers or interrupted schedules cannot produce a passing claim | Analysis regressions: no passes, one pass, empty passes, half of pass 2, one missing answer. Connected rehearsals: the cutoff in withheld pass 1 and in pass 2, a truncated run, timeouts, cancellation and failures all report `incomplete`, with the cleanup reserve untouched. |

## 5. Local results

Full local check (`reports/evidence_comprehension_v2_rehearsal_results.json`, run `package-r1-check`, with
per-test diagnostics under `reports/evidence_comprehension_v2_diagnostics/`): **all six suites passed,
96 tests, 0 failures, 0 errors.**

| Suite | Tests | Result |
|---|---|---|
| Question set, keys, isolation, scoring and decision rules | 35 | passed |
| Schedule, admission and interrupted withheld partition (derived) | 16 | passed |
| Transport, cancellation and cache metrics (v1's suite, reused unchanged) | 14 | passed |
| Diagnostics recorder (derived) | 6 | passed |
| Connected-path rehearsals (derived) | 10 (19 rehearsals) | passed |
| Runtime derivation, inventory and call log | 15 | passed |

Across the connected rehearsals:
- **Normal runs:** all 8,004 calls answered, technically complete.
- **Cutoff in withheld pass 1, and in pass 2:** each reported `incomplete`, with the last call returned
  before the cutoff.
- **Fault cases:**
  - timeout, slow abort, late abort, trickling metrics and late reply were each handled within the
    per-call bound;
  - a server that ignores cancellation, or has prefix caching enabled, was refused;
  - HTTP error, storage, cancellation, monitor loss (mid-study and before readiness), model-startup
    failure, log flood and a surviving child each failed within seconds, cleaned up and kept honest
    evidence.

Everything in this section is CPU rehearsal with scripted answers from the fake server. The rehearsal track
verdicts (`no_clear_improvement` for both tracks) are artefacts of those scripted answers. They are not results.

## 6. What the local evidence cannot show

- **Behaviour of vLLM 0.19.0 on the target GPU.** Whether aborts land and metrics return to idle, as for
  v1. The live run checks both itself and stops if either fails.
- **Runtime.** The budget is planning figures (protocol §11), fitted to v1's measured calls. The call log
  removes the growth found in rehearsal, but live disk behaviour for 8,004 calls is unmeasured. Admission
  control, not the estimate, protects the cleanup reserve; a slow run is reported `incomplete`.
- **Model answers.**

## 7. Residual risks

- **Inherited from v1.** The `late_abort` rehearsal test depends on the host not pausing. v1's reviewer
  accepted this risk for v1; it is not recorded as accepted for v2.
- **The call-log evidence format is new.** It is covered by regressions and rehearsals, not by a live run.
- **The notebook inventory is a closure.** A repository file reached only by a dynamically built path on
  an unexercised live branch would be missing. The checks in §3 found none on the questionnaire path.

## 8. Budget proposal (for a separate compute authorization; nothing is authorized here)

| Item | Value |
|---|---|
| Attempts | 1, no automatic retry |
| Authorized seconds | ≤ 3,600, with a 3,300 s internal limit and a 300 s cleanup reserve |
| Questionnaire calls | 8,004 (the withheld partition twice, then development and transfer once) |
| Canaries | 1 |
| Game actions, scored submissions, holdout runs | 0 |
| Expected first cell (planning) | 1,823 s with v1's measured overhead; 2,216 s with the allowances |

## 9. How to verify

```sh
python -m scripts.derive_evidence_comprehension_v2 --check   # derived files match the derivation
python -m scripts.check_evidence_comprehension_v2            # every local suite; rewrites the rehearsal results
python -m scripts.review_evidence_comprehension_v2_notebook --folder notebooks/evidence-comprehension-v2-review-r1
```

The notebook review does four things, as v1's did:
1. Checks every binding and the metadata (private, offline, GPU off).
2. Executes the frozen cell and requires a `PermissionError` before installation.
3. Executes the same cell in rehearsal mode from the extracted payload. The full questionnaire must pass
   the independent evaluator.
4. Runs the snapshot through approval, reservation and packaging, and checks the packaged authority gate.
