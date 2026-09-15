# Phase 2 diagnostic capture and replay

Status: **V1 capture/replay complete; fresh cd82 reproduction validated**.

Current closure: `config/phase2_closure.json`. The fresh parent runs establish
their own reproduced trajectory; they do not recover missing Phase 1 evidence.
The infrastructure account below describes the earlier capture milestone.

## Captured transition fields

The write-only local recorder captures the raw model proposal or executed
fallback, rejection category, repeated action and post-state counts, action
legality, workspace calls and exhaustion, exact evidence availability,
transport outcome-unknown phase, mechanical progress, and content-addressed
frame/transition references. Records are bounded to 256 transitions per game.

Mechanical progress has one prospective definition:
`grid change OR level increment OR WIN`. A no-change transition additionally
requires identical game state, level counters, legal actions, and final grid.

## Isolation

Diagnostic state is not read by either the R/F representation builders or the
E1 prompt builder. An A/B fixture verifies byte-equivalent model requests and
identical dispatched actions with capture disabled and enabled. Recorder
exceptions are contained and do not interrupt legal play. Game IDs exist only
in local evaluator records and are absent from model messages.

## Replay

`scripts/replay_phase2_diagnostics.py` verifies the bundle hash, every retained
uint8 frame hash, every transition signature, and recomputes changed-cell,
no-change, and progress values. It then groups failures by game, treatment,
and category.

```bash
make phase2-diagnostic-replay DIAGNOSTICS=reports/phase2-diagnostics
```

The causal E1 runners accept `--diagnostics-dir` and write separate bundles;
diagnostics do not alter the experiment result document.

## Exit-gate accounting

A deterministic infrastructure fixture exercises the actual E1S-R policy:
an invalid JSON proposal is rejected, the legal deterministic fallback is
executed, the unchanged transition is retained exactly, and replay reproduces
the failure twice with stable repeated-action and repeated-state counts.

That fixture proves the capture/replay mechanism, but it is not represented as
a retrospective reproduction of a particular Kaggle transition. The existing
Phase 1 downloads retain aggregate game/cell policy-failure counts and zero
scores, but not raw proposals or transition frames. Therefore the historical
Phase 1 transition evidence remains unavailable. The later fresh instrumented
E1S-R runs produced replayable bundles, closing the new diagnostic investigation
with `unsupported_other`. No E2–E4 treatment was admitted.
