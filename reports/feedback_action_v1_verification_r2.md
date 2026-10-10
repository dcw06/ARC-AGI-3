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
