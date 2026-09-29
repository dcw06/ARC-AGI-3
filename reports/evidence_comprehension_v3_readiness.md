# Evidence comprehension v3: readiness record (Workstream 1, Milestone A)

Recorded 2026-09-29. This record establishes **what exactly would run**. It grants nothing: readiness is not
authorization.

## 1. Identity of the experiment

| Item | Value |
|---|---|
| Repository commit at verification | `4275286` (fast-forward from `eaa90c0`, the package-freeze commit; the only intervening commit adds team documents and one `.gitignore` line, and touches no bound file) |
| Package | `notebooks/evidence-comprehension-v3-review-r1` |
| Review lock | `notebooks/evidence-comprehension-v3-review-r1/review-source-lock.json`, SHA-256 **`66713c6282ac395bdd0a23154cc3ea0c4427d66f4bcaf73c4b5b308dd7955cfd`** |
| Lock status | `reviewed_launch_source`; `authorized_seconds: 0`; `gpu_launch_authorized: false` |
| Question set | `research/evidence_comprehension_v3/probes.json`, SHA-256 `d27e5eda7da6f11819e9fca133bb4df2deb0d93a2876de19e69fd51adda972dc` (3,390 questions; 6,054 scheduled calls) |
| Protocol | `reports/evidence_comprehension_v3_protocol.md` (revision 2) |
| Review report | `reports/evidence_comprehension_v3_review.md` |

**On historical text.** The protocol's status and "Next" lines predate the runner milestone and still describe the
runner and package as future work. The locked protocol is not edited. The review report and this record give the
current implementation status: the runner, evaluator, token audit, budget proposal and GPU-disabled package are
complete.

## 2. Verification results (test results; not approvals)

All checks were run on 2026-09-29 against commit `4275286`.

| Check | Result |
|---|---|
| Every lock binding matches its file | **274 / 274** |
| Every lock review document matches its file | **25 / 25** |
| Notebook artifacts match (`profile.ipynb`, `kernel-metadata.json`) | **2 / 2** |
| Question set rebuilds byte-identically (`build_evidence_comprehension_v3 --check`) | **matches** `d27e5eda…72dc` |
| v3 runtime derivation reproduces its 20 files (`derive_evidence_comprehension_v3 --check`) | **matches** |
| v2 derivations still reproduce (`derive_evidence_comprehension_v2 --check`, `…_v2_postrun --check`) | **match** |
| Runtime tests: v3 derivation, inventory and allow-list; v2 approved-lock checks (`tests.test_evidence_comprehension_v3_derivation`, `tests.test_evidence_comprehension_v2_postrun`) | **11 passed** |
| Package review at freeze (`reports/evidence_comprehension_v3_package_review.json`) | refuses without authority before installation; the rehearsal from the extracted payload answered all 6,054 calls and was technically complete; the approval, reservation and packaging path was verified on a temporary copy |
| Full local check at freeze (`reports/evidence_comprehension_v3_rehearsal_results.json`) | 6 suites, 76 tests, all passed (CPU rehearsals with scripted answers; no model calls) |

No file has changed since the review, so no new review revision is needed and the lock was not regenerated.

## 3. Has any approval or launch already occurred? No.

| Evidence | Finding |
|---|---|
| Local v3 approval, authorization, execution lock, reservation, claim, prelaunch or launch records | **none exist** |
| v3 launch package folder (`notebooks/evidence-comprehension-v3-run`) | **does not exist** |
| Git history (all branches) | no v3 approve, reserve or launch commit |
| Kaggle kernel `daichongwei06/arc3-evidence-comprehension-v3` | **not found**. A read-only lookup was refused as inaccessible, while the same lookup on the v2 kernel returned `COMPLETE`, so the account's kernels are visible to it. |

There is no existing attempt to duplicate.

## 4. Approval decisions (separate from the results above)

| Decision | Status |
|---|---|
| Source approval for lock `66713c62…5cfd` | **not given** |
| Acceptance of the residual risks (§6) | **not given** |
| Compute authorization (one attempt, ≤ 3,600 s, 6,054 calls, 1 canary, no retry, no game actions or submissions) | **not given** |
| Launch operator | **not yet designated** |

The earlier v1 and v2 authorizations are consumed and do not carry over.

## 5. Operator

**To be designated by the project owner.** One person is responsible for the approval, reservation, packaging and
single upload. That operator records the provider's pre-launch and post-run GPU counters, and hands the downloaded
output to evaluation. The experiment's author should not be the only person validating the result.

## 6. Outstanding risks (disclosed; none accepted)

1. **Inherited from v1.** The `late_abort` rehearsal test depends on the host not pausing. It was accepted for v1
   only; it is not accepted for v2 or v3.
2. **Closure inventory.** The notebook carries the import closure, not whole directories. A repository file reached
   only through a dynamically built path, on a live branch no rehearsal exercises, would be missing. The checks at
   freeze found none on the questionnaire path, and every packaged file shared with v1's or v2's live lock is
   byte-identical to what ran.
3. **Runtime is estimated.** Estimates are fitted to v2's measured calls, with first-cell overhead allowances: the
   first cell would end at 1,485 s with v2's measured overhead, 1,854 s with the allowances, and 2,818 s at 2×
   slower, against a 3,000 s admission cutoff. Admission control, not the estimate, protects the 300 s cleanup
   reserve.
4. **Scope of the evidence.**
   - The transfer questions omit grids, so they do not show robustness to full live visual observations.
   - The counterfactual histories are synthetic. They show sensitivity to irrelevant history in those cases only.
   - Track A success would show a more usable interface; Track B success would be tool-assisted. Neither would
     show unaided reasoning.
5. **Provider billing.** The exact billed seconds are not reported by the provider. Only account-counter
   differences can be recorded.

The v2 run has since exercised the append-only call-log evidence format live, answering all 8,004 calls
technically complete. That removes it as an untested risk for v3, which reuses the same module unchanged.

## 7. Exposure registry (which material informed design)

| Material | Model answers inspected? | Status for v3 |
|---|---|---|
| v1 questions, keys and live answers (attempt `ecv1-4458251e`) | yes | development material; v1's six archived observations are reused only as a descriptive transfer check |
| v2 questions (all partitions), keys and live answers (attempt `ecv2-65759c16`) | yes | development material; v2's results informed the v3 design |
| v3 development partition (30 contexts) | no (never run) | development; single pass; descriptive |
| v3 withheld partition (128 contexts, 60 with counterfactual variants) | no (never run) | **fresh evaluation material.** New seeds; no observation repeats any v1 or v2 observation (checked in the build). The candidates were frozen before any v3 model answer existed. |
| H1/H2 games | — | not used |

After the v3 run, v3's withheld questions become development material too. They must not be reused as fresh
evaluation for a follow-up tuned on their answers.

## 8. What happens next

The next step needs the project owner's decisions in §4 and an operator in §5. After that, the single attempt goes
through the recorded package path:
1. approval, recorded verbatim;
2. reservation;
3. packaging;
4. one upload;
5. download, independent evaluation, archive and replay;
6. provider accounting;
7. a results report separating technical validity, the control-interface result, the tool-assisted history result,
   the secondary history sensitivity, and limitations.
