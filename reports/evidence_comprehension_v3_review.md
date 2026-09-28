# Evidence comprehension v3: runner and review package r1

**Status:** GPU-disabled review snapshot. Authorized seconds are zero. There has been no reservation, upload or
model call. Source approval and a new, separately sized compute authorization would follow only after
independent review. No earlier authorization is reusable.

The protocol is `reports/evidence_comprehension_v3_protocol.md` (revision 2). The question set is
`research/evidence_comprehension_v3/probes.json` (SHA-256 `d27e5eda…72dc`, 3,390 questions, 6,054 scheduled calls).

## 1. Reuse of the v2 stack

v2's runner and package files ran live (attempt `ecv2-65759c16`) and are bound by v2's review lock
(`de9642c6…82a3`). They are reused, not edited.

| Kind | Files | Relation to v2 |
|---|---|---|
| **Derived** | `research/evidence_comprehension_v3/{authority,host,worker,runner,resources,monitor,supervisor}.py`; the v3 launch, package, review-build, notebook-review, rehearse, evaluate and check scripts; the v3 connected, schedule, snapshot and diagnostics suites and fixtures | Exactly the v2 file, with v2's banner line dropped, the global v2 → v3 renames, and counted per-file substitutions (`scripts/derive_evidence_comprehension_v3.py`). A test fails on drift, or if a v2 source differs from the hash v2's lock bound. |
| **Re-exported unchanged** | `schedule.py` (v2's call order; v1's timing and admission), `evidence.py` (v2's append-only call log), `transport.py` (v1's) | The same objects, checked by identity. |
| **New for v3** | `service.QuestionnaireService` (v1's service with the v3 allow-list and a ceiling of 6,054 calls); `fake_server.ScriptedAnswers` (v2's answer rule keyed to v3); the question-set modules | Hand-written; reviewed here. Neither loads v2's question set. |

Substitutions of substance:
- authority limits allow 6,054 calls, and the required sources include the reused v1 and v2 modules;
- the evaluator's completeness is the primary completeness of both tracks (protocol r2);
- rehearsal slow-latency faults are sized for a 2,664-call withheld pass (0.12 s and 0.05 s per call);
- test numbers, and the report paths the tests read, are updated, and verdict checks accept the `_tool_assisted`
  suffix.

## 2. Notebook inventory

This is v2's import-closure inventory, applied to v3's entry points. Every packaged file shared with v1's or
v2's live-launch lock is byte-identical to what ran (test). The closure is closed: every repository import of
every packaged file resolves inside the package (test). v2's question set is not carried.

## 3. The required regressions, and where they are

| Requirement | Where it is shown |
|---|---|
| Each candidate differs from its reference only by its addition | `tests/test_evidence_comprehension_v3.py`, `Interventions` |
| The tool never turns uncertainty into certainty; fixed precedence; eligible set equals v2's frozen rule | `Interventions.test_tool_never_turns_uncertainty_into_certainty`, `test_tool_precedence` |
| Counterfactual histories are consistent, labelled and matched | `Counterfactuals` |
| No keys, variants, partitions or annotations enter requests | `RequestContent` |
| Primary, secondary and schedule completeness are separate, and the policy holds | `Completeness` (missing original or counterfactual answers in either pass; a missing development answer) |
| Every response retained and independently rescored; interrupted schedules reported incomplete | The connected suite (derived) |

## 4. Local results

Full local check (`reports/evidence_comprehension_v3_rehearsal_results.json`, run `package-r1-check`, with
per-test diagnostics under `reports/evidence_comprehension_v3_diagnostics/`): **all six suites passed,
76 tests, 0 failures, 0 errors.**

| Suite | Tests | Result |
|---|---|---|
| Question set, keys, interventions, counterfactuals, completeness and decision rules | 23 | passed |
| Schedule, admission and interrupted withheld partition (derived) | 16 | passed |
| Transport, cancellation and cache metrics (v1's suite, reused unchanged) | 14 | passed |
| Diagnostics recorder (derived) | 6 | passed |
| Connected-path rehearsals (derived) | 10 | passed |
| Runtime derivation, inventory and allow-list | 7 | passed |

A standalone full rehearsal answered all 6,054 calls in 158 s of first-cell time and was technically complete.

These are CPU rehearsals with scripted answers from the fake server. Their track verdicts are artefacts of those
answers, not results.

## 5. Budget proposal (for a separate compute authorization; nothing is authorized here)

The source is `reports/evidence_comprehension_v3_token_audit.json`: exact prompt tokens from the pinned
tokenizer, and scenarios fitted to v2's measured calls, taken with caching off on one RTX Pro 6000. That was a
different workload.

| Item | Value |
|---|---|
| Attempts | 1, no automatic retry |
| Authorized seconds | ≤ 3,600, with a 3,300 s internal limit and a 300 s cleanup reserve (never spent by any estimate) |
| Questionnaire calls | 6,054; canaries 1; game actions, submissions and holdout runs 0 |
| Prompt tokens | 4.47 M scheduled; largest prompt 1,160 |
| First cell (planning) | 1,485 s with v2's measured overhead; 1,854 s with the allowances (2× installation, 1.5× startup, 30 s minima); 2,818 s at 2× slower |
| Withheld headroom | Fits the 3,000 s cutoff up to 2.93× (measured overhead) or 2.53× (allowances) v2's call rates |

## 6. What the local evidence cannot show, and residual risks

- **Model answers, and live runtime.** Admission control, not the estimate, protects the reserve.
- **Inherited from v1.** The `late_abort` rehearsal test depends on the host not pausing. It is not accepted for
  v3.
- **The closure inventory.** A repository file reached only by a dynamically built path on an unexercised live
  branch would be missing. Checked as for v2, with none found on the questionnaire path.

## 7. How to verify

```sh
python -m scripts.derive_evidence_comprehension_v3 --check
python -m scripts.check_evidence_comprehension_v3
python -m scripts.review_evidence_comprehension_v3_notebook --folder notebooks/evidence-comprehension-v3-review-r1
```
