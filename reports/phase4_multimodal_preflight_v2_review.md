# Multimodal preflight v2: startup observability and deadline repair

This is the proposed successor to v1 review R2 (the previously discussed R3
repair), placed in a new v2 namespace so the failed attempt, source files,
review locks, approvals and consumed reservation remain unchanged. No launch
authority is carried forward.

## Narrow change

The model-startup ceiling is 900 seconds instead of 750. The supervisor, model
service and evaluator agree on that ceiling. The existing bridge already had
a 900-second ceiling. The supervisor still measures from worker release, so
hashing, processor loading, server readiness and the canary share that window;
these are not additional 900-second windows.

The model host emits flushed JSON markers with UTC, monotonic time and PID at
authority, runtime check, artifact hashing, tokenizer verification, mount
inventory, processor load, tokenizer load, server launch, readiness and canary.
Hash progress reports cumulative bytes actually read and files completed at
most once per ten seconds, plus a final total. The artifact-tree-v1 hash format
and pinned expected digest are unchanged. A read that stalls cannot emit new
progress: the last marker identifies the unfinished stage but cannot explain
the underlying storage problem.

The bounded supervisor log reader now uses `read1` rather than waiting for a
full 4 KiB buffer. Small flushed markers reach retained logs promptly. The same
3 MiB per-process log ceiling, evidence limits and fail-closed behavior remain.
Process-group teardown drains the log pipe even when the model never publishes
readiness or worker state. A killed process may have a begin marker without an
end marker; that is evidence of interruption, not proof of its cause.

## Unchanged experiment and interpretation

Exact cases, images, prompts, expected answers and tokenizer expectations are
preserved. Four probes plus one text canary, at most 384 generated tokens,
zero environment actions, zero scorecards, no retries. The outcome evaluator
changes only its startup threshold (and namespace); image acceptance, token
parity, behavioural/arithmetic flags and comparison blocking rules are unchanged.
The text-versus-image comparison remains blocked until target evidence passes
all existing gates. The failed v1 run establishes no image-support finding.

## Budget proposal, not authorization

One fresh 1,800-second provider attempt; 1,680-second startup-inclusive internal
lifecycle, admission cutoff at 1,380 seconds and 300-second cleanup reserve.
Install cap 450 seconds, model startup cap 900 seconds, probe window cap 300
seconds, per-request timeout 120 seconds. The global deadline takes precedence:
these per-stage maxima cannot all be spent in one attempt.

Using the prior roughly 160-second install, 900-second startup, under 60 seconds
for short probes and 300 seconds cleanup gives about 1,420 seconds. This is a
planning estimate, not a guarantee: disk reads and target probe time remain
uncertain. If startup consumes the admission window the attempt stops safely;
there is no automatic extension, budget reuse or retry.

## Local verification and package boundary

`scripts/check_phase4_multimodal_preflight_v2.py` runs the inherited case,
transport, evaluator and authority regressions, plus tests of unchanged hash
identity, progress counts, stage error markers, the new deadline and retained
markers after supervisor-enforced startup timeout and process cleanup. Ten
supervised fixture modes retain the original outcomes and blocking rules.
The checksum-bound fixture archive is replayable without model calls:

```sh
python scripts/check_phase4_multimodal_preflight_v2.py --replay
```

The GPU-disabled, private, offline notebook is
`notebooks/phase4-multimodal-preflight-v2-review-r1/profile.ipynb`. Package review
checks all source hashes, compiles unpacked Python, checks rejection without
authority, and exercises the actual snapshot approval/reservation/packaging
path with synthetic approvals and a fake backend in a temporary directory.
Those fixtures create no real approval, reservation or provider submission.

Source approval and separate fresh 1,800-second compute authorization are
required against the final review lock before a reservation or launch package
is created. No model calls or GPU runs are authorized by this repair. Exact
billing, production certification and Phase 4 remain open.
