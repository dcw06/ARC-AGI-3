# Diagnostic v2: received-response retention repair

V2 corrects the reviewed v1 evidence gap without changing the three prompt arms, model, observations, strict validation, or compute limits. V1 source and notebook remain immutable. No model/GPU calls have been performed and no launch has been authorized.

## Evidence order and process boundary

Immediately after receiving a completion, the model helper constructs bounded response evidence containing the first 8,192 UTF-8 bytes (without splitting a character), full-content SHA-256, original byte count, truncation flag, request hash, local tokenizer count, observed server prompt/completion counts and elapsed service time. It emits this record into the supervisor-owned bounded model log **before** testing token parity, missing usage, completion-token limits or response size. Nonfinite or malformed usage values are retained using bounded JSON-safe typed representations; they never become valid counts.

The startup canary's retention callback also updates its audit before validation, so the failure handler retains body/hash/counts rather than only an error. Model startup fails closed and cannot retry the canary. Since a startup failure precedes bridge readiness, its evidence is retained through the bounded model log captured by the supervisor; no claim is made that an unavailable bridge delivered it.

For diagnostic cases, `ResponseValidationError` carries this bounded record in a structured bridge failure reply (maximum 65,536 encoded bytes, inside the existing 1 MiB bridge envelope). The proxy reconstructs the failure with its evidence. The worker saves it to the current case, records whether the received request hash matches the planned case, marks the case/run failed and aborts without another call. A parity mismatch detected on the proxy itself also captures the response and both audit/result counts before raising.

No acceptance rule is relaxed. Truncated responses, token-count mismatches, missing usage and invalid actions remain failures. No coordinates or token counts are repaired. The model log provides an independent retained copy if the bridge fails entirely; a process crash before a received response can be recorded cannot guarantee evidence that never reached a retention point. Existing log/evidence ceilings and failure behavior remain enforced.

## Frozen execution requirements

All substantive scope, startup-inclusive budgets, resource limits, cleanup and finalization requirements from `reports/phase4_diagnostic_v1_review.md` remain, now bound to `certification/phase4_diagnostic_v2/protocol.json` and a new source lock:

- Three arms across 15 development initial observations: 45 sequential diagnostic requests; no game actions or scorecards.
- One startup canary, 46 completions maximum overall, at most 128 completion tokens each (5,888 total), no retries.
- Proposed reservation/provider timeout: 3,600 seconds. Internal first-cell deadline: 3,300 seconds. Installation by +900 seconds, startup at most 900 seconds after worker release, request window at most 1,200 seconds and admission cutoff +3,000 seconds, with 300 seconds reserved for finalization.
- 120-second request/canary transport timeouts; 180-second bridge ceiling. Late completions reject the run.
- VRAM 86 GiB, RAM 128 GiB, mutable scratch 4 GiB, evidence 64 MiB. Existing per-component/log limits apply to the additional received-response records; exhaustion fails closed.
- Independent monitoring precedes CUDA startup and continues through owned-group cleanup. Both continuous-monitor and independent GPU cleanup are directly required. Source/dependency/scratch removal and final receipt publication must finish within the shared clock.

The notebook is private, offline and GPU-disabled. A future launch requires a source approval bound to this v2 review and a separately bound, one-attempt diagnostic-v2 compute authorization. V1/full-pilot authority cannot satisfy its namespace/scope checks. The source review and compute approval remain separate decisions; no consumed reservation is reused.

## Local validation

18 tests passed. Canary regressions cover wrong prompt count, missing completion count, over-limit completion count and invalid action body. Helper regressions cover missing prompt count, boolean/nonfinite counts and oversized multibyte content. A real spawned local process served the Unix bridge and sent a tokenizer mismatch; the worker retained body, hash and counts (46 local / 45 server / 29 completion), persisted failure after exactly one request and did not retry. Proxy-side parity rejection is covered separately.

The remaining suite verifies exact inventory, cancellation/deadlines, response limits, separate authorization, disabled notebook, evidence rejection, startup success, fault cleanup and finalization. After the final oversized-response transport guard, the five affected mismatch/canary tests passed again. These tests use fake completions; they are not target model validation.

A retained CPU run passed all 45 scripted cases in about 10.9 seconds with process and scratch cleanup. The outer receipt and archive hashes are recorded in `reports/phase4_diagnostic_v2_review_receipt.json`. The freeze additionally verifies v1 and v13 source/artifact bindings remain unchanged. No new target run occurred.

Review notebook: `notebooks/phase4-action-diagnostic-v2-review-r1/profile.ipynb`. Written requirements and the source lock are jointly bound by `reports/phase4_diagnostic_v2_requirements_lock.json`.

Phase 4 remains open: production one-scorecard/110-distinct-game certification, production `C_admit`, and exact billing reconciliation are unresolved. This repair does not authorize a full pilot or advance those claims.
