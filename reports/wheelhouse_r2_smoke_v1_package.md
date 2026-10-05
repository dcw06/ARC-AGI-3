# Wheelhouse R2 smoke test v1: package, CPU rehearsals and remaining bindings

Prepared October 4, 2026 on branch `wheelhouse-r2-smoke-v1` (Step 4 of the R2 path).

**Status.** No approval, compute authorization or reservation exists.
- **GPU disabled throughout.** No bundle was built, nothing was uploaded, no attempt was reserved, and no real model was called.
- **Evidence class.** Everything below is scripted CPU rehearsal evidence of the control code. It is **not** GPU compatibility evidence.

## What the package does (live path, once authorized)

Package: `certification/wheelhouse_r2_smoke_v1/`. Frozen settings: `protocol.json` (sha256 `f472c551…08538`).

The live path runs one attempt on one clock, from installation start through cleanup:

| Stage | What is checked |
|---|---|
| Live gate | Runs before anything else. It requires: no `UNRESOLVED:` placeholder; sources matching the review lock; a source approval; the Record C compute authorization, bound to the protocol, the dataset binding and the exact limits; an unconsumed reservation; and the launch-side claim (see "Once-only accounting"). A session-local marker then stops a second run within the same provider session. |
| Host | CPython 3.12.x, x86_64, glibc ≥ 2.34 |
| Bundle integrity | `SHA256SUMS` and `bundle-manifest.json` match their bound hashes; every listed file matches; no file is unlisted; `requirements.lock` is `ba80d350…`; 174 wheels |
| Offline installation | Fresh venv; `pip install --no-index --no-cache-dir --require-hashes --only-binary=:all:`; `pip check`; exact versions (torch `2.10.0+cu128`, vLLM 0.19.0, transformers 4.57.6, numpy 2.2.6); imports; torch CUDA build 12.8. A mismatch fails, with no upgrade attempted. |
| GPU | Exactly one GPU whose name contains `RTX PRO 6000`, with its driver and memory recorded; telemetry sampled before the server, after startup, after inference and after cancellation |
| Model artifact | Tree SHA-256 `052ab27f…8627`, required files, 4 shards (Qwen3-VL-30B-A3B-Instruct-FP8, revision `d9748a51…`) |
| Server | The pinned vLLM command line (`config/m0_launch_spec_q3vl30.json`) in its own process group. Readiness is detected by TCP connection only, within a 900-second startup ceiling. |
| Startup probes | S1 `/health`, S2 `/v1/models` (served name), S3 canary completion |
| Inference | I1 and I2 (exact word), I3 (long context), I4 (image), all at temperature 0 with seed 0 |
| Cancellation probes | C1 streams a long completion and closes the connection after the first content chunk. C2 reads `/metrics` until running and waiting are 0 (at most 2 reads, 3 s apart). C3 confirms the server still responds. |
| Cleanup | SIGTERM to the process group, then SIGKILL; the group must be verified absent; then an independent check that no compute process remains on the bound GPU. This stage always runs. |
| Evidence | `/kaggle/working/wheelhouse-r2-smoke-v1/`: result, request ledger, phase timings, GPU telemetry, server and installation log tails (2 MiB each), and a SHA-256 manifest |

**Request accounting.** Every HTTP request to the model server counts toward the cap of 12, including the startup and cancellation probes. Only planned request IDs are admitted, each at most its permitted number of times, and nothing is admitted after the admission cutoff. Refusals are recorded. The plan's worst case is 11 requests.

**Time limits** (proposed for Record C to freeze):

| Limit | Seconds |
|---|---|
| Authorized | 3,600 |
| Internal | 3,420 |
| Cleanup reserve | 300 |
| Admission cutoff | 3,120 |
| Installation | 900 |
| Model verification | 600 |
| Startup ceiling | 900 |

At the admission cutoff, a whole-run alarm hands control to cleanup.

**Cleanup is its own bounded phase.** Fixes review finding P1-1 on `77eb06f`.
- Cleanup first disarms the cutoff alarm and blocks `SIGALRM`, so the cutoff cannot interrupt it. That transition is retried once if the one-shot alarm lands at that instant.
- `stop()` runs its SIGKILL escalation and the reap in `finally` blocks, so an interruption during the SIGTERM grace is recorded and still reaches SIGKILL. A recorded interruption marks the run failed.

**Request deadlines are absolute.** Fixes review finding P2 on `77eb06f`.
- Each request's deadline covers connection, headers and body.
- A watchdog shuts the socket at the deadline, so trickling bytes cannot extend a read.
- Every read is followed by a deadline check, so content that completes late is rejected.

**Settled rules.** One attempt and no automatic retry. A failure consumes the attempt and is diagnosed before any new authorization.

## Once-only accounting, and its limits

