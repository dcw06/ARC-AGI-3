# Closed-loop v1 implementation review

This implements the frozen original-prompt versus no-example development protocol.
It is an **early-progress experiment**: 15 paired games, matched environment/request
seed 0, fresh state per arm, and a cap of 20 decisions per episode. Zero completed
levels would not establish that removing examples can never help. No result here
is production certification, a production admission limit, or exact billing evidence.

## Runtime and independent checks

The new `certification/phase4_closed_loop_v1` namespace preserves all historical
source snapshots. Each episode opens its own local OFFLINE scorecard and adapter,
bootstraps once, constructs a new GameRuntimeState, and closes/finalizes in a finally
block. Each acknowledged action supplies the next observation and history. No
historical 110-client inventory gate, fallback controller, later reset, proposal
retry or resampling is used. WIN/GAME_OVER stop naturally; errors stop the attempt.

The fixed 30-episode schedule and exact system texts are loaded from the frozen
protocol. Only the system text is treated differently; subsequent observation
differences are consequences of executed actions. All requests, response prefixes,
hashes, observed token counts, attempts, dispatch journals and lossless observations
are retained. Content-addressed observation blobs avoid repeated frame storage.
Worker records are at most 1 MiB; the shared 128 MiB evidence budget includes atomic
write overhead and per-component reserved failure receipts. Exhaustion fails closed.

Model-side request guards use only standard-library and schema code, preserving
model/game dependency separation. The model service admits at most 600 policy calls
after exactly one canary. A single bridge slot enforces sequential service access.
Validation-failure and late-response evidence survives the bridge; canary evidence
is logged before validation and before bridge readiness. Frozen strict action and
token rules remain in force.

Independent evaluation reconstructs initial state and every subsequent request from
observations/history. It verifies all 15 pairs, schedule/seeds, canonical equality
of paired initial states, response/body hashes, token counts, legal actions,
decision IDs, serialized dispatch hashes, pre/post journal bindings, monotonic
progress counters, terminal reasons, lifecycle receipts, and complete evidence
inventory. It computes level deltas, paired differences, transitions, repetition,
frame/canonical changes and click distributions rather than trusting worker metrics.
The terminal replay separately checks final notebook hashes, source/dependency
removal and the independent GPU-cleanup receipt. Scripted CPU results remain
explicitly non-model evidence.

## Budget and cleanup

The proposed budget remains separate and unchanged: one future private offline
RTX PRO 6000 attempt, 3,600 provider seconds, 3,300 startup-inclusive internal
seconds, 1,200-second workload window ending before first-cell 3,000 seconds,
300-second cleanup reserve, at most 600 decisions plus one canary, and 76,928
maximum completion tokens. Monitoring and independent post-termination GPU cleanup
are inherited from the tested lifecycle. All game files are checksum-verified and
staged into the dependency tree before it is made read-only.

Compute and source approval records are absent by default. Live entry fails before
installation/GPU access without a new source approval and a separate matching
3,600-second reservation with exclusive attempt identity. Historical diagnostic
reservations cannot satisfy the new scope or 601-call/30-episode limits.

## Validation and operational limits

Local tests cover fresh history, isolated state, 600-action ceilings, incomplete
pairs, initial-state mismatch, stale requests, response/action/journal drift,
progress counters, missing finalization, token mismatches, response retention across
a spawned process, evidence exhaustion, deadlines, cancellation and cleanup faults.
An isolated interpreter check prevents game-package imports in the model validator.

The supervised CPU fixture uses native Linux temporary storage and retains an
archive. An initial Windows-mounted output run exceeded its 120-second CPU smoke
limit and correctly canceled/cleaned up; this is retained as a local validation
limitation, not target evidence. Actual local development games are additionally
checked with scripted actions. The initial two-minute engine-check budget stopped
near the final pair; the separate CPU integration check permits five minutes of
work and a six-minute outer alarm. This does not change GPU protocol deadlines.
The final validation receipt records completion status, runtimes and archive hashes.

Notebook review must verify the decompressed sources and entrypoint, compile every
packaged Python file, confirm GPU/internet disabled, and run the no-authority gate
before approval. No model or GPU run is part of this implementation review.

Next gate: explicit source approval of the resulting review lock and **separate**
authorization/reservation of the proposed one-hour attempt. A later launch must
create a fresh package and exclusive claim. Exact billing and production
one-scorecard/110-distinct-game certification remain open.
