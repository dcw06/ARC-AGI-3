# Three-arm diagnostic runner: frozen local review

Implemented `certification/phase4_diagnostic_v1` and froze the private, offline, GPU-disabled notebook at `notebooks/phase4-action-diagnostic-v1-review-r1/profile.ipynb`. This is the proposed initial-decision experiment, not another full pilot. No GPU launch, new reservation, source-approval sidecar, environment action, or model call was performed.

## Scope and exact requests

The runner executes the 45 hashed requests from `reports/phase4_action_selection_probe_proposal.json`: 15 retained development starting observations, each paired with original examples, relocated click coordinates `(47,9)`, and no concrete examples. The proposal SHA-256 is `d8de6535ff6d54c155e151ca48660b7e84b01029f3ebc51208a0b4f09c6e4655`.

Arm ordering, model, tokenizer, observation, legal-action JSON schema, temperature, seed, non-thinking setting and 128-token completion limit remain exactly as proposed. Only the planned system-prompt edits differ. The worker performs one sequential pass, with a durable intent receipt before each call. The model-side service independently enforces the request allowlist and 45-call ceiling. Neither side retries. No game/scorecard adapter is instantiated; the existing two isolated interpreter installations are reused for their dependency isolation and transport support only.

The configuration is E1S-R-derived `arc_action_v12`, not unchanged historical E1S-R. The three-arm comparison is diagnostic; passing means complete valid evidence, not improved solving. The evaluator produces per-game actions and per-arm click counts, original/relocated coordinate matches, baseline agreement and action-type switches. It never emits a capacity candidate or production admission value.

## Startup-inclusive frozen budget

| Limit | Frozen requirement |
| --- | --- |
| Proposed provider reservation / timeout | 3,600 seconds, one attempt; not authorized |
| Internal lifecycle deadline | 3,300 seconds from the first notebook cell, including source unpacking, installation, startup, requests, evidence and cleanup |
| Installation | Complete by first-cell +900 seconds, using the frozen offline wheelhouse checks and isolated model/game environments |
| Model startup | At most 900 seconds after monitored worker release, including CUDA/artifact/tokenizer checks and canary |
| Diagnostic request window | At most 1,200 seconds after readiness, and never beyond first-cell +3,000 seconds |
| Admission cutoff / finalization reserve | Stop admission at +3,000 seconds; reserve 300 seconds for cancellation, termination, evidence and removal |
| Startup inference | One constrained ACTION6 canary, maximum 128 tokens, 120-second transport timeout |
| Diagnostic inference | At most 45 sequential calls, maximum 128 tokens each, 120-second transport timeout; bridge ceiling 180 seconds |
| Total inference ceiling | 46 completions including canary; at most 5,888 completion tokens; no retries or warm-up completions |
| Environment actions / scorecards | Zero / zero |
| Mutable resources | VRAM 86 GiB, process-group RAM 128 GiB, mutable scratch 4 GiB |
| Retained evidence | 64 MiB total; component and atomic-replacement peak limits enforced |

The provider reservation includes 300 seconds beyond the internal deadline as an external backstop, not extra request time. Stage limits are upper bounds; the shared absolute deadline can truncate a later stage. Immutable interpreter trees are outside mutable workload scratch, as in the verified split installation; their installation and removal still count toward the first-cell deadline. The pinned model launch spec remains unchanged. The diagnostic service overrides inherited operational request/canary timeouts and scheduling-envelope fields with these diagnostic limits; it does not create the full-pilot inference queue.

## Cleanup and evidence acceptance

The independent monitor releases the worker only after a durable readiness handshake, before CUDA/model startup. It samples throughout the worker/model process-group lifetime and group termination: 0.25-second interval, maximum accepted gap 1 second, and 13,220 retained samples at most. Logs remain bounded; exhausted logs/evidence or monitor failure reject the run.

