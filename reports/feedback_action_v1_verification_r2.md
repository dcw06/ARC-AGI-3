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
