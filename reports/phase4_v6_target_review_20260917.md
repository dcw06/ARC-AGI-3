# Phase 4 v6 target-gate review — September 17, 2026

Disposition: **not approved for a GPU model pilot**. Local source review and
remediation are complete for the issues below; target evidence is still absent.
Neither compute ledger has been changed. No notebook was uploaded, no session
was launched, and no prior reservation was released or reused.

## Gate 1: target installation — pending separate target session

Current WSL checks: Linux x86_64, Python 3.12.3, 31 frozen environment wheels.
Neither `nvidia-smi` nor Docker is available. No Kaggle access-token/config file,
API-token environment variable, or nonempty Kaggle credential field in `.env`
was found. Credential values were not printed.

The model-service wheelhouse and model weights are not part of this transfer.
The configured target is a fresh Kaggle RTX PRO 6000 notebook session, not a
remote service at the model's in-notebook loopback address.

Prepared installation-only proposal:
`notebooks/phase4-v6-install-check-proposal-r1/`.

- Verify the frozen model wheelhouse's two manifest digests and every payload;
  verify all 31 frozen environment wheels against the repository manifest.
- Create a new isolated Python 3.12 venv without system site-packages.
- Install the model-service wheels, then the environment wheels using `--no-index`
  and no pip cache. Run `pip check` and retain the complete installed-package list.
- Require exact torch `2.10.0+cu128`, vLLM `0.19.0`, transformers `4.57.6`,
  engine/toolkit versions, Linux x86_64, CUDA build 12.8, and one RTX PRO 6000.
- Import vLLM's native extension; execute and synchronize a small CUDA matrix
  operation; retain driver/device inventory and check empty GPU process inventory
  after subprocess cleanup. This does not establish model-serving compatibility.
- Bound command logs to 1 MiB, use a 900-second internal elapsed ceiling, kill and
  reap owned command groups, remove the fresh environment, and retain failures.

Proposed accounting reservation: **one 1,800-second installation-check session**,
zero retries, private, internet disabled. No model attachment, gameplay, holdout,
or submission. Authorized/reserved time remains zero. A reservation is accounting,
not a provider-enforced cutoff. Unexpected provider/session time must remain
charged or retained until reconciled; the internal clock is not a billing receipt.
Hash verification and filesystem cleanup are checked at boundaries, not contained
against an uninterruptible host/filesystem failure. Provider termination remains
the outer boundary. Account allowance and target availability must be checked
before upload.

## Gate 2: integrated path — local review and changes

| Area | Review and disposition |
| --- | --- |
| Readiness | Worker held behind a pipe until retained nonce/PID/mode-bound readiness and its first sample agree. Target binding requires one idle RTX PRO 6000 and exact UUID. Real readiness timing remains unverified. |
| Cleanup | Normal completion monitors through worker/model process-group absence, then requires empty GPU process inventory. Evaluator now independently rejects missing/false GPU cleanup and canceled admission. Monitor loss or unknown cleanup remains a failure, never certification. Detached descendants and a dead outer process require provider containment. |
| Evidence | Previous monolithic telemetry would require roughly 47,148,908 bytes during replacement at the nominal full-duration sampling rate, over its 16 MiB allocation. New 1,024-sample lossless gzip/base64 chunks retain original JSON values, exact sequence/count and SHA-256 bindings. The full 110,161-sample synthetic case fits and round-trips. Existing aggregate budgets, temporary-write charging, failure receipts and sampling thresholds are unchanged. Compression and filesystem timing must still be measured on target. |
| Scratch | Worker environment routes known vLLM, Hugging Face, PyTorch, Triton, CUDA and temporary paths into the monitored scratch tree. Source bytecode writes are disabled. This is path routing, not filesystem isolation; unanticipated target writes must be reviewed. |
| Deadline | Admission and worker/startup watchdogs remain. Added checks include independent evaluator runtime and result publication; late completion clears success/capacity. Synchronous I/O or failure of the outer process is not a provider-level hard-stop guarantee. |
| Scientific scope | Still 110 clients repeating 15 development games with independent scorecards. No claim about the production one-scorecard/110-distinct-game lifecycle. Capacity stays unapproved until actual model evidence and review. |

Cache variables were checked against the pinned
[vLLM 0.19.0 source](https://github.com/vllm-project/vllm/blob/v0.19.0/vllm/envs.py).
Cache routing preserves the frozen model, request, queue and inference parameters.

## Gate 3: review snapshots, not execution approval

The new `notebooks/phase4-lifecycle-v6-review-r3` binds current sources, tests and
protocol. It stays GPU-disabled with the live authority gate closed. The old r2
notebook/archive is preserved unchanged. The installation-only proposal has its
own source and artifact lock; neither is a pilot execution lock.

After successful target installation evidence: review native extension/runtime
results, runtime topology and resource behavior; resolve any failures without
relaxing thresholds retrospectively; then freeze a new execution notebook and
complete source/protocol/evidence lock. The live authority implementation still
intentionally raises `PermissionError`; this review does not replace it with a
boolean switch or borrow another revision's authorization.

## Gate 4: separate one-shot pilot and usage reconciliation

The later model pilot remains a separate **one-attempt, 28,800-second** proposal.
Its reservation must bind its eventual approved execution lock. Installation-check
authority cannot authorize it. Record the attempt before upload, preserve the
provider version/identity and ambiguous launch outcomes, and never automatically
retry. Download and evaluate retained evidence, then reconcile actual provider
usage including failed/interactive sessions. Keep the reservation when exact
billing/session accounting is unavailable; notebook wall time is not billed time.

The historical prescreen's full 28,800 seconds remain retained. This report grants
no authority for holdouts, scored submissions, or scheduler alternatives.

## Validation

Final full local suite: **320 tests passed in 220.816 seconds**, run against this
Windows-mounted workspace through WSL. This includes the actual 110-client
scripted pilot, full-envelope telemetry round-trip, failure/cancellation tests,
installation-proposal checks and deadline/cleanup rejection tests. Both new
review locks' source bindings and the installation proposal's artifact hashes
were independently checked against files on disk. `git diff --check` passed.
These are local checks, not target installation or GPU evidence. Details are in
`reports/phase4_v6_target_review_20260917.json`.

All changes were made in the Windows workspace. The separate native Linux
working copy was not synchronized or overwritten.