This section fixes review finding P1-2 on `77eb06f`. Once-only accounting lives on the launch side, in the repository (`certification/wheelhouse_r2_smoke_v1/launch.py`):
- **Claim** (`config/wheelhouse_r2_smoke_v1_launch_claim.json`). Created exclusively, and never overwritten, once the approvals and the reservation are valid. It is immutable and embedded in the launch package, and the notebook gate requires it.
- **Receipt** (`reports/wheelhouse_r2_smoke_v1_launch.json`). Created exclusively as `submitting` **before** the provider push. It is then replaced by `submitted` (with the provider's kernel ref and version) or `submission_uncertain` (the push raised, or its outcome is unknown).
- **Any receipt spends the attempt.** That includes `submitting`, which is left behind if the push was interrupted. The tooling then refuses to claim, package or submit that attempt again, from any session or working directory.
- **An uncertain submission** is reconciled by hand against the provider's version history and is never relaunched. A new attempt needs a new authorization and reservation.

**What an offline notebook cannot prevent.** The notebook runs with internet disabled, so it cannot consult any shared state. Its consumption marker only stops a second run inside the same provider session. It cannot stop someone from manually re-running the pushed kernel, saving another version, or pushing a copy with the same sidecars.

Such a replay is therefore **detected and reported, not prevented**:
- every evidence result carries the attempt ID;
- the notebook records the provider run type;
- reconciliation after the run checks that the provider's version history for the kernel shows exactly one run, matching the receipt.

Any extra run is a protocol violation. It is reported, and it never counts as evidence.

## CPU rehearsals (scripted; not GPU evidence)

`python scripts/wheelhouse_r2_smoke_rehearsal.py` writes `reports/wheelhouse_r2_smoke_rehearsal.json` and keeps the nominal scenario's evidence folder.

Each scenario runs the real control code:
- the gate, clock, ledger, client deadlines, cancellation handling, process-group cleanup and evidence retention;
- a real hash-pinned offline install into a fresh venv, using fixture wheels in the R2 bundle layout;
- a scripted stub server, launched as a real process with real sockets.

No GPU query is made, and CUDA is hidden.

| Scenario | Expected outcome |
|---|---|
| nominal | passes; 11 counted requests; group terminated |
| bundle file tampered / `SHA256SUMS` binding mismatch | fails at bundle integrity; nothing installed; no request |
| version mismatch | fails at installation |
| model tree mismatch | fails at the model artifact stage |
| server exits early / never ready | fails at `server_ready` (exit detected / startup ceiling); group cleaned up |
| wrong served model | fails at S2 |
| request timeout | fails at S3 on its deadline; group cleaned up |
| not idle after cancellation | fails at C2 after its 2 permitted reads |
| server ignores SIGTERM / child ignores SIGTERM | passes; SIGKILL needed and sent; whole group verified absent |

The refusal paths are tested with fixtures in `tests/test_wheelhouse_r2_smoke.py`, part of `scripts/run_wheelhouse_checks.py`:
- this checkout refuses because of the four placeholders and the missing authorization;
- placeholders refuse even when every approval is present;
- a complete fixture authorization opens the gate, which proves the gate can open at all;
- each single defect then refuses: source drift; a missing source approval; a missing compute authorization; a compute limit or seconds mismatch; compute not bound to the dataset or the protocol; a missing or consumed reservation; an unbound execution lock;
- the session marker works within one session only (documented limit);
- a missing or unbound launch claim refuses;
- the launch package refuses on this checkout.

Regressions for the three review findings on `77eb06f`. The first three fail on `77eb06f` and pass now; slow body already failed correctly at `77eb06f`.

| Test | Finding | What it checks |
|---|---|---|
| a real alarm during the SIGTERM grace | P1-1 | SIGKILL is still sent and the group is verified gone |
| slow headers | P2 | headers trickled past the deadline: the request fails within the deadline plus 0.25 s |
| slow stream | P2 | a first content line completing after about 0.36 s against a 0.1 s deadline is rejected |
| slow body | P2 | a body trickled past the deadline fails |
| nothing sent | P2 | a silent server fails on time |
| timely stream | P2 | on-time content is still accepted |
| entering cleanup disarms the cutoff | P1-1 | no interruption is recorded |
| cutoff during `run()` cleanup | P1-1 | bypassed transition: SIGKILL sent, group gone, run failed. Proper transition: no interruption, run passes |
| claim | P1-2 | created once; refused without valid approvals |
| a submitted attempt | P1-2 | refused from any later session (submit, package or claim); the backend is pushed exactly once |
| uncertain or interrupted submission | P1-2 | the attempt is spent |
| tampered package | P1-2 | never submitted |

The local review check executes the review notebook's exact code with no GPU and a decoy `nvidia-smi` (`reports/wheelhouse_r2_smoke_review_check_r2.json`). It stops at the live gate, `nvidia-smi` is never called, and no temporary files remain.

## Review snapshot

`notebooks/wheelhouse-r2-smoke-v1-review-r2/` (r1 is preserved but stale, since its sources changed with these fixes):
- GPU disabled;
- no dataset source, because the binding is unresolved;
- every package source embedded and hash-bound.

This is a review snapshot, not an approval.

## After Record B (not done; requires the upload approval)

1. **Bind the dataset.** Replace the four placeholders in `protocol.json` with the actual Kaggle dataset ref and version, the `SHA256SUMS` hash and the `bundle-manifest.json` hash from Record A.
2. **Verify attachment access** from the launch account. The account must be able to list the files and attach that version. A provider `invalid*Sources` result counts as a failure even with HTTP 200. Then re-verify `SHA256SUMS` against the attached files. Kaggle kernel metadata names the dataset but cannot pin a version, so the live path's bundle-integrity stage is the version guard: any other version fails before installation.
3. **Rebuild and re-check the review snapshot** (r3). Rerun the tests and rehearsals from a fresh clone, and present the final package for review.
4. **Bring Record C back for explicit confirmation**, with the review lock hash, the protocol hash, the dataset binding and the limits above. Only then record the source approval and compute authorization, reserve the single attempt, build the launch package (`launch-build`, which refuses until then) and launch.
