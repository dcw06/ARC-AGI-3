# Windows/WSL local pilot resolution — September 17, 2026

The native Linux full suite passes: **312 tests, 141.962 seconds, zero failures**.
Log: `.cache/resolution-tests.log` (available in both working copies).

## Diagnosis and scope

The original local runner defaulted to 90 seconds (admission cutoff at 80), but
used the frozen v3 evaluator's separate 60-second elapsed-time check. This host
repeatedly exceeded admission time. A diagnostic restricted to one CPU completed
in about 67 seconds and failed only the historical elapsed-time check. Thus a
complete functional workload could still fail the inherited timing gate.

The local v6 functional smoke test now has its own explicit 300-second ceiling
and 10-second finalization reserve. Reports bind the configured budget, and the
evaluator retains the complete original v3 verdict alongside the new functional
verdict. This is a change to local test criteria, not proof of meeting the old
60-second requirement or a target-performance improvement. Frozen v3 source,
previous evidence, GPU limits and authorization are unchanged.

Checkpoint work also caused unnecessary contention. Timeline snapshots now copy
flat event dictionaries rather than recursively copying scalar values. The worker
copies append-only evidence lists under its lock and writes outside that lock.
Already-completed clients are collected together into each checkpoint, preserving
all records without rewriting the entire accumulated history once per client.

The local CLI now retains the original failure and exits unsuccessfully if the
pilot fails, instead of raising `KeyError: worker`. Invariance fields remain null
when a comparison cannot be performed.

## Verification

- Full native Linux suite: 312 tests passed, including the actual 110-client run.
- Separately retained local run: 110 clients, 7,722 requests, 91.757 seconds;
  every client's request and action/state-hash sequences match the archived v3
  run. It passes the new local functional gate and explicitly fails the preserved
  historical 60-second check. Summary: `reports/windows_pilot_verification.json`.
  Full evidence is in the Linux copy under
  `reports/runs/wsl-local-smoke-v6-verified-20260917`.
- Added tests cover snapshot isolation, inference progress during checkpoint
  writes, deadline boundaries, budget binding, preservation of the historical
  rejection, missing clients, cleanup/resource failures, and CLI failure receipts.
- Historical Phase 2–3 verification passed after the changes.
- `git diff --check` passed.

An earlier diagnostic run failed a monitor resource-or-sampling-gap check; its
failure and verified cleanup remain in
`reports/runs/wsl-local-smoke-v6-20260917` in the Linux working copy. No monitor
threshold was relaxed. Host stalls can still legitimately fail a run.

Review-r2 notebooks and ZIPs remain historical snapshots and do not package this
revision. GPU/model-runtime installation and execution review remain separate.

## VPN distinction

The local pilot uses bundled games and scripted completions without external
network access. A profiling-tool download failed with a connection timeout during
debugging; that may be VPN-related, but causation was not established. Microsoft
documents Cisco AnyConnect interactions with WSL networking:
https://learn.microsoft.com/en-us/windows/wsl/troubleshooting#cisco-anyconnect-vpn-issues-with-wsl-in-nat-mode
