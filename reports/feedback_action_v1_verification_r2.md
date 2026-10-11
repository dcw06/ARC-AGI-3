# Feedback-action v1: verification of the freeze revision (review snapshots r2)

**Revision.** `512cbd2` on `track1-successor-runtime-v1`: protocol v2 frozen on the owner's decisions of October 10,
2026 (gate A `ascii_only`, gate B `denominator_floor_10`), with the review documents bound and verified. Review lock
r2: `9ebbc968f91e5f10b0627a617254ab7c52bb38954021e10b631d77244dd06468`. r1 (lock `4b5b7a06…`) is kept unchanged.

## In the worktree, before the commit (installed interpreter pair)

| Check | Result |
|---|---|
| Derivations (`derive --check`, `derive_runtime --check`) | 11 and 4 derived files, 8 verbatim files and 1 copied function match |
| Review check r2 | refused at the live gate; no `nvidia-smi` call; no files left (`reports/feedback_action_v1_review_check_r2.json`) |
| Review rehearsal r2 (the same cell, MODE switched, from the extracted payload) | passed; technically complete; no lifecycle errors; pinned tokenizer and grammar check on (`reports/feedback_action_v1_review_rehearsal_r2.json`) |
| All Track 1 suites, installed game interpreter (with the installed model interpreter, pinned tokenizer, grammar check, replica competition mount) | 178 tests: 0 failures, 0 errors, 1 skip (the HTTP-path test, which needs the model interpreter) |
| HTTP path, installed model interpreter | 1 test, passed |

## Fresh clone of `512cbd2` (with the verified runtime's objects fetched)

| Check | Result |
|---|---|
| Derivations | both match; the verified runtime's source objects were present |
| Structured-output receipt r2 | reproduced byte for byte (dev-env dump, vLLM 0.19.0 check in the installed model interpreter) |
| Review check r2 | refused at the live gate; no `nvidia-smi` call; no files left. The rewritten report differs only in the random temporary folder names |
| `launch-build` | refused (exit 1) |
| All Track 1 suites, development environment | 178 tests: 0 failures, 0 errors, 1 skip (the HTTP-path test) (`reports/feedback_action_v1/cpu_checks_dev-env.json`) |
| Working tree | only the dev-env receipt differs, which this commit adds |

**Not established by these checks:** model behaviour, GPU or model load, guided decoding during generation on the
server, and the provider mounts or image (frozen protocol §11).

## Review snapshots r3 (October 10, 2026): the review's P2 fix

**Finding (review of `512cbd2`).** The live evaluator checked the hashes of the files a lock listed, but did not
require the complete runtime inventory or check the lock's scope and GPU-disabled status. A lock with the policy's
binding removed (and the policy changed), empty bindings, or a wrong scope still evaluated as technically complete
with `session_2_permitted`. The launch gate already rejected those locks.

**Fix.** `live_evaluation.review_lock_status` now applies the launch gate's own `binding.check_sources`: the scope, the
GPU-disabled status, the complete embedded-source inventory, every binding's hash and every review document. Its
separate document list is removed. The gate's source check is static, and the evaluator still imports none of the
runner, the live policy or the adapter (a test checks the loaded modules).

| Check | Result |
|---|---|
| Review snapshot r3 | lock `180c33ee895b5af2aca4032b8d5f9f878dbaa57fabdb32a1e1e5b612ed2f415d`; `profile.ipynb` and `kernel-metadata.json` byte-identical to r2's, embedded-source bindings identical; only the evaluator's review-document hash changed. r2's review rehearsal therefore covers this payload |
| Review check r3 | refused at the live gate; no `nvidia-smi` call; no files left |
| Regressions (`LiveModeSourceLock`): removed policy binding with changed source, empty bindings, wrong scope, GPU-enabled lock, missing review document | each refused: not technically complete, session 2 not permitted; the reviewed checkout is verified and permits it |
| The same regressions against the evaluator's check at `512cbd2` | the four reviewed cases are accepted there (4 failures), which reproduces the finding; the missing review document was already refused |
| Successor suite | 31 tests passed |

The frozen protocol text is unchanged: §10 and §15 already require the checkout to match its review lock; the fix
makes the evaluator enforce it fully. As agreed, the full suites were not rerun for r3.

## Review snapshots r4 (October 11, 2026): installation fix after session 1, attempt 1

**What happened.** The authorized session 1 attempt (`fa1-s1-8c598909…`) failed in the first cell after 136 s. The
verified installer's package checks for the game interpreter exited 1 because the Kaggle notebook's `MPLBACKEND`
(`module://matplotlib_inline.backend_inline`) leaked into the isolated game interpreter; its package check imports
matplotlib (the game engine's dependency), which rejects that backend. The supervisor never started: no model call,
no game action, no study data. The attempt is consumed and preserved and is never relaunched.

**Confirmed on the target by that attempt.** Host facts; the publisher and competition mounts, including the
competition mount layout (an r1 "GPU-only" item); the three games staged by manifest hash; bundle integrity (174
wheels); the model interpreter's installation and checks; the 31 game wheels.

**Fix.** `runtime.prepare` passes the notebook environment with `MPLBACKEND=Agg` to both installations (the verbatim
installer is unchanged; the import checks and the supervisor launch already set it).

| Check | Result |
|---|---|
| The installed game interpreter's package check | with Kaggle's value: exit 1, the same error; with `Agg`: exit 0 |
| The unfixed installation path on the CPU replica mounts, Kaggle's value set | fails with the attempt's exact error |
| The fixed installation path, same conditions | passed in 176.7 s (`reports/feedback_action_v1/runtime_install_check_kaggle_mplbackend.json`) |
| Regression test (`test_installation_never_inherits_the_notebook_matplotlib_backend`) | passes |
| Review snapshot r4 | lock `f0a5ad977b95d66fac91d0ddc482f3c02afe0b44bc3d8e954260796908817090`; review check refuses at the live gate, no `nvidia-smi` call; review rehearsal technically complete |
| Derivations; successor suite | match; 32 tests passed |

Record: `reports/feedback_action_v1/kaggle_mplbackend_reproduction.json`. The frozen protocol text is unchanged.

## Review snapshots r5 (October 11, 2026): owner amendment A1

The owner adopted amendment A1: exactly one replacement session-1 attempt after attempt 1's setup-only failure,
with attempt 1 consumed and preserved, the scientific design unchanged and no further replacement for any session.
It is frozen in `reports/feedback_action_v1_protocol_v2_frozen.md` §16, and §12's retry row cites it.

| Check | Result |
|---|---|
| Review snapshot r5 | lock `a32893cb63be0381e835770ac600f03e8760c94b1094f9dc52ed9eaba6e7c98d`; `profile.ipynb` and `kernel-metadata.json` byte-identical to r4's (only the frozen text, a review document, changed), so r4's review rehearsal covers this payload |
| Review check r5 | refused at the live gate; no `nvidia-smi` call; no files left |
| Derivations; successor suite | match; 32 tests passed |
