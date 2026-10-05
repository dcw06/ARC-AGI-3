# Wheelhouse R2 smoke review r4 validation

Validated source revision: `e3b0871616b4f17ae7a052f2d8567aa90992198d`, pushed to
`wheelhouse-r2-smoke-v1` on 2026-10-05. This fixes startup ownership and the final
lifecycle deadline. The licence-preview fix and worksheet review remain independent;
no licence source, decision or evidence file was changed by these smoke fixes.

Startup defers Python-handled interruption from process creation through PID/PGID
registration, without giving the child a blocked termination signal. An exceptional
spawn outcome remains `uncertain`; only `never_spawned` or a registered, verified
absent process group can produce `groups_absent=True`. A known child still receives
emergency termination when registration is uncertain.

A passing verdict now requires an explicit deadline check after server/GPU cleanup,
log retention, temporary-environment/extracted-source removal and pending evidence
finalization. Verdict/manifest publication receives another deadline check; a late
publication is replaced with failed evidence. Emergency termination can continue
after an overrun, but the attempt cannot pass.

## Historical regression demonstration

The two original reproductions are retained in
[`tests/test_wheelhouse_r2_smoke_lifecycle.py`](../tests/test_wheelhouse_r2_smoke_lifecycle.py).
Both fail on `9073068`, as does the additional interruption before group registration:

| Regression on `9073068` | Observed failure |
|---|---|
| Interruption after spawn, before assigning the handle | Child survives while cleanup incorrectly reports `groups_absent=True` |
| Interruption before registering the process group | Child survives; cleanup cannot signal a missing PGID |
| Cleanup crosses the internal deadline | Run still reports `passed=True` |

The historical runtime bytes were verified against Git before executing the same
regression tests. The expected three failures, test-source hash and source hashes are
retained in [`wheelhouse_r2_smoke_9073068_regressions.json`](wheelhouse_r2_smoke_9073068_regressions.json)
and its [log](wheelhouse_r2_smoke_9073068_regressions.log). The tests terminate their
own sleeper processes even when the historical cleanup leaks them.

## Fresh-checkout results

A clean native Linux checkout of `e3b0871`, cloned with `core.autocrlf=false`, was
validated with Python 3.12.3 under WSL2. All 14 review source bindings matched, and
every packaged Python source compiled. The initial checkout was clean; the check
runner's later `working_tree_clean=false` includes generated validation output.

| Check | Result | Retained evidence |
|---|---|---|
| Full wheelhouse tooling suite, including licence checks | 181 passed, zero failures/errors/skips; offline reports reproduce | [JSON](wheelhouse_tooling_checks_e3b0871.json), [log](wheelhouse_tooling_checks_e3b0871.log) |
| New startup/lifecycle regression suite | All 18 passed within the full suite | Same full-suite receipt |
| Scripted CPU rehearsals | All 12 behaved as expected, including SIGKILL escalation | [Scenario results](wheelhouse_r2_smoke_rehearsal_r4.json), [nominal evidence](wheelhouse_r2_smoke_rehearsal_evidence_r4/nominal/evidence-manifest.json) |
| Exact r4 notebook code | Refused at live gate; `nvidia-smi` never called; no temporary files left | [Review check](wheelhouse_r2_smoke_review_check_r4.json) |

Commands, exit codes, durations, source revision and initial-checkout checks are in
[`wheelhouse_r2_smoke_r4_fresh_checkout.json`](wheelhouse_r2_smoke_r4_fresh_checkout.json).
The commands run in that checkout were:

```text
python scripts/run_wheelhouse_checks.py --out reports/wheelhouse_tooling_checks_e3b0871.json
python scripts/wheelhouse_r2_smoke_rehearsal.py
python scripts/wheelhouse_r2_smoke_package.py review-check --revision 4
```

An earlier Windows clone inherited `core.autocrlf=true` and converted hash-pinned
licence evidence to CRLF. Its run had five failures and four errors, while all 58
smoke checks passed. That failed run is preserved separately in the
[Windows-checkout receipt](wheelhouse_tooling_checks_e3b0871_windows_checkout.json)
and [log](wheelhouse_tooling_checks_e3b0871_windows_checkout.log). Disabling checkout
line-ending conversion restored the expected evidence bytes and the full passing
result; no licence artifact or integrity check was edited.

## Rebuilt snapshot and scope

Review r4 is retained in
[`notebooks/wheelhouse-r2-smoke-v1-review-r4/`](../notebooks/wheelhouse-r2-smoke-v1-review-r4/).
Its review lock SHA-256 is
`f829d98b55997f491945aaadac309dfefe2917a518e61801586139afdfcc7398`.
Historical r1-r3 snapshots are preserved. GPU, TPU and internet are disabled in r4;
there are no dataset attachments, and the four dataset placeholders remain unresolved.

All validation was CPU-only with scripted servers and fixture wheels. No GPU,
CUDA/vLLM engine, model weights, upload, provider submission or reservation was used.
This snapshot grants no source or compute approval and does not authorize a launch.
