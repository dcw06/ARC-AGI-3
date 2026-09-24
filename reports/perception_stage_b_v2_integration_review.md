# Stage B R2 offline integration review

Status: **GPU disabled; no live launch authority or reservation.** This
revision preserves the R1 notebook and the completed CPU archive. It repairs
local process-group cleanup and exercises the two-arm runner through the
historical Unix model bridge with scripted responses. It is not a target
model-host executable.

## Cleanup and bridge findings

The external CPU supervisor now waits for **all live members** of its owned
process group after SIGTERM. If any remain at the grace deadline, it sends
SIGKILL to the group and verifies that no live member remains. A regression
forks a child that ignores SIGTERM, lets the leader exit, and verifies that
cleanup removes the survivor. Zombie-only groups count as terminated because
zombies cannot execute or hold GPU memory; the supervisor retains its separate
temporary-game-removal and scorecard-close evidence. Cleanup errors remain
visible in the monitor record.

`BridgeService` uses the frozen Stage B request guard and the historical
bounded Unix bridge. A single ACTION6 startup canary must pass before the
12-call study allowance opens. The service retains the attempted canary and
the bounded received body, SHA-256, token counts, request hash, and finish
reason **before** token/schema validation; its injected retention callback
must be wired to durable evidence in a target host. A failed canary cannot be
retried on that service. A scripted end-to-end bridge test completes the two
arms and independent replay with twelve study calls. Another test confirms
that a token mismatch crosses the bridge with the received evidence intact.
The model is not loaded by these tests.

R1 remains a historical hash-bound source snapshot. The R2 notebook is a new
GPU-disabled snapshot binding this code and report. The review script checks
R1's embedded hashes without comparing them to newer checkout source, and
checks R2 against the current checkout. Neither contains a launch entrypoint.

## Proposed target envelope, not compute authority

Frozen workload remains two isolated ar25 development episodes, control then
target, two actions each, four dispatches total, twelve study inferences
(policy, sealed prediction, sealed feedback per action), plus one startup
canary. The completion cap is 128 tokens per inference. The pinned local audit
found a 25,798-token maximum exact policy request; a six-frame feedback
request used 59,569 tokens and a seven-frame request exceeded the 65,536
context limit. Every target request still requires the exact pinned-tokenizer
admission check before transport. The 32,768-byte bounded response evidence
cap and archive member hashes remain unchanged.

A **candidate** target reservation is one 3,600-second provider attempt with
a 3,300-second internal deadline and a 300-second cleanup reserve. Allocate
at most 450 seconds for offline installation, 900 seconds for model startup
and canary, and 120 seconds for each of the twelve study calls. Those maxima
sum to 2,790 seconds, leaving 210 seconds before the 3,000-second admission
cutoff for staging, four game actions, evidence writes, and finalization.
This is an engineering envelope to be reviewed against actual target startup
telemetry and resource limits; it is **not** an authorization or proof that
the workload fits. All stages need absolute monotonic deadlines, and no
retry or fallback is permitted.

## Remaining live integration gates

Before approval, build and locally exercise a separate target host and
supervisor that start the pinned model in its isolated environment, wire the
canary callback to bounded durable evidence, expose the bridge to the game
process, monitor GPU/process memory and log/evidence limits, enforce the
startup-inclusive deadline, and independently verify model/game process-group
and GPU cleanup. The supervisor must retain startup failure evidence even if
the bridge never becomes ready. Audit the final notebook's unpacked source,
exact requests, mounts, provider settings, source lock, and authority rejection
paths. A fresh source approval and separate one-attempt compute authorization
and reservation are then required; this R2 review grants none.

Equal canonical initial observations establish visible equality only, not
hidden-state equality. Fixed arm order may confound effects. The sealed audits
measure prediction and interpretation but do not feed answers into subsequent
policy choices. Two actions per arm can locate a grounding or execution break;
zero level progress would not establish a general inability to solve.
