# WS3 transition questionnaire v1: readiness record (package r2)

Recorded 2026-10-01. This record states **what exactly would run** and what has been verified. It grants nothing.
Readiness is not authorization. Source approval and compute authorization are both still pending.

This record lives outside the r2 lock on purpose. It reports checks of that lock, so the lock cannot bind it.

## 1. Identity

| Item | Value |
|---|---|
| Package-freeze commit | `d46afc2` (branch `ws3-action-effects`) |
| Package | `notebooks/ws3-questionnaire-v1-review-r2` |
| Review lock | `notebooks/ws3-questionnaire-v1-review-r2/review-source-lock.json`, SHA-256 **`de7f1f8cb48b2d0ab37c427f06dfbe046a3096d476f4f715534df03781a5add6`** |
| Lock status | `reviewed_launch_source`; `authorized_seconds: 0`; `gpu_launch_authorized: false` |
| Bound files | 280 source bindings (all git-tracked) and 27 review documents |
| Question set | `research/ws3_questionnaire_v1/probes.json`, SHA-256 `dbf9696ef4743d1667f73909f410a8bd8d8c1339f68a0e2a765da68091159202` (3,116 questions; 5,616 scheduled calls) |
| Review guide | `reports/ws3_questionnaire_v1_review.md` (bound by the lock) |
| Superseded | Package r1 (`notebooks/ws3-questionnaire-v1-review-r1`, lock `c0be18a5…7b28`), kept unchanged; its receipt is `reports/ws3_questionnaire_v1_package_review_r1.json` |

## 2. Verification from fresh checkouts (test results; not approvals)

Both checks ran in clean clones of the committed branch. Those clones contain no untracked or ignored files apart
from the link to the development environment. The R8 trajectory that blocked r1 is absent from both.

| Check | Commit | Result |
|---|---|---|
| Full local check, run `package-r2-fresh-checkout-3` (`reports/ws3_questionnaire_v1_rehearsal_results.json`) | `32d8b3b` (code identical to the freeze; later commits change only the review guide and add the package) | 7 suites, **100 tests, all passed** |
| Notebook review and approval path (`reports/ws3_questionnaire_v1_package_review.json`) | `d46afc2` | **passed**; details below |

Package review details:
- Every source binding matches its file: **280 / 280**.
- Every packaged Python file compiles. The notebook is 810,911 bytes, under the 900 kB guard.
- GPU and internet are disabled in the kernel metadata.
- Without authority, the notebook refuses before installing anything, and it removes the extracted source.
- **Notebook-bootstrap rehearsal**, from the extracted payload against a CPU fake server with scripted answers:
  - answered **5,616 / 5,616** calls;
  - technically complete, with gate status complete.
- The actual snapshot was carried through the real approval, reservation and packaging path, including the packaged
  gate.

All of these are CPU rehearsals with scripted answers. Their labels are not results. No model was called, nothing was
reserved or uploaded, and no GPU was used.

## 3. What remains

1. **Independent review** of package r2, the lock above.
2. **Source approval**, recorded verbatim, if that review passes.
3. **A separately sized compute authorization.** The budget proposal is in the review guide, §5.

Only after all three may one GPU attempt be reserved and launched.
