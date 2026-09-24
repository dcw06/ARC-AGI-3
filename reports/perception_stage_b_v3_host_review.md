# Stage B R3 supervised-host review

Status: **CPU rehearsal only; GPU disabled; no launch authority or reservation.**
R1 and R2 source snapshots and the completed offline archive remain unchanged.
This revision advances the Stage B host/supervisor code but does not claim a
target GPU lifecycle has run.

The host factory references the pinned model configuration, model-artifact
verification, and offline model-readiness check from the integrated lifecycle.
It is intended to run under a separately pinned model interpreter; that
interpreter and target mount have not been exercised in this revision. Its
server startup replaces that lifecycle's legacy
canary with the single Stage B ACTION6 canary. The canary's attempted,
received, and final states are written through a bounded durable evidence
store; the received response body, hash, request identity, token counts and
finish reason are retained before validation. The bridge publishes readiness
only after the canary passes. The game-side proxy checks the real `ready`
reply, artifact identity, canary evidence, and startup duration before
admitting any study call; tests no longer manually set `started=True`.

The CPU fixture runs host and game worker in an externally owned process
group. It uses the historical monitor's **injected** telemetry and the
historical outer supervisor's monitor-ready handshake, startup-inclusive
deadline, cancellation, and process-group cleanup. A successful rehearsal
completed twelve scripted bridge calls, four actual offline-development game
actions, and read-only independent replay. Startup failure, preexisting
cancellation, and host evidence exhaustion all failed before study admission;
the outer supervisor verified group and scratch cleanup. The test fixture has
no model, GPU or live target capability.

The host module's CLI and the supervisor's CLI both reject live use. The R3
notebook is a private GPU-disabled **source snapshot**, not a launch package.
The candidate 3,600-second provider / 3,300-second internal budget in R2 is
still only a proposal. The exact target package must review installation,
model startup and canary, twelve 120-second maximum study calls, four game
actions, evidence finalization, 300-second cleanup reserve, and a 3,000-second
admission cutoff against actual target telemetry.

## Before any source approval or compute request

1. Bind an actual target entrypoint to this source and to **new Stage B-specific**
   source, compute, and single-reservation records. Historical integrated-v2
   authority cannot authorize this study. Reject missing, mismatched, or
   consumed records before any install, model import, subprocess, or GPU query.
2. Run the game and model under distinct pinned interpreters; route model
   caches to monitored scratch. The external monitor must use real GPU UUID,
   VRAM, RAM, scratch, and sampling-gap checks, and fail closed if it stops or
   its evidence writer exhausts.
3. Bound all process logs and study evidence under a shared target allocation.
   The CPU fixture's standalone trajectory file is not yet an approved live
   evidence writer. Independently check post-termination GPU processes and
   process groups, and retain that receipt even on worker/monitor failure.
4. Re-audit every exact target request with the pinned tokenizer, unpack and
   inspect the launch-enabled notebook, and independently test full target
   startup, cancellation, evidence exhaustion, deadline, and cleanup paths.

No level-solving benefit is claimed. Equal initial visible observations do
not prove hidden-state equality; control-first order and two actions per arm
limit interpretation.
