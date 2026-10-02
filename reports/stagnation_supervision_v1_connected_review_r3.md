# Track 3 R3: cache configuration, target lifecycle replay, and control eligibility

This successor addresses the review of `bbf9531`. R1 and R2 notebooks, locks and
receipts remain unchanged. This is a GPU-disabled review candidate: no source
approval, compute authorization, reservation, upload or GPU attempt is granted.

## Effective server configuration

The host replaces the inherited `--enable-prefix-caching` argument with exactly
one `--no-enable-prefix-caching` argument. It rejects absent, duplicated or
conflicting inherited settings, and retains the effective argv before startup.
The historical operational launch specification is unchanged.

After `/v1/models` becomes ready, the host makes one bounded `/metrics` request.
It retains the received body and hash before parsing, and requires the single
engine-0 `vllm:cache_config_info` gauge to report `enable_prefix_caching="False"`.
Missing, ambiguous, enabled or oversized evidence prevents the canary and study
admission. A zero cache-hit count is not treated as configuration evidence.
The configuration record is stored under the shared evidence budget at
`worker/server-configuration.json`. CPU rehearsals explicitly label it injected.

The interface is grounded in pinned vLLM 0.19.0's
[metrics logger](https://github.com/vllm-project/vllm/blob/v0.19.0/vllm/v1/metrics/loggers.py)
and [CacheConfig.metrics_info](https://github.com/vllm-project/vllm/blob/v0.19.0/vllm/config/cache.py).
Local tests exercise the actual inherited argument generator and this parser;
verification against an actual running vLLM server remains a condition of any
future authorized target startup, not a result of this CPU review.

## Independent overall evaluation

`closed_loop/evaluate.py` now labels its verdict `trajectory_only`.
`closed_loop/target_evaluate.py` independently requires both complete trajectories
and lifecycle evidence. It checks the frozen live session and budget, first-cell
origin and duration, startup/canary/artifact bindings, effective cache setting,
monitor handshake and lossless samples, sampling gaps and resource ceilings,
coverage through worker cleanup, independently queried GPU cleanup, all owned
process-group closure receipts, dependency and scratch removal, and normal host
finalization. Missing, malformed, contradictory or over-budget receipts fail
closed even when trajectory evidence remains valid. Recorded monotonic times
connect readiness, admission, monitoring and cleanup to the same first-cell clock.

The overall result retains the trajectory verdict and lifecycle failures
separately. `target_accepted` additionally requires live evidence; a passing CPU
rehearsal never becomes a GPU acceptance result. As with other archive replay,
this verifies retained evidence and internal bindings; it is not independent
provider attestation or exact billing reconciliation.

Read-only live replay after downloading a future authorized run:

```sh
python -m scripts.evaluate_stagnation_supervision_v1_target --output PATH_TO_OUTPUT --session 1
```

For the explicitly shortened CPU package rehearsal:

```sh
python -m scripts.evaluate_stagnation_supervision_v1_target --output PATH_TO_OUTPUT --session 1 --mode rehearsal --rehearsal-internal-seconds 1500 --rehearsal-group b1-ar25 --rehearsal-actions 12
```

## ls20 and provisional gate eligibility

The user's selection stands: ls20 remains an exposed exploratory development
case, with display-driven novelty and playfield oscillation reported. All cases
retain descriptive false-interruption statistics. Only the explicitly qualified
wa30 control currently contributes to the provisional gate. Game aliases are
canonicalized so one game cannot supply two controls. ls20 and unvalidated cases
cannot supply points, episodes or games toward that gate's minimum.

Consequently the current reference inventory cannot meet the two-game minimum.
Adding another gate-eligible control requires a separately reviewed reference
validation decision; mechanically labelled LC points alone cannot do so. This
does not remove exploratory trajectories or change their descriptive outcomes.

## Verification and frozen scope

`stagnation_supervision_v1_local_checks_r3.json` binds the passing CPU suite to
the complete R3 embedded-source inventory and test/review scripts. Regressions
include enabled/missing/ambiguous cache configuration with retained failure
evidence; valid trajectories accompanied by monitor, canary, cleanup, ownership,
clock, budget or configuration faults; connected success and fault rehearsals;
and wa30/ls20 synthetic controls for both detector-trigger and delivered-call
statistics. GPU probes and model responses remain injected in CPU rehearsals.

Requests and decoding settings are unchanged. The new
`stagnation_supervision_v1_token_audit_input_replay_r2.json` replays every ordered
request against the existing pinned tokenizer audit and binds the successor
derivation. The audit covers 1,080 policy requests and 42 scripted reflections,
not all possible future observations; exact runtime admission remains required.

```sh
python -m scripts.derive_stagnation_supervision_v1 --check
python -m scripts.check_stagnation_supervision_v1_review_r3 --check
python -m unittest discover -s tests -p 'test_stagnation_supervision_v1*.py' -v
python -m scripts.verify_stagnation_supervision_v1_audit_inputs_r2 --check
python -m scripts.review_stagnation_supervision_v1_notebook_r3 --folder notebooks/stagnation-supervision-v1-review-r3
```

The notebook verifier unpacks the new source, checks all bindings, rejects live
execution before installation, and runs the scripted offline-engine bootstrap
through independent trajectory **and lifecycle** replay. Development games are
restored from the committed checksum-bound archive; ignored environment files
are not required. R1/R2 current-source checks may differ after this repair; their
unchanged embedded snapshots and historical commits remain the replay sources
for those revisions.

The proposed provider/internal budgets remain 5,400/5,100 seconds for session 1
and 4,800/4,500 for session 2. The live gate remains deliberately closed. Review
must still disposition the online stop rules, timing uncertainty, two-session
proposal and reference-label audit, then a reviewed launch-authority revision
must bind the executable, separate approvals and a fresh session reservation.
One inherited resource limit also needs disposition before launch: telemetry is
capped at 13,220 samples. At the monitor's nominal 0.25-second interval this is
about 3,305 seconds of monitoring, shorter than either full internal reservation.
The writer fails closed at that cap; a passing short rehearsal does not establish
coverage of the full proposed duration. A reviewed per-study sample allocation
or sampling schedule must resolve this before the longer budget is approved.
Phase 4 production certification, admission limits and exact accounting remain open.