The supervisor owns worker/model and monitor groups. Cancellation closes admission; exceptions and timeouts trigger group termination and verification. An independent post-termination GPU query runs even after monitor failure. The evaluator directly requires both continuous-monitor cleanup and independent cleanup; neither can replace missing coverage. Source, dependency trees and mutable scratch must be removed. The final receipt binds evaluation and dependency-cleanup hashes and rechecks the 3,300-second deadline. Cleanup failure, uncertainty or late publication prevents a pass.

Required evidence includes:

- Hash-bound proposal, source/protocol snapshot and exact request IDs/order; package/model/runtime/install identities.
- Startup canary request audit, bounded response body, SHA-256 and token parity. Received and failed canary diagnostics are written to the bounded model log before throwing; a success also reaches worker evidence. A transport failure may have no response body and is recorded as such.
- All 45 case identities, game/arm labels, request hashes, sequential start/return times, response bodies/hashes, exact token audits, parsed validated actions, errors and request-start count.
- Valid response bodies up to 8,192 bytes. An oversized body retains its full-content hash, byte count and bounded prefix, is explicitly marked truncated and fails; it is not silently accepted. Malformed, missing, late or mismatched responses are retained when available and terminate the diagnostic without another call.
- Continuous telemetry, rejected-sample diagnostics when applicable, owned-process receipts, independent GPU cleanup, dependency/source removal and final deadline receipt.

Evaluation requires every case exactly once in its frozen order, all response/request/action bindings, strict legal actions and integer coordinates, exact prompt-token parity and token/context ceilings. Cancellation, missing/extra cases, evidence drift or any failed case prevents the comparison from being published as passed. Per-arm counters use the appropriate click-eligible denominator; action diversity is not scored as solving success.

The 64 MiB store retains its reviewed allocation: control 1 MiB, monitor 16 MiB, worker 32 MiB, evaluation 8 MiB and logs 7 MiB. Installation logs are bounded and compressed; each owned-process log is capped at 3 MiB. Full requests are preserved in the frozen proposal/notebook rather than repeatedly duplicated in output.

## Local validation and freeze

All 14 Linux regression tests passed. They cover the complete scripted 45-case lifecycle, model-side allowlist/count checks, separately scoped authority and budget, GPU-disabled notebook execution, mocked canary success/failure with no second attempt, invalid/oversized response retention, transport errors without retries, cancellation, late completion, finalization deadlines, evaluator evidence mutations, and process/scratch cleanup after worker/monitor/evidence/cancellation faults.

A retained CPU run passed all 45 cases with no model inference or GPU activity, in approximately 28 seconds; the retained outer lifecycle receipt records 27.338 seconds before final evaluator publication. Its per-arm comparison is explicitly marked scripted. Target serving of these three arms remains untested. The mocked startup tests are not new Linux/CUDA/model evidence.

- Review source-lock SHA-256: `3cf523339dfbc8a624402ae1f84d42cfc8a8fe16be9bbfa7f217edb23b15e21b`.
- Notebook: 552,021 bytes; SHA-256 `09964f4287045b6f732ca37071408168274d5f4eb98b74cbdc99117d4954db86`.
- Local evidence: `evidence/phase4-diagnostic-v1-local-review.zip`, SHA-256 `0d15c90c1f64a87e684e5e8b44ca8b357a2a2f6a059aa0613c12287c479079ed`.
- Machine-readable receipt: `reports/phase4_diagnostic_v1_review_receipt.json`.

All frozen v7–v13 source and artifact bindings were verified unchanged. The diagnostic authority gate rejects absent approval, wrong scope, the old eight-hour budget, excessive call limits and retries. It requires a fresh source approval and separately bound one-attempt 3,600-second compute authorization; none exists. Any future launch package must include both approval documents and the matching reservation/claim, and must preserve the frozen review rather than toggle its metadata.

For another CPU-only check in the configured Linux interpreter, use `scripts/run_phase4_diagnostic_local.py --output <new-empty-path>`. This command cannot select live mode.

Phase 4 remains open: one-scorecard/110-distinct-game certification, production `C_admit`, and exact billing reconciliation are unresolved. This diagnostic neither resolves those gates nor authorizes a full pilot, holdout use, scored submission, advanced scheduling change, or subsequent model run.
