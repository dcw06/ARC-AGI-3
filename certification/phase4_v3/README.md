# v3 — acknowledged terminal-state lifecycle handling

This revision resolves the five post-terminal dispatch failure cases found in
the local v2 workload. Preparation v1, the failed v2 result, E1S-R policy code,
the environment package, seeds and 80-action ceilings remain unchanged.

## Cause and prospective amendment

The old loop stopped at WIN but not GAME_OVER. The engine's `perform_action`
returns an empty frame list for non-reset actions after GAME_OVER. That response
fails the strict observation parser, causing a correct quarantine after an
unnecessary post-terminal dispatch. The model schema accepts actions 1–7, not
RESET, so reset was not an available frozen model response.

`TerminalAwareLoop` stops at an acknowledged GAME_OVER before another proposal.
It does not change policy prompts, relax frame validation, fabricate a frame,
retry a quarantined action, or add automatic resets. It finalizes the scorecard
using the existing lifecycle path. This **changes the lifecycle acceptance rule**:
a rendered, journal-bound GAME_OVER is a terminal loss, not a certification
infrastructure failure. `protocol.json` registers that amendment prospectively.
It is not retrospective validation of the earlier failed run.

The v3 evaluator requires the terminal observation, final dispatch audit and
acknowledged journal to agree on state/hash; it rejects post-terminal actions,
missing receipts, ambiguous dispatches and unexplained early termination.
Cancellation still takes precedence and is not relabeled as GAME_OVER.

## Evidence

Two fresh old/new pairs per game, counterbalanced in order, reproduced the cause
on sp80, vc33, s5i5, sc25 and lf52. Across all ten comparisons, v3 preserved the
old run's successful action prefix, omitted only its extra post-GAME_OVER call,
and finalized without quarantine. See `reports/phase4_v3_terminal_reproduction.json`.

The source snapshot was recorded and verified before the new 110-client CPU run.
The independent evaluator passed: **110 acknowledged local scorecard closes,
zero quarantines, 7,722 acknowledged actions**, 35 terminal losses and 75 action
caps. Elapsed time was 27.30 seconds, peak process-group RSS 264,667,136 bytes,
scratch peak 20,005,280 bytes, and verified cleanup 0.023 seconds. Do not interpret
the timing difference from v2 as a controlled throughput improvement.

All 33 targeted terminal, lifecycle, supervisor and evaluator regressions passed.
`reports/phase4_v3_terminal_result.json` binds the evidence archive, which includes
diagnostics, complete run outputs and the snapshotted source. The existing offline
environment/dependency archive remains an explicit separately checksummed input.

```sh
.venv/bin/python certification/phase4_v3/run_local.py \
  --environments /path/to/verified/environment_files \
  --output /path/to/new-output-directory
.venv/bin/python -m unittest tests.test_phase4_terminal tests.test_phase4_integration tests.test_phase4_lifecycle tests.test_phase4 -q
```

Process-table access is required for the local supervisor; missing monitoring
fails closed. Do not edit the snapshotted source for a later run without a new
revision/snapshot. This is a local CPU source freeze, not GPU spending authority.

## Next section

Integrate the actual shared model service with tokenizer/server token parity,
GPU UUID/VRAM monitoring and externally bounded shutdown; then register and
measure a representative real-trajectory capacity design and review the target
notebook. Current completions are scripted, so `C_nominal`/`C_admit` remain null.
No GPU launch, reservation release, model-backed pass or Phase 4 closure occurred.

This remains 110 clients repeating 15 development games with separate scorecards
and one bounded episode each. GAME_OVER means a loss, not successful game solving.
Production reset behavior and the one-scorecard/110-distinct-game lifecycle are
still uncertified. The separate compute proposal has zero authorization, and all
eight prescreen hours remain retained pending accounting.
