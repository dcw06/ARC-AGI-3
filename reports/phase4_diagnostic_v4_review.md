# Diagnostic v4 repeat: corrected runtime evaluator

The user requested "Sure launch another GPU run" after review of diagnostic v2
R2's retained results and the v3 offline evaluator correction. This authorizes
one repeat of the same private three-arm diagnostic, not a full pilot or production
certification run. Source preparation and compute authority are recorded separately.

V4 copies the frozen v2 runtime into a new namespace and incorporates the v3
evaluator's four-ULP allowance solely for reconstructed request-window duration.
Actual completion-before-cutoff, absolute cleanup reserve, resource limits,
monitor coverage, token validation and independent cleanup remain strict.
All earlier frozen revisions remain unchanged.

The exact 45 requests are unchanged: 15 initial development observations each
under original examples, relocated examples, and no concrete examples. Model,
temperature, seed, schema and observation content remain unchanged. This is a
repeatability check of example-coordinate sensitivity, not new solving evidence.

Frozen limits: one attempt, 3,600 provider seconds, 3,300 startup-inclusive internal
seconds, installation by 900 seconds, model startup at most 900 seconds,
1,200-second request window capped at first-cell 3,000 seconds, and 300 seconds
reserved for cleanup/finalization. Maximum 45 sequential diagnostic completions
plus one canary, 128 tokens each, 5,888 total completion tokens, zero retries,
zero game actions, scorecards, holdout runs or scored submissions. GPU is private
offline RTX PRO 6000. VRAM 86 GiB, RAM 128 GiB, scratch 4 GiB, mutable evidence
64 MiB; monitoring 0.25-second interval and at most one-second sampling gap.

Bounded response prefix (8,192 bytes), full response hash, byte count, request
identity and observed token counts are retained before validation. Structured
failure evidence survives the model bridge; startup-canary failures survive in
supervisor-owned bounded logs before bridge readiness. One-shot failures do not
retry. Tests include canary/call mismatches, real process bridge retention,
oversized Unicode responses, deadline boundaries, cleanup faults and v2 replay.

Acceptance requires complete inventory, valid responses and counts, monitored and
independent GPU cleanup, process/scratch/dependency/source removal and final
notebook deadline. Download and archive terminal artifacts, independently replay
the same evaluator, and retain quota observations. Aggregate quota is not exact
per-job billing. Phase 4, production C_admit and exact historical billing remain open.
